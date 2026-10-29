#!/usr/bin/env python3
"""Render Córdoba's streaming Next.js sections before assigning any issuer."""
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
 context=browser.new_context(locale="es-ES")
 page=context.new_page()
 for day in ("05-10-2026","15-10-2026","29-10-2026"):
  try:
   page.goto(f"https://bop.dipucordoba.es/dia/{day}",wait_until="domcontentloaded",timeout=40000)
   try:page.locator("li.announcement").first.wait_for(timeout=20000)
   except Exception:pass
   page.wait_for_timeout(2500)
   print("\nDAY",day,"TITLE",page.title(),"H2",page.locator("h2").all_text_contents()[:3],flush=True)
   print("LI",page.locator("li.announcement").count(),flush=True)
   details=page.locator("li.announcement").evaluate_all("""rows=>rows.map((x,i)=>({
       i,txt:x.querySelector('p')?.textContent?.slice(0,180),
       agency:x.closest('li.emisor')?.querySelector('h2')?.textContent,
       pdf:x.querySelector('a.pdf')?.getAttribute('href'),
       html:!x.closest('li.emisor')?x.outerHTML.slice(0,850):null
    }))""")
   problems=[x for x in details if not x["agency"] or not x["pdf"]]
   print("BROKEN",len(problems),problems[:12],flush=True)
   print("SAMPLE",details[:2],flush=True)
  except Exception as e:print("ERROR",day,type(e).__name__,str(e)[:350],flush=True)
 browser.close()
