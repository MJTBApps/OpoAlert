#!/usr/bin/env python3
"""Inspect Angular controllers to identify supported BORM official services."""
from concurrent.futures import ThreadPoolExecutor
import requests,re,json
BASE="https://www.borm.es/"
FILES=[
"scripts/boletines/factories/boletinFactory.js",
"scripts/sumario/factories/sumarioFactory.js",
"scripts/suplementos/factories/suplementoFactory.js",
"scripts/sumarioSuplementos/factories/sumarioSuplementoFactory.js",
"scripts/calendario/factories/calendarioFactory.js",
"scripts/anuncio/factories/anuncioFactory.js",
"scripts/app.js",
"scripts/boletines/controllers/boletinController.js",
"scripts/suplementos/controllers/suplementoController.js",
"scripts/homeBorm/controllers/homeController.js",
"scripts/sumario/controllers/sumarioController.js",
"scripts/sumarioSuplementos/controllers/sumarioSuplementoController.js",
"scripts/calendario/controllers/calendarioController.js",
"scripts/anuncio/controllers/anuncioController.js",
"scripts/ayuntamientos/controllers/ayuntamientosController.js",
]
def inspect(path):
 try:
  r=requests.get(BASE+path,timeout=(8,25))
  s=r.text
  signals=list(re.finditer(r"(?:\$http|http\.|/services/|services/|url\s*:|getBoletin|getSumario|fechaBoletin|loadBoletin)",s,re.I))
  extracts=[]
  for match in signals:
   piece=s[max(0,match.start()-160):match.end()+240].replace("\n"," ")
   if piece not in extracts: extracts.append(piece)
  urls=sorted(set(re.findall(r"""["']([^"' ]*(?:services|boletin|sumario|pdf|datosAbiertos)[^"' ]*)["']""",s,re.I)))
  return {"file":path,"http":r.status_code,"size":len(s),"signals":len(signals),"excerpts":extracts[:36],"service_urls":urls[:120],"first":s[:350]}
 except Exception as e:return {"file":path,"error":repr(e)}
with ThreadPoolExecutor(max_workers=7) as p:
 for x in p.map(inspect,FILES):print("BORM_JS",json.dumps(x,ensure_ascii=False)[:22000],flush=True)
