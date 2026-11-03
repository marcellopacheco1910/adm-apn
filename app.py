import os,json,sqlite3,re,io,hashlib,math
from pathlib import Path
from urllib.parse import parse_qs
from http import HTTPStatus
import xlrd
import private_module
ROOT=Path(__file__).parent
DB=Path(os.environ.get('APN_DATA_DIR',str(ROOT/'data')))/'balancetes.sqlite3'
def read(name):return json.loads((ROOT/'data'/name).read_text())
def connect():
 DB.parent.mkdir(parents=True,exist_ok=True);c=sqlite3.connect(DB,timeout=30);c.row_factory=sqlite3.Row
 c.execute('CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY,period TEXT,digest TEXT,active INTEGER,payload TEXT)');c.execute('CREATE TABLE IF NOT EXISTS private_versions(id INTEGER PRIMARY KEY,source TEXT,period TEXT,digest TEXT,active INTEGER,payload TEXT)');return c
def save(period,rows,digest):
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  if c.execute('SELECT 1 FROM versions WHERE period=? AND digest=? AND active=1',(period,digest)).fetchone():return False
  c.execute('UPDATE versions SET active=0 WHERE period=?',(period,))
  c.execute('INSERT INTO versions(period,digest,active,payload) VALUES(?,?,1,?)',(period,digest,json.dumps(rows,ensure_ascii=False)))
 return True
def seed():
 with connect() as c:
  if c.execute('SELECT COUNT(*) FROM versions').fetchone()[0]:return
 for p in read('initial.json')['periods']:save(p['period'],p['accounts'],p['digest'])
def private_save(source,period,payload):
 encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True);digest=hashlib.sha256(encoded.encode()).hexdigest()
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  if c.execute('SELECT 1 FROM private_versions WHERE source=? AND period=? AND digest=? AND active=1',(source,period,digest)).fetchone():return False
  c.execute('UPDATE private_versions SET active=0 WHERE source=? AND period=?',(source,period))
  c.execute('INSERT INTO private_versions(source,period,digest,active,payload) VALUES(?,?,?,1,?)',(source,period,digest,encoded))
 return True

def private_dataset():
 with connect() as c:
  count=c.execute('SELECT COUNT(*) FROM private_versions').fetchone()[0]
 if not count:
  for source,periods in read('private_initial.json')['sources'].items():
   for period,payload in periods.items():private_save(source,period,payload)
 sources={'direct':{},'insurance':{}}
 with connect() as c:
  for r in c.execute('SELECT * FROM private_versions WHERE active=1 ORDER BY period'):sources[r['source']][r['period']]=json.loads(r['payload'])
  history=[dict(r) for r in c.execute('SELECT id,source,period,active,digest FROM private_versions ORDER BY id DESC')]
 return {'sources':sources,'monthly':private_module.summarize(sources),'history':history,'costs':read('private_costs.json')}

def dataset():
 with connect() as c:
  rows=c.execute('SELECT * FROM versions WHERE active=1 ORDER BY period').fetchall()
  history=[dict(r) for r in c.execute('SELECT id,period,digest,active FROM versions ORDER BY id DESC')]
 return {'private':private_dataset(),'periods':[{'period':r['period'],'accounts':json.loads(r['payload']),'status':'Preliminar','version':r['id']} for r in rows],'history':history,'plan':read('plan.json')['accounts'],'production':read('faturamento.json')}
def parse_upload(raw,period):
 if not re.fullmatch(r'20\d\d-(0[1-9]|1[0-2])',period):raise ValueError('Competência inválida.')
 s=xlrd.open_workbook(file_contents=raw,logfile=io.StringIO()).sheet_by_index(0);known={r['code']:r for r in read('plan.json')['accounts']};rows=[];seen=set()
 for i in range(s.nrows):
  v=s.row_values(i);m=re.match(r'^(\s*)\[(\d+)\](.*)',str(v[0]))
  if not m:continue
  code=m[2]
  if code in seen:raise ValueError('Código duplicado: '+code)
  if code not in known:raise ValueError('Conta não cadastrada no plano: '+code)
  seen.add(code)
  try:a,d,c,f=map(float,v[3:7])
  except (ValueError,TypeError):raise ValueError('Valores inválidos na linha '+str(i+1))
  if not all(math.isfinite(x) for x in [a,d,c,f]):raise ValueError('Valor não finito.')
  if abs(a+d-c-f)>.010001:raise ValueError('Saldo inconsistente: '+code)
  rows.append(dict(code=code,name=m[3].strip(),classification=known[code]['classification'],indent=len(m[1]),initial=a,debits=d,credits=c,final=f,source_row=i+1))
 if not rows:raise ValueError('Nenhuma conta reconhecida.')
 for i,r in enumerate(rows):
  r['leaf']=i==len(rows)-1 or rows[i+1]['indent']<=r['indent']
  if not r['leaf']:
   children=[]
   for x in rows[i+1:]:
    if x['indent']<=r['indent']:break
    if x['indent']==r['indent']+2:children.append(x)
   for k in ['initial','debits','credits','final']:
    if abs(r[k]-sum(x[k] for x in children))>.010001:raise ValueError('Subtotal inconsistente: '+r['code'])
 if abs(sum(r['debits']-r['credits'] for r in rows if r['leaf']))>.010001:raise ValueError('Débitos e créditos não equilibrados.')
 for code,prefix in [('6412','3'),('7308','4')]:
  control=next((r for r in rows if r['code']==code),None)
  if not control:raise ValueError('Conta de controle ausente: '+code)
  for k in ['debits','credits']:
   if abs(control[k]-sum(r[k] for r in rows if r['leaf'] and r['classification'].startswith(prefix)))>.010001:raise ValueError('Reconciliação do resultado falhou.')
 return rows
