#!/usr/bin/env python3
"""Diagnóstico sin publicar: API oficial BOE y datos abiertos BOPT.
No guarda ni reproduce textos largos del boletín. Solo esquema y contadores.
"""
import gzip
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree as ET

URLS = [
    ("BOE_JSON_20261027", "https://www.boe.es/datosabiertos/api/boe/sumario/20261027", "application/json"),
    ("BOE_XML_20261028", "https://www.boe.es/datosabiertos/api/boe/sumario/20261028", "application/xml"),
    ("BOPT_RSS_20261028", "https://aplicacions.dipta.cat/bopt/web/datos-abiertos/boletin-del-dia/feed", "application/xml"),
    ("BOPT_RSS_LOCAL", "https://aplicacions.dipta.cat/bopt/web/datos-abiertos/boletin-del-dia/administracion-local/feed", "application/xml"),
    ("BOPT_HISTORICO_20261027", "https://aplicacions.dipta.cat/bopt/web/es", "text/html"),
]

def tag_name(tag):
    return tag.rsplit("}",1)[-1]

def summary_json(value, depth=0):
    if isinstance(value, dict):
        result = {"keys":list(value.keys())[:24]}
        if depth < 6:
            result["sample"] = {k:summary_json(v,depth+1) for k,v in list(value.items())[:8]}
        return result
    if isinstance(value,list):
        return {"length":len(value),"first":summary_json(value[0],depth+1) if value and depth < 7 else None}
    if value is None:return None
    return str(value)[:140]


def show_boe_selected_day(date="20261028"):
    try:
        req=Request("https://www.boe.es/datosabiertos/api/boe/sumario/"+date,headers={
          "Accept":"application/json", "User-Agent":"OpoAlert/1.3 Public official jobs feed"
        })
        with urlopen(req,timeout=25) as response: payload=json.load(response)
        summary=payload["data"]["sumario"]
        diario=summary["diario"]
        if isinstance(diario,dict):diario=[diario]
        rows=[]
        for issue in diario:
            for section in issue.get("seccion",[]):
                if section.get("codigo") != "2B":continue
                depts=section.get("departamento",[])
                if isinstance(depts,dict):depts=[depts]
                for dep in depts:
                    eps=dep.get("epigrafe",[])
                    if isinstance(eps,dict):eps=[eps]
                    if not eps: eps=[dep]
                    for ep in eps:
                        items=ep.get("item",[])
                        if isinstance(items,dict):items=[items]
                        rows.extend((dep.get("nombre"),ep.get("nombre"),i) for i in items)
        sample=[{"department":dept,"epigraph":ep,"keys":list(item),"sample":{k:(v if isinstance(v,str) else {key: str(val)[:70] for key,val in v.items()}) for k,v in item.items()}} for dept,ep,item in rows[:4]]
        print("BOE_2B_DETAIL="+json.dumps({"date":date,"diarios":len(diario),"count":len(rows),"samples":sample},ensure_ascii=False),flush=True)
    except Exception as exc:
        print("BOE_2B_ERROR="+repr(exc),flush=True)

show_boe_selected_day()

for name, url, accept in URLS:
    try:
        req=Request(url,headers={
            "Accept":accept,
            "User-Agent":"OpoAlert/1.3 (consulta y auditoria de boletines publicos; contacto proyecto github.com/MJTBApps/OpoAlert)",
            "Accept-Encoding":"gzip"
        })
        with urlopen(req,timeout=25) as response:
            data=response.read(3_000_000)
            if response.headers.get("Content-Encoding","").lower()=="gzip":data=gzip.decompress(data)
            content_type=response.headers.get("content-type","")
            status=response.status
        result={"name":name,"url":url,"status":status,"contentType":content_type,"bytes":len(data)}
        if b"<" in data[:50] and ("xml" in content_type or data.lstrip().startswith(b"<")):
            try:
                root=ET.fromstring(data)
                counts={}
                for element in root.iter():
                    key=tag_name(element.tag)
                    counts[key]=counts.get(key,0)+1
                result["root"]=tag_name(root.tag)
                result["rootChildren"]=[tag_name(x.tag) for x in list(root)[:10]]
                result["tags"]=dict(sorted(counts.items(),key=lambda x:-x[1])[:35])
                for e in root.iter():
                    if tag_name(e.tag) in ("item","entrada","entry"):
                        result["firstItem"]=[{"tag":tag_name(c.tag),"text":((c.text or "").strip()[:120]),"attributes":c.attrib} for c in list(e)[:12]]
                        break
                if "BOE" in name:
                    for e in root.iter():
                        if tag_name(e.tag) in ("seccion","subseccion","departamento","epigrafe"):
                            result.setdefault("hierarchyExample",[]).append({"tag":tag_name(e.tag),"attrs":e.attrib})
                            if len(result["hierarchyExample"])>=12: break
            except ET.ParseError as error:
                result["parseError"]=str(error)
                result["prefix"]=data[:200].decode("utf-8","replace")
        else:
            try:result["json"]=summary_json(json.loads(data))
            except Exception:result["prefix"]=data[:300].decode("utf-8","replace")
        print("NATIONAL_PROBE="+json.dumps(result,ensure_ascii=False),flush=True)
    except Exception as exc:
        print("NATIONAL_PROBE_ERROR="+json.dumps({"name":name,"error":str(exc)[:450]},ensure_ascii=False),flush=True)
