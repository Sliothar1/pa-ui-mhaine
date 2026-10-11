// PA shared theme: one script on every page. Saved in localStorage 'pa-theme'.
(function(){
  var d=document.documentElement;
  d.setAttribute('data-theme',localStorage.getItem('pa-theme')||'dark');
  function label(){var t=d.getAttribute('data-theme');document.querySelectorAll('.themebtn').forEach(function(b){b.setAttribute('aria-label','Theme: '+t+'. Switch to '+(t==='dark'?'light':'dark')+' theme');b.setAttribute('aria-pressed',t==='dark'?'true':'false');});}
  function toggle(){var t=d.getAttribute('data-theme')==='dark'?'light':'dark';d.setAttribute('data-theme',t);localStorage.setItem('pa-theme',t);label();}
  document.addEventListener('DOMContentLoaded',function(){document.querySelectorAll('.themebtn').forEach(function(b){b.addEventListener('click',toggle);});label();});
})();
