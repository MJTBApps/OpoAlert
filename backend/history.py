#!/usr/bin/env python3
"""OpoAlert: intenta recuperar boletines previos usando la busqueda por fechas.

Solo registra un rango como completo si se ha aplicado el filtro y se ha alcanzado
la ultima pagina. Primer uso: ejecutar en Windows y verificar el diagnostico.
No marca 30 dias como verificados cuando el sitio cambia o no aplica el filtro.
"""
from __future__ import annotations
import argparse
import html as html_module
import unicodedata
from xml.etree import ElementTree
from dataclasses import asdict
from html.parser import HTMLParser
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
import traceback
from urllib.parse import parse_qs

from scan import SOURCE
from idioma_bop import seleccionar_castellano
from bop_full import CoverageError, scan_browser, safe_write_json, Audit


def _normalized_date(value: str) -> str | None:
    """Reconoce el valor del formulario sin confundir su formato con pérdida."""
    value = value.strip()
    for pattern in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d.%m.%Y',
                    '%d/%m/%y', '%d-%m-%y'):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass
    return None


def _read_date_fields(page):
    """Usa los IDs reales confirmados en el diagnostico del BOP Valencia.

    Buscar por texto 'Des de'/'Fins a' puede encontrar un nodo distinto
    del calendario y terminar comprobando un input equivocado. PrimeFaces
    puede reconstruir inputs tras AJAX; por eso obtenemos locators de nuevo.
    """
    selectors = ('[id="filtroCalendarioIni_input"]',
                 '[id="filtroCalendarioFin_input"]')
    controls = []
    for selector in selectors:
        control = page.locator(selector)
        if control.count() != 1 or not control.first.is_visible():
            raise CoverageError('No se encontro el calendario oficial: ' + selector)
        controls.append(control.first)
    return tuple(controls)


def _values_match(page, first: date, last: date) -> bool:
    start, end = _read_date_fields(page)
    actual_first = _normalized_date(start.input_value())
    actual_last = _normalized_date(end.input_value())
    return actual_first == first.isoformat() and actual_last == last.isoformat()


# OpoAlert 0.4.7: el BOP rechaza fechas antiguas escritas a mano
# ("Des de: Validation Error: Value is not valid."). Seleccionamos
# las fechas mediante los controles reales del calendario de PrimeFaces.
_MONTH_NAMES = (
    ('gener', 'enero', 'january'),
    ('febrer', 'febrero', 'february'),
    ('marc', 'marzo', 'march'),
    ('abril', 'april'),
    ('maig', 'mayo', 'may'),
    ('juny', 'junio', 'june'),
    ('juliol', 'julio', 'july'),
    ('agost', 'agosto', 'august'),
    ('setembre', 'septiembre', 'september'),
    ('octubre', 'october'),
    ('novembre', 'noviembre', 'november'),
    ('desembre', 'diciembre', 'december'),
)


def _normalize_calendar_word(value: str) -> str:
    value = unicodedata.normalize('NFKD', value.lower())
    return ''.join(c for c in value if not unicodedata.combining(c)).strip()


def _month_number(value: str, is_select: bool = False) -> int:
    word = _normalize_calendar_word(value)
    if word.isdigit():
        number = int(word)
        if is_select and 0 <= number <= 11:
            return number + 1  # Las opciones de jQuery usan meses 0..11.
        if 1 <= number <= 12:
            return number
    for index, names in enumerate(_MONTH_NAMES, 1):
        if any(word == name or word.startswith(name + ' ') for name in names):
            return index
    raise CoverageError('Mes no reconocido en el calendario: ' + repr(value))


