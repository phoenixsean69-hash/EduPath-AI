"""EduPath AI local SQLite demonstration backend.

Python standard library only. Starts on http://127.0.0.1:8765 and is NOT a production server.
The Student / Recruiter switch is a demonstrator, not authentication.
"""
from __future__ import annotations
import csv
import io
import json
import os
import sqlite3
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DB = DATA / 'edupath.sqlite3'
PORT = int(os.environ.get('EDUPATH_PORT', '8765'))
LOCK = threading.RLock()
DEMO_STUDENT_ID = 'student-demo-001'


def conn():
    db = sqlite3.connect(DB, timeout=15)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=10000')
    db.row_factory = sqlite3.Row
    return db


@contextmanager
def managed_conn():
    db=conn()
    try:
        with db:
            yield db
    finally:
        db.close()

def j(v):
    return json.dumps(v, separators=(',', ':'), ensure_ascii=False)


def audit(db, kind, ref, description):
    db.execute('INSERT INTO audit_events(kind, reference_id, description) VALUES (?, ?, ?)',
               (kind, ref, description))


def create_schema(db):
    db.executescript((DATA / 'schema.sql').read_text(encoding='utf-8'))
    # Non-destructive migration: existing demo data and uploaded photos are preserved.
    cols = {row['name'] for row in db.execute('PRAGMA table_info(students)')}
    if 'avatar_blob' not in cols:
        db.execute('ALTER TABLE students ADD COLUMN avatar_blob BLOB')
    if 'avatar_mime' not in cols:
        db.execute('ALTER TABLE students ADD COLUMN avatar_mime TEXT')
    if 'avatar_version' not in cols:
        db.execute('ALTER TABLE students ADD COLUMN avatar_version INTEGER NOT NULL DEFAULT 0')


