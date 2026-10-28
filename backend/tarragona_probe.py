#!/usr/bin/env python3
"""Diagnostic of official Tarragona BOPT HTML, no data published."""
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup

URLS = [
    'https://aplicacions.dipta.cat/bopt/web/anteriores/2026-10-23',
    'https://aplicacions.dipta.cat/bopt/web/anteriores/2026-10-23/2',
    'https://aplicacions.dipta.cat/bopt/web/anteriores/2026-10-12',
]
for url in URLS:
    print('\n==', url, flush=True)
    try:
        with urlopen(Request(url, headers={'User-Agent':'OpoAlert/1.4 (+https://github.com/MJTBApps/OpoAlert)','Accept-Language':'es,en;q=0.8'}), timeout=25) as response:
            content=response.read(2_000_000)
            print('HTTP',response.status,'BYTES',len(content),'FINAL URL',response.url, flush=True)
    except HTTPError as err:
        print('HTTP',err.code,'CONTENT',err.read(2000).decode('utf-8','replace')[:800],flush=True)
        continue
    soup=BeautifulSoup(content,'html.parser')
    print('TITLE:', soup.title.get_text(' ',strip=True) if soup.title else None,flush=True)
    alltext=soup.get_text(' ',strip=True)
    import re
    match=re.search(r'(?:Se encontraron|S.han trobat).{0,60}resultad',alltext,re.I)
    print('TOTAL:',alltext[match.start():match.start()+170] if match else 'NOT FOUND', flush=True)
    links=[a for a in soup.select('a[href]') if '/anuncio/' in a.get('href','') and '/descargar' not in a.get('href','')]
    print('ANUNCIO LINKS:',len(links),flush=True)
    for a in links[:2]:
        print('ANCHOR:',str(a)[:1000],flush=True)
        for j,parent in enumerate(a.parents):
            if j>=4:break
            print(' PARENT',j,parent.name,parent.get('class'),parent.get_text(' ',strip=True)[:450],flush=True)
            if j==2:print(' HTML:',str(parent)[:2400],flush=True)
    print('PAGE LINKS:',[(a.get('href'),a.get_text(' ',strip=True)) for a in soup.select('a[href]') if re.search(r'/anteriores/2026-10-23/\d+',a.get('href',''))][:12],flush=True)
