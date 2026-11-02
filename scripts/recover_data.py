"""Reconstrói bases a partir dos anexos originais; nunca altera os arquivos-fonte."""
import glob,io,re,json,hashlib
from pathlib import Path
import xlrd,openpyxl
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def recover():
 planpath=glob.glob('/workspace/attachments/*/PLANO*')[0];s=xlrd.open_workbook(planpath,encoding_override='cp1252',logfile=io.StringIO()).sheet_by_index(0);plan={}
 for i,row in enumerate(s.get_rows(),1):
  r=[c.value for c in row];cls=str(r[0]).strip()
  if re.fullmatch(r'\d+(?:\.\d+)*',cls) and isinstance(r[15],(int,float)):
   code=str(int(r[15]));assert code not in plan
   plan[code]={'code':code,'classification':cls,'name':' '.join(str(v).strip() for v in r[3:12] if str(v).strip()),'source_row':i}
 periods=[];previous={}
 for path in sorted(glob.glob('/workspace/attachments/*/BALANCETE*'),key=lambda p:p.split('BALANCETE ')[1]):
  month=int(re.search(r'BALANCETE (\d+)',path)[1]);s=xlrd.open_workbook(path,logfile=io.StringIO()).sheet_by_index(0);rows=[]
  for i in range(s.nrows):
   r=s.row_values(i);m=re.match(r'^(\s*)\[(\d+)\](.*)',str(r[0]))
   if m:rows.append(dict(code=m[2],name=m[3].strip(),indent=len(m[1]),initial=r[3],debits=r[4],credits=r[5],final=r[6],classification=plan[m[2]]['classification'],source_row=i+1))
  assert len({r['code'] for r in rows})==len(rows)
  for i,r in enumerate(rows):
   r['leaf']=i==len(rows)-1 or rows[i+1]['indent']<=r['indent']
   assert abs(r['initial']+r['debits']-r['credits']-r['final'])<.010001
   if r['code'] in previous:assert abs(r['initial']-previous[r['code']]['final'])<.010001
   if not r['leaf']:
    children=[]
    for x in rows[i+1:]:
     if x['indent']<=r['indent']:break
     if x['indent']==r['indent']+2:children.append(x)
    for key in ['initial','debits','credits','final']:assert abs(r[key]-sum(x[key] for x in children))<.010001
  assert abs(sum(r['debits']-r['credits'] for r in rows if r['leaf']))<.010001
  previous={r['code']:r for r in rows}
  periods.append(dict(period=f'2026-{month:02}',accounts=rows,digest=sha(path),source=Path(path).name,status='Preliminar'))
 path=glob.glob('/workspace/attachments/*/Faturamento_APN*')[0];w=openpyxl.load_workbook(path,data_only=True)
 def table(name):
  s=w[name];assert s.sheet_state=='visible';heads=[c.value for c in s[5]]
  return [{str(heads[j]):v for j,v in enumerate(row) if heads[j] is not None}|{'source_row':i} for i,row in enumerate(s.iter_rows(min_row=6,values_only=True),6) if isinstance(row[0],str) and re.fullmatch('2026-\d{2}',row[0])]
 prod={'year':2026,'source':Path(path).name,'sha256':sha(path),'monthly':table('Mensal'),'bases':{name:table(name) for name in ['Faturamento','Setores','Procedimentos','Itens OPM','OPM fiscal','Ocorrências','Controles fonte','Conferência','Importações']}}
 received=[r for r in prod['monthly'] if r['Situação']=='Importado']
 for key,cell in [('Pacientes reabilitação SUS¹','A7'),('Total atendimentos²','F7'),('OPM quantidade³','K7')]:assert sum(r[key] for r in received)==w['Dashboard anual'][cell].value
 for r in received:
  assert r['Atendimentos SUS²']+r['Atendimentos particular²']+r['Atendimentos convênio²']==r['Total atendimentos²']
  assert sum(x['Quantidade'] or 0 for x in prod['bases']['Itens OPM'] if x['Competência']==r['Competência'])==r['OPM quantidade³']
 history={}
 for r in prod['bases']['Importações']:history.setdefault(r['Competência'],[]).append(r)
 for period,parts in history.items():assert json.loads(''.join(r['Registro para atualização'] for r in sorted(parts,key=lambda r:r['Parte'])))['period']==period
 for name,obj in [('plan.json',{'accounts':list(plan.values()),'source':Path(planpath).name}),('initial.json',{'periods':periods}),('faturamento.json',prod)]:
  (ROOT/'data'/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
 print(f'Recuperados {len(plan)} contas, {len(periods)} balancetes e {len(received)} meses de produção.')
if __name__=='__main__':recover()
