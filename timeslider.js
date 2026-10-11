// PA Uí Mhaine time map. Data: data/claims.json (single source of truth) + data/eras.json (sketch geometry).
(function(){
'use strict';
const RM=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const CL={attested:'Core sites attested · outline sketched',interpretation:'Interpretation',claimed:'Claimed'};
const PL={Athlone:[53.423,-7.940],Roscommon:[53.634,-8.182],Ballinasloe:[53.328,-8.229],Tiaquin:[53.37,-8.62],Abbeyknockmoy:[53.437,-8.745],
 Kilconnell:[53.333,-8.400],Aughrim:[53.299,-8.316],Ahascragh:[53.398,-8.336],Fohenagh:[53.391,-8.421],'Tycooly (Ticooly)':[53.475,-8.412],Clonmacnoise:[53.326,-7.986],Knockdoe:[53.354,-8.887]};
const SVGNS='http://www.w3.org/2000/svg';
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.getElementById('jsui').hidden=false;
const map=L.map('tmap',{zoomControl:true,keyboard:true,zoomAnimation:!RM,fadeAnimation:!RM,markerZoomAnimation:!RM}).setView([53.42,-8.3],9);
let tileErrors=0;
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:18})
 .on('tileerror',()=>{if(++tileErrors===3)document.getElementById('tilenote').hidden=false;}).addTo(map);
const terrG=L.featureGroup().addTo(map);
function ensureHatch(){const svg=map.getPanes().overlayPane.querySelector('svg');if(!svg||svg.querySelector('#hatch'))return;
 const defs=document.createElementNS(SVGNS,'defs'),pat=document.createElementNS(SVGNS,'pattern'),line=document.createElementNS(SVGNS,'line');
 [['id','hatch'],['width','8'],['height','8'],['patternUnits','userSpaceOnUse'],['patternTransform','rotate(45)']].forEach(a=>pat.setAttribute(a[0],a[1]));
 [['x1','0'],['y1','0'],['x2','0'],['y2','8'],['stroke','#b07d1a'],['stroke-width','3']].forEach(a=>line.setAttribute(a[0],a[1]));
 pat.appendChild(line);defs.appendChild(pat);svg.insertBefore(defs,svg.firstChild);}
function applyHatch(){ensureHatch();terrG.eachLayer(l=>{if(l.options.hatched&&l.getElement())l.getElement().setAttribute('fill','url(#hatch)');});}
map.on('zoomend moveend viewreset',applyHatch);
const STY={attested:{color:'#8a5a00',weight:3,fillColor:'#d4a64a',fillOpacity:.35},interpretation:{color:'#b07d1a',weight:2,dashArray:'6 6',fillColor:'#d4a64a',fillOpacity:.2},claimed:{color:'#b07d1a',weight:2,dashArray:'2 6',fillOpacity:.5,hatched:true}};
for(const [n,ll] of Object.entries(PL))L.circleMarker(ll,{radius:5,color:'#fff',weight:1,fillColor:'#0f7c80',fillOpacity:.95}).bindTooltip(n,{permanent:['Athlone','Roscommon','Ballinasloe','Fohenagh','Abbeyknockmoy','Tiaquin'].includes(n),direction:'right',className:'lbl'}).addTo(map);
const odonovan=L.polygon([[53.75,-8.45],[53.75,-7.95],[53.40,-7.88],[53.05,-8.05],[52.98,-8.40],[53.20,-8.85],[53.50,-8.85]],{color:'#789',weight:1,dashArray:'2 6',fillOpacity:.04}).bindTooltip("O'Donovan 1843: a claim, not a fact · sketch, not traced");
const RT=[
 {p:[[53.328,-8.229],[53.330,-8.285],[53.331,-8.340]],n:'1. Ballinasloe west along the Eiscir Riada (the esker road). The Turoe Stone lies away to the south, on the left.'},
 {p:[[53.331,-8.340],[53.333,-8.400]],n:'2. On to Kilconnell on the esker line, where the poets turn north.'},
 {p:[[53.333,-8.400],[53.355,-8.402],[53.3746,-8.4009]],n:'3. North from Kilconnell by Callow Lough to Doon fort.'},
 {p:[[53.3746,-8.4009],[53.405,-8.440],[53.4341,-8.4761]],n:'4. Doon on to Gallagh (Gallagh Castle site; which Gallagh: verify with Garry Lohan).'},
 {p:[[53.4341,-8.4761],[53.420,-8.440],[53.4067,-8.4063]],n:'5. Gallagh to the court at Pallas (An Lios Mór), Fohenagh: journey\'s end (FitzPatrick).'}];
