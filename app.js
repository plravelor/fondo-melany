/* CONTADOR PÚBLICO: no maneja dinero ni guarda datos personales. */
(() => {
  "use strict";
  const cfg = window.CAMPANA || {};
  const el = id => document.getElementById(id);
  const num = x => Number.isFinite(Number(x)) ? Math.max(0, Math.round(Number(x))) : 0;
  const meta = num(cfg.meta) || 3000000;
  const manual = num(cfg.recaudadoManual);
  const money = x => new Intl.NumberFormat('es-CO', {style:'currency', currency:'COP', maximumFractionDigits:0}).format(x).replace(/\s*COP\s*/g,'').replace(/\u00a0/g,'');
  const pct = x => (x * 100).toLocaleString('es-CO', {maximumFractionDigits:1}) + ' %';
  let actual = manual;
  let currentSuggestion = 50000;
  let toastTimer;

  function flash(message) {
    const t = el('toast'); t.textContent = message; t.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2800);
  }
  async function copyText(value) {
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(value);
      else {
        const area = document.createElement('textarea'); area.value = value; area.style.position = 'fixed';
        area.style.top='-2000px'; document.body.appendChild(area); area.select();
        if (!document.execCommand('copy')) throw new Error('No se pudo copiar');
        area.remove();
      }
      flash('Copiado. Verifica los datos antes de transferir.');
    } catch (err) { flash('No se pudo copiar. Mantén presionado el dato para copiarlo.'); }
  }
  const hitos = (Array.isArray(cfg.hitos) ? cfg.hitos : [500000,1000000,2000000,meta]).map(num).filter(x=>x>0).sort((a,b)=>a-b);
  if (!hitos.includes(meta)) hitos.push(meta);

  function renderMilestones(total) {
    const wrap = el('milestones'); wrap.replaceChildren();
    const current = hitos.find(x => total < x);
    hitos.forEach((h) => {
      const item=document.createElement('div'); item.className = 'milestone' + (total>=h?' done':current===h?' active':'');
      const mark=document.createElement('div'); mark.className='milestone-dot'; mark.textContent=total>=h?'✓':'';
      const label=document.createElement('div'); label.className='milestone-label'; label.textContent=money(h);
      item.append(mark,label); wrap.append(item);
    });
  }
  function renderSuggestion() {
    const missing = Math.max(0,meta-actual);
    el('collective').textContent = missing===0
      ? '¡Se alcanzó la meta! Gracias por ayudar a hacer posible esta participación.'
      : `Si ${Math.ceil(missing/currentSuggestion)} personas aportaran ${money(currentSuggestion)}, se cubriría lo que falta.`;
  }
  function render(total,source) {
    actual = num(total);
    const progress=actual/meta;
    el('recaudado').textContent=money(actual);
    el('meta').textContent=money(meta);
    el('faltante').textContent=money(Math.max(0,meta-actual));
    el('pct-main').textContent=pct(progress);
    const circle=el('dial-progress'); const circumference=2*Math.PI*72;
    circle.style.strokeDasharray=`${circumference}`;
    circle.style.strokeDashoffset=`${circumference*(1-Math.min(1,progress))}`;
    const next=hitos.find(h=>actual<h);
    if(next){
      const stepProg=Math.min(1,actual/next);
      el('hito-titulo').textContent=(next===hitos[0]?'Primer objetivo: ':'Próximo objetivo: ')+money(next);
      el('hito-pct').textContent=pct(stepProg);
      el('hito-bar').style.width=`${stepProg*100}%`;
      el('hito-texto').textContent=`Ya está cubierto el ${pct(stepProg)} de este objetivo. Faltan ${money(next-actual)} para alcanzarlo.`;
      el('bar-accessible').setAttribute('aria-valuenow',String(Math.round(stepProg*100)));
    }else{
      el('hito-titulo').textContent='¡Meta general alcanzada!';
      el('hito-pct').textContent='100 %';
      el('hito-bar').style.width='100%';
      el('hito-texto').textContent= actual>meta ? `Aportes por encima de la meta: ${money(actual-meta)}. Se informará su destinación en el balance final.` : 'Gracias por los aportes. Se publicará el balance al cierre.';
      el('bar-accessible').setAttribute('aria-valuenow','100');
    }
    renderMilestones(actual); renderSuggestion();
    el('estado-datos').textContent=source==='google'?'Monto confirmado publicado por el equipo de la colecta en Google Sheets.':source==='error'?'Mostrando el último monto guardado; no fue posible consultar la hoja de actualización.':'Cifra inicial registrada manualmente. Los ingresos se verifican por fuera de esta página.';
  }
  function payments() {
    const wrap=el('payment-list'); wrap.replaceChildren();
    for(const b of (cfg.bancos||[])){
      const card=document.createElement('div');card.className='payment-item';
      const name=document.createElement('span');name.className='type';name.textContent=b.nombre;
      const val=document.createElement('strong');val.textContent=b.dato;
      const desc=document.createElement('span');desc.className='descriptor';desc.textContent=b.tipo;
      const btn=document.createElement('button');btn.type='button';btn.textContent='Copiar dato';btn.setAttribute('aria-label',`Copiar ${b.tipo} de ${b.nombre}`);btn.addEventListener('click',()=>copyText(b.dato));
      card.append(name,val,desc,btn);wrap.append(card);
    }
  }
  function initOptions() {
    document.querySelectorAll('.amount-btn').forEach(b=>b.addEventListener('click',()=>{
      currentSuggestion=Number(b.dataset.amount);
      document.querySelectorAll('.amount-btn').forEach(other=>{
        other.classList.toggle('selected',other===b);
        other.setAttribute('aria-pressed',String(other===b));
      });renderSuggestion();
    }));
  }
  function share() {
    const url=location.href.split('#')[0].split('?')[0];
    const txt=`Apoyemos a Melany Queeman a presentar su investigación sobre el Vireo caribaeus en Brasil. Consulta la meta, el avance y cómo aportar: ${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(txt)}`,'_blank','noopener,noreferrer');
  }
  function loadSheet(){
    // Solo lee una celda de una hoja PÚBLICA dedicada exclusivamente al total.
    const id=String(cfg.sheetId||'').trim();
    if(!id) return;
    if(!/^[A-Za-z0-9_-]{15,}$/.test(id)){ render(manual,'error'); return; }
    const sheet=encodeURIComponent(cfg.sheetName||'PUBLICO');
    const url=`https://docs.google.com/spreadsheets/d/${id}/gviz/tq?sheet=${sheet}&range=B2&headers=0&tqx=${encodeURIComponent('out:json;responseHandler:melanyRecibeMonto')}&_=${Date.now()}`;
    const script=document.createElement('script');script.async=true;script.src=url;
    let settled=false;
    const timer=setTimeout(()=>{if(!settled){settled=true;render(manual,'error');script.remove();}},10000);
    window.melanyRecibeMonto=function(response){
      if(settled)return; settled=true;clearTimeout(timer);script.remove();
      const cell=response?.table?.rows?.[0]?.c?.[0];
      const value=cell?.v;
      if(response?.status==='ok' && typeof value==='number' && Number.isFinite(value) && value>=0)render(value,'google');
      else render(manual,'error');
    };
    script.onerror=()=>{if(!settled){settled=true;clearTimeout(timer);render(manual,'error');script.remove();}};
    document.head.append(script);
  }
  function init(){
    render(manual,'manual');payments();initOptions();loadSheet();
    el('share').addEventListener('click',share);
    el('copy-link').addEventListener('click',()=>copyText(location.href.split('?')[0].split('#')[0]));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
