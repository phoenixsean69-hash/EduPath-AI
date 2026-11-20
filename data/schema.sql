PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS institutions (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
 city TEXT, abbr TEXT, summary TEXT
);
CREATE TABLE IF NOT EXISTS programmes (
 id TEXT PRIMARY KEY,
 institution_id TEXT NOT NULL REFERENCES institutions(id),
 name TEXT NOT NULL, level TEXT NOT NULL, duration TEXT NOT NULL,
 annual_fee_usd REAL NOT NULL DEFAULT 0, career TEXT,
 tags_json TEXT NOT NULL DEFAULT '[]', intake TEXT, capacity INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admission_requirements (
 programme_id TEXT NOT NULL REFERENCES programmes(id), subject TEXT NOT NULL,
 minimum_grade TEXT NOT NULL, PRIMARY KEY (programme_id, subject)
);
CREATE TABLE IF NOT EXISTS students (
 id TEXT PRIMARY KEY, full_name TEXT NOT NULL, email TEXT,
 phone TEXT, city TEXT, interest TEXT,
 avatar_blob BLOB, avatar_mime TEXT, avatar_version INTEGER NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS qualifications (
 student_id TEXT NOT NULL REFERENCES students(id), subject TEXT NOT NULL,
 grade TEXT NOT NULL, PRIMARY KEY (student_id, subject)
);
CREATE TABLE IF NOT EXISTS applications (
 id TEXT PRIMARY KEY,
 student_id TEXT REFERENCES students(id),
 student_name TEXT NOT NULL,
 programme_id TEXT NOT NULL REFERENCES programmes(id),
 institution_id TEXT NOT NULL REFERENCES institutions(id),
 status TEXT NOT NULL CHECK (status IN ('Draft','Submitted','Under Review','Documents Required','Shortlisted','Offer Issued','Accepted','Declined')),
 submitted_date TEXT NOT NULL, source TEXT, internal_note TEXT NOT NULL DEFAULT '',
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS application_status_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, application_id TEXT NOT NULL REFERENCES applications(id),
 from_status TEXT, to_status TEXT NOT NULL, note TEXT, changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS campaigns (
 id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES institutions(id),
 name TEXT NOT NULL, channel TEXT NOT NULL, budget REAL NOT NULL DEFAULT 0,
 spend REAL NOT NULL DEFAULT 0, visits INTEGER NOT NULL DEFAULT 0,
 leads INTEGER NOT NULL DEFAULT 0, applications INTEGER NOT NULL DEFAULT 0,
 offers INTEGER NOT NULL DEFAULT 0, enrolled INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'Draft', start_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS campaign_attributions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id TEXT NOT NULL REFERENCES campaigns(id),
 application_id TEXT REFERENCES applications(id), source TEXT, event_name TEXT NOT NULL,
 event_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS recruitment_leads (
 id INTEGER PRIMARY KEY AUTOINCREMENT, institution_id TEXT NOT NULL REFERENCES institutions(id),
 full_name TEXT NOT NULL, programme_interest TEXT,
 source TEXT, stage TEXT NOT NULL DEFAULT 'New', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chat_messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL REFERENCES students(id),
 role TEXT NOT NULL CHECK(role IN ('assistant','user')), message TEXT NOT NULL,
 sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS guardians (
 id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL REFERENCES students(id),
 name TEXT NOT NULL, relationship TEXT, contact TEXT
);
CREATE TABLE IF NOT EXISTS application_documents (
 id INTEGER PRIMARY KEY AUTOINCREMENT, application_id TEXT NOT NULL REFERENCES applications(id),
 document_type TEXT NOT NULL, file_path TEXT, verified INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS institution_staff (
 id INTEGER PRIMARY KEY AUTOINCREMENT, institution_id TEXT NOT NULL REFERENCES institutions(id),
 staff_name TEXT NOT NULL, role TEXT NOT NULL, email TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT REFERENCES students(id),
 message TEXT NOT NULL, seen INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS institution_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, institution_id TEXT NOT NULL REFERENCES institutions(id),
 title TEXT NOT NULL, starts_at TEXT, location TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, reference_id TEXT,
 description TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS demo_settings (
 key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_programmes_institution ON programmes(institution_id);
CREATE INDEX IF NOT EXISTS idx_app_institution_status ON applications(institution_id, status);
CREATE INDEX IF NOT EXISTS idx_app_programme ON applications(programme_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_institution ON campaigns(institution_id);
CREATE INDEX IF NOT EXISTS idx_status_app ON application_status_events(application_id);
CREATE INDEX IF NOT EXISTS idx_chat_student ON chat_messages(student_id);