const routes=L.layerGroup([
 L.polyline([[53.27,-8.80],[53.30,-8.55],[53.33,-8.40],[53.33,-8.23],[53.38,-8.05],[53.423,-7.94]],{color:'#0f7c80',weight:3,dashArray:'10 6'}).bindTooltip('Slighe Mhór (Eiscir Riada), indicative line'),
 L.polyline([[53.66,-8.22],[53.55,-8.27],[53.45,-8.25],[53.33,-8.22],[53.23,-8.10],[53.18,-8.03]],{color:'#2563eb',weight:3}).bindTooltip('River Suck (approximate)'),
 L.polyline([[53.65,-8.00],[53.50,-7.97],[53.423,-7.94],[53.326,-7.99],[53.20,-8.02]],{color:'#2563eb',weight:4}).bindTooltip('River Shannon (approximate)'),
 L.circleMarker([53.2606,-8.5547],{radius:7,color:'#7c3aed',fillOpacity:.8}).bindTooltip('Turoe Stone, Bullaun: Iron Age decorated stone (landmark)'),
 ...RT.map(s=>L.polyline(s.p,{color:'#c2410c',weight:4,dashArray:'8 6'}).bindTooltip("Poets' route · route as told locally, reconstructed<br>"+s.n,{sticky:true}))]);
const assembly=L.layerGroup([L.circleMarker([53.40,-8.38],{radius:7,color:'#a16207'}).bindTooltip('Tullyneeny assembly / fair site (location approximate, verify)')]);
const learned=L.layerGroup([
 L.circleMarker([53.4067,-8.4063],{radius:7,color:'#be185d'}).bindTooltip('An Lios Mór (Irish form provisional), Pallas: court of Ó Ceallaigh and site of the 1351 feast (FitzPatrick)'),
 L.circleMarker([53.3746,-8.4009],{radius:6,color:'#be185d'}).bindTooltip('An Dún (Irish form provisional) · Doon fort'),
 L.circleMarker([53.3875,-8.4006],{radius:6,color:'#be185d'}).bindTooltip('Baile Uí Dhúgáin · Ballydoogan'),
 L.circleMarker([53.395,-8.388],{radius:6,color:'#be185d'}).bindTooltip('Baile na Banaba · Ballynabanaba: Ó Longargáin the harper (approximate position)'),
 L.circleMarker([53.4341,-8.4761],{radius:6,color:'#be185d'}).bindTooltip('Gallagh: on the poets\' route between Doon and Pallas (site identification: verify)'),
 L.circleMarker([53.434,-8.43],{radius:6,color:'#be185d'}).bindTooltip('Caltra: nearby court country (approximate)')]);
const boundary=L.geoJSON(null,{style:{color:'#dc2626',weight:3,fillOpacity:0}});
L.control.layers(null,{"O'Donovan 1843 claim (sketch, not traced)":odonovan,"Routes, rivers and the poets' route":routes,'Assembly sites':assembly,'Learned families and court':learned},{collapsed:window.innerWidth<600}).addTo(map);
fetch('data/true-boundary.geojson').then(r=>r.ok?r.json():null).then(g=>{const note=document.getElementById('boundarynote');
 if(g&&Array.isArray(g.features)&&g.features.length){boundary.addData(g).bindTooltip('Surveyed boundary (Garry Lohan)').addTo(map);note.textContent='Surveyed boundary shown in red.';note.dataset.state='drawn';}
 else{note.textContent='Boundary survey coming soon.';note.dataset.state='empty';}}).catch(()=>{const n=document.getElementById('boundarynote');n.textContent='Boundary survey coming soon.';n.dataset.state='empty';});
