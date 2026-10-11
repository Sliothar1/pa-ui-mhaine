#!/usr/bin/env python3
"""PA Uí Mhaine v2 checks. Usage: BASE=http://localhost:8799/ AXE=path/to/axe.min.js python3 tests/run_tests.py
Writes tests/results.json and exits 1 on any failure."""
import json,os,re,sys,glob
from urllib.parse import urljoin,urlparse
from playwright.sync_api import sync_playwright
BASE=os.environ.get('BASE','http://localhost:8799/');AXE=open(os.environ.get('AXE','node_modules/axe-core/axe.min.js')).read()
ROOT=os.path.dirname(os.path.abspath(__file__))+'/..'
PAGES=sorted([p for p in glob.glob('*.html',root_dir=ROOT)])+sorted('scenes/'+os.path.basename(p) for p in glob.glob(ROOT+'/scenes/*.html'))
CLAIMS=json.load(open(ROOT+'/data/claims.json'))['claims']
R=[]
def rec(id,name,ok,detail=''):R.append({'id':id,'test':name,'result':'PASS' if ok else 'FAIL','detail':detail});print(('PASS ' if ok else 'FAIL ')+id+' '+name+(' :: '+str(detail)[:300] if detail else ''))
TILE='tile.openstreetmap.org'
with sync_playwright() as p:
  b=p.chromium.launch()
  # T1 status / console / failed requests, link check, external leaflet
  bad=[];links=set();ext=[]
  for pg_ in PAGES:
    c=b.new_context();pg=c.new_page();errs=[];fails=[]
    pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None);pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('response',lambda r:fails.append(f'{r.status} {r.url}') if r.status>=400 and TILE not in r.url else None)
    pg.on('request',lambda r:ext.append(r.url) if 'unpkg.com' in r.url else None)
    r=pg.goto(BASE+pg_,wait_until='networkidle');pg.wait_for_timeout(800)
    if r.status!=200 or errs or fails:bad.append({'page':pg_,'status':r.status,'console':errs,'failed':fails})
    for h in pg.eval_on_selector_all('a[href]','as=>as.map(a=>a.href)'):
      if h.startswith(BASE):links.add(h.split('#')[0])
    c.close()
  rec('T01','all pages 200, no console errors, no failed requests (tiles excluded)',not bad,bad)
  c=b.new_context();pg=c.new_page();broken=[l for l in sorted(links) if pg.request.get(l).status!=200];c.close()
  rec('T02','internal link check',not broken,f'{len(links)} links; broken={broken}')
  rec('T03','Leaflet self-hosted (no unpkg requests)',not ext,ext[:3])
  # T4 nav identical + theme toggle on every page
  navs={};theme_bad=[]
  for pg_ in PAGES:
    c=b.new_context();pg=c.new_page();pg.goto(BASE+pg_,wait_until='domcontentloaded')
    navs[pg_]=[(a['t'],re.sub(r'^(\.\./)+','',a['h'])) for a in pg.eval_on_selector_all('nav.sitenav a','as=>as.map(a=>({t:a.textContent,h:a.getAttribute("href")}))')]
    t0=pg.get_attribute('html','data-theme');pg.click('.themebtn');t1=pg.get_attribute('html','data-theme');lab=pg.get_attribute('.themebtn','aria-label')
    pg.reload();t2=pg.get_attribute('html','data-theme')
    if not(t0!=t1 and t1==t2 and ('Theme: '+t1) in lab):theme_bad.append((pg_,t0,t1,t2,lab))
    c.close()
  ref=navs['index.html'];diff=[k for k,v in navs.items() if v!=ref]
  rec('T04','nav identical on every page (server-rendered)',not diff,diff)
  rec('T05','theme toggle works, label shows state, choice persists on every page',not theme_bad,theme_bad)
  # T6 UM-043 Galey across all pages
  gal={}
  for pg_ in PAGES:
    c=b.new_context(java_script_enabled=False);pg=c.new_page();pg.goto(BASE+pg_);txt=pg.inner_text('body');gal[pg_]=txt.count('Galey');c.close()
  ok=all(v==0 for k,v in gal.items() if k not in('cuirt-fothnach.html','sources.html')) and gal['cuirt-fothnach.html']==1 and gal['sources.html']==1
  c=b.new_context();pg=c.new_page();pg.goto(BASE+'cuirt-fothnach.html');box='Where was the feast' in pg.inner_text('body');c.close()
  rec('T06','UM-043 Galey: one line on court and sources pages, none elsewhere; no both-sides box',ok and not box,{k:v for k,v in gal.items() if v})
  # T7 boundary loader both states
  c=b.new_context();pg=c.new_page();pg.goto(BASE+'timeslider.html',wait_until='networkidle');pg.wait_for_timeout(800)
  s1=(pg.get_attribute('#boundarynote','data-state'),pg.inner_text('#boundarynote'));c.close()
  c=b.new_context();pg=c.new_page()
  pg.route('**/data/true-boundary.geojson',lambda r:r.fulfill(content_type='application/json',body=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[[[-8.5,53.3],[-8.3,53.3],[-8.3,53.45],[-8.5,53.45],[-8.5,53.3]]]}}]})))
  pg.goto(BASE+'timeslider.html',wait_until='networkidle');pg.wait_for_timeout(800)
  s2=(pg.get_attribute('#boundarynote','data-state'),pg.evaluate("document.querySelectorAll('path[stroke=\"#dc2626\"]').length"));c.close()
  rec('T07','true-boundary loader: empty -> "coming soon"; features -> drawn',s1[0]=='empty' and 'coming soon' in s1[1] and s2[0]=='drawn' and s2[1]>=1,{'empty':s1,'with_feature':s2})
  # T8 UM-046 cards agree with claims.json
  c=b.new_context(reduced_motion='reduce');pg=c.new_page();pg.goto(BASE+'timeslider.html',wait_until='networkidle');pg.wait_for_timeout(500);mism=[]
  for i,cl in enumerate(CLAIMS):
    pg.click(f'#ticks button:nth-child({i+1})');pg.wait_for_timeout(100)
    st=pg.inner_text('#card .status');refx=pg.inner_text('#card .srcp')
    if st!=cl['status'] or cl['reference'] not in refx:mism.append((cl['id'],st,cl['status']))
    if cl['status']=='pinned' and not cl['pinned']:mism.append((cl['id'],'pinned without pin'))
  c.close()
  c=b.new_context(java_script_enabled=False);pg=c.new_page();pg.goto(BASE+'timeslider.html')
  stat=pg.eval_on_selector_all('#stoplist .status','e=>e.map(x=>x.textContent)');c.close()
  if stat!=[cl['status'] for cl in CLAIMS]:mism.append(('static list',stat))
  rec('T08','UM-046 card status/reference agree with data/claims.json (JS cards and static list)',not mism,mism)
  # T9 shortcuts scoped
  c=b.new_context(reduced_motion='reduce');pg=c.new_page();pg.goto(BASE+'timeslider.html',wait_until='networkidle');pg.wait_for_timeout(500)
  v0=pg.input_value('#slider');pg.evaluate('document.activeElement.blur()');pg.keyboard.press('.');pg.keyboard.press('End');v1=pg.input_value('#slider')
  pg.focus('#ticks button');pg.keyboard.press('.');v2=pg.input_value('#slider');pg.focus('#slider');pg.keyboard.press('Home');v3=pg.input_value('#slider')
  rec('T09','shortcuts only act with focus in the slider region (WCAG 2.1.4)',v0==v1 and v2!=v1 and v3=='0',(v0,v1,v2,v3))
  # T10 hatch persists after zoom/move
  pg.click('#ticks button:nth-child(10)');pg.wait_for_timeout(300);pg.click('.leaflet-control-zoom-in');pg.wait_for_timeout(600);pg.mouse.move(400,800);pg.evaluate("window.scrollTo(0,0)")
  h=pg.evaluate("[...document.querySelectorAll('.leaflet-overlay-pane path')].filter(p=>p.getAttribute('fill')==='url(#hatch)').length");d=pg.evaluate("!!document.querySelector('pattern#hatch line')")
  rec('T10','hatch fill re-applied after zoom; defs built with createElementNS',h>=1 and d,{'hatched_paths':h,'pattern':d})
  pg.wait_for_timeout(8000);rec('T11','reduced motion: autoplay disabled',pg.is_disabled('#play') and 'off' in pg.inner_text('#play'),pg.inner_text('#play'));c.close()
  c=b.new_context(java_script_enabled=False);pg=c.new_page();pg.goto(BASE+'timeslider.html');n=pg.locator('#stoplist li').count();rec('T12','no-JS: 12 stops readable',n==12 and pg.is_visible('#stoplist'),n);c.close()
  over=[]
  for w in(320,390):
    for pg_ in PAGES:
      c=b.new_context(viewport={'width':w,'height':800});pg=c.new_page();pg.goto(BASE+pg_,wait_until='networkidle');sw=pg.evaluate('document.documentElement.scrollWidth')
      if sw>w:over.append((w,pg_,sw))
      c.close()
  rec('T13','no horizontal scroll at 320 and 390 px',not over,over)
  # T14 axe on every page, both themes, incl. court after a theme click
  ax={}
  for theme in('light','dark'):
    for pg_ in PAGES:
      c=b.new_context();c.add_init_script(f"localStorage.setItem('pa-theme','{theme}')");pg=c.new_page();pg.goto(BASE+pg_,wait_until='networkidle');pg.wait_for_timeout(600)
      pg.add_script_tag(content=AXE);v=json.loads(pg.evaluate("axe.run(document).then(r=>JSON.stringify(r.violations.map(v=>[v.id,v.nodes.length])))"))
      if v:ax[f'{theme} {pg_}']=v
      c.close()
  c=b.new_context();pg=c.new_page();pg.goto(BASE+'cuirt-fothnach.html',wait_until='networkidle');pg.click('.themebtn');pg.wait_for_timeout(300);pg.add_script_tag(content=AXE)
  v=json.loads(pg.evaluate("axe.run(document).then(r=>JSON.stringify(r.violations.map(v=>[v.id,v.nodes.length])))"));c.close()
  if v:ax['court after theme click']=v
  rec('T14','axe-core: 0 violations on all pages, light and dark, and the court page after a theme click',not ax,ax)
  b.close()
json.dump(R,open(ROOT+'/tests/results.json','w'),ensure_ascii=False,indent=1)
print(sum(r['result']=='PASS' for r in R),'/',len(R),'passed');sys.exit(0 if all(r['result']=='PASS' for r in R) else 1)
