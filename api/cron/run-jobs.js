// The durable scheduler's tick. Vercel Cron calls this every minute.
//
// Nothing here depends on a browser being open or a function staying warm:
// jobs live in Postgres, are claimed with SKIP LOCKED so overlapping runs
// cannot take the same job twice, and survive redeploys.
import { db, requireEnv } from '../_db.js';

const WORKER = `vercel-${Math.random().toString(36).slice(2, 8)}`;

export default async function handler(req, res) {
  // Vercel Cron sends this header; a stray public request must not run jobs
  const secret = process.env.CRON_SECRET;
  if (secret) {
    const sent = (req.headers.authorization || '').replace(/^Bearer\s+/i, '');
    if (sent !== secret) return res.status(401).json({ error: 'unauthorized' });
  }
  if (!requireEnv(res, ['DATABASE_URL'])) return;

  const pool = db();
  const done = [];

  try {
    const { rows: jobs } = await pool.query('select * from claim_jobs($1, $2)', [WORKER, 15]);

    for (const job of jobs) {
      try {
        if (job.kind === 'lead_follow_up') {
          done.push(await leadFollowUp(pool, job));
        } else if (job.kind === 'review_request') {
          done.push(await reviewRequest(pool, job));
        } else {
          await pool.query('select finish_job($1,$2,$3)', [job.id, 'failed', 'unknown job kind']);
          done.push({ id: job.id, outcome: 'unknown_kind' });
        }
      } catch (e) {
        await pool.query('select finish_job($1,$2,$3)', [job.id, 'failed', String(e.message).slice(0, 500)]);
        done.push({ id: job.id, outcome: 'error', detail: String(e.message).slice(0, 200) });
      }
    }
    return res.status(200).json({ claimed: jobs.length, results: done });
  } catch (e) {
    console.error('job runner failed', e);
    return res.status(500).json({ error: 'job runner failed' });
  }
}

async function leadFollowUp(pool, job) {
  const leadId = job.payload.lead_id;

  const { rows: [elig] } = await pool.query(
    'select ok, reason, send_channel from follow_up_eligibility($1)', [leadId]);

  // The owner call task is created whether or not a message may be sent —
  // a lead with no messaging permission still needs a human to ring them.
  await pool.query(`
    insert into event_tasks (lead_id, contact_id, title, detail, priority, due_at, reason)
    select $1, l.contact_id,
           'Call ' || c.full_name,
           coalesce(nullif(c.phone,''),'no number on file') || ' · ' ||
             coalesce(nullif(l.event_type,''),'enquiry') ||
             case when l.event_date is not null then ' · ' || to_char(l.event_date,'DD Mon YYYY') else '' end ||
             case when l.guests > 0 then ' · ' || l.guests || ' guests' else '' end,
           case when l.priority = 'high_priority' then 'urgent' else 'high' end,
           now(),
           '30 minutes after the enquiry arrived and it had not been picked up'
      from leads l join contacts c on c.id = l.contact_id
     where l.id = $1
       and l.status in ('new_inquiry','follow_up_due','owner_call_required')
       and not exists (select 1 from event_tasks t
                        where t.lead_id = $1 and t.status = 'open'
                          and t.title like 'Call %')`, [leadId]);

  if (!elig.ok) {
    await pool.query(
      `insert into follow_up_attempts (job_id, lead_id, channel, outcome, detail)
       values ($1,$2,'none','skipped',$3)`, [job.id, leadId, elig.reason]);
    await pool.query('select finish_job($1,$2,$3)', [job.id, 'done', elig.reason]);
    return { id: job.id, outcome: 'skipped', reason: elig.reason };
  }

  // A channel is eligible, but nothing can actually be sent until the
  // provider is connected. Record that honestly rather than claiming a send.
  const canSend = elig.send_channel === 'whatsapp'
    ? Boolean(process.env.WHATSAPP_ACCESS_TOKEN && process.env.WHATSAPP_PHONE_NUMBER_ID)
    : Boolean(process.env.EMAIL_PROVIDER_API_KEY);

  if (!canSend) {
    await pool.query(
      `insert into follow_up_attempts (job_id, lead_id, channel, outcome, detail)
       values ($1,$2,$3,'blocked','provider not connected')`,
      [job.id, leadId, elig.send_channel]);
    await pool.query(`
      insert into owner_notifications (kind, title, body, lead_id, severity)
      values ('follow_up_manual','Follow-up is due and must be sent by hand',
              'The customer agreed to be contacted, but no messaging provider is connected yet.',
              $1,'warn')`, [leadId]);
    await pool.query('select finish_job($1,$2,$3)', [job.id, 'done', 'provider not connected']);
    return { id: job.id, outcome: 'owner_task_only', channel: elig.send_channel };
  }

  // Sending is implemented in api/whatsapp.js / api/email.js once credentials exist.
  await pool.query(
    `insert into follow_up_attempts (job_id, lead_id, channel, outcome, detail)
     values ($1,$2,$3,'pending_send','queued for the provider')`,
    [job.id, leadId, elig.send_channel]);
  await pool.query('select finish_job($1,$2,$3)', [job.id, 'done', 'queued']);
  return { id: job.id, outcome: 'queued', channel: elig.send_channel };
}

async function reviewRequest(pool, job) {
  const { rows: [r] } = await pool.query(
    `select rr.id, rr.channel, rr.status, e.status as event_status
       from review_requests rr left join events e on e.id = rr.event_id
      where rr.id = $1`, [job.payload.review_id]);

  if (!r) { await pool.query('select finish_job($1,$2,$3)', [job.id, 'done', 'request gone']);
            return { id: job.id, outcome: 'gone' }; }

  // a cancelled or rescheduled event must never trigger a thank-you
  if (r.event_status && r.event_status !== 'completed') {
    await pool.query(
      `update review_requests set status='cancelled', reason='event is no longer completed' where id=$1`,
      [r.id]);
    await pool.query('select finish_job($1,$2,$3)', [job.id, 'done', 'event not completed']);
    return { id: job.id, outcome: 'cancelled' };
  }
  if (!r.channel) {
    await pool.query(
      `update review_requests set status='skipped', reason='no messaging permission' where id=$1`, [r.id]);
    await pool.query('select finish_job($1,$2,$3)', [job.id, 'done', 'no permission']);
    return { id: job.id, outcome: 'skipped' };
  }
  await pool.query('select finish_job($1,$2,$3)', [job.id, 'done', 'queued']);
  return { id: job.id, outcome: 'queued' };
}
