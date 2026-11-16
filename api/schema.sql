-- Run once in the Supabase SQL editor.

create table if not exists leads (
  id           uuid primary key default gen_random_uuid(),
  payload_id   text unique,                 -- stops a retry creating a duplicate
  source       text default 'website',
  form         text,
  lang         text default 'en',
  name         text not null,
  email        text,
  phone        text,
  event_type   text,
  event_date   date,
  guests       int default 0,
  message      text,
  stage        text default 'new',
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

create index if not exists leads_created_idx on leads (created_at desc);
create index if not exists leads_stage_idx   on leads (stage);

-- The public may submit an enquiry and read nothing back.
-- Reads happen in api/lead.js with the service-role key, never from a browser.
alter table leads enable row level security;

drop policy if exists "anon can submit" on leads;
create policy "anon can submit" on leads for insert to anon with check (true);
