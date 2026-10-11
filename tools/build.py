#!/usr/bin/env python3
"""Rebuild generated content from the single source of truth (data/claims.json, data/eras.json).
Also normalises the shared head (theme.js, social meta, vendored Leaflet) and the nav on every page."""
import json,re,glob,html,os,math,sys

# Publishing switch. False while the site is a draft: every page keeps noindex and has NO canonical link.
# Set True at launch: drops noindex and adds <link rel="canonical"> + og:url pointing at GitHub Pages.
LIVE=False
PAGES_BASE="https://sliothar1.github.io/pa-ui-mhaine/"
os.chdir(os.path.dirname(os.path.abspath(__file__))+'/..')
U=dict(encoding='utf-8')
def rd(f):
  with open(f,**U) as fh:return fh.read()
def wr(f,s):
  with open(f,'w',**U) as fh:fh.write(s)
def jdump(o,f,**k):
  with open(f,'w',**U) as fh:json.dump(o,fh,ensure_ascii=False,**k)
D=json.loads(rd('data/claims.json'));C=D['claims'];G=json.loads(rd('data/eras.json'));PLACES=D.get('places',[]);MAP=json.loads(rd('data/places.json'))['places']
UNPINNED=lambda v:(not v) or str(v).strip().upper() in ('','NEEDS SOURCE')
# schema validation
REQ=('id','date','title','ga','claim','kind','evidence','reference','pinned','status','centre','zoom','polys')
errs=[]
ids=[c.get('id') for c in C]+[p.get('id') for p in PLACES]
if len(ids)!=len(set(ids)):errs.append('duplicate ids')
for c in C:
  for k in REQ:
    if k not in c:errs.append(f"{c.get('id')}: missing {k}")
  if c.get('status') not in D['status_values']:errs.append(f"{c['id']}: unknown status {c.get('status')}")
  if c.get('kind') not in ('recorded','tradition'):errs.append(f"{c['id']}: unknown kind")
  if c.get('status')=='pinned' and UNPINNED(c.get('pinned')):errs.append(f"{c['id']}: pinned without pin")
  for p in c.get('polys',[]):
    if p.get('conf') not in ('attested','interpretation','claimed'):errs.append(f"{c['id']}: unknown conf {p.get('conf')}")
    if p.get('geom') not in G:errs.append(f"{c['id']}: unknown geom {p.get('geom')}")
for p in PLACES:
  for k in ('id','name','reference','date','evidence','status'):
    if k not in p:errs.append(f"{p.get('id')}: missing {k}")
seen={}
for p in MAP:
  k=tuple(p['ll'])
  if k in seen:errs.append(f"coordinate {k} defined twice ({seen[k]}, {p['id']})")
  seen[k]=p['id']
if len({p['id'] for p in MAP})!=len(MAP):errs.append('duplicate place ids in places.json')
if errs:sys.exit('claims.json invalid: '+'; '.join(errs))
def area_km2(r):
  R=6371;lat0=math.radians(sum(q[0] for q in r)/len(r));xy=[(math.radians(q[1])*R*math.cos(lat0),math.radians(q[0])*R) for q in r]
  return abs(sum(xy[i][0]*xy[i-1][1]-xy[i-1][0]*xy[i][1] for i in range(len(xy))))/2
CL={'attested':'core sites attested · outline sketched','interpretation':'interpretation','claimed':'claimed'}
e=html.escape
os.makedirs('generated',exist_ok=True)
# generated outputs (never edit by hand)
jdump([{k:c[k] for k in ('id','date','title','ga','claim','kind','evidence','reference','pinned','status')} for c in C],'generated/story-cards.json',indent=1)
feats=[]
for c in C:
  for p in c['polys']:
    r=G[p['geom']];feats.append({'type':'Feature','properties':{'claim':c['id'],'date':c['date'],'confidence':CL[p['conf']],'source':p['src'],'note':'approximate sketch'+(' · not to scale' if p['geom']=='WIDE' else '')},'geometry':{'type':'Polygon','coordinates':[[[q[1],q[0]] for q in r+[r[0]]]]}})
jdump({'type':'FeatureCollection','note':'Generated from data/claims.json + data/eras.json by tools/build.py','features':feats},'generated/era-polygons.geojson')
rows=['| ID | Date | Claim | Reference | Pinned | Status |','|---|---|---|---|---|---|']+[f"| {c['id']} | {c['date']} | {c['title']} | {c['reference']} | {'NEEDS SOURCE' if UNPINNED(c['pinned']) else c['pinned']} | {c['status']} |" for c in C]
wr('generated/verification-table.md','# Verification table (generated from data/claims.json)\n\n'+'\n'.join(rows)+'\n')
# static, no-JS stop list in timeslider.html
lis=''.join(f'<li><h3><span lang="ga">{e(c["ga"])}</span> · {e(c["title"])} <span class="meta">({e(c["date"])})</span></h3><p>{e(c["claim"])}</p><p class="srcp" data-claim="{c["id"]}"><b>Reference:</b> {e(c["reference"])} · <b>Date:</b> {e(c["date"])} · <b>Evidence:</b> {e(c["evidence"])} · <b>Status:</b> <span class="status">{e(c["status"])}</span> · Map: {", ".join(CL[p["conf"]] for p in c["polys"])}</p>'+(f'<p class="srcp extra"><b>Confidence:</b> {e(c["confidence"])} · <span class="alts"><b>Alternatives:</b> {e(", ".join(c["alternatives"]))}</span> · <b>Basis:</b> {e(c["basis"])} '+(f' · <b>Revision:</b> {e(c["revision"])}' if c.get("revision") else '')+'</p>' if c.get("confidence") else '')+'</li>' for c in C)
t=rd('timeslider.html')
for mk in ('<!--STOPS-->','<!--/STOPS-->','<!--AREA-->','<!--/AREA-->','<!--CAREA-->','<!--/CAREA-->'):
  assert mk in t,f'marker {mk} missing in timeslider.html'
