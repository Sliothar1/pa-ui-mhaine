#!/usr/bin/env python3
"""Rebuild generated content from the single source of truth (data/claims.json, data/eras.json).
Also normalises the shared head (theme.js, social meta, vendored Leaflet) and the nav on every page."""
import json,re,glob,html,os
os.chdir(os.path.dirname(os.path.abspath(__file__))+'/..')
D=json.load(open('data/claims.json'));C=D['claims'];G=json.load(open('data/eras.json'))
CL={'attested':'core sites attested · outline sketched','interpretation':'interpretation','claimed':'claimed'}
e=html.escape
os.makedirs('generated',exist_ok=True)
# generated outputs (never edit by hand)
json.dump([{k:c[k] for k in ('id','date','title','ga','claim','kind','evidence','reference','pinned','status')} for c in C],open('generated/story-cards.json','w'),ensure_ascii=False,indent=1)
feats=[]
for c in C:
  for p in c['polys']:
    r=G[p['geom']];feats.append({'type':'Feature','properties':{'claim':c['id'],'date':c['date'],'confidence':CL[p['conf']],'source':p['src'],'note':'approximate sketch'+(' · not to scale' if p['geom']=='WIDE' else '')},'geometry':{'type':'Polygon','coordinates':[[[q[1],q[0]] for q in r+[r[0]]]]}})
json.dump({'type':'FeatureCollection','note':'Generated from data/claims.json + data/eras.json by tools/build.py','features':feats},open('generated/era-polygons.geojson','w'),ensure_ascii=False)
rows=['| ID | Date | Claim | Reference | Pinned | Status |','|---|---|---|---|---|---|']+[f"| {c['id']} | {c['date']} | {c['title']} | {c['reference']} | {c['pinned'] or 'NEEDS SOURCE'} | {c['status']} |" for c in C]
open('generated/verification-table.md','w').write('# Verification table (generated from data/claims.json)\n\n'+'\n'.join(rows)+'\n')
# static, no-JS stop list in timeslider.html
lis=''.join(f'<li><h3><span lang="ga">{e(c["ga"])}</span> · {e(c["title"])} <span class="meta">({e(c["date"])})</span></h3><p>{e(c["claim"])}</p><p class="srcp" data-claim="{c["id"]}"><b>Reference:</b> {e(c["reference"])} · <b>Date:</b> {e(c["date"])} · <b>Evidence:</b> {e(c["evidence"])} · <b>Status:</b> <span class="status">{e(c["status"])}</span> · Map: {", ".join(CL[p["conf"]] for p in c["polys"])}</p>'+(f'<p class="srcp extra"><b>Confidence:</b> {e(c["confidence"])} · <span class="alts"><b>Alternatives:</b> {e(", ".join(c["alternatives"]))}</span> · <b>Basis:</b> {e(c["basis"])} '+(f' · <b>Revision:</b> {e(c["revision"])}' if c.get("revision") else '')+'</p>' if c.get("confidence") else '')+'</li>' for c in C)
t=open('timeslider.html').read()
t=re.sub(r'<!--STOPS-->.*?<!--/STOPS-->','<!--STOPS--><ol class="stops" id="stoplist">'+lis+'</ol><!--/STOPS-->',t,flags=re.S)
open('timeslider.html','w').write(t)
# shared head + nav
NAV=[('index.html#overview','Overview'),('index.html#map-section','Map'),('index.html#scenes','Scenes'),('timeslider.html','Time map'),('cuirt-fothnach.html','The court'),('sources.html','Sources'),('index.html#about','About')]
CUR={'index.html':'Overview','timeslider.html':'Time map','cuirt-fothnach.html':'The court','sources.html':'Sources'}
for f in sorted(glob.glob('*.html')+glob.glob('scenes/*.html')):
  p='../' if f.startswith('scenes/') else ''
  x=open(f).read()
  cur='Scenes' if f.startswith('scenes/') else CUR.get(f)
  nav=f'<nav class="sitenav" aria-label="Main"><div class="navin"><a class="brand" href="{p}index.html">PA <span lang="ga">Uí Mhaine</span></a><div class="navlinks">'+''.join(f'<a href="{p}{h}"'+(' aria-current="page"' if n==cur else '')+f'>{n}</a>' for h,n in NAV)+'</div><button class="iconbtn themebtn" type="button" aria-label="Switch light or dark theme">◐</button></div></nav>'
  x=re.sub(r'<nav class="sitenav".*?</nav>',nav,x,count=1,flags=re.S)
  x=re.sub(r'<script>\(function\(\)\{var t=localStorage.*?</script>','',x,flags=re.S)
  x=re.sub(r'<script src="(\.\./)?theme\.js"></script>','',x)
  x=x.replace('<meta charset="utf-8">',f'<meta charset="utf-8"><script src="{p}theme.js"></script>',1)
  x=re.sub(r'<link rel="stylesheet" href="https://unpkg\.com/leaflet[^>]*>',f'<link rel="stylesheet" href="{p}vendor/leaflet/leaflet.css">',x)
  x=re.sub(r'<script src="https://unpkg\.com/leaflet[^>]*></script>',f'<script src="{p}vendor/leaflet/leaflet.js"></script>',x)
  title=re.search(r'<title>(.*?)</title>',x).group(1);desc=(re.search(r'<meta name="description" content="([^"]*)"',x) or [None,''])[1]
  url='https://sliothar1.github.io/pa-ui-mhaine/'+('' if f=='index.html' else f)
  x=re.sub(r'<meta property="og:[^>]*>|<meta name="twitter:[^>]*>','',x)
  social=f'<meta property="og:type" content="website"><meta property="og:site_name" content="PA Uí Mhaine"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{url}"><meta property="og:locale" content="en_IE"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}">'
  x=x.replace('</title>','</title>'+social,1)
  x=re.sub(r'onclick="tt\(\)"\s*','',x)
  open(f,'w').write(x)
print('built',len(C),'claims')
