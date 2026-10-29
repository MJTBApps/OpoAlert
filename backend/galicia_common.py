#!/usr/bin/env python3
"""Galicia supplementary hiring-title detection across Galician and Spanish."""
from clm_common import employment
from provincial_common import fold
def galicia_employment(title):
    t=" ".join(fold(title).split())
    negatives=(
      "convocatoria de subvenc", "convocatoria para subvenc","convocatoria de axudas",
      "convocatoria de ayudas","convocatoria de premios","convocatoria de asamblea",
      "convocatoria de asemblea","contratacion de obras","contratacion de suministros",
      "lista definitiva de", "lista provisional de", "listado provisional de",
      "listaxe definitiva de", "relacion definitiva de", "relacion provisional de",
      "admitidos","admitidas","excluidos","excluidas","nomeamento",
      "nombramiento","tribunal cualificador","tribunal calificador",
      "resolucion definitiva","resultado do proceso","concurso de traslados",
      "concurso de meritos resolto","correccion de erros","correccion de errores",
      "bolsa de suplentes","becas", "bolsas de estudo", "bolsas de estudios",
      "licitacion", "poxa","subasta", "seleccion de empresas", "seleccion de proveedores",
      "seleccion de viticultores","seleccion de beneficiarios",
    )
    if any(x in t for x in negatives):return None
    if "bolsa" in t or "bolsas" in t:
        if any(x in t for x in ("persoal","personal","traballo","trabajo","emprego","empleo","interin","seleccion","contratacion")):
            return "Bolsa de trabajo"
    if any(x in t for x in ("proceso selectivo","procesos selectivos","pruebas selectivas","probas selectivas",
            "seleccion de persoal","seleccion de personal","convocatoria de prazas",
            "convocatoria de plazas","oferta de emprego publico","oferta de empleo publico",
            "bases reguladoras para a seleccion","bases para a seleccion","bases para la seleccion",
            "provision de postos","provision de puestos","concurso oposicion","concurso-oposicion",
            "cobertura de prazas","cobertura de plazas")):
        return "Plaza / oposición"
    if any(x in t for x in ("praza","prazas","plaza","plazas","puesto de trabajo","posto de traballo","persoal laboral","personal laboral",
            "persoal funcionario","personal funcionario")) and any(x in t for x in
            ("convocatoria","convoca","seleccion","cobertura","bases","provision",
             "ingreso","acceso libre","oposicion","oposicion","contratacion")):
        return "Plaza / oposición"
    return employment(title)
