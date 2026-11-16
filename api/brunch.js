// POST /api/brunch — reserve a Saturday brunch seating
// GET  /api/brunch?date=YYYY-MM-DD — remaining seats per seating
import { db, cors, requireEnv, body } from './_db.js';

export default async function handler(req, res) {
  if (cors(req, res)) return;
  if (!requireEnv(res, ['DATABASE_URL'])) return;

  if (req.method === 'GET') {
    const date = String((req.query && req.query.date) || '').slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      return res.status(400).json({ error: 'date=YYYY-MM-DD is required' });
    }
    try {
      const { rows } = await db().query(
        `select seating, capacity, taken, remaining, open
           from brunch_load where service_date = $1 order by seating`, [date]);
      return res.status(200).json({ date, seatings: rows });
    } catch (e) {
      console.error('availability failed', e);
      return res.status(500).json({ error: 'could not read availability' });
    }
  }

  if (req.method === 'POST') {
    const b = body(req);
    const errors = {};
    if (String(b.name || '').trim().length < 2) errors.name = 'required';
    if (!b.email && !b.phone) errors.contact = 'an email or a phone number is required';
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(b.service_date || ''))) errors.service_date = 'invalid';
    if (!String(b.seating || '').trim()) errors.seating = 'required';
    const guests = Number(b.guests);
    if (!Number.isFinite(guests) || guests < 1 || guests > 40) errors.guests = 'invalid';
    if (Object.keys(errors).length) return res.status(400).json({ error: 'validation failed', errors });

    const payload = {
      id: b.id || null, name: b.name, email: b.email || '', phone: b.phone || '',
      lang: b.lang === 'fr' ? 'fr' : 'en',
      service_date: b.service_date, seating: String(b.seating).slice(0, 20),
      guests, notes: String(b.notes || '').slice(0, 2000)
    };

    try {
      const { rows } = await db().query(
        'select reservation_id, res_status, seats_left, was_created from book_brunch($1::jsonb)',
        [JSON.stringify(payload)]
      );
      const r = rows[0];
      // Pending, not confirmed. A submitted form is a request, not a booking.
      return res.status(200).json({
        ok: true, id: r.reservation_id, status: r.res_status,
        seats_left: r.seats_left, duplicate: !r.was_created
      });
    } catch (e) {
      // the capacity check raises check_violation when the seating just filled
      if (e && e.code === '23514') {
        return res.status(409).json({ error: 'seating full', detail: e.message, retry: false });
      }
      console.error('brunch booking failed', e);
      return res.status(500).json({ error: 'could not save the reservation', retry: true });
    }
  }

  return res.status(405).json({ error: 'method not allowed' });
}