t=re.sub(r'<!--AREA-->.*?<!--/AREA-->','<!--AREA-->'+f'{round(area_km2(G["WIDE"]),-1):,.0f}'+'<!--/AREA-->',t,flags=re.S)
CA=next(c['curley_area_km2'] for c in C if 'curley_area_km2' in c)
t=re.sub(r'<!--CAREA-->.*?<!--/CAREA-->',f'<!--CAREA-->{CA:,}<!--/CAREA-->',t,flags=re.S)
t=re.sub(r'<!--STOPS-->.*?<!--/STOPS-->','<!--STOPS--><ol class="stops" id="stoplist">'+lis+'</ol><!--/STOPS-->',t,flags=re.S)
wr('timeslider.html',t)
# court-page source panels from data/claims.json places, between <!--PANEL:id--> markers
ct=rd('cuirt-fothnach.html');PD={p['id']:p for p in PLACES}
found=re.findall(r'<!--PANEL:(UM-P\d+)-->',ct)
assert sorted(found)==sorted(PD),f'court panels {sorted(found)} != places {sorted(PD)}'
def panel(m):
  p=PD[m.group(1)]
  return f'<!--PANEL:{p["id"]}--><span class="srcp" data-claim="{p["id"]}"><b>Reference:</b> {e(p["reference"])} · <b>Date:</b> {e(p["date"])} · <b>Evidence:</b> {e(p["evidence"])} · <b>Status:</b> <span class="status">{e(p["status"])}</span></span><!--/PANEL-->'
ct=re.sub(r'<!--PANEL:(UM-P\d+)-->.*?<!--/PANEL-->',panel,ct,flags=re.S)
wr('cuirt-fothnach.html',ct)
# sources page: claims and their references, generated
sp=rd('sources.html');assert '<!--CLAIMS-->' in sp and '<!--/CLAIMS-->' in sp,'CLAIMS markers missing in sources.html'
rowsh=''.join(f'<li><b>{e(c["date"])}</b> · {e(c["title"])}: {e(c["reference"])} <span class="meta">({e(c["status"])})</span></li>' for c in C)
sp=re.sub(r'<!--CLAIMS-->.*?<!--/CLAIMS-->',lambda m:'<!--CLAIMS--><ul class="claimrefs">'+rowsh+'</ul><!--/CLAIMS-->',sp,flags=re.S)
wr('sources.html',sp)
# shared head + nav
NAV=[('index.html#overview','Overview'),('index.html#map-section','Map'),('index.html#scenes','Scenes'),('timeslider.html','Time map'),('cuirt-fothnach.html','The court'),('sources.html','Sources'),('index.html#about','About')]
CUR={'index.html':'Overview','timeslider.html':'Time map','cuirt-fothnach.html':'The court','sources.html':'Sources'}
for f in sorted(glob.glob('*.html')+glob.glob('scenes/*.html')):
  p='../' if f.startswith('scenes/') else ''
  x=rd(f)
  cur='Scenes' if f.startswith('scenes/') else CUR.get(f)
  nav=f'<nav class="sitenav" aria-label="Main"><div class="navin"><a class="brand" href="{p}index.html">PA <span lang="ga">Uí Mhaine</span></a><div class="navlinks">'+''.join(f'<a href="{p}{h}"'+(' aria-current="page"' if n==cur else '')+f'>{n}</a>' for h,n in NAV)+'</div><button class="iconbtn themebtn" type="button" aria-label="Switch light or dark theme">◐</button></div></nav>'
  x=re.sub(r'<nav class="sitenav".*?</nav>',nav,x,count=1,flags=re.S)
  x=re.sub(r'<script src="(\.\./)?theme\.js"></script>','',x)
  x=x.replace('<meta charset="utf-8">',f'<meta charset="utf-8"><script src="{p}theme.js"></script>',1)
  title=re.search(r'<title>(.*?)</title>',x).group(1);desc=(re.search(r'<meta name="description" content="([^"]*)"',x) or [None,''])[1]
  url=PAGES_BASE+('' if f=='index.html' else f)
  x=re.sub(r'<meta property="og:[^>]*>|<meta name="twitter:[^>]*>|<link rel="canonical"[^>]*>','',x)
  social=f'<meta property="og:type" content="website"><meta property="og:site_name" content="PA Uí Mhaine"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:locale" content="en_IE"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}">'+(f'<meta property="og:url" content="{url}"><link rel="canonical" href="{url}">' if LIVE else '')
  x=x.replace('</title>','</title>'+social,1)
  x=re.sub(r'<meta name="robots"[^>]*>','',x)
  if not LIVE:x=x.replace('<meta charset="utf-8">','<meta charset="utf-8"><meta name="robots" content="noindex, nofollow">',1)
  wr(f,x)
print('built',len(C),'claims')
