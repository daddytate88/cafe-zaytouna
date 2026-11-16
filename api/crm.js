// The CRM's single endpoint.
//   GET  /api/crm  — everything the dashboard needs, in one round trip
//   POST /api/crm  — one mutation at a time, named by `action`
// Both require CRM_READ_TOKEN. This is the owner's data; nothing here is public.
import { db, cors, requireEnv, authorised, body } from './_db.js';

const STATUSES = ['new_inquiry','awaiting_customer','follow_up_due','owner_call_required',
  'contacted','qualified','needs_review','tour_scheduled','proposal_sent','negotiation',
  'booked','lost','archived'];

export default async function handler(req, res) {
  if (cors(req, res)) return;
  if (!requireEnv(res, ['DATABASE_URL'])) return;
  if (!authorised(req)) return res.status(401).json({ error: 'unauthorized' });

  const pool = db();

  if (req.method === 'GET') {
    try {
      const [leads, tasks, notifs, events, reviews, brunch, stats] = await Promise.all([
        pool.query(`
          select l.id, l.payload_id, l.created_at, l.updated_at, l.source, l.form,
                 l.language, l.event_type, l.event_date, l.date_flexible, l.guests,
                 l.budget_band, l.message, l.status, l.priority, l.score,
                 l.next_follow_up_at, l.automation_paused, l.lost_reason,
                 c.id as contact_id, c.full_name, c.email, c.phone, c.notes as contact_notes,
                 coalesce(ce.granted,false) as consent_email,
                 coalesce(cw.granted,false) as consent_whatsapp
            from leads l
            join contacts c on c.id = l.contact_id
            left join consent_current ce on ce.contact_id = c.id and ce.channel='email'
            left join consent_current cw on cw.contact_id = c.id and cw.channel='whatsapp'
           order by l.created_at desc limit 500`),
        pool.query(`
          select t.id, t.lead_id, t.title, t.detail, t.priority, t.due_at, t.status, t.reason
            from event_tasks t where t.status='open' order by t.due_at nulls last limit 200`),
        pool.query(`
          select id, kind, title, body, lead_id, severity, read_at, created_at
            from owner_notifications order by created_at desc limit 120`),
        pool.query(`
          select e.id, e.lead_id, e.title, e.event_type, e.event_date, e.start_time,
                 e.guests, e.status, c.full_name
            from events e join contacts c on c.id = e.contact_id
           order by e.event_date nulls last limit 200`),
        pool.query(`
          select r.id, r.status, r.channel, r.scheduled_for, r.sent_at, r.reason,
                 c.full_name, e.title as event_title
            from review_requests r
            join contacts c on c.id = r.contact_id
            left join events e on e.id = r.event_id
           order by r.scheduled_for desc limit 120`),
        pool.query(`
          select b.service_date, b.seating, b.capacity, b.taken, b.remaining,
                 (select count(*) from brunch_reservations r
                   where r.service_id = b.service_id and r.status <> 'cancelled') as bookings
            from brunch_load b
           where b.service_date >= current_date - 7
           order by b.service_date, b.seating limit 60`),
        pool.query(`
          select
            (select count(*) from leads where status='new_inquiry')                  as new_inquiries,
            (select count(*) from leads where status not in ('booked','lost','archived')) as open_leads,
            (select count(*) from leads where status='booked')                       as booked,
            (select count(*) from leads where priority='high_priority'
                and status not in ('booked','lost','archived'))                      as high_priority,
            (select count(*) from event_tasks where status='open'
                and due_at <= now())                                                 as calls_due,
            (select count(*) from owner_notifications where read_at is null)         as unread,
            (select count(*) from events where status='confirmed'
                and event_date >= current_date)                                      as upcoming_events,
            (select count(*) from review_requests)                                   as reviews_total,
            (select count(*) from review_requests where status='scheduled')          as reviews_scheduled,
            (select count(*) from review_requests where status in ('sent','delivered')) as reviews_sent,
            (select count(*) from review_requests where status in ('skipped','failed','cancelled')) as reviews_blocked,
            (select count(*) from brunch_reservations where status<>'cancelled')     as brunch_total`)
      ]);

      const notesRes = await pool.query(`
        select lead_id, detail, created_at, actor from lead_activities
         where kind='note' order by created_at desc limit 400`);

      return res.status(200).json({
        ok: true,
        fetched_at: new Date().toISOString(),
        leads: leads.rows,
        tasks: tasks.rows,
        notifications: notifs.rows,
        events: events.rows,
        reviews: reviews.rows,
        brunch: brunch.rows,
        notes: notesRes.rows,
        stats: stats.rows[0]
      });
    } catch (e) {
      console.error('crm read failed', e);
      return res.status(500).json({ error: 'could not read the workspace' });
    }
  }

  if (req.method === 'POST') {
    const b = body(req);
    try {
      switch (b.action) {
        case 'lead.stage': {
          if (!STATUSES.includes(b.status)) return res.status(400).json({ error: 'unknown status' });
          await pool.query('update leads set status=$2 where id=$1', [b.id, b.status]);
          await pool.query(
            `insert into lead_activities (lead_id, actor, kind, detail)
             values ($1,'owner','stage',$2)`, [b.id, 'Moved to ' + b.status]);
          // booking a lead creates the event the calendar shows
          if (b.status === 'booked') {
            await pool.query(`
              insert into events (lead_id, contact_id, title, event_type, event_date, guests, status)
              select l.id, l.contact_id, c.full_name || ' — ' || coalesce(nullif(l.event_type,''),'Event'),
                     l.event_type, l.event_date, l.guests, 'confirmed'
                from leads l join contacts c on c.id=l.contact_id
               where l.id=$1 and not exists (select 1 from events e where e.lead_id=l.id)`, [b.id]);
          }
          if (b.status === 'completed' || b.status === 'booked') {
            await pool.query(`update events set status=$2 where lead_id=$1 and $2='completed'`,
              [b.id, b.status]);
          }
          return res.status(200).json({ ok: true });
        }
        case 'lead.update': {
          const f = b.fields || {};
          await pool.query(`
            update leads set
              event_type   = coalesce($2, event_type),
              event_date   = coalesce($3::date, event_date),
              guests       = coalesce($4::int, guests),
              budget_band  = coalesce($5, budget_band),
              message      = coalesce($6, message),
              next_follow_up_at = coalesce($7::timestamptz, next_follow_up_at),
              automation_paused = coalesce($8::boolean, automation_paused),
              lost_reason  = coalesce($9, lost_reason)
            where id=$1`,
            [b.id, f.event_type ?? null, f.event_date || null, f.guests ?? null,
             f.budget_band ?? null, f.message ?? null, f.next_follow_up_at || null,
             f.automation_paused ?? null, f.lost_reason ?? null]);
          return res.status(200).json({ ok: true });
        }
        case 'contact.update': {
          const f = b.fields || {};
          await pool.query(`
            update contacts set
              full_name = coalesce($2, full_name),
              email     = coalesce($3, email),
              phone     = coalesce($4, phone),
              language  = coalesce($5, language),
              notes     = coalesce($6, notes)
            where id=$1`,
            [b.id, f.full_name ?? null, f.email ?? null, f.phone ?? null,
             f.language ?? null, f.notes ?? null]);
          return res.status(200).json({ ok: true });
        }
        case 'note.add': {
          if (!String(b.body || '').trim()) return res.status(400).json({ error: 'empty note' });
          await pool.query(`
            insert into lead_activities (lead_id, contact_id, actor, kind, detail)
            select $1, l.contact_id, 'owner', 'note', $2 from leads l where l.id=$1`,
            [b.id, String(b.body).slice(0, 4000)]);
          return res.status(200).json({ ok: true });
        }
        case 'task.done': {
          await pool.query(
            `update event_tasks set status='done', completed_at=now() where id=$1`, [b.id]);
          return res.status(200).json({ ok: true });
        }
        case 'task.snooze': {
          await pool.query(
            `update event_tasks set due_at = now() + ($2 || ' minutes')::interval where id=$1`,
            [b.id, String(Number(b.minutes) || 60)]);
          return res.status(200).json({ ok: true });
        }
        case 'notif.read': {
          if (b.all) await pool.query('update owner_notifications set read_at=now() where read_at is null');
          else await pool.query('update owner_notifications set read_at=now() where id=$1', [b.id]);
          return res.status(200).json({ ok: true });
        }
        case 'brunch.status': {
          await pool.query('update brunch_reservations set status=$2 where id=$1',
            [b.id, ['pending','confirmed','cancelled','seated','no_show'].includes(b.status)
              ? b.status : 'pending']);
          return res.status(200).json({ ok: true });
        }
        default:
          return res.status(400).json({ error: 'unknown action' });
      }
    } catch (e) {
      console.error('crm write failed', e);
      return res.status(500).json({ error: 'could not save that change' });
    }
  }

  return res.status(405).json({ error: 'method not allowed' });
}
