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
