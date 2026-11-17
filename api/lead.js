// POST  /api/lead  — a visitor submits a private-event enquiry
// GET   /api/lead  — the CRM collects enquiries (token required)
import { db, cors, requireEnv, authorised, body, validateLead } from './_db.js';

export default async function handler(req, res) {
  if (cors(req, res)) return;
  if (!requireEnv(res, ['DATABASE_URL'])) return;

  if (req.method === 'POST') {
    const b = body(req);
    const { ok, errors } = validateLead(b);
    if (!ok) return res.status(400).json({ error: 'validation failed', errors });

    const payload = {
      id: b.id || null,
      name: b.name, email: b.email || '', phone: b.phone || '',
      lang: b.lang === 'fr' ? 'fr' : 'en',
      source: ['website', 'ai', 'whatsapp', 'phone', 'walkin', 'manual']
        .includes(b.source) ? b.source : 'website',
      form: String(b.form || '').slice(0, 40),
      event_type: String(b.event_type || '').slice(0, 80),
      event_date: b.event_date || null,
      date_flexible: ['yes', 'no', 'deciding'].includes(b.date_flexible) ? b.date_flexible : null,
      guests: Number(b.guests) || 0,
      budget_band: String(b.budget_band || '').slice(0, 40),
      message: String(b.message || '').slice(0, 4000),
      preferred_channel: ['email', 'phone', 'whatsapp'].includes(b.preferred_channel)
        ? b.preferred_channel : null,
      answers: b.answers && typeof b.answers === 'object' ? b.answers : {},
      // consent is only recorded when the visitor actually ticked the box,
      // and the exact wording they saw is stored with it
      consent: b.consent && b.consent.granted
        ? {
            channel: ['whatsapp', 'email', 'sms'].includes(b.consent.channel)
              ? b.consent.channel : 'whatsapp',
            purpose: 'follow_up',
            granted: true,
            wording: String(b.consent.wording || '').slice(0, 1000),
            version: String(b.consent.version || 'v1').slice(0, 20)
          }
        : null
    };

    try {
      const { rows } = await db().query(
        'select lead_id, contact_id, created from intake_lead($1::jsonb)',
        [JSON.stringify(payload)]
      );
      const r = rows[0];

      // A daily platform cron cannot drive a 30-minute follow-up by itself,
      // so each submission also drains whatever is already due. This is a
      // safety net, not the scheduler: /api/cron/run-jobs is still the
      // reliable path and should be called every minute.
      db().query('select * from claim_jobs($1,$2)', ['inline-drain', 3])
        .catch((e) => console.error('inline drain failed', e));

      // Fire-and-forget email alert to the owner — never blocks the response
      if (!r.created === false) {
        // only on genuinely new leads (created = true)
        sendOwnerEmail(payload).catch((e) => console.error('owner email failed', e));
      }

      // "duplicate: true" means this was a retry of a submission already stored
      return res.status(200).json({
        ok: true, id: r.lead_id, contact_id: r.contact_id, duplicate: !r.created
      });
    } catch (e) {
      console.error('lead intake failed', e);
      // the caller keeps the visitor's answers on screen so nothing is retyped
      return res.status(500).json({ error: 'could not save the enquiry', retry: true });
    }
  }

  if (req.method === 'GET') {
    if (!authorised(req)) return res.status(401).json({ error: 'unauthorized' });
    try {
      const { rows } = await db().query(`
        select l.id, l.payload_id, l.created_at, l.source, l.form, l.language as lang,
               l.event_type, l.event_date, l.guests, l.message, l.status, l.priority, l.score,
               c.full_name as name, c.email, c.phone
          from leads l join contacts c on c.id = l.contact_id
         order by l.created_at desc limit 200`);
      return res.status(200).json({
        leads: rows.map((r) => ({
          v: 1, id: r.payload_id || r.id, at: r.created_at,
          source: r.source, form: r.form, lang: r.lang,
          name: r.name, email: r.email, phone: r.phone,
          event_type: r.event_type,
          event_date: r.event_date ? String(r.event_date).slice(0, 10) : '',
          guests: r.guests, message: r.message,
          status: r.status, priority: r.priority, score: r.score
        }))
      });
    } catch (e) {
      console.error('lead list failed', e);
      return res.status(500).json({ error: 'could not read enquiries' });
    }
  }

  return res.status(405).json({ error: 'method not allowed' });
}

// ── Email alert ───────────────────────────────────────────────────────────────
async function sendOwnerEmail(payload) {
  const apiKey  = process.env.EMAIL_PROVIDER_API_KEY;
  const toEmail = process.env.OWNER_EMAIL;
  if (!apiKey || !toEmail) return; // silently skip if not configured

  const eventDate  = payload.event_date || 'Not specified';
  const eventType  = payload.event_type || 'Not specified';
  const guests     = payload.guests     || 'Not specified';
  const budget     = payload.budget_band || 'Not specified';
  const phone      = payload.phone      || '—';
  const email      = payload.email      || '—';
  const message    = payload.message    || '—';

  const html = `
<div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#222">
  <div style="background:#2d4a3e;padding:24px 32px;border-radius:8px 8px 0 0">
    <h1 style="margin:0;color:#fff;font-size:20px">New Inquiry — Nathan Café Floral</h1>
  </div>
  <div style="background:#f9f9f7;padding:24px 32px;border-radius:0 0 8px 8px;border:1px solid #e5e5e0">
    <table style="width:100%;border-collapse:collapse">
      <tr><td style="padding:8px 0;font-weight:600;width:140px">Name</td><td>${payload.name}</td></tr>
      <tr><td style="padding:8px 0;font-weight:600">Email</td><td>${email}</td></tr>
      <tr><td style="padding:8px 0;font-weight:600">Phone</td><td>${phone}</td></tr>
      <tr><td style="padding:8px 0;font-weight:600">Event type</td><td>${eventType}</td></tr>
      <tr><td style="padding:8px 0;font-weight:600">Event date</td><td>${eventDate}</td></tr>
      <tr><td style="padding:8px 0;font-weight:600">Guests</td><td>${guests}</td></tr>
      <tr><td style="padding:8px 0;font-weight:600">Budget</td><td>${budget}</td></tr>
      <tr><td style="padding:8px 0;font-weight:600;vertical-align:top">Message</td><td>${message}</td></tr>
    </table>
    <div style="margin-top:24px">
      <a href="https://nathan-cafe-floral.vercel.app/crm" style="background:#2d4a3e;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">Open CRM →</a>
    </div>
  </div>
</div>`;

  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: 'Nathan Café Floral <onboarding@resend.dev>',
      to:   [toEmail],
      subject: `New inquiry from ${payload.name} — Nathan Café Floral`,
      html
    })
  });

  if (!resp.ok) {
    const txt = await resp.text().catch(() => '');
    throw new Error(`Resend ${resp.status}: ${txt}`);
  }
}
