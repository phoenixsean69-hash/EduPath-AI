# EduPath AI — SQLite demonstration UI specification

The existing student and recruiter screens retain their Tabler design and sidebar navigation. They now load institution, programme, qualification, application and campaign records from a local SQLite backend through `server.py`.

**Student:** Dashboard, Profile, Qualifications, Institutions, Programmes, Recommendations, Compare, Applications, Assistant, Deadlines, Notifications, Career Pathways.

**Recruiter:** Overview, Applicant CRM, Applications, Programmes, Admissions, Campaigns, Audience Segments, Communications, Events, Recruitment Analytics, Campaign Analytics, Smart Insights, Reports, Team, Settings.

Working persistence: profile/grades, applications, review changes, campaigns, chat. Static/read-only sample areas: events, institutional publication, team permissions, actual messaging, document uploads. Campaign performance numbers are fictional seeded data and not live advertising events. There is no real authentication; role switching is only for presenting both views.

Frontend: `index.html`, `css/`, `js/app.js` (original Tabler UI language).
Backend: `server.py` (Python built-in HTTP server + `sqlite3`).
Database: `data/edupath.sqlite3`, initial schema `data/schema.sql`.
