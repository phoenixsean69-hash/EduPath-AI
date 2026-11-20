"""Avatar persistence and validation regression tests (standard library only)."""
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

# Valid tiny JPEG test fixture. Header validation is intentionally limited;
# UI uploads a browser-decoded/re-encoded JPEG.
JPEG=b'\xff\xd8\xff\xe0'+b'JFIF\x00'+b'\x00'*24+b'\xff\xd9'

class AvatarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.previous=server.DB
        server.DB=Path(cls.temp.name)/'test.sqlite3'
        server.initialize()
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.url='http://127.0.0.1:'+str(cls.http.server_port)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();server.DB=cls.previous;cls.temp.cleanup()
    def request(self,path,method='GET',data=None,mime=None):
        req=Request(self.url+path,data=data,method=method,headers={'Content-Type':mime} if mime else {})
        with urlopen(req) as r:return r.status,r.headers,r.read()
    def test_01_avatar_upload_download_restart_remove(self):
        import json
        snap=json.loads(self.request('/api/bootstrap')[2])
        self.assertFalse(snap['state']['profile']['hasAvatar'])
        self.assertEqual(snap['state']['profile']['avatarVersion'],0)
        status,headers,body=self.request('/api/avatar','POST',JPEG,'image/jpeg')
        self.assertEqual(status,200)
        result=json.loads(body);self.assertEqual(result['avatarVersion'],1)
        self.assertTrue(json.loads(self.request('/api/bootstrap')[2])['state']['profile']['hasAvatar'])
        status,headers,body=self.request('/api/avatar')
        self.assertEqual(headers['Content-Type'],'image/jpeg');self.assertEqual(body,JPEG)
        server.initialize()  # server restart: schema migration must NOT erase photo
        self.assertEqual(self.request('/api/avatar')[2],JPEG)
        with server.managed_conn() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM institutions').fetchone()[0],4)
        self.request('/api/avatar','DELETE')
        self.assertFalse(json.loads(self.request('/api/bootstrap')[2])['state']['profile']['hasAvatar'])
        with self.assertRaises(HTTPError) as ctx:self.request('/api/avatar')
        self.assertEqual(ctx.exception.code,404)
    def test_02_invalid_files_rejected(self):
        for data,mime,expected in [(b'<svg><script/></svg>','image/svg+xml',415),(b'not-an-image-file-xxxxxxxx','image/jpeg',400)]:
            with self.assertRaises(HTTPError) as ctx:self.request('/api/avatar','POST',data,mime)
            self.assertEqual(ctx.exception.code,expected)
    def test_03_migrate_old_database_preserves_existing_records(self):
        import sqlite3
        p=Path(self.temp.name)/'legacy.sqlite3'
        with sqlite3.connect(p) as db:
            db.executescript("""
            CREATE TABLE institutions(id TEXT PRIMARY KEY,name TEXT,type TEXT,city TEXT,abbr TEXT,summary TEXT);
            INSERT INTO institutions VALUES ('legacy-school','Legacy School','College','Harare','LS','Existing record');
            CREATE TABLE students(id TEXT PRIMARY KEY, full_name TEXT, email TEXT, phone TEXT, city TEXT, interest TEXT, updated_at TEXT);
            INSERT INTO students VALUES('student-demo-001','Tariro Moyo','tariro@example.test','','Harare','Technology','2026-11-10');
            """)
            db.commit()
        original=server.DB;server.DB=p
        try:
            server.initialize()
            with server.managed_conn() as db:
                row=db.execute('SELECT full_name,avatar_blob,avatar_version FROM students WHERE id=?',('student-demo-001',)).fetchone()
                self.assertEqual(row['full_name'],'Tariro Moyo')
                self.assertIsNone(row['avatar_blob']);self.assertEqual(row['avatar_version'],0)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM institutions').fetchone()[0],1)
        finally:server.DB=original
if __name__=='__main__':unittest.main()
