// Shared Postgres access. All business logic lives in SQL functions, so these
// routes stay thin and the rules cannot drift between callers.
import pg from 'pg';

let pool;
export function db() {
  if (!pool) {
    const url = process.env.DATABASE_URL;
    if (!url) throw new Error('DATABASE_URL is not set');
    pool = new pg.Pool({
      connectionString: url,
      max: 1,                       // serverless: one socket per instance
      idleTimeoutMillis: 10_000,
      connectionTimeoutMillis: 8_000,
      ssl: url.includes('localhost') ? false : { rejectUnauthorized: false }
    });
  }
  return pool;
}

export function cors(req, res) {
  res.setHeader('Access-Control-Allow-Origin', process.env.SITE_ORIGIN || '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Vary', 'Origin');
  if (req.method === 'OPTIONS') { res.status(204).end(); return true; }
  return false;
}

export function requireEnv(res, keys) {
  const missing = keys.filter((k) => !process.env[k]);
  if (missing.length) {
    res.status(503).json({
      error: 'not configured',
      missing,
      hint: 'Set these in Vercel → Settings → Environment Variables, then redeploy.'
    });
    return false;
  }
  return true;
}

export function authorised(req) {
  const want = process.env.CRM_READ_TOKEN;
  if (!want) return false;
  const sent = (req.headers.authorization || '').replace(/^Bearer\s+/i, '') ||
               (req.query && req.query.token) || '';
  // length-safe comparison
  if (sent.length !== want.length) return false;
  let diff = 0;
  for (let i = 0; i < want.length; i++) diff |= sent.charCodeAt(i) ^ want.charCodeAt(i);
  return diff === 0;
}

export function body(req) {
  if (!req.body) return {};
  if (typeof req.body === 'string') { try { return JSON.parse(req.body); } catch { return {}; } }
  return req.body;
}

// Server-side validation. The browser's checks are a convenience, not a guard.
export function validateLead(b) {
  const errors = {};
  const name = String(b.name || '').trim();
  const email = String(b.email || '').trim();
  const phone = String(b.phone || '').trim();
  if (name.length < 2) errors.name = 'required';
  if (!email && !phone) errors.contact = 'an email or a phone number is required';
  if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) errors.email = 'invalid';
  if (phone && phone.replace(/\D/g, '').length < 10) errors.phone = 'invalid';
  const guests = Number(b.guests);
  if (b.guests !== undefined && b.guests !== '' && (!Number.isFinite(guests) || guests < 0 || guests > 2000))
    errors.guests = 'invalid';
  if (b.event_date && !/^\d{4}-\d{2}-\d{2}$/.test(b.event_date)) errors.event_date = 'invalid';
  if (b.lang && !['en', 'fr'].includes(b.lang)) errors.lang = 'invalid';
  return { ok: Object.keys(errors).length === 0, errors };
}