def _visible_calendar_month(panel) -> tuple[int, int]:
    title = panel.locator('.ui-datepicker-title')
    if title.count() != 1:
        raise CoverageError('No se encuentra el titulo del calendario del BOP')
    month_el = title.locator('.ui-datepicker-month')
    year_el = title.locator('.ui-datepicker-year')
    if not month_el.count() or not year_el.count():
        raise CoverageError('Faltan mes o ano en el calendario desplegable')
    month_el, year_el = month_el.first, year_el.first
    month_select = month_el.evaluate('(el) => el.tagName === "SELECT"')
    year_select = year_el.evaluate('(el) => el.tagName === "SELECT"')
    if month_select:
        selected_option = month_el.locator('option:checked')
        selected_label = selected_option.first.inner_text() if selected_option.count() else ''
        try:
            month = _month_number(selected_label)
        except CoverageError:
            month = _month_number(month_el.input_value(), is_select=True)
    else:
        month = _month_number(month_el.inner_text())
    year_text = year_el.input_value() if year_select else year_el.inner_text()
    match = re.search(r'\b(?:19|20)\d{2}\b', year_text)
    if not match:
        raise CoverageError('Ano no reconocido en el calendario: ' + repr(year_text))
    return int(match.group()), month


def _date_panel(page, base_id: str):
    panel = page.locator('[id="' + base_id + '_panel"]')
    if panel.count() != 1:
        raise CoverageError('Falta el calendario de ' + base_id)
    return panel


def _open_date_panel(page, base_id: str):
    field = page.locator('[id="' + base_id + '_input"]')
    if field.count() != 1:
        raise CoverageError('No se encuentra el campo ' + base_id)
    field.click(timeout=10000)
    panel = _date_panel(page, base_id)
    if not panel.is_visible():
        # PrimeFaces permite configurar que el popup se abra por el boton.
        trigger = page.locator('[id="' + base_id + '"] .ui-datepicker-trigger')
        if trigger.count() and trigger.first.is_visible():
            trigger.first.click(timeout=10000)
    if not panel.is_visible():
        raise CoverageError('No se abrio el calendario de ' + base_id)
    return panel


def _go_to_calendar_month(page, panel, target: date):
    for _ in range(18):
        current = _visible_calendar_month(panel)
        wanted = (target.year, target.month)
        if current == wanted:
            return
        backwards = current > wanted
        selector = '.ui-datepicker-prev' if backwards else '.ui-datepicker-next'
        arrow = panel.locator(selector)
        if not arrow.count() or not arrow.first.is_visible():
            raise CoverageError('El calendario no permite navegar a ' + target.isoformat())
        arrow.first.click(timeout=10000)
        page.wait_for_timeout(100)
        if _visible_calendar_month(panel) == current:
            raise CoverageError('La flecha del calendario no cambio el mes')
    raise CoverageError('No se pudo navegar al mes ' + target.strftime('%m/%Y'))


def _choose_calendar_day(panel, target: date):
    # El calendario del BOP muestra dias del mes anterior/siguiente.
    # Nunca elegir un dia de otra celda aunque tenga el mismo numero.
    cells = panel.locator('td:not(.ui-datepicker-other-month):not(.ui-state-disabled):not(.ui-datepicker-unselectable)')
    for index in range(cells.count()):
        cell = cells.nth(index)
        if not cell.is_visible():
            continue
        text = cell.inner_text().strip()
        if text != str(target.day):
            continue
        link = cell.locator('a.ui-state-default, a[data-date], a, button, [role="button"]')
        if link.count() and link.first.is_visible():
            link.first.click(timeout=10000)
        else:
            # Algunos temas PrimeFaces usan un span clicable.
            cell.click(timeout=10000)
        return
    raise CoverageError('El calendario no ofrece como seleccionable el dia ' +
                        target.strftime('%d/%m/%Y') +
                        '. Puede tener restricciones propias del servidor.')


def _choose_date(page, base_id: str, target: date):
    panel = _open_date_panel(page, base_id)
    _go_to_calendar_month(page, panel, target)
    _choose_calendar_day(panel, target)
    field = page.locator('[id="' + base_id + '_input"]')
    actual = _normalized_date(field.input_value())
    if actual != target.isoformat():
        raise CoverageError('El calendario no selecciono ' + target.isoformat() +
                            '; valor actual ' + repr(field.input_value()))


