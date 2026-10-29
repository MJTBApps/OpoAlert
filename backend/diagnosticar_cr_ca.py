import requests,ssl,socket,hashlib,certifi,tempfile
from cryptography import x509
from cryptography.hazmat.primitives import serialization
host="bop.dipucr.es"
url="https://secure.globalsign.com/cacert/gsgccr6alphasslca2025.crt"
try:
 r=requests.get(url,timeout=(10,18))
 print("DOWNLOAD",r.status_code,r.url,len(r.content),r.headers.get("content-type"),flush=True)
 r.raise_for_status()
 try:cert=x509.load_der_x509_certificate(r.content)
 except ValueError:cert=x509.load_pem_x509_certificate(r.content)
 print("INTERMEDIATE SUBJECT",cert.subject.rfc4514_string(),flush=True)
 print("INTERMEDIATE ISSUER",cert.issuer.rfc4514_string(),flush=True)
 ctx=ssl._create_unverified_context()
 with socket.create_connection((host,443),timeout=15) as sock:
  with ctx.wrap_socket(sock,server_hostname=host) as tls:
   leaf=x509.load_der_x509_certificate(tls.getpeercert(binary_form=True))
 print("ISSUER MATCH",cert.subject==leaf.issuer,flush=True)
 if cert.subject!=leaf.issuer:raise ValueError("issuer mismatch")
 with tempfile.NamedTemporaryFile("wb",delete=False) as p:
  p.write(open(certifi.where(),"rb").read()+b"\n"+cert.public_bytes(serialization.Encoding.PEM))
  bundle=p.name
 answer=requests.get("https://bop.dipucr.es/bop/2026/10/29",timeout=(12,20),verify=bundle)
 print("BOP-VERIFY",answer.status_code,"LEN",len(answer.content),answer.url,flush=True)
except Exception as e:print("ERROR",type(e).__name__,str(e)[:500],flush=True);raise
