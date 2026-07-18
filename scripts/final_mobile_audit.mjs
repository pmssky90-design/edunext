import { writeFile } from 'node:fs/promises';

const BASE = 'http://127.0.0.1:8017';
const pages = [
  ['home', '/'],
  ['busan-region', '/부산과외/'],
  ['gumi-region', '/구미과외/'],
  ['yangsan-region', '/양산과외/'],
  ['town', '/부산남천동과외/'],
  ['school-general', '/부산경남고과외/'],
  ['school-english', '/부산경남고영어과외/'],
  ['school-math', '/부산경남고수학과외/'],
  ['subject', '/영어과외/'],
  ['grade', '/초등과외/'],
];
const widths = [320, 360, 375, 390, 430];
const info = await (await fetch('http://127.0.0.1:9224/json/version')).json();
const ws = new WebSocket(info.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
let seq = 0;
const pending = new Map();
const consoleErrors = [];
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.method === 'Runtime.exceptionThrown') consoleErrors.push(msg.params.exceptionDetails.text || 'exception');
  if (!msg.id) return;
  const job = pending.get(msg.id);
  pending.delete(msg.id);
  msg.error ? job.reject(new Error(msg.error.message)) : job.resolve(msg.result);
};
const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
  const id = ++seq;
  pending.set(id, { resolve, reject });
  ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
});
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const page = (method, params = {}) => send(method, params, sessionId);
await page('Runtime.enable');
const results = [];
for (const [kind, path] of pages) {
  for (const width of widths) {
    await page('Emulation.setDeviceMetricsOverride', { width, height: width <= 768 ? 844 : 900, deviceScaleFactor: 1, mobile: false });
    if (width === widths[0]) {
      await page('Page.navigate', { url: BASE + path });
      await new Promise(resolve => setTimeout(resolve, 500));
    } else {
      await new Promise(resolve => setTimeout(resolve, 80));
    }
    const check = await page('Runtime.evaluate', {
      expression: `(()=>{const all=Array.from(document.querySelectorAll('body *'));const bad=all.filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+1||r.left<-1});const small=all.filter(e=>['A','BUTTON','SUMMARY'].includes(e.tagName)&&e.getBoundingClientRect().height>0&&e.getBoundingClientRect().height<44);const h=document.querySelector('h1');const lh=h?parseFloat(getComputedStyle(h).lineHeight):0;return JSON.stringify({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,overflowElements:bad.slice(0,8).map(e=>e.tagName+'.'+String(e.className)),smallTargets:small.length,smallElements:small.slice(0,8).map(e=>e.tagName+'.'+String(e.className)+':'+e.textContent.trim().slice(0,30)),h1Lines:h&&lh?Math.round(h.getBoundingClientRect().height/lh):0,menuCount:document.querySelectorAll('.top-nav a').length,bodyCard:!!document.querySelector('.content-body')})})()`,
      returnByValue: true,
    });
    results.push({ kind, path, width, ...JSON.parse(check.result.value) });
  }
}

await page('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false });
await page('Page.navigate', { url: BASE + '/부산과외/' });
await new Promise(resolve => setTimeout(resolve, 400));
const interaction = await page('Runtime.evaluate', {
  expression: `(()=>{const b=document.querySelector('.menu-toggle'),n=document.querySelector('.top-nav');b.click();const opened=n.classList.contains('is-open')&&b.getAttribute('aria-expanded')==='true'&&document.body.classList.contains('menu-open');n.click();const panelClickStaysOpen=n.classList.contains('is-open');b.click();const toggleClosed=!n.classList.contains('is-open')&&!document.body.classList.contains('menu-open');b.click();document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));const escapeClosed=!n.classList.contains('is-open')&&b.getAttribute('aria-expanded')==='false'&&!document.body.classList.contains('menu-open');b.click();document.querySelector('main').click();const outsideClosed=!n.classList.contains('is-open')&&!document.body.classList.contains('menu-open');return {opened,panelClickStaysOpen,toggleClosed,escapeClosed,outsideClosed}})()`,
  returnByValue: true,
});
await page('Runtime.evaluate', { expression: `document.querySelector('.top-nav a[href="/#high-schools"]').click()` });
await new Promise(resolve => setTimeout(resolve, 700));
const school = await page('Runtime.evaluate', { expression: `({schoolUrl:location.href,schoolTarget:!!document.getElementById('high-schools'),closedAfterLink:!document.querySelector('.top-nav').classList.contains('is-open')})`, returnByValue: true });
await writeFile('audit/final-mobile-results.json', JSON.stringify({ results, interaction: {...interaction.result.value, ...school.result.value}, consoleErrors }, null, 2));
await send('Target.closeTarget', { targetId });
ws.close();