def fill_date_range(page, first: date, last: date):
    """Selecciona fechas con el calendario oficial, NO con fill() ni JS.

    Los diagnósticos 0.4.6 confirmaron que el BOP acepta fechas recientes,
    pero rechaza una antigua al escribirla directamente: error JSF de 'Des de'.
    Un clic real en el dia debe permitir al widget validar su estado.
    """
    if last < first:
        raise CoverageError('Las fechas estan invertidas')
    _choose_date(page, 'filtroCalendarioFin', last)
    _choose_date(page, 'filtroCalendarioIni', first)
    if not _values_match(page, first, last):
        raise CoverageError('El calendario cambio una fecha al seleccionar la otra')
    print('Fechas seleccionadas desde los calendarios: ' +
          first.strftime('%d/%m/%Y') + ' -> ' + last.strftime('%d/%m/%Y'))


def _jsf_messages(xml_text: str) -> list[str]:
    """Lee las validaciones del XML AJAX, no confunde HTTP 200 con exito."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []
    messages = []
    for element in root.iter():
        tag = element.tag.rsplit('}', 1)[-1]
        update_id = element.attrib.get('id', '').lower()
        if tag == 'update' and ('message' in update_id or 'error' in update_id):
            rendered = html_module.unescape(element.text or '')
            cleaned = re.sub(r'<[^>]*>', ' ', rendered)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned:
                messages.append(cleaned[:400])
    return messages


def _validation_error_text(xml_text: str) -> str | None:
    for message in _jsf_messages(xml_text):
        if re.search(r'validation error|value is not valid|validaci[oó]|no es v[aá]lid|no [eé]s v[aà]lid',
                     message, re.IGNORECASE):
            return message
    return None


def _search_button(page):
    """Boton real del formulario, identificado en el error Playwright del BOP."""
    primary = page.locator('[id="buscarBtn"]')
    if primary.count() == 1 and primary.is_visible() and primary.is_enabled():
        return primary

    # Reserva para otras traducciones o cambios del portal.
    for selector in (
        "button:has-text('Cerca')", "button:has-text('Buscar')",
        "input[type='submit'][value='Cerca']",
        "input[type='submit'][value='Buscar']",
    ):
        nodes = page.locator(selector)
        for index in range(min(nodes.count(), 4)):
            control = nodes.nth(index)
            if control.is_visible() and control.is_enabled():
                return control
    raise CoverageError('No se encontro el boton Buscar/Cerca del formulario oficial')


def _datepicker_open(page):
    """Los calendarios PrimeFaces pueden impedir el clic fisico en Buscar."""
    for selector in ('[id="filtroCalendarioIni_panel"]',
                     '[id="filtroCalendarioFin_panel"]'):
        panel = page.locator(selector)
        if panel.count() and panel.is_visible():
            return True
    return False


def _is_search_ajax(response) -> bool:
    """Reconoce la RESPUESTA AJAX del boton Buscar del propio portal JSF."""
    request = response.request
    if request.method != 'POST':
        return False
    data = request.post_data or ''
    return ('buscarBtn' in data and 'portal.xhtml' in response.url)


def _posted_date_values(post_data: str) -> tuple[str | None, str | None]:
    """Comprueba las fechas que de verdad se enviaron al servidor, no solo el DOM."""
    form = parse_qs(post_data or '', keep_blank_values=True)
    start = form.get('filtroCalendarioIni_input', [None])[-1]
    end = form.get('filtroCalendarioFin_input', [None])[-1]
    return start, end


def _paginator_total(page) -> int | None:
    """Total que declara el paginador del portal (si lo expone)."""
    text = page.locator('body').inner_text()
    # Variantes valencianas y castellanas: Mostrant del 1 al 25 de 66.
    match = re.search(
        r'(?:Mostrant|Mostrando)\s+(?:del|de)\s*\d+\s+(?:al|a)\s*\d+\s+de\s+([\d.,]+)',
        text, re.IGNORECASE,
    )
    if not match:
        return None
    number = re.sub(r'[^0-9]', '', match.group(1))
    return int(number) if number else None


def _search_diagnostic(page, first: date, last: date, status: str):
    """Metadatos no sensibles: sin ViewState, HTML completo ni cookies."""
    try:
        from scan import extract_index
        entries, _ = extract_index(page.content())
        issue_ids = sorted({e['bulletin'] for e in entries})
        dates = sorted({e['date'] for e in entries})
        return {'rangeStart':first.isoformat(), 'rangeEnd':last.isoformat(),
                'state':status, 'rowsOnPage':len(entries), 'issueNumbers':issue_ids,
                'datesOnPage':dates, 'paginatorTotal':_paginator_total(page)}
    except Exception as exc:
        return {'rangeStart':first.isoformat(), 'rangeEnd':last.isoformat(),
                'state':status, 'diagnosticError':str(exc)[:180]}


def search_date_range(page, first: date, last: date):
    """Busca y ESPERA la confirmacion AJAX real del BOP, no un tiempo fijo.

    En versiones anteriores se pulsaba buscar y se recorria el sumario antiguo.
    Ahora se comprueba que el navegador haya recibido una respuesta AJAX del
    servidor, con las DOS fechas correctas en el POST. Una respuesta de error
    o ausente cancela el proceso antes de publicar resultados.
    """
    fill_date_range(page, first, last)
    if not _values_match(page, first, last):
        raise CoverageError('Las fechas cambiaron antes de pulsar Buscar')

    button = _search_button(page)
    print('Buscando del ' + first.strftime('%d/%m/%Y') + ' al ' +
          last.strftime('%d/%m/%Y') + ': esperando la respuesta AJAX real...')

    if not hasattr(page, 'expect_response'):
        # Paginas simuladas en pruebas de regresion existentes: no afirmamos
        # haber validado ninguna respuesta del servidor.
        button.dispatch_event('click')
        page.wait_for_timeout(200)
        error_dialog = page.locator('[id="dlgBusquedaError"]')
        if error_dialog.count() and error_dialog.is_visible():
            raise CoverageError('El BOP ha mostrado un error al buscar por fechas')
        return {'mode':'test_only', 'serverConfirmed':False}

    try:
        with page.expect_response(_is_search_ajax, timeout=90000) as pending:
            button.dispatch_event('click')
        response = pending.value
    except Exception as exc:
        raise CoverageError(
            'No se ha recibido respuesta AJAX de Buscar. No se asume que el '
            'filtro se aplico. ' + str(exc)[:180]
        ) from exc

    posted_first, posted_last = _posted_date_values(response.request.post_data or '')
    if (_normalized_date(posted_first or '') != first.isoformat() or
            _normalized_date(posted_last or '') != last.isoformat()):
        raise CoverageError(
            'El formulario envio fechas diferentes al servidor. '
            f'Enviado: desde={posted_first!r}, hasta={posted_last!r}; '
            'el calendario JSF puede estar revirtiendo los valores.'
        )

    if response.status != 200:
        raise CoverageError('El BOP devolvio HTTP ' + str(response.status))
    content = response.text()
    if '<partial-response' not in content.lower():
        raise CoverageError('La respuesta del BOP no es una actualizacion AJAX JSF valida')
    if re.search(r'<error(?:\s|>)', content, re.IGNORECASE):
        raise CoverageError('El BOP devolvio un error AJAX al ejecutar la busqueda')
    validation_message = _validation_error_text(content)
    if validation_message:
        raise CoverageError('El servidor rechazo un campo del formulario: ' + validation_message[:350])
    # Que llegue XML no implica que los anuncios ya se hayan redibujado.
    # Esperar a que jQuery/PrimeFaces termine de procesar la respuesta.
    try:
        page.wait_for_function(
            "() => !window.jQuery || window.jQuery.active === 0",
            timeout=20000,
        )
    except Exception as exc:
        raise CoverageError('El portal no termino de aplicar la respuesta de busqueda') from exc
    page.wait_for_timeout(500)
    error_dialog = page.locator('[id="dlgBusquedaError"]')
    if error_dialog.count() and error_dialog.is_visible():
        raise CoverageError('El BOP ha mostrado un error al buscar por fechas')

    report = _search_diagnostic(page, first, last, 'ajax_completed')
    print('Respuesta aplicada:', json.dumps(report, ensure_ascii=False))
    return {'mode':'primefaces_ajax', 'serverConfirmed':True,
            'report':report}


class _BOPPublicationCalendarParser(HTMLParser):
    """Extrae exclusivamente dias enlazados del calendario oficial del BOP.

    Los dias sin publicacion vienen como <span ... ui-state-disabled>, en
    vez de <a>. Nunca considerar habilitados esos dias, aunque un <td>
    contenga su numero. Esta distincion se observo en el HTML real del 27/10.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside_table = False
        self.inside_cell = False
        self.cell_allowed = False
        self.collect_day = False
        self.current_text = []
        self.days = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set((attributes.get('class') or '').split())
        if tag == 'table' and 'ui-datepicker-calendar' in classes:
            self.inside_table = True
        elif self.inside_table and tag == 'td':
            self.inside_cell = True
            self.cell_allowed = not bool(classes & {
                'ui-datepicker-other-month', 'ui-datepicker-unselectable',
                'ui-state-disabled', 'p-disabled'})
        elif self.inside_cell and self.cell_allowed and tag == 'a':
            if 'ui-state-disabled' not in classes and 'p-disabled' not in classes:
                self.collect_day = True
                self.current_text = []

    def handle_data(self, data):
        if self.collect_day:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.collect_day:
            number = ''.join(self.current_text).strip()
            if number.isdigit() and 1 <= int(number) <= 31:
                self.days.append(int(number))
            self.collect_day = False
            self.current_text = []
        elif tag == 'td':
            self.inside_cell = False
            self.cell_allowed = False
        elif tag == 'table' and self.inside_table:
            self.inside_table = False


