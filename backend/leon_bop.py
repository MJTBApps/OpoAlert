#!/usr/bin/env python3
"""BOP León, plataforma OpenCms (igual Granada/Sevilla): 30 días y PDF originales."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from andalucia_opencms_bop import Source,audit
LEON=Source("leon","León","LN","bop.dipuleon.es","BOP-LE")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    x=audit(LEON)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"LEON AUDITADO: {x['historyCoverage']['issuesRead']} boletines, "
      f"{x['coverage']['announcementsRead']} anuncios, "
      f"{len(x['notices'])} candidatas",flush=True)