def warnings(period,rows):
 ps={p['period']:p['accounts'] for p in dataset()['periods']};year,month=map(int,period.split('-'));out=[];current={r['code']:r for r in rows}
 prev=f'{year-1}-12' if month==1 else f'{year}-{month-1:02}';nxt=f'{year+1}-01' if month==12 else f'{year}-{month+1:02}'
 old={r['code']:r for r in ps.get(prev,[])}
 for code,r in current.items():
  if code in old and abs(r['initial']-old[code]['final'])>.010001:out.append('Continuidade divergente: '+code)
 if old:
  out.extend('Conta ausente no mês atual: '+c for c in old.keys()-current.keys());out.extend('Conta incluída: '+c for c in current.keys()-old.keys())
 for r in ps.get(nxt,[]):
  if r['code'] in current and abs(r['initial']-current[r['code']]['final'])>.010001:out.append('Revisar continuidade do mês seguinte: '+r['code'])
 return out
def application(env,start):
 path=env.get('PATH_INFO','/');method=env.get('REQUEST_METHOD','GET')
 def response(status,body,kind='application/json'):
  raw=json.dumps(body,ensure_ascii=False).encode() if kind=='application/json' else body
  start(f'{status} {HTTPStatus(status).phrase}',[('Content-Type',kind+('; charset=utf-8' if kind.startswith('text/') or kind=='application/json' else '')),('Content-Length',str(len(raw))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'")]);return [raw]
 if path=='/healthz':
  try:
   with connect() as c:c.execute('SELECT 1').fetchone()
   return response(200,{'status':'ok'})
  except sqlite3.Error:return response(503,{'status':'unavailable'})
 if os.environ.get('APN_ENV')=='production':
  if os.environ.get('APN_AZURE_AUTH_ENABLED')!='1':return response(503,{'error':'Autenticação Azure não configurada.'})
  if not env.get('HTTP_X_MS_CLIENT_PRINCIPAL_ID'):return response(401,{'error':'Autenticação necessária.'})
 if method=='GET':
  if path=='/api/data':return response(200,dataset())
  files={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css'),'/logo-pestalozzi.png':('logo-pestalozzi.png','image/png')}
  if path not in files:return response(404,{'error':'Não encontrado'})
  name,kind=files[path];return response(200,(ROOT/'static'/name).read_bytes(),kind)
 if method!='POST':return response(405,{'error':'Método não permitido'})
 if path not in ['/api/preview','/api/import','/api/private/preview','/api/private/import']:return response(404,{'error':'Não encontrado'})
 allowed=os.environ.get('APN_PUBLIC_ORIGIN') or 'http://'+env.get('HTTP_HOST','localhost')
 if os.environ.get('APN_ENV')=='production' and not os.environ.get('APN_PUBLIC_ORIGIN'):return response(503,{'error':'Endereço público não configurado.'})
 if env.get('HTTP_ORIGIN') and env['HTTP_ORIGIN']!=allowed:return response(403,{'error':'Origem não permitida.'})
 try:
  length=int(env.get('CONTENT_LENGTH') or 0)
  if not 0<length<=10*1024*1024:raise ValueError('Máximo de 10 MB por arquivo.')
  raw=env['wsgi.input'].read(length);query=parse_qs(env.get('QUERY_STRING',''));period=query.get('period',[''])[0]
  if path.startswith('/api/private/'):
   source=query.get('source',[''])[0]
   if source not in ['direct','insurance']:raise ValueError('Selecione a fonte: particulares diretos ou convênios.')
   parsed=private_module.extract(raw)
   if period not in parsed[source]:raise ValueError('A competência não está recebida para a fonte escolhida no gerencial.')
   old=private_dataset()['sources'][source].get(period);payload=parsed[source][period];rows=payload['rows'];revenue=sum(r['value'] for r in rows)
   alerts=[f"Linha {r['source_row']}: {alert}" for r in rows for alert in r['alerts']]
   alerts.extend(f"Conferência de {r['specialty']}: diferença R$ {r['revenue_difference']} e procedimentos {r['quantity_difference']}." for r in payload['checks'] if abs(r['revenue_difference'] or 0)>.01 or r['quantity_difference'])
   changed=None
   if path=='/api/private/import':
    private_module.archive(raw);changed=private_save(source,period,payload)
   return response(200,{'rows':len(rows),'quantity':sum(r['quantity'] for r in rows),'revenue':round(revenue,2),'previous_revenue':round(sum(r['value'] for r in old['rows']),2) if old else None,'warnings':alerts,'changed':changed})
  rows=parse_upload(raw,period);alerts=warnings(period,rows)
  changed=save(period,rows,hashlib.sha256(raw).hexdigest()) if path=='/api/import' else None
  return response(200,{'accounts':len(rows),'warnings':alerts,'changed':changed,'revenue':round(sum(r['credits']-r['debits'] for r in rows if r['leaf'] and r['classification'].startswith('3')),2),'expense':round(sum(r['debits']-r['credits'] for r in rows if r['leaf'] and r['classification'].startswith('4')),2)})
 except (ValueError,xlrd.XLRDError,IndexError) as e:return response(400,{'error':str(e)})
 except sqlite3.Error:return response(503,{'error':'Armazenamento indisponível.'})
if __name__=='__main__':
 import argparse
 from wsgiref.simple_server import make_server
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8000);args=p.parse_args();seed()
 with make_server('127.0.0.1',args.port,application) as server:server.serve_forever()
