# EduPath AI database architecture — v0.1

## Tenancy and authorization

- Each student has a global identity in Supabase `auth.users` and a `student_profiles` row keyed to that UUID.
- Institutions are isolated by `institution_id` on programmes, campaigns, leads and applications.
- Membership and permissions live in `institution_staff`. Staff should be invited only by a trusted institution administrator through the backend.
- A student may apply to multiple programmes across multiple institutions.
- The database verifies that an application's programme and intake belong to its institution using composite foreign keys.
- Recruitment leads and campaign attribution cannot point to a campaign outside their institution.
- Document associations verify that the attached document belongs to the applicant.

## Primary relationships

```text
Supabase Auth Users
   ├── student_profiles ─── qualifications
   │        ├── student_documents ─── application_documents
   │        └── applications ─── application_status_events
   │                     └── campaign_attributions
   └── institution_staff ─── institutions
                                    ├── programmes ─── intakes
                                    │       └── programme_requirements
                                    ├── campaigns ─── recruitment_leads
                                    └── audit_events
```

## MVP analytics

- Total leads per campaign: count `recruitment_leads` grouped by `campaign_id`.
- Applications per campaign: count unique applications in `campaign_attributions`, filtered by attribution type.
- Enrolments: count applications with `status='enrolled'`.
- Cost per application = campaign spend / attributed applications, excluding zero denominator.
- Cost per enrolment = campaign spend / attributed enrolments, excluding zero denominator.
- Future work: event-based attribution, campaign impressions/clicks, scheduled budget vs actual spend, detailed funnel stage timestamps, channel connectors and validated statistical forecasts.

## Application decisions

Statuses are declared in the schema, but transitions are validated by the backend. For example:

`draft -> submitted -> in_review -> offered -> accepted -> enrolled`

Other paths include `more_info`, `waitlisted`, `declined` and `withdrawn`.

Insert an `application_status_events` entry and a server-side `audit_events` entry in the same transaction whenever a decision/status changes. An application must keep a server-generated immutable `submission_snapshot` when submitted, so qualification changes later cannot silently alter historical admissions evidence.

## Document storage

`student_documents` stores only a private object path in Supabase Storage. The storage bucket must be private. Uploading, downloading and document approval should be mediated by trusted API routes with ownership checks and expiring signed URLs. The SQL schema does **not** automatically create a Storage bucket or Storage policies.

## Security position

All app tables are RLS-enabled. `anon` can read only verified published catalogue data. `authenticated` can read own student rows and institutions' permitted records. Writes are denied to browser database roles and must come from the trusted backend after authorization. The Supabase service key or database connection string must never appear in `index.html`, the JavaScript bundle, or GitHub. A backend using elevated credentials must implement full authorization; RLS is not a substitute for backend authorization in this design.

Student identity, consent handling for minors, privacy notices, backups, malware scanning, and regulatory compliance must be reviewed before processing real applicant data. The database migration is a foundation, not a certified production system.
