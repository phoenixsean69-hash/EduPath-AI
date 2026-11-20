"""Run with: python -m unittest discover -s tests -v (from project folder)."""
import json
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

class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        server.DB=Path(cls.temp.name)/'test.sqlite3'
        server.initialize()
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.url='http://127.0.0.1:'+str(cls.http.server_port)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.temp.cleanup()
    def get(self,path):
        with urlopen(self.url+path) as resp:return json.load(resp)
    def post(self,path,payload):
        req=Request(self.url+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(req) as resp:return json.load(resp)
    def test_01_seed_and_schema(self):
        health=self.get('/api/health');self.assertEqual(health['counts']['institutions'],4)
        self.assertEqual(health['counts']['programmes'],10)
        self.assertEqual(health['counts']['applications'],7)
        self.assertEqual(health['counts']['campaigns'],4)
        with server.managed_conn() as db:
            n=db.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name NOT LIKE "sqlite_%"').fetchone()[0]
            self.assertEqual(n,18)
    def test_02_bootstrap(self):
        data=self.get('/api/bootstrap');self.assertEqual(data['backend'],'sqlite')
        self.assertEqual(data['state']['profile']['name'],'Tariro Moyo')
        self.assertEqual(len(data['programmes']),10)
    def test_03_apply_review_campaign_and_persist(self):
        state=self.get('/api/bootstrap')['state']
        state['applications'].append({'id':'APP-TEST-2026','student':'Tariro Moyo','programme':'GD310',
          'inst':'lakeside','status':'Submitted','submitted':'2026-11-10','source':'Direct','note':''})
        state['campaigns'].append({'id':'CMP-TEST','name':'Pilot outreach','channel':'Facebook','budget':100,
          'spend':0,'visits':0,'leads':0,'applications':0,'offers':0,'enrolled':0,'status':'Draft','start':'2026-11-10'})
        state['chat'].extend([{'role':'user','text':'Hello'},{'role':'assistant','text':'Hi!'}])
        self.assertTrue(self.post('/api/state',state)['ok'])
        live=self.get('/api/bootstrap')['state'];self.assertTrue(any(a['id']=='APP-TEST-2026' for a in live['applications']))
        self.assertTrue(any(c['id']=='CMP-TEST' for c in live['campaigns']))
        self.assertEqual(live['chat'][-1]['text'],'Hi!')
        a=next(a for a in live['applications'] if a['id']=='APP-TEST-2026')
        a['status']='Shortlisted';a['note']='Good candidate'
        self.post('/api/state',live)
        saved=next(a for a in self.get('/api/bootstrap')['state']['applications'] if a['id']=='APP-TEST-2026')
        self.assertEqual(saved['status'],'Shortlisted')
        with server.managed_conn() as db:
            events=db.execute("SELECT COUNT(*) FROM application_status_events WHERE application_id='APP-TEST-2026'").fetchone()[0]
            self.assertEqual(events,2)
    def test_04_security_headers_and_path(self):
        try:urlopen(self.url+'/data/edupath.sqlite3');self.fail('Database exposed')
        except HTTPError as exc:self.assertEqual(exc.code,404)
        with urlopen(self.url+'/index.html') as r:
            self.assertEqual(r.headers.get('X-Content-Type-Options'),'nosniff')

if __name__=='__main__':unittest.main()