def published_days_in_month(html_fragment: str, year: int, month: int) -> set[date]:
    """Funcion pura, verificable contra el HTML real del calendario oficial."""
    parser = _BOPPublicationCalendarParser()
    parser.feed(html_fragment)
    days = set()
    for day in parser.days:
        try:
            days.add(date(year, month, day))
        except ValueError:
            raise CoverageError('El calendario publico contiene un dia invalido')
    return days


def official_published_days(page, first: date, last: date) -> list[date]:
    """Visita meses del calendario DE EDICIONES, no el filtro de busqueda.

    Los dias sin boletin (sabados, domingos y determinados festivos) no
    admiten ser seleccionados por el calendario de busqueda del BOP.
    Determinamos las fechas oficiales dinamicamente en vez de asumir un
    calendario laboral fijo. No se publica si no podemos leer todos los meses.
    """
    panel = page.locator('[id="calen_panel"]')
    if panel.count() != 1 or not panel.is_visible():
        raise CoverageError('No se encuentra el calendario oficial de ediciones BOP')
    first_month = (first.year, first.month)
    last_month = (last.year, last.month)
    current_month = _visible_calendar_month(panel)
    if current_month < last_month:
        raise CoverageError('El calendario oficial no alcanza el ultimo mes pedido')
    collected = set()
    covered_months = set()
    # Hasta 90 dias admitidos por la CLI, mas un margen de navegacion.
    for _ in range(9):
        current_month = _visible_calendar_month(panel)
        if first_month <= current_month <= last_month:
            current_days = published_days_in_month(
                panel.inner_html(), *current_month)
            collected.update(d for d in current_days if first <= d <= last)
            covered_months.add(current_month)
        if current_month <= first_month:
            break
        previous = panel.locator('.ui-datepicker-prev')
        if previous.count() != 1 or not previous.is_visible():
            raise CoverageError('No se puede recorrer el calendario oficial BOP')
        previous.click(timeout=10000)
        for _retry in range(40):
            page.wait_for_timeout(125)
            if _visible_calendar_month(panel) != current_month:
                break
        else:
            raise CoverageError('El calendario oficial no avanzo al mes anterior')
    else:
        raise CoverageError('Se alcanzo el limite al recorrer calendario oficial')
    month = first_month
    expected_months = set()
    while month <= last_month:
        expected_months.add(month)
        month = (month[0]+1,1) if month[1] == 12 else (month[0],month[1]+1)
    if covered_months != expected_months:
        raise CoverageError('No se han inspeccionado todos los meses del BOP: ' +
                            repr(sorted(expected_months - covered_months)))
    if not collected:
        raise CoverageError('El calendario oficial no muestra ediciones en el rango')
    return sorted(collected)


