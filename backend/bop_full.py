#!/usr/bin/env python3
"""OpoAlert: rastreador del indice del ULTIMO BOP Valencia con paginacion.

El sitio usa componentes dinamicos JSF/PrimeFaces: no basta un GET del HTML
inicial. Se usa un navegador real Playwright, sin saltar controles del sitio.

IMPORTANTE: hasta contrastar una ejecucion real con el BOP oficial, el lector
no puede GARANTIZAR cobertura. La salida incluye estado de auditoria; ante
paginas repetidas, ausencia de paginador o fallos no se publica un falso exito.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, date
import json
from pathlib import Path
import re
import time
from typing import Any

from scan import SOURCE, extract_index, datagrid_row_count, TextParser

# PrimeFaces y variantes compatibles; no todos los portales usan el mismo HTML.
NEXT_SELECTORS = (
    ".ui-paginator-next", ".p-paginator-next",
    "button[aria-label='Next Page']", "button[aria-label='Página siguiente']",
    "a[aria-label='Página siguiente']", "button[title='Siguiente']",
    "a[title='Siguiente']", "button[title='Següent']",
)
LOAD_MORE_SELECTORS = (
    ".ui-datascroller-loader", "button:has-text('Cargar más')",
    "button:has-text('Carregar més')", "button:has-text('Mostrar más')",
    "button:has-text('Mostrar més')",
)

class CoverageError(RuntimeError):
    """No se ha demostrado que se haya examinado la edicion completa."""

@dataclass
class Audit:
    bulletin: str
    pagesVisited: int
    announcementsRead: int
    opportunities: int
    complete: bool
    status: str
    details: str


def _find_control(page: Any, selectors: tuple[str, ...]):
    for selector in selectors:
        controls = page.locator(selector)
        for i in range(min(controls.count(), 4)):
            control = controls.nth(i)
            if control.is_visible():
                return control
    return None


def _disabled(control: Any) -> bool:
    if control.is_disabled():
        return True
    classes = control.get_attribute('class') or ''
    aria = control.get_attribute('aria-disabled') or ''
    return ('ui-state-disabled' in classes or 'p-disabled' in classes
            or aria.lower() == 'true')


def _bulletin(value: str) -> str:
    return value.split('-', 1)[0]


def _index_for_issue(html: str, issue: str | None):
    entries, heading = extract_index(html)
    current_issue = issue or heading
    if not current_issue:
        raise CoverageError('No se ha podido identificar el numero de boletin')
    # Exclusiones: 'Mostrar Original' puede mostrar un anuncio de otro boletin.
    entries = [e for e in entries if _bulletin(e['bulletin']) == current_issue]
    if not entries:
        raise CoverageError('No se han encontrado anuncios del boletin actual')
    return entries, current_issue


def _visible_rows_from_html(html: str) -> int | None:
    """Filas de resultados que declara el paginador, no registros adjuntos.

    En el BOP, el HTML puede mostrar bajo una correccion el anuncio original
    de un boletin anterior. Esos registros pueden sumar 27 metadatos cuando
    la pagina dice que muestra 25 resultados. Solo toleramos los originales
    anteriores al intervalo si las entradas dentro del intervalo coinciden
    EXACTAMENTE con las 25 filas declaradas por el paginador.
    """
    parser = TextParser()
    parser.feed(html)
    text = re.sub(r"\s+", " ", "".join(parser.parts))
    match = re.search(
        r"(?:Mostrant|Mostrando)\s+(?:del|de)\s*(\d+)\s+(?:al|a)\s*(\d+)\s+de\s+([\d.,]+)",
        text, re.IGNORECASE,
    )
    if match is None:
        return None
    first, last, total = (int(re.sub(r"[^0-9]", "", value))
                          for value in match.groups())
    if first < 1 or last < first or total < last:
        raise CoverageError('Paginador de busqueda con cifras inconsistentes')
    return last - first + 1


def _index_for_range(html: str, bounds: tuple[date, date]):
    """Obtiene los anuncios reales del intervalo frente al paginador.

    El BOP incluye en el HTML registros auxiliares de otras fechas (p.ej.
    originales, correcciones o anuncios relacionados) que NO forman parte de
    las filas del resultado. Los diagnósticos del 27/10/2026 muestran 27
    registros en HTML cuando la paginación declara 25.

    Nunca basta con descartar fechas sin más: exigimos que el número de
    registros *dentro* del intervalo coincida exactamente con las filas
    anunciadas por el paginador para cada página. Si hay uno de menos,
    uno de más, no hay contador, o hay fechas mal formadas, fallamos.
    """
    entries, _heading = extract_index(html)
    if not entries:
        raise CoverageError('La busqueda no contiene anuncios legibles')
    start, end = bounds
    displayed = _visible_rows_from_html(html)
    structured_count = datagrid_row_count(html)
    if structured_count:
        # HTML real de PrimeFaces: hay exactamente una ficha principal por
        # .ui-datagrid-column. Las correcciones anidadas NO son filas aparte.
        # Por ello, cualquier ficha estructural fuera del intervalo es un
        # verdadero error de la busqueda y no se descarta silenciosamente.
        if displayed is None:
            raise CoverageError('No hay contador del paginador para las fichas del BOP')
        if len(entries) != structured_count or structured_count != displayed:
            raise CoverageError(
                f'El BOP declara {displayed} filas, el HTML contiene '
                f'{structured_count} fichas y se extrajeron {len(entries)} '
                'anuncios principales. No se confirma cobertura.')
        outside_main = []
        for row in entries:
            try:
                day = datetime.strptime(row['date'], '%d/%m/%Y').date()
            except (KeyError, ValueError) as exc:
                raise CoverageError('Fecha de ficha principal no reconocida') from exc
            if not start <= day <= end:
                outside_main.append(row)
        if outside_main:
            sample = ', '.join(f"{r['id']} ({r['date']})" for r in outside_main[:3])
            raise CoverageError(
                f'El BOP muestra {len(outside_main)} fichas principales '
                f'fuera del intervalo solicitado: {sample}')
        return entries, 'varios'
    eligible = []
    outside = []
    for row in entries:
        try:
            day = datetime.strptime(row['date'], '%d/%m/%Y').date()
        except (ValueError, KeyError) as exc:
            raise CoverageError('Una fecha de anuncio no es valida') from exc
        if start <= day <= end:
            eligible.append(row)
        else:
            outside.append(row)

    if displayed is None:
        if outside:
            raise CoverageError(
                'Hay anuncios fuera del rango y no hay un paginador que '
                'permita separar los resultados de otras referencias')
        if not eligible:
            raise CoverageError('No hay anuncios del intervalo confirmado')
        # En una pagina sin contador seguimos sin confirmar completitud; el
        # chequeo final de paginacion y total es responsabilidad del lector.
        return eligible, 'varios'

    if len(eligible) != displayed:
        example = ', '.join(sorted({r['date'] for r in outside})[:4])
        raise CoverageError(
            f'El paginador muestra {displayed} anuncios, pero el extractor '
            f'encuentra {len(eligible)} dentro de {start} a {end}; '
            f'hay {len(outside)} referencias externas ({example}). '
            'No se confirma cobertura.')

    if outside:
        example = ', '.join(sorted({r['date'] for r in outside})[:4])
        print(f'Auditoria: {len(outside)} referencias fuera del intervalo '
              f'({example}) separadas; {len(eligible)}/{displayed} '
              'resultados validos segun el paginador.', flush=True)

    if not eligible:
        raise CoverageError('No hay anuncios del intervalo confirmado')
    return eligible, 'varios'


def scan_browser(page: Any, max_pages: int = 80, polite_delay: float = 0.45,
                 date_range: tuple[date, date] | None = None):
    """Devuelve (oportunidades, auditoria). No declara completitud sin señal verificable."""
    if max_pages < 1:
        raise ValueError('max_pages debe ser positivo')

    visited_signatures = set()
    entries_by_id = {}
    issue = None
    status = 'unknown'
    detail = ''
    pages = 0

    for _ in range(max_pages):
        html = page.content()
        entries, current_issue = (
            _index_for_range(html, date_range) if date_range is not None
            else _index_for_issue(html, issue)
        )
        if issue is None:
            issue = current_issue
        elif current_issue != issue:
            raise CoverageError('El boletin ha cambiado durante la lectura')

        signature = tuple(e['id'] for e in entries)
        if signature in visited_signatures:
            raise CoverageError('El paginador repitio una pagina; escaneo interrumpido')
        visited_signatures.add(signature)
        pages += 1
        for item in entries:
            entries_by_id[item['id']] = item

        next_button = _find_control(page, NEXT_SELECTORS)
        if next_button is not None:
            if _disabled(next_button):
                status = 'paginator_last_page'
                detail = 'Se alcanzo la ultima pagina del paginador visible.'
                break
            next_button.click(timeout=12000)
            # Esperamos a que CAMBIEN los registros, no solamente a que responda la red.
            for _retry in range(22):
                page.wait_for_timeout(400)
                try:
                    new_entries, _ = (_index_for_range(page.content(), date_range) if date_range is not None else _index_for_issue(page.content(), issue))
                except (ValueError, CoverageError):
                    continue
                if tuple(e['id'] for e in new_entries) != signature:
                    break
            else:
                raise CoverageError('Se hizo clic en Siguiente pero no cambio la pagina')
            if polite_delay > 0:
                page.wait_for_timeout(int(polite_delay * 1000))
            continue

        more_button = _find_control(page, LOAD_MORE_SELECTORS)
        if more_button is not None:
            if _disabled(more_button):
                status = 'load_more_finished'
                detail = 'No hay mas resultados en el control Cargar mas.'
                break
            more_button.click(timeout=12000)
            for _retry in range(22):
                page.wait_for_timeout(400)
                new_entries, _ = (_index_for_range(page.content(), date_range) if date_range is not None else _index_for_issue(page.content(), issue))
                if tuple(e['id'] for e in new_entries) != signature:
                    break
            else:
                raise CoverageError('Cargar mas no mostro anuncios nuevos')
            if polite_delay > 0:
                page.wait_for_timeout(int(polite_delay * 1000))
            continue

        # Sin boton/paginador no se puede asumir que el HTML sea el sumario total.
        status = 'pagination_not_detected'
        detail = 'No se detecto paginador ni control Cargar mas; cobertura SIN VERIFICAR.'
        break
    else:
        raise CoverageError(f'Se alcanzo el limite de {max_pages} paginas sin llegar al final')

    all_issues = list(entries_by_id.values())
    opportunities = [e for e in all_issues if e['type'] is not None]
    audit = Audit(
        bulletin=issue or '?', pagesVisited=pages,
        announcementsRead=len(all_issues), opportunities=len(opportunities),
        complete=(status in ('paginator_last_page', 'load_more_finished')),
        status=status, details=detail,
    )
    # Atributo complementario para el historial: los boletines VISITADOS,
    # incluyendo los que no tengan plazas detectadas. No altera la forma
    # del JSON diario ni los consumidores de Audit/asdict.
    audit.issue_numbers = sorted({_bulletin(row['bulletin']) for row in all_issues})
    audit.issue_dates = sorted({datetime.strptime(row['date'], '%d/%m/%Y').date().isoformat()
                               for row in all_issues})
    return opportunities, audit



def safe_write_json(output: Path, payload: dict):
    """Reemplazo atomico: nunca deja un JSON truncado tras una interrupcion."""
    import os
    import tempfile
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                     dir=output.parent, suffix='.tmp',
                                     delete=False) as handle:
        scratch = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    try:
        os.replace(scratch, output)
    finally:
        scratch.unlink(missing_ok=True)

def publish_result(output: Path, entries: list[dict], audit: Audit, force_partial=False):
    """Historico + metadatos. No modificar resultados buenos tras falla de auditoria."""
    if not audit.complete and not force_partial:
        raise CoverageError(audit.details)

    previous = []
    prior_history_coverage = None
    if output.exists():
        existing = json.loads(output.read_text(encoding='utf-8'))
        previous = existing.get('notices', [])
        prior_history_coverage = existing.get('historyCoverage')
    by_id = {entry['id']: entry for entry in previous}
    by_id.update({entry['id']: entry for entry in entries})

    def sort_key(entry):
        day, month, year = entry.get('date', '01/01/1970').split('/')
        return year + month + day + entry['id']

    history = sorted(by_id.values(), key=sort_key, reverse=True)[:6000]
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        'schemaVersion': 1,
        'source': SOURCE,
        'lastCheckedUTC': timestamp,
        'coverage': asdict(audit),
        'countNewBulletin': len(entries),
        'notices': history,
        'warning': 'Verifica siempre el anuncio oficial. Los plazos pueden abrirse en el BOE.',
    }
    if prior_history_coverage:
        payload['historyCoverage'] = prior_history_coverage
    output.parent.mkdir(parents=True, exist_ok=True)
    safe_write_json(output, payload)
    return len(history)


def main():
    ap = argparse.ArgumentParser(description='Auditar TODAS las paginas del ultimo BOP Valencia')
    ap.add_argument('--output', type=Path, default=Path('data/convocatorias.json'))
    ap.add_argument('--max-pages', type=int, default=80)
    ap.add_argument('--headful', action='store_true', help='Mostrar navegador para diagnostico')
    ap.add_argument('--screenshot', type=Path, default=Path('backend/diagnostico_bop.png'))
    ap.add_argument('--allow-unverified', action='store_true', help='Solo diagnostico: publica un fichero parcial NO certificado')
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit('Falta Playwright: python -m pip install -r backend/requirements.txt') from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        page = browser.new_page(locale='ca-ES', viewport={'width': 1280, 'height': 900})
        try:
            page.goto(SOURCE, wait_until='domcontentloaded', timeout=60000)
            page.locator('body').wait_for(timeout=15000)
            page.wait_for_timeout(1600)
            opportunities, audit = scan_browser(page, max_pages=args.max_pages)
            print(json.dumps(asdict(audit), ensure_ascii=False, indent=2))
            if not audit.complete:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(args.screenshot), full_page=True)
                diagnostic = args.screenshot.with_suffix('.html')
                diagnostic.write_text(page.content(), encoding='utf-8')
                print('No se puede confirmar el total. Diagnostico guardado en:', diagnostic)
            count = publish_result(args.output, opportunities, audit, force_partial=args.allow_unverified)
            print(f'Guardadas {count} convocatorias; archivo: {args.output}')
            if not audit.complete:
                raise SystemExit('ALERTA: lectura INCOMPLETA. No publicar como exhaustiva.')
        except Exception:
            try:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(args.screenshot), full_page=True)
                args.screenshot.with_suffix('.html').write_text(page.content(), encoding='utf-8')
                print('Diagnostico de error:', args.screenshot)
            except Exception:
                pass
            raise
        finally:
            browser.close()

if __name__ == '__main__':
    main()
