// PA shared theme: one script on every page. Saved in localStorage 'pa-theme'.
(function(){
  var d=document.documentElement,KEY='pa-theme',COL={dark:'#061f33',light:'#f3f8f9'};
  function get(){try{return localStorage.getItem(KEY);}catch(e){return null;}}
  function set(v){try{localStorage.setItem(KEY,v);}catch(e){}}
  function apply(t){d.setAttribute('data-theme',t);var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute('content',COL[t]);}
  apply(get()==='light'?'light':'dark');
  function label(){var t=d.getAttribute('data-theme');document.querySelectorAll('.themebtn').forEach(function(b){b.setAttribute('aria-label','Theme: '+t+'. Switch to '+(t==='dark'?'light':'dark')+' theme');b.setAttribute('aria-pressed',t==='dark'?'true':'false');});}
  function toggle(){var t=d.getAttribute('data-theme')==='dark'?'light':'dark';apply(t);set(t);label();}
  function init(){apply(d.getAttribute('data-theme'));document.querySelectorAll('.themebtn').forEach(function(b){b.addEventListener('click',toggle);});label();document.querySelectorAll('.egg42').forEach(function(b){b.addEventListener('click',function(){var n=document.getElementById(b.getAttribute('aria-controls'));var o=b.getAttribute('aria-expanded')==='true';b.setAttribute('aria-expanded',String(!o));if(n)n.hidden=o;});});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