def publication_windows(first: date, last: date, published: list[date],
                        days_per_window: int = 5):
    """Convierte 30 dias naturales en consultas con extremos publicables.

    Abarca CADA fecha que el calendario del propio BOP muestra con boletin,
    exactamente una vez. Los dias sin boletin quedan registrados para la
    auditoria, nunca se envian como extremos imposibles del datepicker.
    """
    if not published:
        raise CoverageError('No hay dias publicados para crear ventanas')
    if len(published) != len(set(published)):
        raise CoverageError('Calendario oficial con dias de publicacion repetidos')
    if any(day < first or day > last for day in published):
        raise CoverageError('Calendario oficial contiene dias fuera del rango')
    days = set(published)
    planned = []
    covered = []
    for requested_first, requested_last in date_windows(first, last, days_per_window):
        dates = [d for d in published if requested_first <= d <= requested_last]
        excluded = [requested_first + timedelta(days=i) for i in range(
            (requested_last-requested_first).days+1)
            if requested_first + timedelta(days=i) not in days]
        item = {
            'requestedStart': requested_first,
            'requestedEnd': requested_last,
            'start': dates[0] if dates else None,
            'end': dates[-1] if dates else None,
            'publishedDates': dates,
            'nonPublicationDates': excluded,
        }
        planned.append(item)
        covered.extend(dates)
    if sorted(covered) != sorted(published):
        raise CoverageError('El plan del historico pierde dias con boletin')
    return planned