def seed(db):
    """Fictional seed data, matching the already approved Tabler UI."""
    d = json.loads((DATA / 'seed.json').read_text(encoding='utf-8'))
    for inst in d['institutions']:
        db.execute('INSERT INTO institutions(id,name,type,city,abbr,summary) VALUES (?,?,?,?,?,?)',
                   tuple(inst[k] for k in ['id','name','type','city','abbr','summary']))
    for p in d['programmes']:
        db.execute('''INSERT INTO programmes(id,institution_id,name,level,duration,annual_fee_usd,
            career,tags_json,intake,capacity) VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (p['id'],p['inst'],p['name'],p['level'],p['duration'],p['fee'],p['career'],j(p['tags']),p['intake'],p['capacity']))
        for subject, grade in p['subjects'].items():
            db.execute('INSERT INTO admission_requirements(programme_id,subject,minimum_grade) VALUES (?,?,?)',
                       (p['id'],subject,grade))
    profile = {'name':'Tariro Moyo','email':'tariro@example.test','phone':'+263 000 000 000','city':'Harare','interest':'Technology'}
    db.execute('INSERT INTO students(id,full_name,email,phone,city,interest) VALUES (?,?,?,?,?,?)',
               (DEMO_STUDENT_ID,*profile.values()))
    for subject, grade in {'Mathematics':'B','Physics':'C','English':'B','Chemistry':'C'}.items():
        db.execute('INSERT INTO qualifications(student_id,subject,grade) VALUES (?,?,?)',
                   (DEMO_STUDENT_ID,subject,grade))
    for a in d['initialApplications']:
        db.execute('''INSERT INTO applications(id,student_id,student_name,programme_id,institution_id,
            status,submitted_date,source,internal_note) VALUES (?,?,?,?,?,?,?,?,?)''',
            (a['id'], DEMO_STUDENT_ID if a['student']==profile['name'] else None,a['student'],a['programme'],a['inst'],a['status'],a['submitted'],a['source'],a['note']))
        audit(db,'seed_application',a['id'],'Fictional application created')
    for c in d['initialCampaigns']:
        db.execute('''INSERT INTO campaigns(id,institution_id,name,channel,budget,spend,visits,leads,
            applications,offers,enrolled,status,start_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (c['id'],'northbridge',c['name'],c['channel'],c['budget'],c['spend'],c['visits'],c['leads'],
             c['applications'],c['offers'],c['enrolled'],c['status'],c['start']))
    db.execute('INSERT INTO chat_messages(student_id,role,message) VALUES (?,?,?)',
               (DEMO_STUDENT_ID,'assistant','Hello! I can explain sample programmes, entry rules, and application steps. How can I help?'))
    db.execute('INSERT INTO demo_settings(key,value) VALUES (?,?)',('version','sqlite-demo-v1'))
    audit(db,'demo_initialized','system','Created fictional demonstration data')


def initialize(reset=False):
    DATA.mkdir(parents=True, exist_ok=True)
    with LOCK:
        if reset and DB.exists():
            DB.unlink()
        with managed_conn() as db:
            create_schema(db)
            n=db.execute('SELECT COUNT(*) FROM institutions').fetchone()[0]
            if n==0:
                seed(db)
            db.commit()


def list_institutions(db):
    return [dict(r) for r in db.execute('SELECT id,name,type,city,abbr,summary FROM institutions ORDER BY rowid')]


def list_programmes(db):
    rows=[]
    for r in db.execute('SELECT * FROM programmes ORDER BY rowid'):
        p=dict(r)
        rows.append({
            'id':p['id'],'inst':p['institution_id'],'name':p['name'],'level':p['level'],
            'duration':p['duration'],'fee':p['annual_fee_usd'],'career':p['career'],
            'tags':json.loads(p['tags_json']),'intake':p['intake'],'capacity':p['capacity'],
            'subjects':{x['subject']:x['minimum_grade'] for x in db.execute(
                'SELECT subject,minimum_grade FROM admission_requirements WHERE programme_id=?',(p['id'],))}
        })
    return rows


def list_applications(db):
    return [{
        'id':r['id'],'student':r['student_name'],'programme':r['programme_id'],
        'inst':r['institution_id'],'status':r['status'],'submitted':r['submitted_date'],
        'source':r['source'] or 'Direct','note':r['internal_note'] or ''
    } for r in db.execute('SELECT * FROM applications ORDER BY rowid DESC')]


def list_campaigns(db):
    return [{
        'id':r['id'],'name':r['name'],'channel':r['channel'],'budget':r['budget'],
        'spend':r['spend'],'visits':r['visits'],'leads':r['leads'],'applications':r['applications'],
        'offers':r['offers'],'enrolled':r['enrolled'],'status':r['status'],'start':r['start_date']
    } for r in db.execute('SELECT * FROM campaigns ORDER BY rowid DESC')]


def snapshot(db):
    s=db.execute('SELECT full_name,email,phone,city,interest,avatar_blob,avatar_version FROM students WHERE id=?',(DEMO_STUDENT_ID,)).fetchone()
    state={
        'profile':{'name':s['full_name'],'email':s['email'],'phone':s['phone'],'city':s['city'],'interest':s['interest'],
                   'hasAvatar':s['avatar_blob'] is not None,'avatarVersion':s['avatar_version']},
        'grades':{r['subject']:r['grade'] for r in db.execute('SELECT subject,grade FROM qualifications WHERE student_id=?',(DEMO_STUDENT_ID,))},
        'applications':list_applications(db),'campaigns':list_campaigns(db),
        'chat':[{'role':r['role'],'text':r['message']} for r in db.execute(
            'SELECT role,message FROM chat_messages WHERE student_id=? ORDER BY id',(DEMO_STUDENT_ID,))]
    }
    return {'institutions':list_institutions(db),'programmes':list_programmes(db),'state':state,'backend':'sqlite','demo':True}

ALLOWED_STATUSES={'Draft','Submitted','Under Review','Documents Required','Shortlisted','Offer Issued','Accepted','Declined'}


def save_state(db, data):
    if not isinstance(data,dict): raise ValueError('Invalid state object')
    profile=data.get('profile',{})
    if not isinstance(profile,dict) or not profile.get('name'):
        raise ValueError('Student name is required')
    db.execute('''UPDATE students SET full_name=?,email=?,phone=?,city=?,interest=?,updated_at=CURRENT_TIMESTAMP
        WHERE id=?''',(
        str(profile['name'])[:120],str(profile.get('email',''))[:200],
        str(profile.get('phone',''))[:100],str(profile.get('city',''))[:100],
        str(profile.get('interest',''))[:150],DEMO_STUDENT_ID))
    grades=data.get('grades',{})
    if not isinstance(grades,dict):raise ValueError('Invalid grades')
    db.execute('DELETE FROM qualifications WHERE student_id=?',(DEMO_STUDENT_ID,))
    for subject, grade in grades.items():
        if str(grade).upper() not in 'ABCDEF' or not 1<=len(str(grade))<=1:continue
        db.execute('INSERT INTO qualifications(student_id,subject,grade) VALUES (?,?,?)',
                   (DEMO_STUDENT_ID,str(subject)[:100],str(grade).upper()))
    submitted_apps=data.get('applications',[])
    if not isinstance(submitted_apps,list) or len(submitted_apps)>3000:
        raise ValueError('Invalid number of applications')
    for a in submitted_apps:
        if not isinstance(a,dict) or a.get('status') not in ALLOWED_STATUSES:continue
        pid=str(a.get('programme',''))
        row=db.execute('SELECT institution_id FROM programmes WHERE id=?',(pid,)).fetchone()
        if row is None:continue
        inst=row['institution_id'] # derives tenant from programme, never trusts frontend field
        id_=str(a.get('id',''))[:64]
        if not id_:continue
        previous=db.execute('SELECT status,internal_note FROM applications WHERE id=?',(id_,)).fetchone()
        full_name=str(a.get('student',''))[:120] or 'Unnamed applicant'
        values=(id_,DEMO_STUDENT_ID if full_name==profile['name'] else None,
                full_name,pid,inst,a['status'],str(a.get('submitted',''))[:20],
                str(a.get('source','Direct'))[:80],str(a.get('note',''))[:1000])
        if previous is None:
            db.execute('''INSERT INTO applications(id,student_id,student_name,programme_id,institution_id,
                status,submitted_date,source,internal_note) VALUES (?,?,?,?,?,?,?,?,?)''',values)
            audit(db,'application_created',id_,'Demo application created')
            db.execute('''INSERT INTO application_status_events(application_id,from_status,to_status,note)
                VALUES (?,NULL,?,?)''',(id_,a['status'],a.get('note','')))
        else:
            db.execute('''UPDATE applications SET student_id=?,student_name=?,programme_id=?,institution_id=?,
                status=?,submitted_date=?,source=?,internal_note=?,updated_at=CURRENT_TIMESTAMP WHERE id=?''',values[1:]+(id_,))
            if previous['status']!=a['status']:
                db.execute('''INSERT INTO application_status_events(application_id,from_status,to_status,note)
                    VALUES (?,?,?,?)''',(id_,previous['status'],a['status'],str(a.get('note',''))[:1000]))
                audit(db,'application_status',id_,previous['status']+' → '+a['status'])
    campaigns=data.get('campaigns',[])
    if not isinstance(campaigns,list) or len(campaigns)>1000:
        raise ValueError('Invalid campaigns')
    for c in campaigns:
        if not isinstance(c,dict):continue
        id_=str(c.get('id',''))[:64]
        if not id_:continue
        previous=db.execute('SELECT id FROM campaigns WHERE id=?',(id_,)).fetchone()
        values=(id_,'northbridge',str(c.get('name',''))[:200],str(c.get('channel','Other'))[:70],
                max(0,float(c.get('budget') or 0)), max(0,float(c.get('spend') or 0)),
                *[max(0,int(c.get(k) or 0)) for k in ('visits','leads','applications','offers','enrolled')],
                str(c.get('status','Draft'))[:30],str(c.get('start',''))[:20])
        if previous is None:
            db.execute('''INSERT INTO campaigns(id,institution_id,name,channel,budget,spend,visits,leads,
                applications,offers,enrolled,status,start_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',values)
            audit(db,'campaign_created',id_,'Demo campaign created')
        else:
            # Only sample values and new local campaign fields; demo not connected to advertising providers.
            db.execute('''UPDATE campaigns SET name=?,channel=?,budget=?,spend=?,visits=?,leads=?,applications=?,
                offers=?,enrolled=?,status=?,start_date=? WHERE id=?''',values[2:]+(id_,))
    chat=data.get('chat',[])
    if not isinstance(chat,list) or len(chat)>500:raise ValueError('Invalid chat history')
    count=db.execute('SELECT COUNT(*) FROM chat_messages WHERE student_id=?',(DEMO_STUDENT_ID,)).fetchone()[0]
    for msg in chat[count:]:
        if msg.get('role') not in ('user','assistant'):continue
        db.execute('INSERT INTO chat_messages(student_id,role,message) VALUES (?,?,?)',
                   (DEMO_STUDENT_ID,msg['role'],str(msg.get('text',''))[:4000]))
    db.commit()


def summary(db):
    result={}
    for k,q in {
        'institutions':'SELECT COUNT(*) FROM institutions',
        'programmes':'SELECT COUNT(*) FROM programmes',
        'students':'SELECT COUNT(*) FROM students',
        'applications':'SELECT COUNT(*) FROM applications',
        'campaigns':'SELECT COUNT(*) FROM campaigns',
        'status_events':'SELECT COUNT(*) FROM application_status_events',
    }.items():result[k]=db.execute(q).fetchone()[0]
    return result


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)

    def log_message(self,fmt,*args):
        if not str(args[0]).startswith(('GET /api/health','GET /api/bootstrap')):
            super().log_message(fmt,*args)

    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        super().end_headers()

    def response_json(self,obj,status=200):
        blob=j(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(blob)))
        self.end_headers();self.wfile.write(blob)

    def do_GET(self):
        url=urlsplit(self.path)
        if url.path.startswith('/api/'):
            try:
                with LOCK,managed_conn() as db:
                    if url.path=='/api/avatar':
                        row=db.execute('SELECT avatar_blob,avatar_mime FROM students WHERE id=?', (DEMO_STUDENT_ID,)).fetchone()
                        if not row or row['avatar_blob'] is None:
                            return self.response_json({'error':'No profile photo'},404)
                        blob=bytes(row['avatar_blob'])
                        self.send_response(200)
                        self.send_header('Content-Type',row['avatar_mime'])
                        self.send_header('Content-Length',str(len(blob)))
                        self.end_headers()
                        self.wfile.write(blob)
                        return
                    if url.path=='/api/bootstrap':obj=snapshot(db)
                    elif url.path=='/api/health':obj={'ok':True,'engine':'SQLite','local_only':True, 'database':str(DB.name), 'counts':summary(db)}
                    elif url.path=='/api/institutions':obj=list_institutions(db)
                    elif url.path=='/api/programmes':obj=list_programmes(db)
                    elif url.path=='/api/applications':obj=list_applications(db)
                    elif url.path=='/api/campaigns':obj=list_campaigns(db)
                    elif url.path=='/api/analytics':
                        campaigns=list_campaigns(db)
                        obj={'campaign_spend':sum(c['spend'] for c in campaigns),'leads':sum(c['leads'] for c in campaigns),
                             'attributed_applications':sum(c['applications'] for c in campaigns),
                             'enrolled':sum(c['enrolled'] for c in campaigns),
                             'application_statuses':[dict(r) for r in db.execute('SELECT status,COUNT(*) AS count FROM applications GROUP BY status')],
                             'source':'fictional_seed'}
                    elif url.path=='/api/audit':obj=[dict(r) for r in db.execute('SELECT * FROM audit_events ORDER BY id DESC LIMIT 60')]
                    else:return self.response_json({'error':'Unknown API endpoint'},404)
                    return self.response_json(obj)
            except Exception as exc:return self.response_json({'error':str(exc)},500)
        # Explicit allowlist. Never serve the SQLite file, seed data, scripts or other source.
        path=unquote(url.path)
        segments=path.split('/')
        if '..' in segments or '.' in segments:
            self.send_error(404,'File not accessible');return
        allowed=(path in ('/','/index.html') or
            (path.startswith('/css/') and path.endswith('.css')) or
            (path.startswith('/js/') and path.endswith('.js')))
        if not allowed:
            self.send_error(404,'File not accessible');return
        return super().do_GET()

    def do_POST(self):
        url=urlsplit(self.path)
        if url.path not in ('/api/state','/api/reset','/api/avatar'):
            return self.response_json({'error':'Unknown API endpoint'},404)
        origin=self.headers.get('Origin','')
        if origin and origin not in ('http://localhost:'+str(PORT),'http://127.0.0.1:'+str(PORT)):
            return self.response_json({'error':'Invalid origin'},403)
        if self.headers.get('Content-Type','').split(';')[0]!='application/json' and url.path=='/api/state':
            return self.response_json({'error':'Content-Type must be application/json'},415)
        try:
            content_length=int(self.headers.get('Content-Length','0'))
            if content_length<0:return self.response_json({'error':'Invalid content length'},400)
            if url.path=='/api/avatar':
                if content_length<16 or content_length>2*1024*1024:
                    return self.response_json({'error':'Photo must be smaller than 2 MB'},413)
                mime=self.headers.get('Content-Type','').split(';')[0].strip().lower()
                if mime not in ('image/jpeg','image/png','image/webp'):
                    return self.response_json({'error':'Use JPG, PNG or WebP only'},415)
                blob=self.rfile.read(content_length)
                if len(blob)!=content_length:
                    return self.response_json({'error':'Incomplete upload'},400)
                # Do not accept SVG or arbitrary files merely renamed to .jpg.
                valid=(mime=='image/jpeg' and blob.startswith(b'\xff\xd8\xff')) or \
                      (mime=='image/png' and blob.startswith(b'\x89PNG\r\n\x1a\n')) or \
                      (mime=='image/webp' and blob.startswith(b'RIFF') and blob[8:12]==b'WEBP')
                if not valid:
                    return self.response_json({'error':'Invalid image contents'},400)
                with LOCK,managed_conn() as db:
                    db.execute('UPDATE students SET avatar_blob=?,avatar_mime=?,avatar_version=avatar_version+1 WHERE id=?',
                               (sqlite3.Binary(blob),mime,DEMO_STUDENT_ID))
                    version=db.execute('SELECT avatar_version FROM students WHERE id=?',(DEMO_STUDENT_ID,)).fetchone()[0]
                    audit(db,'profile_photo_uploaded',DEMO_STUDENT_ID,'Student profile photo updated')
                return self.response_json({'ok':True,'hasAvatar':True,'avatarVersion':version})
            if content_length>2_000_000:return self.response_json({'error':'Payload too large'},413)
            if url.path=='/api/reset':
                with LOCK:initialize(reset=True)
                return self.response_json({'ok':True, 'reset':True})
            data=json.loads(self.rfile.read(content_length).decode('utf-8'))
            with LOCK,managed_conn() as db:
                save_state(db,data)
            return self.response_json({'ok':True})
        except (ValueError,sqlite3.IntegrityError,TypeError) as exc:
            return self.response_json({'ok':False,'error':str(exc)},400)
        except Exception as exc:return self.response_json({'ok':False,'error':str(exc)},500)

    def do_DELETE(self):
        url=urlsplit(self.path)
        if url.path!='/api/avatar':
            return self.response_json({'error':'Unknown API endpoint'},404)
        origin=self.headers.get('Origin','')
        if origin and origin not in ('http://localhost:'+str(PORT),'http://127.0.0.1:'+str(PORT)):
            return self.response_json({'error':'Invalid origin'},403)
        with LOCK,managed_conn() as db:
            db.execute('UPDATE students SET avatar_blob=NULL,avatar_mime=NULL,avatar_version=avatar_version+1 WHERE id=?',
                       (DEMO_STUDENT_ID,))
            version=db.execute('SELECT avatar_version FROM students WHERE id=?',(DEMO_STUDENT_ID,)).fetchone()[0]
            audit(db,'profile_photo_removed',DEMO_STUDENT_ID,'Student profile photo removed')
        return self.response_json({'ok':True,'hasAvatar':False,'avatarVersion':version})


def main():
    if '--reset' in sys.argv:
        initialize(reset=True)
        print('Database reset with fictional demonstration data: ',DB)
        return
    initialize()
    print('\nEduPath AI SQLite demo ready')
    print(f'Open http://127.0.0.1:{PORT}')
    print('Local-only server. No sign-in and no institutional security isolation.')
    print('SQLite database:',DB,'\n')
    try:
        server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
        server.serve_forever()
    except OSError as exc:
        print('Failed to start server: ',exc)
        print('If another EduPath server is already running, close it and retry.')
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nServer stopped.')

if __name__=='__main__':main()
