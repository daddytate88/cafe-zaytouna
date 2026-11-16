# Database

Run these in order, once, in the Supabase SQL editor (or `psql -f`):

```
001_init.sql        staff, contacts, leads, answers, activity
002_events.sql      consent, events, guests, RSVP, event pages, brunch
003_ops.sql         conversations, messages, durable jobs, notifications,
                    review requests, knowledge base, integrations, audit
004_functions.sql   upsert_contact, score_lead, intake_lead
005_brunch_jobs.sql book_brunch, claim_jobs, finish_job, follow_up_eligibility
```

Then seed the venue's documented facts:

```sql
insert into knowledge_items (key,label,value,category,approved) values
 ('capacity_seated','Seated capacity','50','venue',true),
 ('brunch_capacity','Places per brunch seating','40','brunch',true),
 ('room_fee','Private room rental','1950','pricing',true),
 ('deposit_pct','Deposit to confirm','30','pricing',true),
 ('damage_deposit','Refundable deposit','250','pricing',true),
 ('balance_due_hours','Balance due before event (hours)','48','pricing',true),
 ('review_url','Review page','https://nathan-cafe-floral-review.vercel.app','marketing',true)
on conflict (key) do nothing;
```

## Why the logic lives in SQL

`intake_lead` and `book_brunch` each run as one transaction. A submission
either produces a contact, a lead, its answers, a consent record, an activity
row, an owner notification and the 30-minute job — or it produces none of them.
There is no state where a lead exists without its follow-up scheduled.

Both take a caller-supplied `id`. A retried submission returns the original
record instead of creating a second one.

## Capacity

`book_brunch` takes `FOR UPDATE` on the seating row before counting seats, so
two simultaneous requests cannot both see the same last places. Verified: ten
concurrent single-seat requests against four remaining seats produced exactly
four reservations and six rejections, with the seating ending full and not
over.

## The scheduler

`scheduled_jobs` is the queue. `claim_jobs` uses `FOR UPDATE SKIP LOCKED`, so
overlapping cron runs never take the same job — verified with two workers
claiming at once: one took all four due jobs, the other took none, zero
double-claims. Jobs survive redeploys because they are rows, not timers.

`follow_up_eligibility` is checked at execution time, not at scheduling time.
It refuses to send when the lead is booked, lost or archived; when the owner
paused automation; when the owner already made contact; when the customer has
replied; or when no messaging permission is on file. Each of those was tested.
