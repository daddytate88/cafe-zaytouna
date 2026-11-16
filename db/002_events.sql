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
