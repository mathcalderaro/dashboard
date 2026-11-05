"""Prepara a página local e empacota dashboard + ETL + documentação."""
from pathlib import Path
import json
import zipfile

ROOT=Path(__file__).resolve().parent
SITE=ROOT/'vigilancia_dashboard'
payload=json.loads((SITE/'data.json').read_text(encoding='utf-8'))
(SITE/'data.js').write_text('window.VIGILANCIA_DADOS = '+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
target=ROOT/'VigiPA_Dashboard_2016_2025.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for p in [SITE/'index.html',SITE/'data.js',SITE/'data.json',ROOT/'vigilancia_etl.py',ROOT/'empacotar_vigilancia.py',ROOT/'vigilancia_README.md']:
        z.write(p,arcname=p.name)
print(target, target.stat().st_size)
