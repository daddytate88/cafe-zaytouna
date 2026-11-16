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
