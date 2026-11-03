"""Regras e importação do módulo Particulares a partir do gerencial APN."""
import io,json,hashlib,math,re,unicodedata,zipfile
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from xml.etree.ElementTree import ParseError
ROOT=Path(__file__).parent
SPECIALTIES=['ACUPUNTURA','FISIOTERAPIA','FONOAUDIOLOGIA','PSICOLOGIA']
def normalize(v):return ' '.join(str(v or '').strip().upper().split())
def specialty(v):
 s=normalize(v).replace('FONOAUDILOGIA','FONOAUDIOLOGIA')
 if s not in SPECIALTIES:raise ValueError('Especialidade não cadastrada: '+s)
 return s
def operator(v):
 s=normalize(v)
 return {'BRADESCO OP.':'BRADESCO OP. PLANOS','MEDSERVICE':'MEDISERVICE'}.get(s,s)
def period(v):
 if isinstance(v,datetime):return v.strftime('%Y-%m')
 if isinstance(v,str) and re.fullmatch(r'20\d\d-(0[1-9]|1[0-2])',v):return v
 raise ValueError('Competência inválida no arquivo.')
def num(v,allow_empty=False):
 if v is None and allow_empty:return None
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError('Campo numérico inválido ou fórmula sem valor calculado.')
 return float(v)
def extract(raw):
 if len(raw)>10*1024*1024:raise ValueError('Máximo de 10 MB.')
 try:
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   if sum(x.file_size for x in z.infolist())>40*1024*1024:raise ValueError('XLSX descompactado excede o limite.')
  w=openpyxl.load_workbook(io.BytesIO(raw),data_only=True,read_only=True)
 except (zipfile.BadZipFile,KeyError,InvalidFileException,ParseError):raise ValueError('Envie a planilha gerencial XLSX do Gestão Particular APN.')
 def table(name):
  if name not in w.sheetnames or w[name].sheet_state!='visible':raise ValueError('Aba obrigatória ausente ou oculta: '+name)
  s=w[name];it=s.iter_rows(min_row=6,values_only=True);headers=next(it)
  required={'Base':['Competência','Chave paciente','Quantidade','Valor unitário','Valor gerencial','Total original','Especialidade'],'Base Convenios':['Competência','Atendimentos','Valor unitário','Valor calculado','Total original','Especialidade','Chave paciente','Operadora normalizada'],'Status Convenios':['Competência','Operadora','Especialidade','Faturado','Em análise','Pago informado','Glosa em recurso','Glosa paga','Glosa definitiva'],'Conferencia':['Competência','Especialidade','Diferença R$','Diferença proced.','Diferença pacientes']}
  if not set(required[name]).issubset(set(headers)):raise ValueError('Cabeçalhos incompatíveis na aba '+name)
  result=[]
  for rowno,row in enumerate(it,7):
   if row[0] is None:continue
   try:month=period(row[0])
   except ValueError:
    if normalize(row[0]).startswith('TOTAL'):
     if name=='Conferencia':break
     continue
    raise ValueError(f'Competência não reconhecida em {name}, linha {rowno}.')
   result.append(({str(k):row[i] for i,k in enumerate(headers) if k is not None},month,rowno))
  return result
 # Use the file's existing patient key, pseudonymized consistently across both sources.
 def patient(key):
  if not key:raise ValueError('Chave de paciente ausente no gerencial; concilie o arquivo antes de importar.')
  return hashlib.sha256(normalize(key).encode()).hexdigest()
 direct=[];insurance=[];status=[];checks=[]
 for r,month,line in table('Base'):
  q=num(r['Quantidade']);unit=num(r['Valor unitário']);cached=num(r['Valor gerencial']);value=q*unit;original=num(r['Total original'],True)
  if q<0 or not q.is_integer():raise ValueError('Quantidade de atendimentos deve ser inteira e não negativa.')
  if abs(value-cached)>.010001:raise ValueError('Receita gerencial não reconciliada com quantidade × valor unitário.')
  date=r.get('Data atend. original');alert=[]
  if date is not None and not isinstance(date,datetime):alert.append('Data original não reconhecida; competência gerencial preservada pela aba.')
  if isinstance(date,datetime) and date.strftime('%Y-%m')!=month:alert.append('Data de atendimento fora da competência da aba.')
  if original is not None and abs(value-original)>.010001:alert.append('Quantidade × valor unitário difere do total original.')
  direct.append(dict(period=month,specialty=specialty(r['Especialidade']),patient=patient(r['Chave paciente']),quantity=q,value=value,unit=unit,original_total=original,source_row=line,source_sheet=r.get('Aba origem'),original_date=str(date) if date is not None else None,alerts=alert))
 for r,month,line in table('Base Convenios'):
  q=num(r['Atendimentos']);unit=num(r['Valor unitário']);value=q*unit
  if q<0 or not q.is_integer():raise ValueError('Quantidade de atendimentos deve ser inteira e não negativa.')
  if abs(value-num(r['Valor calculado']))>.010001:raise ValueError('Valor calculado dos convênios não reconciliado.')
  original=num(r['Total original'],True)
  insurance.append(dict(period=month,specialty=specialty(r['Especialidade']),patient=patient(r['Chave paciente']),quantity=q,value=value,unit=unit,original_total=original,operator=operator(r['Operadora normalizada']),source_row=line,source_sheet=r.get('Aba origem'),alerts=['Valor calculado difere do total original.'] if original is not None and abs(value-original)>.010001 else []))
 for r,month,line in table('Status Convenios'):
  status.append(dict(period=month,operator=operator(r['Operadora']),specialty=specialty(r['Especialidade']),billed=num(r['Faturado']),analysis=num(r['Em análise'],True),paid=num(r['Pago informado'],True),appeal=num(r['Glosa em recurso'],True),appeal_paid=num(r['Glosa paga'],True),denied=num(r['Glosa definitiva'],True),source_row=line))
 for r,month,line in table('Conferencia'):
  checks.append(dict(period=month,specialty=specialty(r['Especialidade']),revenue_difference=num(r['Diferença R$'],True),quantity_difference=num(r['Diferença proced.'],True),patient_difference=num(r['Diferença pacientes'],True),source_row=line))
 if 'Custos' not in w.sheetnames:raise ValueError('Aba Custos ausente.')
 costs=w['Custos'];flags={}
 for row in costs.iter_rows(min_row=7,values_only=True):
  if len(row)>17 and row[14] is not None:
   month=period(row[14]);flags[month]={'direct':normalize(row[15])=='SIM','insurance':normalize(row[17])=='SIM'}
 if not flags:raise ValueError('Não há identificação das competências recebidas em Custos.')
 for source,rs in [('direct',direct),('insurance',insurance)]:
  if any(not flags.get(r['period'],{}).get(source) for r in rs):raise ValueError('Há linhas em competência sem confirmação de recebimento na aba Custos.')
 result={'direct':{},'insurance':{}}
 for month,flag in flags.items():
  for source,rs in [('direct',direct),('insurance',insurance)]:
   if flag[source]:result[source][month]={'rows':[r for r in rs if r['period']==month],'status':[r for r in status if r['period']==month] if source=='insurance' else [],'checks':[r for r in checks if r['period']==month] if source=='direct' else []}
 w.close();return result

