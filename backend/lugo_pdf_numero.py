import requests,io,re
from pypdf import PdfReader
url="https://deputacionlugo.gal/sites/deputacionlugo.org/files/2026-10/03-10-2026%20spa.pdf"
r=requests.get(url,timeout=(12,40));print("LUGO03_PDF",r.status_code,len(r.content),r.headers.get("Content-Type"),flush=True);r.raise_for_status()
print("LUGO03_TEXT",repr(PdfReader(io.BytesIO(r.content)).pages[0].extract_text()[:1100]),flush=True)
