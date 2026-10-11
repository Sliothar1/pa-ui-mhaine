// PA Uí Mhaine v2 time-slider. All polygons are approximate / interpretation only.
(function(){
const RM=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
// [lat,lng] rings; rough sketches around the Suck/Shannon basin.
const CORE=[[53.43,-8.47],[53.44,-8.36],[53.41,-8.28],[53.33,-8.26],[53.27,-8.30],[53.28,-8.42],[53.33,-8.48],[53.39,-8.50]];
const MID=[[53.52,-8.52],[53.56,-8.30],[53.55,-8.12],[53.44,-8.02],[53.32,-8.10],[53.22,-8.22],[53.20,-8.40],[53.27,-8.55],[53.38,-8.60]];
const TIRMAINE=[[53.68,-8.30],[53.70,-8.12],[53.58,-7.98],[53.44,-7.98],[53.36,-8.12],[53.40,-8.35],[53.52,-8.42]];
const WIDE=[[53.46,-8.78],[53.57,-8.60],[53.66,-8.24],[53.66,-8.12],[53.58,-8.00],[53.45,-7.92],[53.38,-7.96],[53.30,-8.10],[53.22,-8.22],[53.20,-8.42],[53.28,-8.62],[53.36,-8.70]];
const LATE=[[53.46,-8.60],[53.58,-8.30],[53.56,-8.08],[53.44,-8.02],[53.32,-8.15],[53.25,-8.28],[53.26,-8.45],[53.34,-8.58]];
const S=[
 {y:'c. 500',t:'Máine Mór comes west',ga:'Teacht Mháine Mhóir',p:MID,c:[53.36,-8.33],z:9,d:'Tradition tells of Máine Mór leading his people from the north to settle the lands west of the Shannon, and of a victory at Claenloch in 538 that secured them. Treat this as the kingdom\'s own origin story.',src:'Curley; O\'Donovan 1843 (tradition)'},
 {y:'c. 800',t:'The ruling lines settle',ga:'Na craobhacha ríoga',p:MID,c:[53.38,-8.30],z:9,d:'Several branches of the dynasty share and contest the kingship, and the kingdom takes shape across the Suck valley.',src:'Curley ch.2'},
 {y:'962',t:'Murchad and the Ó Cellaig name',ga:'Ainm Uí Cheallaigh',p:MID,c:[53.38,-8.30],z:9,d:'The family name comes from Cellach, an earlier king; by the later tenth century his descendants are known as Uí Chellaig. (Exact year as given in the plan; to be confirmed.)',src:'Curley; plan stop 3 (verify)'},
 {y:'1014',t:'Tadg Mór at Clontarf',ga:'Tadhg Mór i gCluain Tarbh',p:MID,c:[53.36,-6.20],z:7,d:'Tadg Mór Ua Cellaig fights beside Brian Bórama at Clontarf and is remembered among the fallen, a proud memory for the family.',src:'Annals, via Curley'},
 {y:'c. 1100',t:'Tír Maine and Clonmacnoise',ga:'Tír Mhaine agus Cluain Mhic Nóis',p:TIRMAINE,c:[53.48,-8.10],z:9,d:'The heartland lies along the Suck and Shannon in Tír Maine. Kings are carried across the river to rest at Clonmacnoise (a burial is recorded in 1167).',src:'Curley; Annals'},
 {y:'1139',t:'Rivers as roads',ga:'Aibhneacha mar bhóithre',p:TIRMAINE,c:[53.42,-8.05],z:9,d:'Toirrdelbach Ó Conchobair works on the waterways; boats on the Suck and Shannon link the kingdom to the wider midlands.',src:'Annals, via Curley (verify detail)'},
 {y:'1316',t:'Tadg at Athenry',ga:'Tadhg ag Baile Átha an Rí',p:CORE.concat([]),c:[53.30,-8.60],z:9,d:'Tadg Ó Ceallaigh is among the Gaelic lords who fight at Athenry; the lordship regroups around its core afterwards.',src:'Annals, via Curley'},
 {y:'1351',t:'The great Christmas feast',ga:'Nollaig na nÉigeas',p:MID,c:[53.40,-8.41],z:10,d:'Uilliam Buide Ó Ceallaigh invites the poets, judges, historians and musicians of Ireland for Christmas, and Gofraidh Fionn Ó Dálaigh praises it in verse. See the flagship page.',src:'Knott, Ériu 5 (1911); FitzPatrick; Curley',link:'cuirt-fothnach.html'},
 {y:'1353',t:'Kilconnell Friary',ga:'Mainistir Chill Chonaill',p:MID,c:[53.333,-8.40],z:10,d:'Uilliam founds a Franciscan friary at Kilconnell, a stone centre of learning and prayer at the heart of the lordship.',src:'AFM 1353, via Curley §5.3'},
 {y:'c. 1400',t:'Widest extent',ga:'Uí Mhaine ina buaic',p:WIDE,c:[53.43,-8.30],z:9,d:'Around 1380 to 1420 the lordship is at its broadest, from Athlone and Roscommon to Abbeyknockmoy and Tiaquin, with Ballinasloe and Tycooly within it (about six baronies by Curley\'s reckoning).',src:'Curley (c. 1,706 km²)'},
 {y:'1504',t:'Knockdoe',ga:'Cnoc Tuagh',p:LATE,c:[53.38,-8.70],z:10,d:'A great battle near Knockdoe draws in lords from across Connacht and beyond; Ó Ceallaigh is at its centre.',src:'AFM, via Curley'},
 {y:'1590s',t:'The old order fades',ga:'Deireadh ré',p:CORE,c:[53.36,-8.38],z:10,d:'By the end of the century the old lordship gives way. The names, townlands, poems and stones remain, and that is what this site celebrates.',src:'Curley; closing note'}
];
const PL={
 Athlone:[53.423,-7.940],Roscommon:[53.634,-8.182],Ballinasloe:[53.328,-8.229],Tiaquin:[53.37,-8.62],Abbeyknockmoy:[53.437,-8.745],
 Kilconnell:[53.333,-8.400],Aughrim:[53.299,-8.316],Ahascragh:[53.398,-8.336],Fohenagh:[53.391,-8.421],Tycooly:[53.475,-8.412],Clonmacnoise:[53.326,-7.986]};
const map=L.map('tmap',{zoomControl:true,keyboard:true,zoomAnimation:!RM,fadeAnimation:!RM}).setView([53.42,-8.3],9);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:18}).addTo(map);
const terr=L.polygon(WIDE,{color:'#d4a64a',weight:2,dashArray:'6 6',fillColor:'#d4a64a',fillOpacity:.25,className:'terr'}).addTo(map);
terr.bindTooltip('Approximate territory · interpretation, not a surveyed boundary',{sticky:true});
for(const [n,ll] of Object.entries(PL))L.circleMarker(ll,{radius:5,color:'#fff',weight:1,fillColor:'#3ec7c7',fillOpacity:.9}).bindTooltip(n,{permanent:['Athlone','Roscommon','Ballinasloe','Fohenagh','Abbeyknockmoy','Tiaquin'].includes(n),direction:'right',className:'lbl'}).addTo(map);
// toggle layers
const odonovan=L.polygon([[53.75,-8.45],[53.75,-7.95],[53.40,-7.88],[53.05,-8.05],[52.98,-8.40],[53.20,-8.85],[53.50,-8.85]],{color:'#9aa',weight:1,dashArray:'2 6',fillOpacity:.05}).bindTooltip("O'Donovan 1843: a claim, not a fact (faint sketch)");
const routes=L.layerGroup([
 L.polyline([[53.27,-8.80],[53.30,-8.55],[53.33,-8.40],[53.33,-8.23],[53.38,-8.05],[53.423,-7.94]],{color:'#8fe0d6',weight:3,dashArray:'10 6'}).bindTooltip('Slighe Mhór (Eiscir Riada), indicative line'),
 L.polyline([[53.66,-8.22],[53.55,-8.27],[53.45,-8.25],[53.33,-8.22],[53.23,-8.10],[53.18,-8.03]],{color:'#5aa9e6',weight:3}).bindTooltip('River Suck (approximate)'),
 L.polyline([[53.65,-8.00],[53.50,-7.97],[53.423,-7.94],[53.326,-7.99],[53.20,-8.02]],{color:'#5aa9e6',weight:4}).bindTooltip('River Shannon (approximate)')]);
