import unittest,json,io,os,tempfile
from pathlib import Path
from unittest.mock import patch
import app
class AppTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.original=app.DB;app.DB=Path(self.tmp.name)/'db.sqlite3';app.seed()
 def tearDown(self):app.DB=self.original;self.tmp.cleanup()
 def request(self,path='/',method='GET',**extra):
  env={'PATH_INFO':path,'REQUEST_METHOD':method,'HTTP_HOST':'localhost:8000','wsgi.input':io.BytesIO()};env.update(extra);result={};body=b''.join(app.application(env,lambda status,headers:result.update(status=status,headers=dict(headers))));return result,body
 def test_recovered_source_counts(self):
  d=app.dataset();self.assertEqual(len(d['plan']),965);self.assertEqual(len(d['periods']),8);self.assertEqual(len([r for r in d['production']['monthly'] if r['Situação']=='Importado']),9)
 def test_accounting_year_and_quarters(self):
  results=[]
  for p in app.dataset()['periods']:
   r=sum(x['credits']-x['debits'] for x in p['accounts'] if x['leaf'] and x['classification'].startswith('3'));e=sum(x['debits']-x['credits'] for x in p['accounts'] if x['leaf'] and x['classification'].startswith('4'));results.append(r-e)
  self.assertAlmostEqual(sum(results),-194025.54,2);self.assertAlmostEqual(sum(results[:3]),284252.20,2);self.assertAlmostEqual(sum(results[3:6]),-134230.75,2);self.assertAlmostEqual(sum(results[6:]),-344046.99,2)
 def test_production(self):
  d=app.read('faturamento.json');rs=[r for r in d['monthly'] if r['Situação']=='Importado']
  self.assertEqual(sum(r['Total atendimentos²'] for r in rs),69267);self.assertEqual(sum(r['OPM quantidade³'] for r in rs),4496);self.assertEqual(sum(r['Pacientes reabilitação SUS¹'] for r in rs),7375)
  self.assertEqual(sum(r['Atendimentos particular²']+r['Atendimentos convênio²'] for r in rs),2707)
  for r in d['monthly']:
   if r['Situação']=='Pendente':self.assertIsNone(r['Total atendimentos²'])
  self.assertTrue(any(r['Código']=='10701020083' for r in d['bases']['Itens OPM']))
 def test_versions_and_idempotency(self):
  d=app.dataset();p=d['periods'][0];self.assertTrue(app.save(p['period'],p['accounts'],'revision'));self.assertFalse(app.save(p['period'],p['accounts'],'revision'));after=app.dataset();self.assertEqual(len(after['periods']),8);self.assertEqual(len(after['history']),9);self.assertEqual(d['periods'][1:],after['periods'][1:])
 def test_import_real_file(self):
  files=list(Path('/workspace/attachments').glob('*/BALANCETE 08-2026.xls'))
  if not files:self.skipTest('Anexo de teste não disponível')
  rows=app.parse_upload(files[0].read_bytes(),'2026-08');self.assertEqual(len(rows),360);self.assertFalse(any('divergente' in x for x in app.warnings('2026-08',rows)))
  with self.assertRaises(ValueError):app.parse_upload(files[0].read_bytes(),'2026-13')
 def test_local_routes(self):
  with patch.dict(os.environ,{'APN_ENV':'development'}):
   for path in ['/','/app.js','/style.css','/api/data']:
    r,b=self.request(path);self.assertTrue(r['status'].startswith('200'));self.assertTrue(b)
 def test_production_gates(self):
  with patch.dict(os.environ,{'APN_ENV':'production','APN_AZURE_AUTH_ENABLED':''}):self.assertTrue(self.request('/api/data')[0]['status'].startswith('503'))
  with patch.dict(os.environ,{'APN_ENV':'production','APN_AZURE_AUTH_ENABLED':'1'}):self.assertTrue(self.request('/api/data')[0]['status'].startswith('401'))
 def test_health_and_csrf(self):
  self.assertEqual(json.loads(self.request('/healthz')[1]),{'status':'ok'})
  with patch.dict(os.environ,{'APN_ENV':'development'}):self.assertTrue(self.request('/api/import','POST',HTTP_ORIGIN='https://other.example')[0]['status'].startswith('403'))
if __name__=='__main__':unittest.main()
