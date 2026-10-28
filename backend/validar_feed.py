#!/usr/bin/env python3
"""Validacion independiente de la auditoria de OpoAlert antes de publicar.

El validador no afirma haber visitado el BOP: verifica coherencia interna de
las evidencias que generaron los lectores Playwright. Ante dudas, NO publica.
Sin dependencias externas: utilizable en Windows y GitHub Actions.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qs

SOURCE = 'https://bop.dival.es/bop/xhtml/portal.xhtml'
VALID_KINDS = {'Bolsa de trabajo', 'Plaza / oposición'}
DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')
ID_RE = re.compile(r'^\d{4}/\d{3,7}$')


class FeedValidationError(ValueError):
    pass


def _require(ok: bool, description: str):
    if not ok:
        raise FeedValidationError(description)


def _iso(value, what):
    try:
        _require(isinstance(value, str), f'{what}: fecha ausente')
        return date.fromisoformat(value)
    except ValueError as exc:
        raise FeedValidationError(f'{what}: fecha ISO invalida: {value!r}') from exc


def _utc(value, what):
    try:
        _require(isinstance(value, str), f'{what}: fecha ausente')
        instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
        _require(instant.tzinfo is not None, f'{what}: falta zona horaria')
        return instant.astimezone(timezone.utc)
    except ValueError as exc:
        raise FeedValidationError(f'{what}: fecha/hora invalida: {value!r}') from exc


def _int(value, what, minimum=0):
    _require(type(value) is int and value >= minimum, f'{what}: entero invalido')
    return value


def validate_feed(payload: dict, *, expected_end: date | None = None,
                  max_age: timedelta | None = None,
                  now: datetime | None = None) -> dict:
    """Devuelve estadisticas si el JSON respeta un historico de 30 dias.

    No confia en un mero `complete: true`: exige auditoria de cada intervalo,
    fechas publicadas/ausentes exhaustivas y contadores conciliados.
    """
    _require(isinstance(payload, dict), 'La raiz JSON no es un objeto')
    _require(payload.get('schemaVersion') == 1, 'Version del feed no compatible')
    _require(payload.get('source') == SOURCE, 'Fuente diferente del BOP Valencia')
    timestamp = _utc(payload.get('lastCheckedUTC'), 'lastCheckedUTC')
    now = now or datetime.now(timezone.utc)
    _require(timestamp <= now + timedelta(minutes=10), 'El feed tiene una fecha futura')
    if max_age is not None:
        _require(now - timestamp <= max_age, 'El feed es demasiado antiguo para su publicacion')

    latest = payload.get('coverage')
    _require(isinstance(latest, dict) and latest.get('complete') is True,
             'Falta auditoria valida del ultimo boletin')
    _require(latest.get('status') in ('paginator_last_page', 'load_more_finished'),
             'No esta confirmado el paginador del ultimo BOP')
    _int(latest.get('pagesVisited'), 'coverage.pagesVisited', 1)
    daily_count = _int(latest.get('opportunities'), 'coverage.opportunities')
    _require(_int(latest.get('announcementsRead'), 'coverage.announcementsRead', 1) >= daily_count,
             'Anuncios del ultimo BOP inconsistentes')
    _require(payload.get('countNewBulletin') == daily_count,
             'El recuento del ultimo BOP no cuadra con su auditoria')

    history = payload.get('historyCoverage')
    _require(isinstance(history, dict) and history.get('complete') is True,
             'Historico NO validado')
    _require(history.get('status') == 'windows_ajax_verified',
             'El historico no tiene la auditoria de busquedas AJAX')
    first = _iso(history.get('rangeStart'), 'historyCoverage.rangeStart')
    last = _iso(history.get('rangeEnd'), 'historyCoverage.rangeEnd')
    _require(last >= first and (last-first).days == 29,
             'La cobertura historica no tiene exactamente 30 dias')
    if expected_end is not None:
        _require(last == expected_end, f'Historico caducado: termina el {last}, no el {expected_end}')
    verified = _utc(history.get('verifiedUTC'), 'historyCoverage.verifiedUTC')
    _require(verified <= timestamp + timedelta(minutes=10),
             'Historial verificado despues de la fecha del feed')

    chunks = history.get('chunks')
    _require(isinstance(chunks, list) and chunks,
             'Faltan las ventanas auditadas del historico')
    expected_dates = {first+timedelta(days=i) for i in range(30)}
    visited_dates = set()
    edition_dates = set()
    seen_issues = set()
    pages = announced = candidates = 0
    for i, chunk in enumerate(chunks, 1):
        label = f'Ventana {i}'
        _require(isinstance(chunk, dict) and chunk.get('complete') is True,
                 f'{label}: incompleta')
        start = _iso(chunk.get('requestedStart'), f'{label}.requestedStart')
        end = _iso(chunk.get('requestedEnd'), f'{label}.requestedEnd')
        _require(first <= start <= end <= last, f'{label}: limites fuera del rango')
        span = {start + timedelta(days=k) for k in range((end-start).days+1)}
        _require(not (visited_dates & span), f'{label}: solapamiento de ventanas')
        visited_dates.update(span)
        dates = chunk.get('publishedDates', [])
        missing = chunk.get('nonPublicationDates', [])
        _require(isinstance(dates, list) and isinstance(missing, list),
                 f'{label}: listado de fechas invalido')
        published = [_iso(d, f'{label}.publishedDates') for d in dates]
        absent = [_iso(d, f'{label}.nonPublicationDates') for d in missing]
        _require(len(set(published+absent)) == len(published+absent),
                 f'{label}: fechas repetidas entre publicadas y ausentes')
        _require(set(published+absent) == span,
                 f'{label}: el calendario no cubre todos los dias naturales')
        edition_dates.update(published)
        chunk_pages = _int(chunk.get('pagesVisited'),f'{label}.pagesVisited')
        chunk_announced = _int(chunk.get('announcementsRead'),f'{label}.announcementsRead')
        chunk_candidates = _int(chunk.get('opportunities'),f'{label}.opportunities')
        _require(chunk_announced >= chunk_candidates, f'{label}: candidatos > anuncios')
        issues = chunk.get('bulletins')
        _require(isinstance(issues, list) and all(isinstance(x,str) and x.isdigit() for x in issues),
                 f'{label}: numeros de boletin invalidos')
        if published:
            _require(chunk_pages > 0 and chunk_announced > 0 and issues,
                     f'{label}: faltan anuncios para fechas con boletin')
            _require(_iso(chunk.get('start'), f'{label}.start') == min(published) and
                     _iso(chunk.get('end'), f'{label}.end') == max(published),
                     f'{label}: extremos no son dias de publicacion')
        else:
            _require(chunk_pages == 0 and chunk_announced == 0 and chunk_candidates == 0 and not issues,
                     f'{label}: una ventana sin boletin no puede contener resultados')
        seen_issues.update(issues)
        pages += chunk_pages
        announced += chunk_announced
        candidates += chunk_candidates
    _require(visited_dates == expected_dates, 'Las ventanas no cubren los 30 dias')
    _require(len(seen_issues) >= 2, 'Menos de dos boletines recuperados')
    _require(history.get('bulletins') == sorted(seen_issues),
             'La lista de boletines no coincide con los intervalos')
    _require(_int(history.get('pagesVisited'),'historyCoverage.pagesVisited') == pages,
             'Descuadre de paginas totales')
    _require(_int(history.get('announcementsRead'),'historyCoverage.announcementsRead') == announced,
             'Descuadre de anuncios totales')
    _require(_int(history.get('opportunities'),'historyCoverage.opportunities') == candidates,
             'Descuadre de oportunidades totales')

    notices = payload.get('notices')
    _require(isinstance(notices,list) and len(notices) <= 5000,
             'No hay una lista de convocatorias valida')
    _require(len(notices) == candidates,
             'Faltan convocatorias o se mezclan anuncios de fuera del rango')
    seen_ids = set()
    for index, row in enumerate(notices, 1):
        label = f'Convocatoria {index}'
        _require(isinstance(row, dict), f'{label}: ficha no valida')
        reg = row.get('id')
        _require(isinstance(reg,str) and bool(ID_RE.fullmatch(reg)),
                 f'{label}: identificador invalido')
        _require(reg not in seen_ids, f'{label}: registro duplicado {reg}')
        seen_ids.add(reg)
        raw = row.get('date')
        _require(isinstance(raw,str) and bool(DATE_RE.fullmatch(raw)),
                 f'{label}: fecha de publicacion invalida')
        try:
            publication = datetime.strptime(raw,'%d/%m/%Y').date()
        except ValueError as exc:
            raise FeedValidationError(f'{label}: fecha inexistente {raw!r}') from exc
        _require(publication in edition_dates,
                 f'{label}: publicacion fuera de dias del historico: {raw}')
        _require(str(row.get('bulletin')) in seen_issues,
                 f'{label}: boletin desconocido')
        _require(row.get('type') in VALID_KINDS,
                 f'{label}: tipo de convocatoria desconocido')
        _require(isinstance(row.get('title'),str) and bool(row['title'].strip()),
                 f'{label}: titulo vacio')
        _require(isinstance(row.get('entity'),str) and bool(row['entity'].strip()),
                 f'{label}: organismo vacio')
        url = row.get('url')
        _require(isinstance(url,str), f'{label}: URL ausente')
        parts = urlsplit(url)
        _require(parts.scheme == 'https' and parts.netloc == 'bop.dival.es' and
                 parts.path == '/bop/downloads' and not parts.username and not parts.password and
                 parse_qs(parts.query).get('anuncioNumReg') == [reg],
                 f'{label}: enlace oficial o registro incorrecto')
    return {'rangeStart':first.isoformat(),'rangeEnd':last.isoformat(),
            'daysWithBulletin':len(edition_dates),'bulletins':len(seen_issues),
            'pages':pages,'announcements':announced,'opportunities':len(notices)}


def main():
    parser = argparse.ArgumentParser(description='Verificar feed OpoAlert sin acceder al BOP')
    parser.add_argument('--input', type=Path, default=Path('docs/convocatorias.json'))
    parser.add_argument('--require-today', action='store_true', help='Exige que el rango termine hoy')
    parser.add_argument('--max-age-hours', type=float, default=None)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding='utf-8'))
        details = validate_feed(
            payload,
            expected_end=date.today() if args.require_today else None,
            max_age=timedelta(hours=args.max_age_hours) if args.max_age_hours is not None else None,
        )
    except (OSError, ValueError, TypeError) as exc:
        print('BLOQUEADO: feed NO publicable. ' + str(exc))
        return 1
    print('VALIDADO:', json.dumps(details, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
