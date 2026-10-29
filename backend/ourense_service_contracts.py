import requests,re,json
url="https://bop.depourense.es/portal/main.js"
s=requests.get(url,timeout=(12,70)).text
for phrase in ("class BoletinService {","class EdictoService {","class PortadaService {","class BusquedaService {","class CalendarioService {"):
 p=s.find(phrase)
 if p>=0:print("OUR_CLASS",phrase,json.dumps(s[p:p+9500],ensure_ascii=False)[:11500],flush=True)
for m in re.finditer(r"this\.http\.(?:get|post)\([^\n]{0,240}",s):
 t=m.group()
 if any(x in t.lower() for x in ("boletin","edicto","baseurl","fecha","ultim")):print("OUR_HTTP",json.dumps(t,ensure_ascii=False)[:330],flush=True)
