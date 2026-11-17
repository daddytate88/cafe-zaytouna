-- =====================================================================
-- Nathan Café Floral — complete database setup
--
-- Paste this whole file into the Supabase SQL editor and press Run, once.
-- It creates every table, view and function, then loads the venue's own
-- figures. Running it twice is safe: nothing is dropped and nothing is
-- duplicated.
-- =====================================================================

-- ------------------- 001_init.sql -------------------
-- =====================================================================
-- Nathan Café Floral — core schema
-- PostgreSQL 15+. Timestamps are stored in UTC; scheduling and display
-- convert to America/Montreal at the edges.
-- =====================================================================

create extension if not exists pgcrypto;

-- ---------- staff ----------
create table if not exists staff_profiles (
  id            uuid primary key default gen_random_uuid(),
  auth_user_id  uuid unique,                       -- Supabase auth.users.id
  email         text not null unique,
  full_name     text not null default '',
  role          text not null default 'staff'
                check (role in ('owner','manager','staff')),
  active        boolean not null default true,
  created_at    timestamptz not null default now()
);

-- ---------- customers ----------
-- One person, however many enquiries. Dedup keys are generated columns so
-- the database enforces uniqueness rather than the application remembering to.
create table if not exists contacts (
  id            uuid primary key default gen_random_uuid(),
  full_name     text not null,
  email         text,
  phone         text,
  email_key     text generated always as (nullif(lower(trim(email)),'')) stored,
  phone_key     text generated always as
                  (nullif(right(regexp_replace(coalesce(phone,''),'\D','','g'),10),'')) stored,
  language      text not null default 'en' check (language in ('en','fr')),
  preferred_channel text check (preferred_channel in ('email','phone','whatsapp')),
  notes         text not null default '',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create unique index if not exists contacts_email_uq on contacts (email_key) where email_key is not null;
create unique index if not exists contacts_phone_uq on contacts (phone_key) where phone_key is not null;

-- ---------- leads ----------
create table if not exists leads (
  id              uuid primary key default gen_random_uuid(),
  payload_id      text unique,            -- browser-generated; makes retries idempotent
  contact_id      uuid not null references contacts(id) on delete cascade,
  source          text not null default 'website'
                  check (source in ('website','ai','whatsapp','phone','walkin','manual')),
  form            text not null default '',
  language        text not null default 'en' check (language in ('en','fr')),
  event_type      text not null default '',
  event_date      date,
  date_flexible   text check (date_flexible in ('yes','no','deciding')),
  guests          integer not null default 0 check (guests >= 0),
  budget_band     text,
  message         text not null default '',
  preferences     text not null default '',
  status          text not null default 'new_inquiry' check (status in (
                    'new_inquiry','awaiting_customer','follow_up_due','owner_call_required',
                    'contacted','qualified','needs_review','tour_scheduled','proposal_sent',
                    'negotiation','booked','lost','archived')),
  priority        text not null default 'needs_review' check (priority in (
                    'high_priority','qualified','needs_review','budget_mismatch','incomplete')),
  score           integer not null default 0,
  assigned_to     uuid references staff_profiles(id) on delete set null,
  lost_reason     text,
  last_interaction_at timestamptz,
  next_follow_up_at   timestamptz,
  automation_paused   boolean not null default false,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index if not exists leads_status_idx   on leads (status);
create index if not exists leads_created_idx  on leads (created_at desc);
create index if not exists leads_contact_idx  on leads (contact_id);
create index if not exists leads_followup_idx on leads (next_follow_up_at) where next_follow_up_at is not null;

-- every answer as given, so the original enquiry is never lost to later edits
create table if not exists lead_answers (
  id         uuid primary key default gen_random_uuid(),
  lead_id    uuid not null references leads(id) on delete cascade,
  question   text not null,
  answer     text not null default '',
  position   integer not null default 0
);
create index if not exists lead_answers_lead_idx on lead_answers (lead_id);

create table if not exists lead_activities (
  id         uuid primary key default gen_random_uuid(),
  lead_id    uuid references leads(id) on delete cascade,
  contact_id uuid references contacts(id) on delete cascade,
  actor      text not null default 'system',
  kind       text not null,
  detail     text not null default '',
  meta       jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists lead_activities_lead_idx on lead_activities (lead_id, created_at desc);

-- ------------------- 002_events.sql -------------------
-- =====================================================================
-- Consent, events, guests, brunch, conversations
-- =====================================================================

-- ---------- consent (Law 25 / CASL evidence) ----------
-- Append-only: a withdrawal is a new row, never an edit, so the history
-- of what was agreed and when stays intact.
create table if not exists consent_records (
  id              uuid primary key default gen_random_uuid(),
  contact_id      uuid not null references contacts(id) on delete cascade,
  channel         text not null check (channel in ('email','whatsapp','sms','phone')),
  purpose         text not null default 'transactional',
  granted         boolean not null,
  wording         text not null,
  wording_version text not null default 'v1',
  source_form     text not null default '',
  language        text not null default 'en',
  recorded_at     timestamptz not null default now()
);
create index if not exists consent_contact_idx on consent_records (contact_id, channel, recorded_at desc);

-- current state of a permission, newest row wins
create or replace view consent_current as
select distinct on (contact_id, channel, purpose)
       contact_id, channel, purpose, granted, wording_version, recorded_at
from consent_records
order by contact_id, channel, purpose, recorded_at desc;

-- ---------- events ----------
create table if not exists events (
  id            uuid primary key default gen_random_uuid(),
  lead_id       uuid references leads(id) on delete set null,
  contact_id    uuid not null references contacts(id) on delete cascade,
  title         text not null default '',
  event_type    text not null default '',
  event_date    date,
  start_time    time,
  end_time      time,
  guests        integer not null default 0,
  status        text not null default 'confirmed'
                check (status in ('tentative','confirmed','completed','cancelled')),
  completed_at  timestamptz,
  cancelled_at  timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists events_date_idx   on events (event_date);
create index if not exists events_status_idx on events (status);

create table if not exists event_tasks (
  id          uuid primary key default gen_random_uuid(),
  event_id    uuid references events(id) on delete cascade,
  lead_id     uuid references leads(id) on delete cascade,
  contact_id  uuid references contacts(id) on delete cascade,
  title       text not null,
  detail      text not null default '',
  priority    text not null default 'normal' check (priority in ('low','normal','high','urgent')),
  due_at      timestamptz,
  assigned_to uuid references staff_profiles(id) on delete set null,
  status      text not null default 'open' check (status in ('open','done','cancelled')),
  reason      text not null default '',
  completed_at timestamptz,
  created_at  timestamptz not null default now()
);
create index if not exists event_tasks_status_idx on event_tasks (status, due_at);

create table if not exists event_guests (
  id          uuid primary key default gen_random_uuid(),
  event_id    uuid not null references events(id) on delete cascade,
  full_name   text not null,
  email       text,
  party_size  integer not null default 1,
  created_at  timestamptz not null default now()
);

create table if not exists rsvps (
  id          uuid primary key default gen_random_uuid(),
  event_id    uuid not null references events(id) on delete cascade,
  guest_id    uuid references event_guests(id) on delete cascade,
  response    text not null check (response in ('yes','no','maybe')),
  party_size  integer not null default 1,
  dietary     text not null default '',
  responded_at timestamptz not null default now()
);

create table if not exists event_pages (
  id            uuid primary key default gen_random_uuid(),
  event_id      uuid not null unique references events(id) on delete cascade,
  slug          text not null unique,
  access_token  text not null unique default encode(gen_random_bytes(24),'hex'),
  published     boolean not null default false,
  theme         jsonb not null default '{}'::jsonb,
  sections      jsonb not null default '[]'::jsonb,
  rsvp_deadline date,
  revoked_at    timestamptz,
  created_at    timestamptz not null default now()
);

-- ---------- brunch ----------
create table if not exists brunch_services (
  id         uuid primary key default gen_random_uuid(),
  service_date date not null,
  seating    text not null,
  capacity   integer not null default 40 check (capacity >= 0),
  open       boolean not null default true,
  unique (service_date, seating)
);

create table if not exists brunch_reservations (
  id          uuid primary key default gen_random_uuid(),
  payload_id  text unique,
  service_id  uuid not null references brunch_services(id) on delete cascade,
  contact_id  uuid not null references contacts(id) on delete cascade,
  guests      integer not null check (guests > 0),
  notes       text not null default '',
  status      text not null default 'pending'
              check (status in ('pending','confirmed','cancelled','seated','no_show')),
  cancelled_at timestamptz,
  created_at  timestamptz not null default now()
);
create index if not exists brunch_res_service_idx on brunch_reservations (service_id, status);

-- seats actually taken, cancellations excluded
create or replace view brunch_load as
select s.id as service_id, s.service_date, s.seating, s.capacity, s.open,
       coalesce(sum(r.guests) filter (where r.status in ('pending','confirmed','seated')),0)::int as taken,
       s.capacity - coalesce(sum(r.guests) filter (where r.status in ('pending','confirmed','seated')),0)::int as remaining
from brunch_services s
left join brunch_reservations r on r.service_id = s.id
group by s.id;

-- ------------------- 003_ops.sql -------------------
-- =====================================================================
-- Conversations, durable jobs, notifications, reviews, knowledge, audit
-- =====================================================================

create table if not exists conversations (
  id          uuid primary key default gen_random_uuid(),
  contact_id  uuid references contacts(id) on delete cascade,
  lead_id     uuid references leads(id) on delete set null,
  channel     text not null check (channel in ('whatsapp','website','email','note')),
  external_id text,
  ai_paused   boolean not null default false,
  assigned_to uuid references staff_profiles(id) on delete set null,
  status      text not null default 'open' check (status in ('open','resolved')),
  last_message_at timestamptz,
  created_at  timestamptz not null default now(),
  unique (channel, external_id)
);

create table if not exists messages (
  id           uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id) on delete cascade,
  direction    text not null check (direction in ('in','out')),
  author       text not null default 'customer' check (author in ('customer','ai','staff','system')),
  body         text not null default '',
  provider_id  text,
  payload      jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  unique (provider_id)
);
create index if not exists messages_conv_idx on messages (conversation_id, created_at);

create table if not exists message_deliveries (
  id          uuid primary key default gen_random_uuid(),
  message_id  uuid not null references messages(id) on delete cascade,
  status      text not null check (status in ('queued','sent','delivered','read','failed')),
  reason      text not null default '',
  at          timestamptz not null default now()
);

-- ---------- durable scheduler ----------
-- Survives redeploys because it lives in the database, not in a timer.
-- dedupe_key makes "schedule this once" actually mean once.
create table if not exists scheduled_jobs (
  id          uuid primary key default gen_random_uuid(),
  kind        text not null,
  dedupe_key  text not null unique,
  run_at      timestamptz not null,
  payload     jsonb not null default '{}'::jsonb,
  status      text not null default 'pending'
              check (status in ('pending','running','done','cancelled','failed')),
  attempts    integer not null default 0,
  last_error  text not null default '',
  locked_at   timestamptz,
  locked_by   text,
  created_at  timestamptz not null default now(),
  finished_at timestamptz
);
create index if not exists jobs_due_idx on scheduled_jobs (status, run_at)
  where status in ('pending','running');

create table if not exists follow_up_attempts (
  id        uuid primary key default gen_random_uuid(),
  job_id    uuid references scheduled_jobs(id) on delete set null,
  lead_id   uuid references leads(id) on delete cascade,
  channel   text not null,
  outcome   text not null,
  detail    text not null default '',
  at        timestamptz not null default now()
);

create table if not exists owner_notifications (
  id         uuid primary key default gen_random_uuid(),
  kind       text not null,
  title      text not null,
  body       text not null default '',
  lead_id    uuid references leads(id) on delete cascade,
  event_id   uuid references events(id) on delete cascade,
  severity   text not null default 'info' check (severity in ('info','warn','error')),
  read_at    timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists notif_unread_idx on owner_notifications (created_at desc) where read_at is null;

create table if not exists review_requests (
  id           uuid primary key default gen_random_uuid(),
  event_id     uuid references events(id) on delete cascade,
  reservation_id uuid references brunch_reservations(id) on delete cascade,
  contact_id   uuid not null references contacts(id) on delete cascade,
  channel      text,
  consent_basis text not null default '',
  scheduled_for timestamptz not null,
  sent_at      timestamptz,
  provider_id  text,
  status       text not null default 'scheduled'
               check (status in ('scheduled','sent','delivered','failed','skipped','cancelled')),
  reason       text not null default '',
  review_url   text not null default '',
  created_at   timestamptz not null default now(),
  constraint review_target check (event_id is not null or reservation_id is not null)
);
create unique index if not exists review_once_per_event on review_requests (event_id)
  where event_id is not null and status <> 'cancelled';

create table if not exists knowledge_items (
  id          uuid primary key default gen_random_uuid(),
  key         text not null unique,
  label       text not null,
  value       text not null default '',
  category    text not null default 'general',
  approved    boolean not null default false,   -- unapproved facts are never quoted by the AI
  updated_by  uuid references staff_profiles(id) on delete set null,
  updated_at  timestamptz not null default now()
);

create table if not exists integration_settings (
  id          uuid primary key default gen_random_uuid(),
  key         text not null unique,
  state       text not null default 'not_configured'
              check (state in ('not_configured','configured_untested','connected','error')),
  detail      text not null default '',
  last_tested_at timestamptz,
  updated_at  timestamptz not null default now()
);

create table if not exists audit_logs (
  id         uuid primary key default gen_random_uuid(),
  actor      text not null default 'system',
  action     text not null,
  entity     text not null default '',
  entity_id  uuid,
  meta       jsonb not null default '{}'::jsonb,
  at         timestamptz not null default now()
);
create index if not exists audit_at_idx on audit_logs (at desc);

-- keep updated_at honest without the application having to remember
create or replace function touch_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end $$ language plpgsql;

do $$ declare t text;
begin
  foreach t in array array['contacts','leads','events'] loop
    execute format('drop trigger if exists %I_touch on %I', t, t);
    execute format('create trigger %I_touch before update on %I
                    for each row execute function touch_updated_at()', t, t);
  end loop;
end $$;

-- ------------------- 004_functions.sql -------------------
-- =====================================================================
-- Server-side operations. Each one is a single transaction so a partial
-- write is impossible, and each is idempotent on a caller-supplied key.
-- =====================================================================

create or replace function upsert_contact(
  p_name text, p_email text, p_phone text, p_language text default 'en',
  p_channel text default null
) returns uuid as $$
declare
  v_email text := nullif(lower(trim(coalesce(p_email,''))),'');
  v_phone text := nullif(right(regexp_replace(coalesce(p_phone,''),'\D','','g'),10),'');
  v_id uuid;
begin
  select id into v_id from contacts
   where (v_email is not null and email_key = v_email)
      or (v_phone is not null and phone_key = v_phone)
   order by created_at limit 1;

  if v_id is null then
    insert into contacts (full_name, email, phone, language, preferred_channel)
    values (coalesce(nullif(trim(p_name),''),'Unnamed contact'), p_email, p_phone,
            case when p_language='fr' then 'fr' else 'en' end, p_channel)
    returning id into v_id;
  else
    -- fill gaps, never overwrite something already known
    update contacts set
      full_name = case when trim(coalesce(full_name,''))='' or full_name='Unnamed contact'
                       then coalesce(nullif(trim(p_name),''), full_name) else full_name end,
      email     = coalesce(nullif(email,''), nullif(trim(p_email),'')),
      phone     = coalesce(nullif(phone,''), nullif(trim(p_phone),'')),
      language  = case when p_language in ('en','fr') then p_language else language end,
      preferred_channel = coalesce(p_channel, preferred_channel)
    where id = v_id;
  end if;
  return v_id;
end $$ language plpgsql;


-- Transparent scoring. Every component is visible so the owner can see why
-- a lead ranked where it did, and nothing is auto-rejected.
create or replace function score_lead(
  p_event_type text, p_guests int, p_budget text, p_date date, p_complete int
) returns table (score int, priority text) as $$
declare s int := 0;
begin
  s := s + case lower(coalesce(p_event_type,''))
             when 'wedding' then 30 when 'engagement' then 22
             when 'corporate' then 20 else 12 end;
  s := s + case
             when p_guests between 20 and 50 then 25
             when p_guests between 10 and 19 then 15
             when p_guests > 50 then 5
             else 8 end;
  s := s + case coalesce(p_budget,'')
             when '15000+' then 30 when '10000-15000' then 25
             when '7500-10000' then 18 when '5000-7500' then 12
             else 6 end;
  s := s + case when p_date is not null and p_date > current_date then 10 else 4 end;
  s := s + least(p_complete,5);

  return query select s,
    case
      when p_guests > (select coalesce(nullif(value,'')::int,50) from knowledge_items
                        where key='capacity_seated') then 'needs_review'
      when coalesce(p_budget,'') in ('not_sure','discuss','') then 'needs_review'
      when p_budget in ('5000-7500') and s < 60 then 'budget_mismatch'
      when s >= 85 then 'high_priority'
      when s >= 65 then 'qualified'
      else 'needs_review'
    end;
end $$ language plpgsql;


-- The whole website submission, atomically.
create or replace function intake_lead(p jsonb)
returns table (lead_id uuid, contact_id uuid, created boolean) as $$
declare
  v_payload text := nullif(p->>'id','');
  v_lead uuid; v_contact uuid; v_score int; v_priority text; v_complete int := 0;
  v_follow_at timestamptz;
  k text; v text;
begin
  -- a retried submission returns the original record instead of making a second
  if v_payload is not null then
    select l.id, l.contact_id into v_lead, v_contact from leads l where l.payload_id = v_payload;
    if v_lead is not null then
      return query select v_lead, v_contact, false; return;
    end if;
  end if;

  v_contact := upsert_contact(p->>'name', p->>'email', p->>'phone',
                              coalesce(p->>'lang','en'), nullif(p->>'preferred_channel',''));

  foreach k in array array['name','email','phone','event_type','event_date','guests','message'] loop
    if coalesce(p->>k,'') <> '' then v_complete := v_complete + 1; end if;
  end loop;

  select s.score, s.priority into v_score, v_priority
  from score_lead(p->>'event_type', coalesce((p->>'guests')::int,0),
                  nullif(p->>'budget_band',''), nullif(p->>'event_date','')::date, v_complete) s;

  insert into leads (payload_id, contact_id, source, form, language, event_type, event_date,
                     date_flexible, guests, budget_band, message, status, priority, score)
  values (v_payload, v_contact, coalesce(nullif(p->>'source',''),'website'),
          coalesce(p->>'form',''), case when p->>'lang'='fr' then 'fr' else 'en' end,
          coalesce(p->>'event_type',''), nullif(p->>'event_date','')::date,
          nullif(p->>'date_flexible',''), coalesce((p->>'guests')::int,0),
          nullif(p->>'budget_band',''), coalesce(p->>'message',''),
          'new_inquiry', v_priority, v_score)
  returning id into v_lead;

  -- the enquiry exactly as it was answered
  for k, v in select key, value from jsonb_each_text(coalesce(p->'answers','{}'::jsonb)) loop
    insert into lead_answers (lead_id, question, answer) values (v_lead, k, v);
  end loop;

  -- consent is recorded separately and only when actually given
  if (p->'consent') is not null then
    insert into consent_records (contact_id, channel, purpose, granted, wording,
                                 wording_version, source_form, language)
    values (v_contact, coalesce(p->'consent'->>'channel','whatsapp'),
            coalesce(p->'consent'->>'purpose','follow_up'),
            coalesce((p->'consent'->>'granted')::boolean,false),
            coalesce(p->'consent'->>'wording',''),
            coalesce(p->'consent'->>'version','v1'),
            coalesce(p->>'form',''), coalesce(p->>'lang','en'));
  end if;

  insert into lead_activities (lead_id, contact_id, actor, kind, detail)
  values (v_lead, v_contact, 'system', 'created',
          'Enquiry received from ' || coalesce(nullif(p->>'source',''),'website'));

  insert into owner_notifications (kind, title, body, lead_id, severity)
  values ('new_lead',
          'New ' || coalesce(nullif(p->>'event_type',''),'event') || ' enquiry',
          coalesce(p->>'name','Someone') || ' — ' || v_priority || ' (score ' || v_score || ')',
          v_lead, case when v_priority='high_priority' then 'warn' else 'info' end);

  -- the 30-minute follow-up, durable and scheduled once
  v_follow_at := now() + interval '30 minutes';
  insert into scheduled_jobs (kind, dedupe_key, run_at, payload)
  values ('lead_follow_up', 'lead_follow_up:' || v_lead::text, v_follow_at,
          jsonb_build_object('lead_id', v_lead, 'contact_id', v_contact))
  on conflict (dedupe_key) do nothing;

  update leads set next_follow_up_at = v_follow_at where id = v_lead;

  insert into audit_logs (actor, action, entity, entity_id, meta)
  values ('system','lead.intake','leads', v_lead, jsonb_build_object('source', p->>'source'));

  return query select v_lead, v_contact, true;
end $$ language plpgsql;

-- ------------------- 005_brunch_jobs.sql -------------------
-- =====================================================================
-- Brunch booking and the job runner. Both have to be safe when two
-- requests arrive at the same instant.
-- =====================================================================

drop function if exists book_brunch(jsonb);
create function book_brunch(p jsonb)
returns table (reservation_id uuid, res_status text, seats_left int, was_created boolean) as $$
declare
  v_payload text := nullif(p->>'id','');
  v_date date := nullif(p->>'service_date','')::date;
  v_seating text := nullif(p->>'seating','');
  v_guests int := coalesce((p->>'guests')::int,0);
  v_service uuid; v_cap int; v_taken int; v_contact uuid;
  v_res uuid; v_status text; v_open boolean;
begin
  if v_guests <= 0 then raise exception 'guests must be at least 1'; end if;
  if v_date is null or v_seating is null then
    raise exception 'service_date and seating are required'; end if;

  -- a retried submission returns the original booking
  if v_payload is not null then
    select r.id, r.status, r.service_id into v_res, v_status, v_service
      from brunch_reservations r where r.payload_id = v_payload;
    if v_res is not null then
      select bl.remaining into v_cap from brunch_load bl where bl.service_id = v_service;
      return query select v_res, v_status, v_cap, false; return;
    end if;
  end if;

  insert into brunch_services (service_date, seating, capacity)
  values (v_date, v_seating,
          coalesce((select nullif(ki.value,'')::int from knowledge_items ki
                     where ki.key='brunch_capacity'),40))
  on conflict (service_date, seating) do nothing;

  -- FOR UPDATE serialises concurrent bookings on this seating: the second
  -- request waits here and then re-reads the true count
  select bs.id, bs.capacity, bs.open into v_service, v_cap, v_open
    from brunch_services bs
   where bs.service_date = v_date and bs.seating = v_seating
   for update;

  if not v_open then raise exception 'that seating is closed'; end if;

  select coalesce(sum(r.guests),0) into v_taken
    from brunch_reservations r
   where r.service_id = v_service
     and r.status in ('pending','confirmed','seated');

  if v_taken + v_guests > v_cap then
    raise exception 'only % seats left for % %', v_cap - v_taken, v_date, v_seating
      using errcode = 'check_violation';
  end if;

  v_contact := upsert_contact(p->>'name', p->>'email', p->>'phone', coalesce(p->>'lang','en'));

  insert into brunch_reservations (payload_id, service_id, contact_id, guests, notes, status)
  values (v_payload, v_service, v_contact, v_guests, coalesce(p->>'notes',''), 'pending')
  returning id into v_res;

  insert into owner_notifications (kind, title, body, severity)
  values ('brunch_reservation',
          'Brunch request - ' || to_char(v_date,'DD Mon') || ' ' || v_seating,
          coalesce(p->>'name','Someone') || ' - ' || v_guests || ' guests - awaiting confirmation',
          'info');

  insert into audit_logs (actor, action, entity, entity_id)
  values ('system','brunch.book','brunch_reservations', v_res);

  return query select v_res, 'pending'::text, (v_cap - v_taken - v_guests), true;
end $$ language plpgsql;


-- Claim due jobs. SKIP LOCKED means two runners never take the same job,
-- which matters because serverless crons can overlap.
create or replace function claim_jobs(p_worker text, p_limit int default 10)
returns setof scheduled_jobs as $$
  update scheduled_jobs j set
    status = 'running', locked_at = now(), locked_by = p_worker, attempts = j.attempts + 1
  where j.id in (
    select id from scheduled_jobs
     where status = 'pending' and run_at <= now()
     order by run_at
     for update skip locked
     limit p_limit)
  returning j.*;
$$ language sql;

create or replace function finish_job(p_id uuid, p_status text, p_error text default '')
returns void as $$
  update scheduled_jobs
     set status = p_status, last_error = coalesce(p_error,''),
         finished_at = now(), locked_at = null, locked_by = null
   where id = p_id;
$$ language sql;

-- Everything that must be true before an automated follow-up may go out.
drop function if exists follow_up_eligibility(uuid);
create or replace function follow_up_eligibility(p_lead uuid)
returns table (ok boolean, reason text, send_channel text) as $$
declare l record; c_wa boolean; c_em boolean;
begin
  select * into l from leads where id = p_lead;
  if not found then return query select false,'lead no longer exists',null::text; return; end if;
  if l.status in ('booked','lost','archived') then
    return query select false,'lead already '||l.status,null::text; return; end if;
  if l.automation_paused then
    return query select false,'automation paused by the owner',null::text; return; end if;
  if l.status in ('contacted','awaiting_customer','tour_scheduled','proposal_sent','negotiation') then
    return query select false,'owner has already made contact',null::text; return; end if;
  if exists (select 1 from messages m
               join conversations cv on cv.id = m.conversation_id
              where cv.lead_id = p_lead and m.direction='in'
                and m.created_at > l.created_at) then
    return query select false,'customer has replied',null::text; return; end if;

  -- cc.* qualified: 'channel' is also an OUT parameter name here
  select cc.granted into c_wa from consent_current cc
    where cc.contact_id = l.contact_id and cc.channel = 'whatsapp'
      and cc.purpose in ('follow_up','marketing','transactional') limit 1;
  select cc.granted into c_em from consent_current cc
    where cc.contact_id = l.contact_id and cc.channel = 'email' limit 1;

  if coalesce(c_wa,false) then return query select true,''::text,'whatsapp'::text; return; end if;
  if coalesce(c_em,false) then return query select true,''::text,'email'::text; return; end if;
  return query select false,'no messaging permission on file',null::text;
end $$ language plpgsql;

-- =====================================================================
-- The venue's documented facts. Every quote and reply is built from these.
-- =====================================================================
insert into knowledge_items (key,label,value,category,approved) values
 ('capacity_seated','Seated capacity','50','venue',true),
 ('brunch_capacity','Places per brunch seating','40','brunch',true),
 ('brunch_seatings','Brunch seatings','10:00, 12:15','brunch',true),
 ('room_fee','Private room rental','1950','pricing',true),
 ('deposit_pct','Deposit to confirm','30','pricing',true),
 ('damage_deposit','Refundable deposit','250','pricing',true),
 ('balance_due_hours','Balance due before event (hours)','48','pricing',true),
 ('balloons_from','Balloon styling from','300','pricing',true),
 ('address','Address','1350 Mazurette, Suite 103, Montréal, Québec','contact',true),
 ('phone','Phone','+1 514-815-9117','contact',true),
 ('email','Email','Info@nathancafefloral.com','contact',true),
 ('review_url','Review page','https://nathan-cafe-floral-review.vercel.app','marketing',true)
on conflict (key) do nothing;

-- what the integrations page will show until each one is actually connected
insert into integration_settings (key,state,detail) values
 ('database','connected','Set up with this script'),
 ('email','not_configured','Needs EMAIL_PROVIDER_API_KEY'),
 ('whatsapp','not_configured','Needs the Meta WhatsApp credentials'),
 ('ai','not_configured','Needs OPENAI_API_KEY behind a server route')
on conflict (key) do nothing;

-- =====================================================================
-- A quick check. Expect: 23 tables, 2 views, 12 knowledge items.
-- =====================================================================
select
  (select count(*) from information_schema.tables
    where table_schema='public' and table_type='BASE TABLE') as tables,
  (select count(*) from information_schema.views where table_schema='public') as views,
  (select count(*) from knowledge_items) as knowledge_items;
