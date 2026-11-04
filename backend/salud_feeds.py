"""Comprueba que los feeds que lee la app siguen al día.

Un fallo suelto de un lector no es una avería: se conserva el feed anterior y la
siguiente ronda lo vuelve a intentar. Lo que sí importa al usuario es que un feed
se quede viejo. Este script falla solo si algún feed de `Province.kt` lleva más
de MAX_HOURS horas sin una lectura validada (sin contar sábados ni domingos,
porque varias fuentes solo se leen de lunes a viernes).

    python backend/salud_feeds.py [--docs docs] [--max-hours 30]
"""
import argparse,json,re,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROVINCE=ROOT/"app/src/main/java/es/opoalert/app/Province.kt"
MAX_HOURS=30

def feeds():
    text=PROVINCE.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'"https://mjtbapps\.github\.io/OpoAlert/([\w./-]+\.json)"',text)))

def weekday_hours(start,end):
    """Horas entre start y end sin contar sábados ni domingos (UTC)."""
    total=0.0;t=start
    while t<end:
        step=min(end,(t+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0))
        if t.weekday()<5:total+=(step-t).total_seconds()/3600
        t=step
    return total

def check(docs,now,max_hours=MAX_HOURS):
    stale=[]
    for name in feeds():
        path=Path(docs)/name
        try:
            checked=json.loads(path.read_text(encoding="utf-8"))["lastCheckedUTC"]
            when=datetime.fromisoformat(checked.replace("Z","+00:00"))
        except Exception as ex:
            stale.append(f"{name}: no se puede leer ({ex})");continue
        age=weekday_hours(when,now)
        if age>max_hours:stale.append(f"{name}: última lectura validada {checked} ({age:.0f} h laborables)")
    return stale

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs",default=str(ROOT/"docs"));ap.add_argument("--max-hours",type=float,default=MAX_HOURS)
    a=ap.parse_args()
    stale=check(a.docs,datetime.now(timezone.utc),a.max_hours)
    print(f"{len(feeds())} feeds revisados, {len(stale)} sin actualizar")
    for s in stale:print(f"::error title=Feed sin actualizar::{s}")
    sys.exit(1 if stale else 0)

if __name__=="__main__":
    main()
