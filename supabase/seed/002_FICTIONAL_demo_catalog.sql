-- OPTIONAL. Run only in a TEST project after 001_edupath_core.sql.
-- The names and requirements below are FICTIONAL; not verified admissions data.

insert into public.institutions(code,name,institution_type,city,verified,active)
values
 ('TEST-RUZIVO','TEST Ruzivo University (Fictional)','university','Harare',true,true),
 ('TEST-MAVAMBO','TEST Mavambo Polytechnic (Fictional)','polytechnic','Bindura',true,true)
on conflict (code) do nothing;

insert into public.programmes(institution_id,code,title,qualification_level,description,campus,duration_months,fee_amount,published)
select i.id,'BSC-CS','BSc Computer Science','bachelor',
 'Fictional programme for EduPath testing only','Main Campus',48,1200,true
from public.institutions i where i.code='TEST-RUZIVO'
on conflict (institution_id,code) do nothing;

insert into public.programmes(institution_id,code,title,qualification_level,description,campus,duration_months,fee_amount,published)
select i.id,'DIP-IT','Diploma in Information Technology','diploma',
 'Fictional programme for EduPath testing only','Main Campus',36,650,true
from public.institutions i where i.code='TEST-MAVAMBO'
on conflict (institution_id,code) do nothing;

insert into public.intakes(programme_id,institution_id,label,opens_on,closes_on,capacity,status)
select p.id,p.institution_id,'TEST Intake',current_date,current_date+90,100,'open'
from public.programmes p
join public.institutions i on i.id=p.institution_id
where i.code in ('TEST-RUZIVO','TEST-MAVAMBO')
  and not exists (select 1 from public.intakes existing
       where existing.programme_id=p.id and existing.label='TEST Intake');

-- No student identities or applications are seeded. Those will come from Auth and API.