const assembly=L.layerGroup([L.circleMarker([53.40,-8.38],{radius:7,color:'#f0c674'}).bindTooltip('Tullyneeny assembly / fair site (location approximate, verify)')]);
const learned=L.layerGroup([
 L.circleMarker([53.4067,-8.4063],{radius:7,color:'#e58fb6'}).bindTooltip('Lios Mór, Pallas: court of Ó Ceallaigh (FitzPatrick)'),
 L.circleMarker([53.3746,-8.4009],{radius:6,color:'#e58fb6'}).bindTooltip('Doon fort'),
 L.circleMarker([53.42,-8.39],{radius:6,color:'#e58fb6'}).bindTooltip('Ballynabanaba: Ó Longargain the harper (approximate position)'),
 L.circleMarker([53.578,-8.066],{radius:6,color:'#e58fb6'}).bindTooltip('Galey (Gailey), Lough Ree: the other candidate site for 1351')]);
const truth=L.geoJSON(null,{style:{color:'#ff5c5c',weight:3}});
fetch('data/true-boundary.geojson').then(r=>r.json()).then(g=>{truth.addData(g);document.getElementById('truthnote').textContent=g.features.length?'Corrected boundary loaded.':'Placeholder: Garry\'s corrected boundary arrives 12 Oct 2026.';}).catch(()=>{});
L.control.layers(null,{"O'Donovan 1843 claim (faint)":odonovan,'Routes and rivers':routes,'Assembly sites':assembly,'Learned families and court':learned,'True boundary (from 12 Oct)':truth},{collapsed:false}).addTo(map);
const sl=document.getElementById('slider'),card=document.getElementById('card'),pb=document.getElementById('play');
let cur=-1,timer=null;
function tween(to){const el=terr.getElement();if(!RM&&el){el.style.transition='opacity .4s';el.style.opacity=0;setTimeout(()=>{terr.setLatLngs(to);el.style.opacity=1},400)}else terr.setLatLngs(to)}
function go(i){i=(i+S.length)%S.length;if(i===cur)return;cur=i;const s=S[i];sl.value=i;sl.setAttribute('aria-valuetext',s.y+': '+s.t);
 tween(s.p);RM?map.setView(s.c,s.z,{animate:false}):map.flyTo(s.c,s.z,{duration:2});
 card.innerHTML='<p class="kicker">Stop '+(i+1)+' of 12 · '+s.y+'</p><h3><span lang="ga">'+s.ga+'</span> · '+s.t+'</h3><p>'+s.d+'</p>'+(s.link?'<p><a href="'+s.link+'">Visit the court at Fohenagh →</a></p>':'')+'<p class="src">Source: '+s.src+' · Shaded area: approximate / interpretation</p>';
 document.querySelectorAll('.ticks button').forEach((b,j)=>b.setAttribute('aria-current',j===i?'step':'false'))}
const tk=document.getElementById('ticks');S.forEach((s,i)=>{const b=document.createElement('button');b.type='button';b.textContent=s.y;b.onclick=()=>{stop();go(i)};tk.appendChild(b)});
sl.max=S.length-1;sl.addEventListener('input',()=>{stop();go(+sl.value)});
function stop(){clearInterval(timer);timer=null;pb.textContent='▶ Play';pb.setAttribute('aria-pressed','false')}
pb.onclick=()=>{if(timer)return stop();pb.textContent='❚❚ Pause';pb.setAttribute('aria-pressed','true');timer=setInterval(()=>go(cur+1),RM?9000:6000)};
document.addEventListener('keydown',e=>{if(e.target.closest&&e.target.closest('#tmap,input,textarea'))return;if(e.key==='ArrowRight'||e.key==='.'){stop();go(cur+1)}if(e.key==='ArrowLeft'||e.key===','){stop();go(cur-1)}if(e.key==='Home'){stop();go(0)}if(e.key==='End'){stop();go(S.length-1)}});
go(9);
})();
