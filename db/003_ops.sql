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