def cost_for(month):
 config=json.loads((ROOT/'data/private_costs.json').read_text())
 return next((c for c in config['versions'] if c['from']<=month<=c['to']),None)
def summarize(sources):
 periods=sorted(set(sources['direct'])|set(sources['insurance']));output=[]
 for month in periods:
  d=sources['direct'].get(month);i=sources['insurance'].get(month);both=d is not None and i is not None;rows=(d or {}).get('rows',[])+(i or {}).get('rows',[]);cost=cost_for(month);quantity=sum(r['quantity'] for r in rows);by=[]
  for spec in SPECIALTIES:
   dr=[r for r in (d or {}).get('rows',[]) if r['specialty']==spec];ir=[r for r in (i or {}).get('rows',[]) if r['specialty']==spec];rs=dr+ir;q=sum(r['quantity'] for r in rs);revenue=sum(r['value'] for r in rs) if both else None
   technical=cost['technical'][spec] if cost else None;admin=cost['administrative']*q/quantity if cost and both and quantity else None;total=technical+admin if admin is not None else None
   by.append(dict(specialty=spec,direct=sum(r['value'] for r in dr) if d is not None else None,insurance=sum(r['value'] for r in ir) if i is not None else None,revenue=revenue,quantity=q,patients=len({r['patient'] for r in rs}),technical=technical,administrative=admin,cost=total,balance=revenue-total if revenue is not None and total is not None else None,weekly_hours=cost['weekly_hours'][spec] if cost else None,monthly_hours=cost['weekly_hours'][spec]*4.5 if cost else None))
  revenue=sum(r['value'] for r in rows) if both else None;total=sum(cost['technical'].values())+cost['administrative'] if cost else None
  output.append(dict(period=month,direct_received=d is not None,insurance_received=i is not None,complete=both and cost is not None,revenue=revenue,direct=sum(r['value'] for r in (d or {}).get('rows',[])) if d is not None else None,insurance=sum(r['value'] for r in (i or {}).get('rows',[])) if i is not None else None,cost=total,technical=sum(cost['technical'].values()) if cost else None,administrative=cost['administrative'] if cost else None,balance=revenue-total if revenue is not None and total is not None else None,quantity=quantity,patients=len({r['patient'] for r in rows}),specialties=by,allocation_valid=bool(both and cost and quantity)))
 return output

def archive(raw):
 """Preserva a fonte original fora dos arquivos versionados e das respostas web."""
 digest=hashlib.sha256(raw).hexdigest();folder=Path(__import__('os').environ.get('APN_DATA_DIR',str(ROOT/'data')))/'source-archives';folder.mkdir(parents=True,exist_ok=True);path=folder/(digest+'.xlsx')
 if not path.exists():path.write_bytes(raw)
 return digest
