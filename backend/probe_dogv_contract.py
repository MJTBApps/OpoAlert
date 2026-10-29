import requests,re,json
s=requests.get("https://dogv.gva.es/dogv-portal-frontend/main.2de782d451d4153cb7a7.js",timeout=(12,75)).text
for term in ["server_url:","domain:","summary_controller:","dogv_controller:","sumario_controller:","export_controller:","getDogvLatest()","getDogvByDate(","getDogvByNum(","getDogvSummary(","getDogvSummaryByDate(","getDogvByFecha(","getIdDogvTopografico(","getDogvOriginal(","getDisposicionesSumario(","getResumen","getDogvFecha","sumario/{numDogv}/pdf"]:
 matches=list(re.finditer(re.escape(term),s,re.I))
 print("DOGV_FIND",term,len(matches),flush=True)
 for m in matches[-3:]:
  print("DOGV_CONTEXT",term,json.dumps(s[max(0,m.start()-240):m.end()+1500],ensure_ascii=False)[:2800],flush=True)