const sl=document.getElementById('slider'),card=document.getElementById('card'),pb=document.getElementById('play'),live=document.getElementById('live'),region=document.getElementById('tsregion');
let S=[],G={},cur=-1,timer=null;
function draw(s){terrG.clearLayers();s.polys.forEach(p=>{L.polygon(G[p.geom],STY[p.conf]).bindTooltip('<b>'+CL[p.conf]+'</b> · approximate'+(p.geom==='WIDE'?' · not to scale':'')+'<br>Source: '+esc(p.src),{sticky:true}).addTo(terrG);});applyHatch();}
function go(i,announce){i=(i+S.length)%S.length;if(i===cur)return;cur=i;const s=S[i];sl.value=i;sl.setAttribute('aria-valuetext',s.date+': '+s.title);
 draw(s);RM?map.setView(s.centre,s.zoom,{animate:false}):map.flyTo(s.centre,s.zoom,{duration:2});
 card.innerHTML='<p class="kicker">Stop '+(i+1)+' of '+S.length+' · '+esc(s.date)+'</p><h2 class="cardh"><span lang="ga">'+esc(s.ga)+'</span> · '+esc(s.title)+'</h2><p class="badges"><span class="badge '+s.kind+'">'+esc(s.kind)+'</span> <span class="badge">'+s.polys.map(p=>CL[p.conf]).join(' + ')+'</span></p><p>'+esc(s.claim)+'</p>'+(s.link?'<p><a href="'+s.link+'">Visit the court at Fohenagh →</a></p>':'')+
  '<p class="srcp" data-claim="'+s.id+'"><b>Reference:</b> '+esc(s.reference)+' · <b>Date:</b> '+esc(s.date)+' · <b>Evidence:</b> '+esc(s.evidence)+' · <b>Status:</b> <span class="status">'+esc(s.status)+'</span></p>';
 if(announce)live.textContent='Stop '+(i+1)+': '+s.date+', '+s.title+'. '+s.kind+'.';
 document.querySelectorAll('.ticks button').forEach((b,j)=>b.setAttribute('aria-current',j===i?'step':'false'));}
function stop(){clearInterval(timer);timer=null;if(RM)return;pb.textContent='▶ Play';pb.setAttribute('aria-pressed','false');}
// Shortcuts are scoped to the slider region (WCAG 2.1.4): only active while focus is inside it.
region.addEventListener('keydown',e=>{if(e.target===sl&&['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;let n=null;
 if(e.key==='.'||e.key==='ArrowRight')n=cur+1;else if(e.key===','||e.key==='ArrowLeft')n=cur-1;else if(e.key==='Home')n=0;else if(e.key==='End')n=S.length-1;
 if(n!==null){e.preventDefault();stop();go(n,true);}});
Promise.all([fetch('data/claims.json').then(r=>r.json()),fetch('data/eras.json').then(r=>r.json())]).then(([c,g])=>{S=c.claims;G=g;
 const tk=document.getElementById('ticks');S.forEach((s,i)=>{const b=document.createElement('button');b.type='button';b.textContent=s.date;b.setAttribute('aria-label',s.date+': '+s.title);b.onclick=()=>{stop();go(i,true);};tk.appendChild(b);});
 sl.max=S.length-1;sl.addEventListener('input',()=>{stop();go(+sl.value,true);});
 if(RM){pb.disabled=true;pb.textContent='Autoplay off (reduced motion)';}
 else pb.onclick=()=>{if(timer)return stop();pb.textContent='❚❚ Pause';pb.setAttribute('aria-pressed','true');timer=setInterval(()=>go(cur+1,true),7000);};
 document.getElementById('stoplist').hidden=true;go(S.findIndex(s=>s.date==='c. 1400'),false);});
})();
