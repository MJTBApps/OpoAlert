#!/usr/bin/env python3
"""Audited 30-day pilot for Alicante/Castellon; NEVER publishes partial data.

Official sites have different architectures; use their own controls and never
infer successful coverage from a non-empty first page. The pilot output is an
artifact in the development branch until the end-to-end audit passes.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta, datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote
from playwright.sync_api import sync_playwright
from alicante import parse_issue as parse_alicante
from castellon import parse_issue as parse_castellon
from provincial_common import ProvincialCoverageError, VerifiedIssue

ALICANTE = 'https://sede.diputacionalicante.es/consultas.bop/'
CASTELLON = 'https://bop.dipcas.es/PortalBOP/'
MONTHS = {n:i for i,n in enumerate(('enero','febrero','marzo','abril','mayo','junio',
                                  'julio','agosto','septiembre','octubre','noviembre','diciembre'), 1)}


def date_label(day):
    return day.strftime('%d/%m/%Y')


def valid_issues(issues: list[VerifiedIssue], province: str, start: date, end: date,
                 examined_days: set[date] | None = None) -> None:
    if not issues:
        raise ProvincialCoverageError(f'{province}: ningun boletin leido')
    dates=[datetime.strptime(x.date,'%d/%m/%Y').date() for x in issues]
    if any(not start<=d<=end for d in dates) or len(dates)!=len(set(dates)):
        raise ProvincialCoverageError(f'{province}: fechas duplicadas o fuera de rango')
    numbers=[int(x.number) for x in issues]
    if len(numbers)!=len(set(numbers)) or sorted(numbers)!=list(range(min(numbers),max(numbers)+1)):
        raise ProvincialCoverageError(f'{province}: numeracion de boletines con huecos o repeticiones')
    if len(issues)<8:
        raise ProvincialCoverageError(f'{province}: solamente {len(issues)} boletines, posible cobertura incompleta')
    if examined_days is not None:
        expected={start+timedelta(days=i) for i in range((end-start).days+1)}
        if examined_days!=expected:
            raise ProvincialCoverageError(f'{province}: no se han probado todas las fechas')
    keys=[r['id'] for issue in issues for r in issue.opportunities]
    if len(keys)!=len(set(keys)):
        raise ProvincialCoverageError(f'{province}: identificadores duplicados entre boletines')


def alicante_scan(page, start:date, end:date) -> tuple[list[VerifiedIssue],set[date]]:
    page.goto(ALICANTE,wait_until='domcontentloaded',timeout=70000)
    page.locator('#fechaboletin').wait_for(timeout=30000)
    page.wait_for_timeout(1600)
    issues=[]
    days=set()
    for k in range((end-start).days+1):
        day=end-timedelta(days=k)
        requested=day.strftime('%d/%m/%Y')
        dateinput=page.locator('#fechaboletin')
        # An official BOP Ajax JSON response is required for each requested day.
        for attempt in range(2):
            try:
                with page.expect_response(
                    lambda r: 'wseConsultaAjax.php' in r.url and requested in unquote(r.url),
                    timeout=30000,
                ) as matched:
                    dateinput.fill(day.isoformat())
                    dateinput.dispatch_event('change')
                response=matched.value
                if response.status!=200:raise ProvincialCoverageError(f'Alicante {requested}: HTTP {response.status}')
                page.wait_for_timeout(180)
                break
            except Exception as exc:
                if attempt==1:raise ProvincialCoverageError(f'Alicante {requested}: sin respuesta oficial confirmada: {exc}') from exc
                page.wait_for_timeout(500)
        if dateinput.input_value()!=day.isoformat():
            raise ProvincialCoverageError(f'Alicante {requested}: selector de fecha revertido')
        rows=page.locator('table.tabla-edictos-inner tbody tr').count()
        if rows==0:
            message=page.locator('#avisos').inner_text(timeout=10000).strip()
            if 'No existen datos en la consulta realizada' not in message:
                raise ProvincialCoverageError(f'Alicante {requested}: no hay filas ni mensaje oficial de ausencia')
            print(f'Alicante {requested}: sin boletin segun servicio oficial',flush=True)
        else:
            issue=parse_alicante(page.content(),requested)
            if issue.announcements_read!=rows:
                raise ProvincialCoverageError(f'Alicante {requested}: {rows} filas visibles vs {issue.announcements_read} leidas')
            issues.append(issue)
            print(f'Alicante {requested}: BOP {issue.number} · {issue.announcements_read} edictos · '
                  f'{len(issue.opportunities)} candidatas',flush=True)
        days.add(day)
        time.sleep(0.15)
    valid_issues(issues,'Alicante',start,end,days)
    return issues,days


def parse_cs_label(label: str) -> tuple[str,date]:
    normalized=' '.join(label.split())
    found=re.search(r'N[ºoúu]m?\.?\s*(\d+)\s+\w+\s+(\d{1,2})\s+(\w+)\s+(\d{4})',normalized,re.I)
    if not found:raise ProvincialCoverageError(f'Castellon: edicion no interpretable: {normalized[:100]}')
    number,day,month,year=found.groups()
    month_index=MONTHS.get(month.casefold())
    if month_index is None:raise ProvincialCoverageError(f'Castellon: mes no reconocido: {month}')
    return number,date(int(year),month_index,int(day))


def pick_castellon(page, number:str) -> None:
    target=page.locator(f'a[aria-label^="Nº {number} "]').first
    if target.count()!=1:raise ProvincialCoverageError(f'Castellon: falta BOP {number} en el carrusel')
    for attempt in range(26):
        if target.is_visible() and target.get_attribute('aria-hidden')!='true' and target.get_attribute('tabindex')!='-1':
            try:
                target.click(timeout=4000)
                page.wait_for_function(
                    '(n)=>[...document.querySelectorAll("label")].some(e=>e.textContent.trim()=="Sumario BOP Nº "+n)',
                    arg=number,timeout=18000)
                page.wait_for_timeout(100)
                return
            except Exception as exc:
                raise ProvincialCoverageError(f'Castellon: BOP {number} no se pudo seleccionar: {exc}') from exc
        nextbtn=page.locator('a.ui-carousel-next').first
        if not nextbtn.count() or nextbtn.get_attribute('aria-disabled')=='true':
            # Try previous direction if we overshot the requested issue.
            prev=page.locator('a.ui-carousel-prev').first
            if not prev.count() or prev.get_attribute('aria-disabled')=='true':break
            prev.click(timeout=3000)
        else:
            nextbtn.click(timeout=3000)
        page.wait_for_timeout(210)
    raise ProvincialCoverageError(f'Castellon: no se pudo hacer visible el BOP {number}')


def castellon_scan(page, start:date,end:date) -> tuple[list[VerifiedIssue],set[date]]:
    page.goto(CASTELLON,wait_until='domcontentloaded',timeout=70000)
    page.locator('span.titulo4').first.wait_for(timeout=20000)
    anchors=page.locator('a[aria-label^="Nº "]')
    bulletin_dates={}
    for i in range(anchors.count()):
        label=anchors.nth(i).get_attribute('aria-label') or ''
        try:number,day=parse_cs_label(label)
        except ProvincialCoverageError:continue
        if start<=day<=end:
            if number in bulletin_dates:raise ProvincialCoverageError('Castellon: boletin repetido en carrusel')
            bulletin_dates[number]=day
    if not bulletin_dates:
        raise ProvincialCoverageError('Castellon: no hay boletines con fecha dentro del periodo')
    if min(bulletin_dates.values())>start+timedelta(days=4):
        raise ProvincialCoverageError('Castellon: la lista visible empieza demasiado tarde')
    result=[]
    for number,day in sorted(bulletin_dates.items(),key=lambda x:x[1],reverse=True):
        pick_castellon(page,number)
        issue=parse_castellon(page.content(),date_label(day),number)
        result.append(issue)
        print(f'Castellon {date_label(day)}: BOP {number} · {issue.announcements_read} anuncios · '
              f'{len(issue.opportunities)} candidatas',flush=True)
        time.sleep(.18)
    valid_issues(result,'Castellon',start,end)
    if len(result)!=len(bulletin_dates):raise ProvincialCoverageError('Castellon: faltan boletines seleccionados')
    return result,set(bulletin_dates.values())


def make_json(issues,province,source,start,end):
    ordered=sorted(issues,key=lambda x:datetime.strptime(x.date,'%d/%m/%Y').date())
    notices=[n for issue in ordered for n in issue.opportunities]
    notices.sort(key=lambda x:(datetime.strptime(x['date'],'%d/%m/%Y'),x['id']),reverse=True)
    all_days={start+timedelta(days=i) for i in range((end-start).days+1)}
    pub_days={datetime.strptime(x.date,'%d/%m/%Y').date() for x in issues}
    return {
        'schemaVersion':1,
        'source':source,
        'province':province,
        'lastCheckedUTC':datetime.now(timezone.utc).isoformat(),
        'coverage':{
            'complete':True,
            'bulletin':ordered[-1].number,
            'pagesVisited':len(issues),
            'announcementsRead':sum(x.announcements_read for x in issues),
            'opportunities':len(notices),
            'status':'complete',
        },
        'historyCoverage':{
            'complete':True,
            'rangeStart':start.isoformat(),
            'rangeEnd':end.isoformat(),
            'issuesRead':len(issues),
            'pagesVisited':len(issues),
            'announcementsRead':sum(x.announcements_read for x in issues),
            'opportunities':len(notices),
            'bulletins':[x.number for x in ordered],
            'publicationDates':[x.isoformat() for x in sorted(pub_days)],
            'nonPublicationDates':[x.isoformat() for x in sorted(all_days-pub_days)],
        },
        'notices':notices,
    }


def main():
    args=argparse.ArgumentParser()
    args.add_argument('--days',type=int,default=30)
    args.add_argument('--province',choices=('alicante','castellon','both'),default='both')
    args.add_argument('--output',type=Path,default=Path('out_provincias'))
    a=args.parse_args()
    if not 1<=a.days<=35:raise SystemExit('Dias fuera de rango')
    a.output.mkdir(parents=True,exist_ok=True)
    end=date.today();start=end-timedelta(days=a.days-1)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            for slug,func,source,proper in (
                ('alicante',alicante_scan,ALICANTE,'Alicante'),
                ('castellon',castellon_scan,CASTELLON,'Castellón'),
            ):
                if a.province not in (slug,'both'):continue
                page=browser.new_page(locale='es-ES',viewport={'width':1366,'height':850})
                try:
                    issues,_days=func(page,start,end)
                    data=make_json(issues,proper,source,start,end)
                    path=a.output/(slug+'.json')
                    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
                    print(f'PILOTO_OK {slug}: {len(issues)} boletines, '
                          f'{data["coverage"]["announcementsRead"]} anuncios, '
                          f'{len(data["notices"])} candidatos, salida {path}',flush=True)
                finally:
                    page.close()
        finally:
            browser.close()

if __name__=='__main__':main()
