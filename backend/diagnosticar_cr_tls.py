#!/usr/bin/env python3
"""Diagnose Ciudad Real BOP certificate without treating unverified HTML as feed."""
import ssl,socket,hashlib,requests
from cryptography import x509
from cryptography.x509.oid import ExtensionOID,AuthorityInformationAccessOID
HOST="bop.dipucr.es"
print("SSL",ssl.OPENSSL_VERSION,flush=True)
ctx=ssl._create_unverified_context()
with socket.create_connection((HOST,443),timeout=15) as sock:
 with ctx.wrap_socket(sock,server_hostname=HOST) as tls:
  der=tls.getpeercert(binary_form=True)
cert=x509.load_der_x509_certificate(der)
print("SUBJECT",cert.subject.rfc4514_string(),flush=True)
print("ISSUER",cert.issuer.rfc4514_string(),flush=True)
print("SHA256",hashlib.sha256(der).hexdigest(),flush=True)
print("DATES",cert.not_valid_before_utc.isoformat(),cert.not_valid_after_utc.isoformat(),flush=True)
try:
 aid=cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
 print("AIA",[(a.access_method.dotted_string,a.access_location.value) for a in aid],flush=True)
except Exception as e:print("AIA",str(e)[:100],flush=True)
for url in ["https://bop.dipucr.es/","https://se1.dipucr.es:4443/SIGEM_BuscadorDocsWeb/getDocument.do?entidad=005&doc=7852888"]:
 try:
  v=requests.get(url,timeout=12,stream=True)
  print("VERIFIED",url,v.status_code,v.headers.get("Content-Type"),flush=True)
  v.close()
 except Exception as e:print("TLS-ERROR",url,type(e).__name__,str(e)[:450],flush=True)
