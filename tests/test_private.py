import unittest,tempfile,json,copy,io,os
from pathlib import Path
from unittest.mock import patch
import app,private_module
class PrivateTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=app.DB;app.DB=Path(self.temp.name)/'private.sqlite3';self.data=app.private_dataset()
 def tearDown(self):app.DB=self.old;self.temp.cleanup()
 def test_initial_totals_and_monthly_allocation(self):
  ms=self.data['monthly'];self.assertEqual(len(ms),9)
  for k,total in [('revenue',80051.31),('cost',112817.61),('balance',-32766.30),('direct',58409.80),('insurance',21641.51)]:self.assertAlmostEqual(sum(m[k] for m in ms),total,2)
  for m in ms:
   self.assertAlmostEqual(sum(r['administrative'] for r in m['specialties']),3853.51,7)
   self.assertAlmostEqual(sum(r['technical'] for r in m['specialties']),8681.78,7)
   self.assertAlmostEqual(sum(r['balance'] for r in m['specialties']),m['balance'],7)
 def test_source_replacement_and_idempotence(self):
  before=copy.deepcopy(self.data['sources']['insurance']);d=copy.deepcopy(self.data['sources']['direct']['2026-01']);d['rows'][0]['value']+=10
  self.assertTrue(app.private_save('direct','2026-01',d));self.assertFalse(app.private_save('direct','2026-01',d))
  after=app.private_dataset();self.assertEqual(before,after['sources']['insurance']);self.assertEqual(len(after['history']),19);self.assertAlmostEqual(after['monthly'][0]['direct']-self.data['monthly'][0]['direct'],10,5)
 def test_missing_source_expired_cost_and_zero_activity(self):
  sources=copy.deepcopy(self.data['sources']);del sources['insurance']['2026-01'];m=private_module.summarize(sources)[0];self.assertFalse(m['complete']);self.assertIsNone(m['revenue']);self.assertIsNone(m['balance']);self.assertIsNotNone(m['direct'])
  sources={'direct':{'2027-03':{'rows':[]}},'insurance':{'2027-03':{'rows':[]}}};m=private_module.summarize(sources)[0];self.assertIsNone(m['cost']);self.assertIsNone(m['balance'])
  sources={'direct':{'2026-01':{'rows':[]}},'insurance':{'2026-01':{'rows':[]}}};m=private_module.summarize(sources)[0];self.assertAlmostEqual(m['balance'],-12535.29,2);self.assertFalse(m['allocation_valid']);self.assertTrue(all(r['administrative'] is None for r in m['specialties']))
 def test_patient_counts_match_workbook_and_import_endpoint(self):
  paths=list(Path('/workspace/attachments').glob('*/Gestao_Particular_APN_2026.xlsx'))
  if not paths:self.skipTest('Fonte de homologação não disponível')
  raw=paths[0].read_bytes();parsed=private_module.extract(raw);self.assertEqual(parsed,self.data['sources'])
  import openpyxl
  w=openpyxl.load_workbook(io.BytesIO(raw),data_only=True);monthly={m['period']:m for m in self.data['monthly']}
  for row in w['Mensal'].iter_rows(min_row=7,values_only=True):
   if row[0] is None:continue
   if not hasattr(row[0],'strftime'):continue
   if row[0].strftime('%Y-%m') not in monthly:continue
   actual=next(r for r in monthly[row[0].strftime('%Y-%m')]['specialties'] if r['specialty']==row[1]);self.assertEqual(actual['patients'],row[7])
  env={'PATH_INFO':'/api/private/preview','REQUEST_METHOD':'POST','HTTP_HOST':'localhost:8000','CONTENT_LENGTH':str(len(raw)),'QUERY_STRING':'source=direct&period=2026-01','wsgi.input':io.BytesIO(raw)};result={}
  with patch.dict(os.environ,{'APN_ENV':'development'}):body=b''.join(app.application(env,lambda status,headers:result.update(status=status)))
  self.assertEqual(result['status'],'200 OK');self.assertEqual(json.loads(body)['quantity'],168)
