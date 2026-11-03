import sys,json,base64
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app
def export(path):
 data=app.read('initial.json');data['history']=[{'id':i+1,'period':p['period'],'active':1} for i,p in enumerate(data['periods'])];data['production']=app.read('faturamento.json');data['plan']=app.read('plan.json')['accounts'];sources=app.read('private_initial.json')['sources'];data['private']={'sources':sources,'monthly':app.private_module.summarize(sources),'history':[],'costs':app.read('private_costs.json')}
 html=(ROOT/'static/index.html').read_text().replace('<link rel="stylesheet" href="/style.css">','<style>'+(ROOT/'static/style.css').read_text()+'</style>')
 logo='data:image/png;base64,'+base64.b64encode((ROOT/'static/logo-pestalozzi.png').read_bytes()).decode('ascii')
 html=html.replace('src="/logo-pestalozzi.png"','src="'+logo+'"')
 js='const OFFLINE_DATA='+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';\n'+(ROOT/'static/app.js').read_text()
 html=html.replace('<script src="/app.js"></script>','<script>'+js.replace('</script','<\\/script')+'</script>');Path(path).write_text(html)
if __name__=='__main__':export(sys.argv[1] if len(sys.argv)>1 else '/workspace/entregas/Gestao-ADM-Previa.html')
