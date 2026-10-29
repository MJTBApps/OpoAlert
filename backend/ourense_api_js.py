import requests,json,re
s=requests.get("https://bop.depourense.es/portal/main.js",timeout=(12,75)).text
print("OUR_JS_LENGTH",len(s),flush=True)
pat=r"(?:api/boletin|api/edicto|api/consulta|api/portada|api/indice|api/busqueda|fechaBoletin|obtenerBoletines|buscarBoletines|urlBase|environment\.api)"
f=list(re.finditer(pat,s,re.I))
print("OUR_JS_MATCHES",len(f),flush=True)
unique=set()
for m in f:
 snippet=s[max(0,m.start()-250):m.end()+330].replace("\n"," ").replace("\r"," ")
 if snippet not in unique:
  unique.add(snippet);print("OUR_JS",json.dumps(snippet,ensure_ascii=False)[:1250],flush=True)
 if len(unique)>=85:break
