import sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parent))
from teruel_bop import scan
result=scan(date(2026,10,13))
print('RESULT',result,flush=True)
