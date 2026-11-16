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
