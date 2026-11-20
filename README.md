# EduPath AI — SQLite local demonstration

This is the existing **Tabler Student + Recruiter UI**, linked to a **real, locally stored SQLite database**. It is designed for a short demonstration, not for production admissions.

## Launch

1. Extract the project ZIP. Open the `EduPath_AI_SQLite` directory.
2. Double-click `Start-EduPath-SQLite.bat` (or run `py -3 server.py` in the VS Code terminal).
3. Open `http://127.0.0.1:8765`.
4. Keep the terminal open while using the site.

**Python 3 only. No pip install, Appwrite, Supabase, PostgreSQL, or Node.js required.**

The original Tabler CSS/JS uses a pinned CDN version. If Internet is unavailable, the included fallback CSS still lets you navigate and demonstrate the app. The exact official Tabler appearance requires CDN access or locally installed Tabler assets.

## What works

- Two Tabler portal interfaces with the original navigation and layouts.
- 4 fictional institutions, 10 fictional programmes, 7 sample applications, 4 campaigns.
- Update student profile and qualifications; verify matching results in Student → Smart Recommendations.
- Student → Explore Programmes → choose a programme not already applied for → Apply. Application persists in SQLite.
- Recruiter → Applications → Review → update status. Student sees updated status after returning to Student view.
- Recruiter → Campaigns → Create campaign. Budget and campaign persist in SQLite.
- Recruiter → Analytics shows metrics calculated from the SQLite-backed **fictional seeded campaign records**.
- Student → AI Assistant provides rules-based sample answers. Conversation persists in SQLite.
- CSV exports, comparison, filters, and light/dark theme.
- Audit events, application status history, and a health endpoint for demonstrations.

**Not implemented:** authentic user login, true institutional tenant authorization, document file uploads, external ad tracking, notification delivery, live jobs, production AI or official admission decisions. Role switch is a **demo-only** control. Never enter real student personal information.

## Demo talk-track (~3 minutes)

1. Start at Recruiter Overview — show the application queue and campaign funnel (fictional metrics).
2. Recruiter → Campaign Management → add a new campaign and return to the list.
3. Switch to Student → My Qualifications → change grades → show Smart Recommendations.
4. Student → Explore Programmes → apply to an available programme.
5. Switch to Recruiter → Applications → review and set **Shortlisted**.
6. Switch back to Student → My Applications → see the updated status.
7. Open `http://127.0.0.1:8765/api/health` to show SQLite table counts.

## Database and API

- SQLite: `data/edupath.sqlite3` (copy this file for backup, when the application is stopped).
- Schema: `data/schema.sql` (18 relational tables).
- Fictional seed: `data/seed.json`.
- Server: `server.py` — Python standard library, bound to `127.0.0.1` only.
- APIs: `/api/health`, `/api/bootstrap`, `/api/programmes`, `/api/institutions`, `/api/applications`, `/api/campaigns`, `/api/analytics`, `/api/audit`.
- Frontend changes POST to `/api/state`; the server validates and writes relational records.
- Browser stores only the display mode/page in `sessionStorage`. Student/application/campaign/chat records are stored in SQLite.

To reset sample data, stop the backend and run `RESET-DEMO-DATABASE.bat`. Or type `py -3 server.py --reset` in the project folder.

## VS Code terminal

```powershell
cd "C:\Users\nooklyweb\Documents\Python Projects\EduPath_AI"
py -3 server.py
```

Open http://127.0.0.1:8765.

## Security boundary

This is not a public website and must **not** be exposed to a network or deployed as-is. Recruiter / Student switching is not authenticated. SQLite is a local persistence choice, not a security system. The fictional dataset deliberately does not include real identities or certificates. A production build must add authentication, institutional access checks, encryption and consent controls, verified rules, upload security and automated tests.