def date_windows(first: date, last: date, days_per_window: int = 5):
    """Intervalos inclusivos, sin huecos, solapamientos ni perdida de dias."""
    if last < first or days_per_window < 1:
        raise ValueError('Rango de fechas o tamano de intervalo invalidos')
    windows = []
    at = first
    while at <= last:
        end = min(last, at + timedelta(days=days_per_window - 1))
        windows.append((at, end))
        at = end + timedelta(days=1)
    return windows


def verify_window(found: list[dict], audit, first: date, last: date,
                  result_total: int | None, baseline_bulletin: str,
                  expected_published_dates: list[date] | None = None):
    if not audit.complete:
        raise CoverageError('Paginador no confirmado para ' + str(first) + ' - ' + str(last))
    if result_total is not None and audit.announcementsRead != result_total:
        raise CoverageError(
            f'El BOP declara {result_total} anuncios, pero solo se han '
            f'leido {audit.announcementsRead}. Rango: {first} - {last}'
        )
    if expected_published_dates is not None:
        actual_dates = set(getattr(audit, 'issue_dates', []))
        expected = {d.isoformat() for d in expected_published_dates}
        if actual_dates != expected:
            raise CoverageError(
                'El listado no cubre exactamente las fechas con boletin del '
                f'calendario oficial ({first} a {last}). '
                f'Esperadas: {sorted(expected)}; leidas: {sorted(actual_dates)}'
            )
    issues = set(getattr(audit, 'issue_numbers', []))
    if not issues:
        issues = {row['bulletin'].split('-', 1)[0] for row in found}
    # En la ventana actual, si todo sigue siendo el boletin del dia, el
    # filtro probablemente no se aplico. Preferimos bloquear a omitir plazas.
    if last == date.today() and (last-first).days >= 3 and issues == {baseline_bulletin}:
        raise CoverageError(
            'La ventana mas reciente solo contiene el ultimo boletin. '
            'No podemos confirmar que el filtro historico se aplicara.'
        )
    return issues

