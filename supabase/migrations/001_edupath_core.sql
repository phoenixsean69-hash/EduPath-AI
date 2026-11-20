-- EduPath AI | Supabase PostgreSQL schema | v0.1
-- Apply to a NEW Supabase project in SQL Editor.
-- Schema-only migration. NO user accounts, passwords or real student data.
-- Architecture: Auth identities in auth.users; private writes through a trusted backend.
-- Browser-accessible anon/authenticated roles get SELECT only, protected by RLS.

begin;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

-- App profiles share the UUID assigned by Supabase Auth.
create table public.student_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null check (length(trim(full_name)) > 0),
  applicant_type text not null check (applicant_type in ('tertiary','high_school')),
  birth_date date,
  email_contact text,
  phone text,
  city text,
  preferences jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.institutions (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  institution_type text not null check (institution_type in ('university','polytechnic','college','high_school')),
  city text,
  website text,
  description text,
  verified boolean not null default false,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  constraint institution_code_nonempty check (length(trim(code)) >= 2)
);

create table public.institution_staff (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('institution_admin','recruiter','reviewer','analyst')),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (institution_id, user_id)
);

create table public.student_guardians (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.student_profiles(user_id) on delete cascade,
  guardian_user_id uuid references auth.users(id) on delete set null,
  guardian_name text not null,
  relationship text not null,
  contact_email text,
  contact_phone text,
  consent_recorded_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.qualifications (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.student_profiles(user_id) on delete cascade,
  education_level text not null,
  examination_board text,
  examination_year integer check (examination_year between 1950 and 2100),
  subject text not null,
  grade text not null,
  verification_status text not null default 'unverified'
    check (verification_status in ('unverified','pending','verified','rejected')),
  created_at timestamptz not null default now()
);

create table public.programmes (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  code text not null,
  title text not null,
  qualification_level text not null,
  description text,
  campus text,
  duration_months integer check (duration_months is null or duration_months > 0),
  fee_amount numeric(12,2) check (fee_amount is null or fee_amount >= 0),
  fee_currency char(3) not null default 'USD',
  published boolean not null default false,
  created_at timestamptz not null default now(),
  unique (institution_id, code),
  unique (id, institution_id)
);

create table public.intakes (
  id uuid primary key default gen_random_uuid(),
  programme_id uuid not null,
  institution_id uuid not null,
  label text not null,
  opens_on date not null,
  closes_on date not null,
  capacity integer check (capacity is null or capacity >= 0),
  status text not null default 'planned' check (status in ('planned','open','closed','archived')),
  created_at timestamptz not null default now(),
  check (closes_on >= opens_on),
  foreign key (programme_id,institution_id) references public.programmes(id,institution_id) on delete cascade,
  unique (id,programme_id,institution_id)
);

-- Structured admissions rules. The institution must approve each published rule version.
create table public.programme_requirements (
  id uuid primary key default gen_random_uuid(),
  programme_id uuid not null references public.programmes(id) on delete cascade,
  version integer not null default 1 check (version >= 1),
  rules jsonb not null default '{}'::jsonb,
  active boolean not null default false,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  unique (programme_id, version),
  check (not active or approved_at is not null)
);
create unique index one_active_requirements_per_programme
  on public.programme_requirements(programme_id) where active;

-- Store storage bucket/path only, not actual certificate bytes in PostgreSQL.
create table public.student_documents (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.student_profiles(user_id) on delete cascade,
  document_type text not null,
  storage_bucket text not null default 'student-documents',
  storage_path text not null unique,
  file_name text not null,
  mime_type text,
  uploaded_at timestamptz not null default now(),
  unique (id,student_id)
);

create table public.campaigns (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  name text not null,
  channel text not null,
  tracking_code text not null unique,
  budget_amount numeric(12,2) not null default 0 check (budget_amount >= 0),
  currency char(3) not null default 'USD',
  start_date date,
  end_date date,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  check (end_date is null or start_date is null or end_date >= start_date),
  unique (id,institution_id)
);

create table public.applications (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.student_profiles(user_id) on delete restrict,
  institution_id uuid not null references public.institutions(id) on delete restrict,
  programme_id uuid not null,
  intake_id uuid not null,
  status text not null default 'draft' check (status in
    ('draft','submitted','in_review','more_info','waitlisted','offered','accepted','declined','withdrawn','enrolled')),
  applicant_answers jsonb not null default '{}'::jsonb,
  -- Immutable server-authored copy of qualifications/rules at submission time.
  submission_snapshot jsonb,
  submitted_at timestamptz,
  decided_at timestamptz,
  reviewer_id uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (programme_id,institution_id) references public.programmes(id,institution_id),
  foreign key (intake_id,programme_id,institution_id) references public.intakes(id,programme_id,institution_id),
  unique (student_id,programme_id,intake_id),
  unique (id,student_id),
  unique (id,institution_id),
  check (status = 'draft' or submitted_at is not null)
);

-- Guarantees a document attached to an application belongs to that applicant.
create table public.application_documents (
  application_id uuid not null,
  document_id uuid not null,
  student_id uuid not null,
  attached_at timestamptz not null default now(),
  primary key (application_id,document_id),
  foreign key (application_id,student_id) references public.applications(id,student_id) on delete cascade,
  foreign key (document_id,student_id) references public.student_documents(id,student_id) on delete restrict
);

create table public.application_status_events (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null references public.applications(id) on delete cascade,
  previous_status text,
  new_status text not null,
  public_reason text,
  changed_by uuid references auth.users(id) on delete set null,
  changed_at timestamptz not null default now()
);

create table public.recruitment_leads (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  campaign_id uuid,
  student_id uuid references public.student_profiles(user_id) on delete set null,
  programme_id uuid,
  lead_stage text not null default 'new' check (lead_stage in ('new','contacted','interested','applied','closed')),
  source_label text,
  captured_at timestamptz not null default now(),
  foreign key (campaign_id,institution_id) references public.campaigns(id,institution_id),
  foreign key (programme_id,institution_id) references public.programmes(id,institution_id)
);

-- Attribution is tenant checked: applications cannot be linked to other institutions' campaigns.
create table public.campaign_attributions (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null,
  application_id uuid not null,
  campaign_id uuid not null,
  attribution_type text not null default 'last_touch'
    check (attribution_type in ('first_touch','last_touch','manual')),
  recorded_at timestamptz not null default now(),
  unique (application_id,attribution_type),
  foreign key (application_id,institution_id) references public.applications(id,institution_id) on delete cascade,
  foreign key (campaign_id,institution_id) references public.campaigns(id,institution_id) on delete restrict
);

create table public.recommendation_events (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references public.student_profiles(user_id) on delete cascade,
  programme_id uuid not null references public.programmes(id) on delete cascade,
  eligibility text not null check (eligibility in ('eligible','ineligible','unknown')),
  score numeric(6,3),
  explanation jsonb not null default '{}'::jsonb,
  engine_version text not null,
  created_at timestamptz not null default now()
);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  recipient_user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  message text not null,
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.audit_events (
  id bigint generated always as identity primary key,
  institution_id uuid references public.institutions(id) on delete restrict,
  actor_user_id uuid references auth.users(id) on delete set null,
  action text not null,
  entity_name text not null,
  entity_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now()
);

-- Backend-only write access. This prevents users from promoting themselves
-- to recruiters, inventing admission decisions or editing campaign outcomes.
create or replace function private.is_institution_member(target_institution uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.institution_staff st
    where st.institution_id = target_institution
      and st.user_id = (select auth.uid())
      and st.active = true
  );
$$;

create or replace function private.is_institution_admin(target_institution uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.institution_staff st
    where st.institution_id = target_institution
      and st.user_id = (select auth.uid())
      and st.active = true and st.role = 'institution_admin'
  );
$$;

-- Functions used by RLS must be executable by authenticated members.
grant usage on schema private to authenticated;
revoke all on function private.is_institution_member(uuid) from public;
revoke all on function private.is_institution_admin(uuid) from public;
grant execute on function private.is_institution_member(uuid) to authenticated;
grant execute on function private.is_institution_admin(uuid) to authenticated;

-- Indexes for RLS queries and common application filters.
create index institution_staff_user_idx on public.institution_staff(user_id,institution_id) where active;
create index qualification_student_idx on public.qualifications(student_id);
create index guardians_student_idx on public.student_guardians(student_id);
create index programmes_inst_idx on public.programmes(institution_id,published);
create index intakes_programme_idx on public.intakes(programme_id,status);
create index requirements_programme_idx on public.programme_requirements(programme_id,active);
create index student_documents_owner_idx on public.student_documents(student_id);
create index applications_student_idx on public.applications(student_id,created_at desc);
create index applications_institution_idx on public.applications(institution_id,status,created_at desc);
create index appdocs_student_idx on public.application_documents(student_id);
create index status_events_application_idx on public.application_status_events(application_id,changed_at desc);
create index campaigns_institution_idx on public.campaigns(institution_id,created_at desc);
create index leads_institution_idx on public.recruitment_leads(institution_id,captured_at desc);
create index attributions_institution_idx on public.campaign_attributions(institution_id,campaign_id);
create index recommendations_student_idx on public.recommendation_events(student_id,created_at desc);
create index notifications_owner_idx on public.notifications(recipient_user_id,created_at desc);
create index audits_inst_idx on public.audit_events(institution_id,occurred_at desc);

-- RLS is enabled on EVERY public table; default behaviour is deny.
alter table public.student_profiles enable row level security;
alter table public.institutions enable row level security;
alter table public.institution_staff enable row level security;
alter table public.student_guardians enable row level security;
alter table public.qualifications enable row level security;
alter table public.programmes enable row level security;
alter table public.intakes enable row level security;
alter table public.programme_requirements enable row level security;
alter table public.student_documents enable row level security;
alter table public.campaigns enable row level security;
alter table public.applications enable row level security;
alter table public.application_documents enable row level security;
alter table public.application_status_events enable row level security;
alter table public.recruitment_leads enable row level security;
alter table public.campaign_attributions enable row level security;
alter table public.recommendation_events enable row level security;
alter table public.notifications enable row level security;
alter table public.audit_events enable row level security;

-- Revoke implicit public-schema API permissions. GRANT SELECT only where needed.
revoke all on table
  public.student_profiles,public.institutions,public.institution_staff,
  public.student_guardians,public.qualifications,public.programmes,
  public.intakes,public.programme_requirements,public.student_documents,
  public.campaigns,public.applications,public.application_documents,
  public.application_status_events,public.recruitment_leads,
  public.campaign_attributions,public.recommendation_events,
  public.notifications,public.audit_events
from anon,authenticated;

grant select on public.institutions,public.programmes,public.intakes,
 public.programme_requirements to anon,authenticated;
grant select on public.student_profiles,public.institution_staff,
 public.student_guardians,public.qualifications,public.student_documents,
 public.campaigns,public.applications,public.application_documents,
 public.application_status_events,public.recruitment_leads,
 public.campaign_attributions,public.recommendation_events,
 public.notifications,public.audit_events to authenticated;

-- Institution catalogue and staff-only unpublished records.
create policy institutions_public on public.institutions
  for select to anon,authenticated using (verified and active);
create policy institutions_staff on public.institutions
  for select to authenticated using ((select private.is_institution_member(id)));
create policy programmes_public on public.programmes
  for select to anon,authenticated using (published and exists (
    select 1 from public.institutions i where i.id=institution_id and i.verified and i.active));
create policy programmes_staff on public.programmes
  for select to authenticated using ((select private.is_institution_member(institution_id)));
create policy intakes_public on public.intakes
  for select to anon,authenticated using (exists (
    select 1 from public.programmes p where p.id=programme_id and p.published));
create policy intakes_staff on public.intakes
  for select to authenticated using ((select private.is_institution_member(institution_id)));
create policy requirements_public on public.programme_requirements
  for select to anon,authenticated using (active and exists (
    select 1 from public.programmes p where p.id=programme_id and p.published));
create policy requirements_staff on public.programme_requirements
  for select to authenticated using (exists (
    select 1 from public.programmes p where p.id=programme_id
      and (select private.is_institution_member(p.institution_id))));

-- Student data: self-reads only through Data API; staff reads use trusted backend.
create policy profiles_self on public.student_profiles
  for select to authenticated using (user_id=(select auth.uid()));
create policy qualifications_self on public.qualifications
  for select to authenticated using (student_id=(select auth.uid()));
create policy guardians_student_or_guardian on public.student_guardians
  for select to authenticated using (student_id=(select auth.uid()) or guardian_user_id=(select auth.uid()));
create policy documents_self on public.student_documents
  for select to authenticated using (student_id=(select auth.uid()));
create policy recommendation_self on public.recommendation_events
  for select to authenticated using (student_id=(select auth.uid()));
create policy notifications_self on public.notifications
  for select to authenticated using (recipient_user_id=(select auth.uid()));

-- Applications: each student sees their own; staff sees only submitted
-- applications belonging to institutions where they hold an active role.
create policy applications_student on public.applications
  for select to authenticated using (student_id=(select auth.uid()));
create policy applications_staff on public.applications
  for select to authenticated using (
    status <> 'draft' and (select private.is_institution_member(institution_id)));
create policy appdocs_student on public.application_documents
  for select to authenticated using (student_id=(select auth.uid()));
create policy appstatus_student on public.application_status_events
  for select to authenticated using (exists (
    select 1 from public.applications a
    where a.id=application_id and a.student_id=(select auth.uid())));
create policy appstatus_staff on public.application_status_events
  for select to authenticated using (exists (
    select 1 from public.applications a where a.id=application_id
      and a.status <> 'draft'
      and (select private.is_institution_member(a.institution_id))));

-- Recruiter-only campaign and lead data. No cross-institution access.
create policy staff_self_or_institution_admin on public.institution_staff
  for select to authenticated using (
    user_id=(select auth.uid()) or (select private.is_institution_admin(institution_id)));
create policy campaigns_staff on public.campaigns
  for select to authenticated using ((select private.is_institution_member(institution_id)));
create policy leads_staff on public.recruitment_leads
  for select to authenticated using ((select private.is_institution_member(institution_id)));
create policy attribution_staff on public.campaign_attributions
  for select to authenticated using ((select private.is_institution_member(institution_id)));
create policy audit_admin on public.audit_events
  for select to authenticated using (
    institution_id is not null and (select private.is_institution_admin(institution_id)));

-- No INSERT/UPDATE/DELETE policy is intentionally provided.
-- Only your trusted backend performs writes with its restricted server credentials.
-- Validate JWTs, roles, record ownership, and status transitions in backend API.
-- Never expose service_role key or the PostgreSQL connection string in the frontend.

commit;
