from pathlib import Path
import zipfile,hashlib,json
ROOT=Path(__file__).resolve().parents[1];out=Path('/workspace/entregas');out.mkdir(exist_ok=True)
with zipfile.ZipFile(out/'Gestao-ADM-Projeto.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in ROOT.rglob('*'):
  rel=p.relative_to(ROOT)
  if p.is_file() and not any(x in {'.git','.venv','.runtime','__pycache__'} for x in rel.parts) and p.suffix not in {'.sqlite3','.pyc'} and p.name!='.env':z.write(p,Path('Gestao-ADM')/rel)
 z.write(out/'Gestao-ADM-Previa.html','Gestao-ADM/Gestao-ADM-Previa.html')
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in {'.html','.zip'}}
(out/'SHA256.json').write_text(json.dumps(files,indent=2))
