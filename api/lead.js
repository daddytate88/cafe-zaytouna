// api/lead.js — the website posts new enquiries here, the CRM reads them back.
//
// This route is live as soon as the three environment variables below are set
// in Vercel. Until then it answers 503 and says which one is missing, rather
// than failing in a way that looks like the form is broken.
//
// Required in Vercel → Settings → Environment Variables:
//   SUPABASE_URL
//   SUPABASE_SERVICE_ROLE_KEY   <- server only; never put this in a page
//   CRM_READ_TOKEN              <- any long random string
// Optional:
//   SITE_ORIGIN                 <- https://nathancafefloral.com (defaults to *)

import { createClient } from '@supabase/supabase-js';

function missingEnv() {
  return ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'CRM_READ_TOKEN']
    .filter((k) => !process.env[k]);
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', process.env.SITE_ORIGIN || '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();

  const missing = missingEnv();
  if (missing.length) {
    return res.status(503).json({
      error: 'not configured',
      missing,
      hint: 'Set these in Vercel → Settings → Environment Variables, then redeploy.'
    });
  }

  const db = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
  );

  // ---- a visitor submitting an enquiry ----
  if (req.method === 'POST') {
    const L = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    if (!L.name || !(L.email || L.phone)) {
      return res.status(400).json({ error: 'name and an email or phone are required' });
    }
    // payload_id comes from the browser, so a retried submission cannot
    // create a second lead for the same enquiry
    const { data, error } = await db
      .from('leads')
      .upsert(
        {
          payload_id: L.id,
          source: L.source || 'website',
          form: L.form || '',
          lang: L.lang === 'fr' ? 'fr' : 'en',
          name: String(L.name).slice(0, 200),
          email: String(L.email || '').slice(0, 200),
          phone: String(L.phone || '').slice(0, 60),
          event_type: String(L.event_type || '').slice(0, 80),
          event_date: L.event_date || null,
          guests: Number(L.guests) || 0,
          message: String(L.message || '').slice(0, 4000),
          stage: 'new'
        },
        { onConflict: 'payload_id' }
      )
      .select('id')
      .single();

    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json({ ok: true, id: data.id });
  }

  // ---- the CRM collecting them ----
  if (req.method === 'GET') {
    const token = process.env.CRM_READ_TOKEN;
    const sent = (req.headers.authorization || '').replace(/^Bearer\s+/i, '') ||
                 req.query.token || '';
    if (!token || sent !== token) {
      return res.status(401).json({ error: 'unauthorized' });
    }
    const { data, error } = await db
      .from('leads')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(200);
    if (error) return res.status(500).json({ error: error.message });

    // shaped exactly as the CRM's Inbox expects
    return res.status(200).json({
      leads: data.map((r) => ({
        v: 1,
        id: r.payload_id || r.id,
        at: r.created_at,
        source: r.source,
        form: r.form,
        lang: r.lang,
        name: r.name,
        email: r.email,
        phone: r.phone,
        event_type: r.event_type,
        event_date: r.event_date,
        guests: r.guests,
        message: r.message
      }))
    });
  }

  return res.status(405).json({ error: 'method not allowed' });
}
