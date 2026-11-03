"""Migração inicial revisável do gerencial. Não altera o banco operacional."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import private_module
if __name__=='__main__':
 path=Path(sys.argv[1]);raw=path.read_bytes();sources=private_module.extract(raw);monthly=private_module.summarize(sources);private_module.archive(raw)
 out=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'data/private_initial.json'
 out.write_text(json.dumps({'source':path.name,'digest':hashlib.sha256(raw).hexdigest(),'sources':sources,'monthly':monthly},ensure_ascii=False,indent=2))
 print('Fontes e competências:',len(sources['direct']),len(sources['insurance']))
 print('Receita conjunta disponível:',round(sum(m['revenue'] or 0 for m in monthly),2))