def merge_history(path: Path, found: list[dict], audit, first: date, last: date,
                  chunks: list[dict] | None = None):
    if not audit.complete:
        raise CoverageError('La paginacion de la busqueda historica no ha terminado')
    issues = sorted({issue for chunk in (chunks or []) for issue in chunk.get('bulletins', [])}
                    or {row['bulletin'].split('-', 1)[0] for row in found})
    # Para los 30 dias, un unico boletin indica que probablemente no se aplico el filtro.
    if (last - first).days >= 7 and len(issues) < 2:
        raise CoverageError('Solo se encontro un boletin. No se puede confirmar el rango solicitado.')
    if not path.exists():
        raise CoverageError('Falta el JSON del ultimo BOP. Ejecuta antes PROBAR_LECTOR_BOP.bat')
    existing = json.loads(path.read_text(encoding='utf-8'))
    if not existing.get('coverage', {}).get('complete'):
        raise CoverageError('La base existente no tiene un boletin diario auditado')
    unique = {item['id']: item for item in existing.get('notices', [])}
    unique.update({item['id']: item for item in found})
    notices = sorted(unique.values(),
                     key=lambda x: (datetime.strptime(x['date'], '%d/%m/%Y').date(), x['id']),
                     reverse=True)[:6000]
    existing['notices'] = notices
    existing['lastCheckedUTC'] = datetime.now(timezone.utc).isoformat()
    existing['historyCoverage'] = {
        'complete': True,
        'rangeStart': first.isoformat(), 'rangeEnd': last.isoformat(),
        'pagesVisited': audit.pagesVisited,
        'announcementsRead': audit.announcementsRead,
        'opportunities': len(found),
        'bulletins': issues,
        'status': audit.status,
        'verifiedUTC': datetime.now(timezone.utc).isoformat(),
        'chunks': chunks or [],
    }
    safe_write_json(path, existing)
    return len(notices), len(issues)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--window-days', type=int, default=5)
    parser.add_argument('--output', type=Path, default=Path('data/convocatorias.json'))
    parser.add_argument('--headful', action='store_true')
    parser.add_argument('--max-pages', type=int, default=200)
    parser.add_argument('--diagnostic-prefix', type=Path,
                        default=Path('backend/diagnostico_historico'))
    parser.add_argument('--test-search', action='store_true',
                        help='Prueba 5 dias de busqueda SIN escribir JSON de convocatorias')
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        raise SystemExit('--days debe estar entre 1 y 90')
    if not 1 <= args.window_days <= 7:
        raise SystemExit('--window-days debe estar entre 1 y 7')

    last = date.today()
    first = last - timedelta(days=args.days - 1)
    if args.test_search:
        first = last - timedelta(days=min(5, args.days) - 1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        page = browser.new_page(locale='es-ES', viewport={'width': 1280, 'height': 900})
        chunks = []
        all_by_id = {}
        audits = []
        active_window = None
        try:
            # Se comprueba la portada original para detectar si una busqueda
            # devuelve el ultimo boletin sin aplicar el rango.
            page.goto(SOURCE, wait_until='domcontentloaded', timeout=60000)
            page.locator('body').wait_for(timeout=15000)
            page.wait_for_timeout(1200)
            seleccionar_castellano(page)
            from scan import extract_index
            _, baseline_issue = extract_index(page.content())
            if not baseline_issue:
                raise CoverageError('No se ha podido identificar el boletin actual')

            published = official_published_days(page, first, last)
            windows = publication_windows(first, last, published, args.window_days)
            print(f'Calendario oficial: {len(published)} dias con boletin '
                  f'entre {first} y {last}.', flush=True)
            # Navegar meses en el calendario oficial puede alterar el estado
            # visual del portal. Reiniciamos la portada antes de BUSCAR.
            page.goto(SOURCE, wait_until='domcontentloaded', timeout=60000)
            page.locator('body').wait_for(timeout=15000)
            page.wait_for_timeout(800)
            seleccionar_castellano(page)
            for number, window in enumerate(windows, 1):
                requested_start, requested_end = window['requestedStart'], window['requestedEnd']
                start, end = window['start'], window['end']
                absent = window['nonPublicationDates']
                print(f'\n[{number}/{len(windows)}] Dias naturales '
                      f'{requested_start} - {requested_end}; '
                      f'con boletin: {start} - {end}; '
                      f'sin edicion: {len(absent)}', flush=True)
                if start is None:
                    # Intervalo sin boletines: confirmado por el calendario
                    # de publicaciones del propio portal.
                    chunks.append({'start': requested_start.isoformat(),
                                   'end': requested_end.isoformat(),
                                   'pagesVisited': 0, 'announcementsRead': 0,
                                   'bulletins': [], 'opportunities': 0,
                                   'nonPublicationDates': [d.isoformat() for d in absent],
                                   'complete': True,
                                   'status': 'no_issues_in_official_calendar'})
                    continue
                active_window = (start, end)
                if number > 1:
                    # Restablece estado del formulario y paginador entre periodos.
                    page.goto(SOURCE, wait_until='domcontentloaded', timeout=60000)
                    page.locator('body').wait_for(timeout=15000)
                    page.wait_for_timeout(1000)
                    seleccionar_castellano(page)
                request_info = search_date_range(page, start, end)
                if not request_info.get('serverConfirmed'):
                    raise CoverageError('No se ha comprobado respuesta del servidor')
                declared_total = _paginator_total(page)
                found, audit = scan_browser(page, max_pages=args.max_pages,
                                            date_range=(start, end), polite_delay=0.5)
                issues = verify_window(found, audit, start, end,
                                       declared_total, baseline_issue,
                                       expected_published_dates=window['publishedDates'])
                print(f'OK intervalo: {audit.pagesVisited} paginas, '
                      f'{audit.announcementsRead} anuncios, '
                      f'{len(found)} candidatas, {len(issues)} boletines', flush=True)
                chunks.append({'start': start.isoformat(), 'end':end.isoformat(),
                               'requestedStart': requested_start.isoformat(),
                               'requestedEnd': requested_end.isoformat(),
                               'publishedDates': [d.isoformat() for d in window['publishedDates']],
                               'nonPublicationDates': [d.isoformat() for d in absent],
                               'pagesVisited': audit.pagesVisited,
                               'announcementsRead': audit.announcementsRead,
                               'bulletins': sorted(issues),
                               'opportunities': len(found),
                               'complete': True})
                for entry in found:
                    all_by_id[entry['id']] = entry
                audits.append(audit)

            issues = sorted({i for c in chunks for i in c['bulletins']})
            if (last - first).days >= 7 and len(issues) < 2:
                raise CoverageError('Solo se detecto un boletin durante todo el historico')
            composite = Audit(bulletin='varios',
                              pagesVisited=sum(a.pagesVisited for a in audits),
                              announcementsRead=sum(a.announcementsRead for a in audits),
                              opportunities=len(all_by_id), complete=True,
                              status='windows_ajax_verified',
                              details=f'{len(chunks)} periodos auditados')
            print('Auditoria historica:', json.dumps(asdict(composite),ensure_ascii=False))
            if args.test_search:
                print('PRUEBA CORRECTA: sin modificar data/convocatorias.json')
                return
            total, issue_count = merge_history(
                args.output, list(all_by_id.values()), composite,
                first, last, chunks=chunks,
            )
            print(f'OK. {issue_count} boletines consultados y '
                  f'{len(all_by_id)} candidatas en el rango; '
                  f'{total} fichas en el archivo.')
        except Exception as exc:
            args.diagnostic_prefix.parent.mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path=str(args.diagnostic_prefix.with_suffix('.png')),
                                full_page=True)
                args.diagnostic_prefix.with_suffix('.html').write_text(
                    page.content(), encoding='utf-8')
                safe_fields = page.locator('input').evaluate_all("els => els.map(x => ({id:x.id, name:x.name, type:x.type, value: x.type === 'hidden' ? '[oculto]' : x.value}))")
                failure_first, failure_last = active_window if active_window else (first, last)
                args.diagnostic_prefix.with_suffix('.json').write_text(
                    json.dumps({'fields':safe_fields, 'completedWindows':chunks,
                                'current':_search_diagnostic(page, failure_first,failure_last,'failed'),
                                'exception': {'type':type(exc).__name__,
                                              'message':str(exc)[:700]},
                                'paginator': (page.locator('[id="list_paginator_top"]').inner_text()[:200]
                                              if page.locator('[id="list_paginator_top"]').count()
                                              else None)},
                               ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass
            print('ERROR. NO SE HA PUBLICADO HISTORICO INCOMPLETO.')
            print('Diagnosticos:', args.diagnostic_prefix)
            traceback.print_exc()
            raise SystemExit(1)
        finally:
            browser.close()


if __name__ == '__main__':
    run()
