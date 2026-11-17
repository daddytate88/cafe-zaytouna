// A single page that says exactly what is and is not working.
// Reports presence of settings, never their values.
import pg from 'pg';

function scrub(msg) {
  // never echo a connection string back, even inside a driver error
  return String(msg || '')
    .replace(/postgres(?:ql)?:\/\/[^\s"']+/gi, '[connection string hidden]')
    .slice(0, 300);
}

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Type', 'application/json');

  const out = {
    deployed: true,
    settings: {
      DATABASE_URL: !!process.env.DATABASE_URL,
      CRM_READ_TOKEN: !!process.env.CRM_READ_TOKEN,
      CRON_SECRET: !!process.env.CRON_SECRET,
      SITE_ORIGIN: process.env.SITE_ORIGIN || null
    },
    database: { reachable: false, tables: null, note: null }
  };

  const url = process.env.DATABASE_URL;
  if (!url) {
    out.database.note = 'DATABASE_URL is not set on this deployment. ' +
      'Check it is ticked for Production, then push a commit to rebuild.';
    return res.status(200).json(out);
  }

  // surface the shape without revealing anything secret
  out.settings.uses_pooler = url.includes(':6543');
  // the transaction pooler needs the user to be postgres.<project-ref>.
  // A plain "postgres" user fails exactly like a wrong password does.
  var userPart = (url.split('://')[1] || '').split(':')[0] || '';
  out.settings.user_has_project_ref = /^postgres\.[a-z0-9]{8,}$/i.test(userPart);
  if (out.settings.uses_pooler && !out.settings.user_has_project_ref) {
    out.database.note = 'The username in DATABASE_URL should be postgres.<project-ref>, ' +
      'not plain postgres. Copy the string again from the Transaction pooler tab.';
  }
  out.settings.host_ends_with = (url.split('@')[1] || '').split(':')[0]?.slice(-28) || null;
  if (!out.settings.uses_pooler) {
    out.database.note = 'That connection string is not the transaction pooler ' +
      '(it should end in :6543/postgres). The direct connection runs out of sockets.';
  }

  let pool;
  try {
    pool = new pg.Pool({
      connectionString: url, max: 1,
      connectionTimeoutMillis: 7000,
      ssl: { rejectUnauthorized: false }
    });
    const { rows } = await pool.query(
      `select count(*)::int as n from information_schema.tables
        where table_schema='public' and table_type='BASE TABLE'`);
    out.database.reachable = true;
    out.database.tables = rows[0].n;
    if (rows[0].n === 0) {
      out.database.note = 'Connected, but this database has no tables. ' +
        'db/setup.sql was run somewhere else, or against a different project.';
    } else if (rows[0].n < 23) {
      out.database.note = `Connected, but only ${rows[0].n} tables of 23. ` +
        'Run db/setup.sql again — it is safe to re-run.';
    } else {
      out.database.note = 'Everything is connected.';
    }
  } catch (e) {
    out.database.reachable = false;
    out.database.error_code = e.code || null;
    out.database.error = scrub(e.message);
    const m = String(e.message || '');
    if (/password authentication failed/i.test(m))
      out.database.note = 'The password in DATABASE_URL is wrong. If you reset it in ' +
        'Supabase, the string you pasted still has the old one.';
    else if (/ENOTFOUND|EAI_AGAIN/i.test(m))
      out.database.note = 'The host in DATABASE_URL is wrong — copy it again from ' +
        "Supabase's green Connect button, Transaction pooler tab.";
    else if (/ECONNREFUSED|ETIMEDOUT/i.test(m))
      out.database.note = 'Nothing answered at that host and port. Check the project ' +
        'is not paused in Supabase.';
    else if (/does not exist/i.test(m))
      out.database.note = 'Connected, but that database is empty or named differently.';
  } finally {
    if (pool) await pool.end().catch(() => {});
  }

  return res.status(200).json(out);
}
