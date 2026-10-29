/* CASCADE replay. The app displays exported evidence; it never invents observations. */
'use strict';
const $ = id => document.getElementById(id);
const SVG_NS = 'http://www.w3.org/2000/svg';
const state = { data: null, day: 0, frame: 0, airport: null, mode: 'forecast', timer: null, budget: null, policy: null, scenarioKey: null };
const repo = 'https://github.com/nazeeh111/cascade';
const number = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value)) ? Number(value) : null;
const fmt = (value, decimals = 0) => number(value) === null ? '—' : Number(value).toLocaleString('en-US', { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
const pct = (value, decimals = 0) => number(value) === null ? '—' : `${fmt(Number(value) * 100, decimals)}%`;
const pp = value => number(value) === null ? '—' : `${fmt(Number(value) * 100, 2)} pp`;
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const safeUrl = value => { try { const url = new URL(value || '#', location.href); return ['https:', 'http:'].includes(url.protocol) ? url.href : '#'; } catch { return '#'; } };
const externalLink = (url, label, cls = '') => `<a class="${cls}" href="${escapeHtml(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)} <span aria-hidden="true">↗</span></a>`;
const color = rate => rate === null ? '#829b9c' : rate < .2 ? '#77b6a1' : rate <= .4 ? '#deb56c' : '#e58b6d';
const day = () => state.data?.days?.[state.day];
const frame = () => day()?.frames?.[state.frame];
const airports = () => state.data?.airports || [];
const rows = () => frame()?.airports || [];
const scheduled = row => number(row?.scheduled ?? row?.sched_n_2h ?? row?.target_n);
const selectedRow = () => rows().find(row => row.airport === state.airport);
const selectedAirport = () => airports().find(airport => airport.airport === state.airport);
const rate = row => number(state.mode === 'forecast' ? row?.prediction : row?.target_rate);
const utcDate = value => { const parsed = new Date(/(?:Z|[+-]\d\d:\d\d)$/.test(String(value)) ? value : `${String(value).replace(' ', 'T')}Z`); return Number.isNaN(parsed.getTime()) ? null : parsed; };
const clock = value => { const d = utcDate(value); return d ? d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) : '—'; };
const longDate = value => { const d = utcDate(`${String(value).slice(0, 10)}T00:00:00Z`); return d ? d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : String(value || '—'); };
const sumAvailable = values => { const present = values.map(number).filter(value => value !== null); return present.length ? present.reduce((total, value) => total + value, 0) : null; };
function weightedRate(items, key) {
  let total = 0, count = 0;
  for (const row of items) { const n = scheduled(row), value = number(row[key]); if (n !== null && n > 0 && value !== null) { total += n * value; count += n; } }
  return count ? total / count : null;
}
function svgElement(tag, attrs = {}, text) { const el = document.createElementNS(SVG_NS, tag); for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value); if (text !== undefined) el.textContent = text; return el; }
function link(id, url) { if (!url) return; $(id).href = safeUrl(url); $(id).target = '_blank'; $(id).rel = 'noopener noreferrer'; }
function setText(id, value) { $(id).textContent = value ?? '—'; }
function formatWindow(start, hours = 2) {
  const from = utcDate(start); if (!from) return 'Time unavailable';
  const to = new Date(from.getTime() + hours * 3600000);
  const rollover = to.toISOString().slice(0, 10) !== from.toISOString().slice(0, 10) ? ' (next day)' : '';
  return `${clock(from.toISOString())} → ${clock(to.toISOString())}${rollover} UTC`;
}
function localAirportTime(airport) {
  try {
    const date = utcDate(frame()?.cutoff); if (!date) return { time: 'Unavailable', date: '' };
    return { time: new Intl.DateTimeFormat('en-US', { timeZone: airport.timezone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZoneName: 'short' }).format(date), date: new Intl.DateTimeFormat('en-GB', { timeZone: airport.timezone, day: '2-digit', month: 'short' }).format(date) };
  } catch { return { time: 'Unavailable', date: '' }; }
}
function captureControlFocus() {
  const active = document.activeElement;
  if (active?.classList.contains('airport-node')) return { surface: 'map', key: active.dataset.airport };
  if (active?.classList.contains('airport-row')) return { surface: 'list', key: active.dataset.airport };
  if (active?.classList.contains('policy-choice')) return { surface: 'policy', key: active.dataset.policy };
  return null;
}
function restoreControlFocus(focus) {
  if (!focus) return;
  const [container, selector, field] = focus.surface === 'map' ? ['networkMap', '.airport-node', 'airport'] : focus.surface === 'list' ? ['airportList', '.airport-row', 'airport'] : ['scenarioTable', '.policy-choice', 'policy'];
  [...$(container).querySelectorAll(selector)].find(control => control.dataset[field] === focus.key)?.focus({ preventScroll: true });
}
function readUrlState() {
  const params = new URLSearchParams(location.search);
  state.day = Math.max(0, state.data.days.findIndex(item => item.date === params.get('day')));
  state.airport = airports().some(item => item.airport === params.get('airport')) ? params.get('airport') : (airports().some(item => item.airport === 'DEN') ? 'DEN' : airports()[0]?.airport);
  state.mode = params.get('view') === 'outcome' ? 'outcome' : 'forecast';
  state.budget = params.has('budget') ? number(params.get('budget')) : null;
  state.policy = params.get('policy');
  selectInitialFrame(params.get('cutoff'));
}
function updateQuery() {
  const params = new URLSearchParams(); params.set('day', day()?.date || ''); params.set('cutoff', clock(frame()?.cutoff)); params.set('airport', state.airport || '');
  if (state.mode !== 'forecast') params.set('view', state.mode);
  if (state.budget !== null) params.set('budget', String(state.budget));
  if (state.policy) params.set('policy', state.policy);
  history.replaceState(null, '', `${location.pathname}?${params}${location.hash}`);
}
function initialize(data) {
  if (!data || !Array.isArray(data.airports) || !data.airports.length || !Array.isArray(data.days) || !data.days.length) throw new Error('The snapshot does not contain replay days and airport metadata.');
  data.days = data.days.filter(item => Array.isArray(item.frames) && item.frames.length);
  if (!data.days.length) throw new Error('The snapshot has no hourly frames to replay.');
  state.data = data;
  readUrlState();
  $('daySelect').innerHTML = data.days.map((item, index) => `<option value="${index}">${escapeHtml(longDate(item.date))}</option>`).join('');
  $('daySelect').value = state.day;
  const meta = data.meta || {};
  link('repoLink', meta.repository_url || repo); link('footerRepo', meta.repository_url || repo);
  link('mapSql', meta.sql_url || `${repo}/blob/main/dbt/models/marts/features.sql`);
  link('edgeSql',meta.edge_sql_url || `${repo}/blob/main/sql/app_edges.sql`); link('scenarioSql',meta.scenario_sql_url || `${repo}/blob/main/sql/scenario_inputs.sql`);
  link('airportSql', meta.sql_url || `${repo}/blob/main/dbt/models/marts/features.sql`);
  link('modelSource', meta.model_url || `${repo}/blob/main/docs/MODEL_CARD.md`);
  link('scenarioSource', meta.scenario_url || `${repo}/blob/main/reports/scenarios.json`);
  setText('daySelectionNote', meta.day_selection ? 'These are historical examples: two ordinary days and the two days with the highest final disruption rates. They were chosen after the fact for contrast, not used to tune the model.' : 'Historical examples. See the source analysis for the selection method.');
  renderFindings(); renderModels(); renderProvenance(); bindEvents();
  $('loadMessage').hidden = true; $('app').hidden = false; render();
  if (location.hash) {
    const initialHash = location.hash; let anchor;
    try { anchor = document.getElementById(decodeURIComponent(initialHash.slice(1))); } catch { anchor = null; }
    const align = () => { if (anchor && location.hash === initialHash) anchor.scrollIntoView({ block: 'start', behavior: 'instant' }); };
    if (document.fonts?.ready) document.fonts.ready.then(align); else align();
  }
}
function selectInitialFrame(preferred) {
  const frames = day().frames;
  let index = preferred ? frames.findIndex(item => clock(item.cutoff) === preferred) : -1;
  if (index < 0) index = frames.findIndex(item => clock(item.cutoff) === '16:00');
  state.frame = index >= 0 ? index : Math.floor(frames.length / 2);
  $('cutoffSlider').max = frames.length - 1;
  $('cutoffSlider').value = state.frame;
}
function render() {
  if (!frame()) return;
  const focus = captureControlFocus();
  const current = frame(), items = rows();
  $('workspace').dataset.view = state.mode;
  $('daySelect').value = state.day;
  setText('dayKind', day().label || (day().kind === 'stress' ? 'HIGH DISRUPTION' : 'ORDINARY DAY'));
  $('dayKind').classList.toggle('stress', day().kind === 'stress' || day().kind === 'severe');
  setText('cutoffDate', longDate(day().date)); setText('cutoffTime', clock(current.cutoff)); setText('sliderTime', `${clock(current.cutoff)} UTC`);
  $('cutoffSlider').value = state.frame;
  $('cutoffSlider').setAttribute('aria-valuetext', `${clock(current.cutoff)} UTC on ${longDate(day().date)}`);
  $('stepBack').disabled = state.frame === 0; $('stepNext').disabled = state.frame === day().frames.length - 1;
  const isForecast = state.mode === 'forecast';
  $('forecastMode').classList.toggle('active', isForecast); $('outcomeMode').classList.toggle('active', !isForecast);
  $('forecastMode').setAttribute('aria-pressed', String(isForecast)); $('outcomeMode').setAttribute('aria-pressed', String(!isForecast));
  setText('scheduledStat', fmt(sumAvailable(items.map(scheduled))));
  setText('rateLabel', isForecast ? 'Forecast disruption' : 'Final disruption');
  setText('rateStat', pct(weightedRate(items, isForecast ? 'prediction' : 'target_rate'), 1));
  setText('backlogStat', fmt(sumAvailable(items.map(item => item.backlog ?? item.backlog_n))));
  setText('horizonText', formatWindow(current.cutoff));
  setText('horizonInline', formatWindow(current.cutoff));
  const totalScheduled = sumAvailable(items.map(scheduled));
  $('intervalEmpty').hidden = totalScheduled !== 0;
  const next = day().frames.findIndex((item, index) => index > state.frame && sumAvailable((item.airports || []).map(scheduled)) > 0);
  $('nextScheduled').hidden = next < 0;
  setText('viewExplanation', isForecast ? `Forecasts use information assumed available by ${clock(current.cutoff)} UTC. Final outcomes remain hidden.` : `Final outcomes were not known at ${clock(current.cutoff)} UTC. This is an after-the-fact comparison.`);
  setText('mapBadge', isForecast ? 'FORECAST' : 'FINAL OUTCOMES'); $('mapBadge').classList.toggle('outcome', !isForecast);
  setText('mapNote', isForecast ? 'Color: predicted disruption in the next 2h. Node size: scheduled departure volume. Select an airport.' : 'Color: final disruption in the next 2h. Node size: scheduled volume. Outcomes were unknown at cutoff.');
  setText('airportListMetric', isForecast ? 'FORECAST' : 'FINAL OUTCOME');
  setText('replayContext',`Question: where is next-2h departure disruption concentrated? Denominator: ${fmt(sumAvailable(items.map(scheduled)))} scheduled WN departures at the eight focal airports. Finding: ${pct(weightedRate(items,isForecast?'prediction':'target_rate'),1)} ${isForecast?'predicted':'observed final'} disruption. Limit: final schedules and feed latencies are assumed; selected carrier/network only. Decision: compare rate with demand, then inspect the bounded recovery experiment.`);
  renderMap(); renderTimeline(); renderAirport(); renderScenarios(); syncPlayback(); updateQuery(); restoreControlFocus(focus);
}
const project = (lon, lat) => [65 + (lon + 126) / 58 * 770, 365 - (lat - 25) / 24 * 300];
function renderMap() {
  const svg = $('networkMap'); svg.replaceChildren();
  const defs = svgElement('defs');
  const glow = svgElement('filter', { id: 'edgeGlow', x: '-30%', y: '-30%', width: '160%', height: '160%' });
  glow.append(svgElement('feGaussianBlur', { stdDeviation: '0.8', result: 'blur' }));
  const merge = svgElement('feMerge'); merge.append(svgElement('feMergeNode', { in: 'blur' }), svgElement('feMergeNode', { in: 'SourceGraphic' })); glow.append(merge); defs.append(glow);
  svg.append(defs);
  const grid = svgElement('g', { class: 'map-grid' });
  for (let longitude = -125; longitude < -65; longitude += 10) { const a = project(longitude, 25), b = project(longitude, 49); grid.append(svgElement('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1] })); }
  for (let latitude = 25; latitude < 50; latitude += 5) { const a = project(-126, latitude), b = project(-68, latitude); grid.append(svgElement('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1] })); } svg.append(grid);
  svg.append(svgElement('image', { href: 'assets/us-states.svg', x: 0, y: 0, width: 900, height: 445, opacity: '.9', 'aria-hidden': 'true' }));
  svg.append(svgElement('text', { x: 70, y: 336, class: 'map-waterlabel', transform: 'rotate(-68 70 336)' }, 'PACIFIC'));
  svg.append(svgElement('text', { x: 768, y: 272, class: 'map-waterlabel', transform: 'rotate(-55 768 272)' }, 'ATLANTIC'));
  const metadata = Object.fromEntries(airports().map(item => [item.airport, item]));
  const edgeGroup = svgElement('g');
  const rawEdges=frame().edges || day().edges || state.data.edges || [];
  const combined=new Map();
  for(const e of rawEdges){const o=e.origin??e.from,d=e.dest??e.to;if(!o||!d||o===d)continue;const key=[o,d].sort().join('-');const v=combined.get(key)||{origin:o,dest:d,flights:0,directions:[]};v.flights+=number(e.flights)||0;v.directions.push(`${o} → ${d}: ${fmt(e.flights)}`);combined.set(key,v);}
  const edges=[...combined.values()];
  for (const edge of edges) {
    const origin = edge.origin ?? edge.from, dest = edge.dest ?? edge.to;
    const a = metadata[origin], b = metadata[dest]; if (!a || !b || origin === dest) continue;
    
    const p = project(Number(a.lon), Number(a.lat)), q = project(Number(b.lon), Number(b.lat));
    const distance = Math.hypot(q[0] - p[0], q[1] - p[1]);
    const curve = Math.min(42, distance * .12), mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2 - curve;
    const isSelected = [origin, dest].includes(state.airport);
    const path = svgElement('path', { d: `M${p[0]},${p[1]} Q${mx},${my} ${q[0]},${q[1]}`, class: `network-edge${isSelected ? ' selected' : ''}`, 'stroke-width': Math.min(2.3, .7 + Math.log1p(number(edge.flights) || 1) / 4) });
    path.append(svgElement('title', {}, `${origin} ↔ ${dest}: ${fmt(edge.flights)} scheduled departures in next 2h, both directions. ${edge.directions.join('; ')}`)); edgeGroup.append(path);
  } svg.append(edgeGroup);
  for (const airport of airports()) {
    if (number(airport.lon) === null || number(airport.lat) === null) continue;
    const [x, y] = project(Number(airport.lon), Number(airport.lat)), row = rows().find(item => item.airport === airport.airport), value = rate(row), n = scheduled(row);
    const radius = 7 + Math.min(7, Math.sqrt(n || 0) * .9);
    const g = svgElement('g', { class: `airport-node${state.airport === airport.airport ? ' selected' : ''}`, transform: `translate(${x},${y})`, role: 'button', tabindex: '0', 'data-airport': airport.airport, 'aria-label': `${airport.airport}, ${airport.name}. ${state.mode === 'forecast' ? 'Forecast' : 'Final'} disruption ${value === null ? 'unavailable' : pct(value)}. Select airport.`, 'aria-pressed': String(state.airport === airport.airport) });
    g.append(svgElement('circle', { r: 25, class: 'hit-area' }));
    g.append(svgElement('circle', { r: radius + 9, class: 'outer', stroke: color(value) }));
    g.append(svgElement('circle', { r: radius + 4, class: 'node-ring' }));
    g.append(svgElement('circle', { r: radius, fill: color(value), stroke: '#18343f', 'stroke-width': 2 }));
    const left = airport.airport === 'OAK' || airport.airport === 'DAL', above = ['BWI', 'MDW', 'DEN', 'LAS'].includes(airport.airport);
    let tx = left ? -18 : 18, ty = above ? -11 : 3;
    if (airport.airport === 'HOU') { tx = 17; ty = 9; }
    g.append(svgElement('text', { x: tx, y: ty, 'text-anchor': left ? 'end' : 'start' }, airport.airport));
    g.append(svgElement('text', { x: tx, y: ty + 14, 'text-anchor': left ? 'end' : 'start', class: 'node-value' }, pct(value)));
    g.addEventListener('click', () => selectAirport(airport.airport));
    g.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectAirport(airport.airport); } });
    svg.append(g);
  }
}
function selectAirport(code) {
  const focus = captureControlFocus(); if (focus && focus.surface !== 'policy') focus.key = code;
  state.airport = code; renderMap(); renderAirport(); updateQuery(); restoreControlFocus(focus);
  setText('announcement', `${code} selected. ${state.mode === 'forecast' ? 'Forecast' : 'Final'} disruption ${pct(rate(selectedRow()))}.`);
}
function renderTimeline() {
  const svg = $('timeline'); svg.replaceChildren();
  const compact=window.matchMedia('(max-width:650px)').matches;
  const frames = day().frames, width = compact?350:850, left = 34, right = 12, top = 8, bottom = 112;
  svg.setAttribute('viewBox',`0 0 ${width} 140`);
  const x = index => left + index / Math.max(1, frames.length - 1) * (width - left - right);
  const allValues = frames.flatMap((item,index) => state.mode==='forecast' ? (index<=state.frame ? [weightedRate(item.airports || [], 'prediction')] : []) : [weightedRate(item.airports || [], 'prediction'),weightedRate(item.airports || [], 'target_rate')]).filter(value=>value!==null);
  const ceiling = Math.max(.4, Math.min(1, Math.ceil(Math.max(0, ...allValues) * 5) / 5));
  const y = value => bottom - Math.min(ceiling, Math.max(0, value)) / ceiling * (bottom - top);
  const defs = svgElement('defs'), gradient = svgElement('linearGradient', { id: 'timelineFill', x1: '0%', y1: '0%', x2: '0%', y2: '100%' });
  gradient.append(svgElement('stop', { offset: '0%', 'stop-color': '#43886b', 'stop-opacity': '.24' }), svgElement('stop', { offset: '100%', 'stop-color': '#43886b', 'stop-opacity': '.01' })); defs.append(gradient); svg.append(defs);
  const cutoffX = x(state.frame);
  if (state.mode === 'forecast' && state.frame < frames.length - 1) {
    svg.append(svgElement('rect', { x: cutoffX, y: top, width: width-right-cutoffX, height: bottom-top, class: 'chart-future' }));
    if (width-right-cutoffX > (compact ? 65 : 110)) svg.append(svgElement('text', { x: (cutoffX+width-right)/2, y: top+16, 'text-anchor': 'middle', class: 'chart-future-label' }, 'AFTER CUTOFF'));
  }
  for (let tick = 0; tick <= 4; tick++) { const value = ceiling * tick / 4, yy = y(value); svg.append(svgElement('line', { x1: left, x2: width - right, y1: yy, y2: yy, class: 'chart-grid' })); svg.append(svgElement('text', { x: left - 8, y: yy + 3, 'text-anchor': 'end', class: 'chart-axis' }, `${Math.round(value * 100)}%`)); }
  const tickStep = Math.max(1, Math.ceil(frames.length / 7));
  for (let index = 0; index < frames.length; index += tickStep) svg.append(svgElement('text', { x: x(index), y: 134, 'text-anchor': 'middle', class: 'chart-axis' }, clock(frames[index].cutoff)));
  setText('timelineModeNote',state.mode==='forecast' ? 'Only forecasts made by this cutoff are shown. Final outcomes and future-cutoff forecasts remain hidden.' : 'Retrospective comparison: complete-day forecasts and final outcomes are now visible.');
  $('finalLegend').hidden=state.mode==='forecast';
  for (const [key, stroke, dashed] of (state.mode==='forecast' ? [['prediction','#2b776c',false]] : [['target_rate', '#bc9970', true], ['prediction', '#2b776c', false]])) {
    let path = '', drawing = false;
    frames.forEach((item, index) => { const value = state.mode==='forecast' && index>state.frame ? null : weightedRate(item.airports || [], key); if (value === null) { drawing = false; return; } path += `${drawing ? 'L' : 'M'}${x(index)},${y(value)} `; drawing = true; });
    if (key === 'prediction') {
      let points = [];
      const flush = () => { if (points.length > 1) { const area = `M${points[0][0]},${bottom} ` + points.map(([xx, yy]) => `L${xx},${yy}`).join(' ') + ` L${points[points.length-1][0]},${bottom} Z`; svg.append(svgElement('path', { d: area, class: 'chart-area' })); } points = []; };
      frames.forEach((item,index) => { const v = state.mode === 'forecast' && index > state.frame ? null : weightedRate(item.airports || [], key); if (v === null) flush(); else points.push([x(index),y(v)]); }); flush();
    }
    svg.append(svgElement('path', { d: path, fill: 'none', stroke, 'stroke-width': dashed ? 1.7 : 2.2, ...(dashed ? { 'stroke-dasharray': '5 5' } : {}), 'stroke-linejoin': 'round' }));
  }
  const currentX = x(state.frame); svg.append(svgElement('line', { x1: currentX, x2: currentX, y1: 2, y2: bottom + 5, class: 'chart-cutoff' }));
  const value = weightedRate(rows(), state.mode === 'forecast' ? 'prediction' : 'target_rate');
  if (value !== null) svg.append(svgElement('circle', { cx: currentX, cy: y(value), r: 4.5, class: 'chart-current' }));
  svg.append(svgElement('title', {}, `Two-hour scheduled-departure disruption rates on ${day().date}; forecasts versus final outcomes. Selected cutoff ${clock(frame().cutoff)} UTC.`));
}
function renderAirport() {
  const airport = selectedAirport(), row = selectedRow(); if (!airport) return;
  setText('airportTitle', airport.airport); setText('airportName', airport.name); const local = localAirportTime(airport); $('airportTimezone').innerHTML = `<span>Local time</span><strong>${escapeHtml(local.time)}</strong><small>${escapeHtml(local.date)}</small>`; $('airportTimezone').title = airport.timezone || 'Timezone unavailable';
  const value = rate(row), n = scheduled(row), observed = number(row?.observed_rate ?? row?.lag_rate_2h);
  const gaugePct = value === null ? 0 : Math.max(0, Math.min(100, value * 100));
  $('airportDetail').innerHTML = `<div class="airport-detail"><div class="airport-gauge${value === null ? ' missing' : ''}" role="img" aria-label="${value === null ? (n === 0 ? 'No scheduled departures in this two-hour window' : 'Disruption rate unavailable') : escapeHtml(pct(value)) + (state.mode === 'forecast' ? ' forecast disruption' : ' final disruption')}" style="--gauge-color:${color(value)};--gauge-pct:${gaugePct}%"><strong class="airport-rate">${escapeHtml(pct(value))}</strong></div><div class="airport-detail-info"><strong>${n === 0 ? 'No scheduled departures' : value === null ? (state.mode === 'forecast' ? 'No forecast available' : 'No final outcome available') : (state.mode === 'forecast' ? 'Forecast next 2h' : 'Final outcome next 2h')}</strong>${escapeHtml(fmt(n))} scheduled departures<span class="detail-secondary">Observed past 2h: ${escapeHtml(pct(observed))}</span></div></div>`;
  const ranked = airports().map(meta => ({ meta, row: rows().find(item => item.airport === meta.airport) })).sort((a, b) => (rate(b.row) ?? -1) - (rate(a.row) ?? -1));
  $('airportList').innerHTML = ranked.map(({ meta, row: item }) => { const r = rate(item); return `<button class="airport-row${meta.airport === state.airport ? ' selected' : ''}" type="button" data-airport="${escapeHtml(meta.airport)}" aria-pressed="${meta.airport === state.airport}" aria-label="${escapeHtml(meta.airport)} ${r === null ? 'rate unavailable' : escapeHtml(pct(r)) + ' disruption'}"><span class="airport-code">${escapeHtml(meta.airport)}</span><span class="airport-bar"><i style="width:${Math.max(0, Math.min(100, (r || 0) * 100))}%;background:${color(r)}"></i></span><span class="airport-row-value">${escapeHtml(pct(r))}</span><span class="airport-row-arrow" aria-hidden="true">↗</span></button>`; }).join('');
  $('airportList').querySelectorAll('button').forEach(button => button.addEventListener('click', () => selectAirport(button.dataset.airport)));
  const weather = row?.weather || row || {}, age = number(weather.age_min ?? weather.weather_age_min), temp = number(weather.temp_c), wind = number(weather.wind_ms), visibility = number(weather.visibility_m);
  $('weatherDetail').innerHTML = `<span class="tiny-label">LAST AVAILABLE WEATHER</span><div class="weather-grid"><div><strong>${temp === null ? '—' : `${fmt(temp, 1)}°C`}</strong><span>Temperature</span></div><div><strong>${wind === null ? '—' : `${fmt(wind, 1)} m/s`}</strong><span>Wind speed</span></div><div><strong>${visibility === null ? '—' : `${fmt(visibility / 1000, 1)} km`}</strong><span>Visibility</span></div></div><p class="weather-age">${age === null ? 'No weather report was available by this cutoff.' : `Observation ${fmt(age)} min before cutoff; eligibility includes declared reporting latency.`}</p>`;
}
function scenarioRows() {
  const currentDay = day(); let all = currentDay.scenarios;
  if (!all) { const source = state.data.scenarios; all = Array.isArray(source) ? source : source?.rows || []; all = all.filter(item => !item.date || String(item.date).slice(0, 10) === currentDay.date); }
  return (all || []).map(item => ({ ...item, budget: number(item.budget ?? item.resources), policy: item.policy ?? item.strategy, baseline_delay_min: number(item.baseline_delay_min ?? item.baseline_minutes), scenario_delay_min: number(item.scenario_delay_min ?? item.delay_minutes ?? item.total_delay_min), benefit_min: number(item.benefit_min ?? item.reduction_min) })).filter(item => item.policy && item.budget !== null);
}
function policyName(policy) { return ({ none: 'No intervention', no_action: 'No intervention', baseline: 'No intervention', volume: 'Scheduled volume', volume_heuristic: 'Scheduled volume', backlog: 'Backlog first', backlog_heuristic: 'Backlog first', forecast: 'Forecast-aware optimizer', optimizer: 'Forecast-aware optimizer', forecast_aware: 'Forecast-aware optimizer', forecast_optimizer: 'Forecast-aware optimizer', random: 'Random allocation', uniform: 'Equal allocation' })[policy] || String(policy).replace(/_/g, ' ').replace(/\b\w/g, value => value.toUpperCase()); }
function renderScenarios() {
  const key = JSON.stringify([day().date, state.budget, state.policy]);
  if (state.scenarioKey === key) return;
  const focus = captureControlFocus();
  const all = scenarioRows(), budgets = [...new Set(all.map(item => item.budget))].sort((a, b) => a - b);
  if (!budgets.includes(state.budget)) state.budget = budgets.find(value => value > 0) ?? budgets[0] ?? null;
  $('budgetSelect').innerHTML = budgets.length ? budgets.map(value => `<option value="${value}">${value} ${value === 1 ? 'resource' : 'resources'}</option>`).join('') : '<option>No evaluated scenarios</option>';
  $('budgetSelect').value = state.budget; $('budgetSelect').disabled = !budgets.length;
  const fixedBudget = budgets.length === 1;
  $('budgetSelect').hidden = fixedBudget; $('budgetFixed').hidden = !fixedBudget;
  $('budgetLabel').htmlFor = fixedBudget ? 'budgetFixed' : 'budgetSelect';
  setText('budgetFixed', fixedBudget ? `${fmt(state.budget)} hypothetical teams` : '');
  $('fixedBudgetNote').hidden = !fixedBudget;
  setText('scenarioContext', `${longDate(day().date)} · Simulation at 16:00 UTC, independent of the replay cursor.`);
  const atBudget = all.filter(item => item.budget === state.budget), policies = [...new Set(atBudget.map(item => item.policy))];
  if (!policies.includes(state.policy)) state.policy = policies.find(policy => /forecast|optimizer/.test(policy)) || policies[0] || null;
  $('policySelect').innerHTML = policies.length ? policies.map(policy => `<option value="${escapeHtml(policy)}">${escapeHtml(policyName(policy))}</option>`).join('') : '<option>No evaluated strategies</option>';
  $('policySelect').value = state.policy; $('policySelect').disabled = !policies.length;
  const selected = atBudget.find(item => item.policy === state.policy);
  state.scenarioKey = JSON.stringify([day().date, state.budget, state.policy]);
  if (!selected) {
    setText('benefitStat', '—'); setText('benefitPercent', 'No evaluated scenario'); $('scenarioBars').innerHTML = ''; $('scenarioTable').innerHTML = '<tr><td colspan="3">No scenario exported for this day.</td></tr>'; $('allocations').innerHTML = '<p class="allocation-empty">No evaluated allocation.</p>'; setText('scenarioContext', `${longDate(day().date)} · No evaluated simulation available.`); setText('scenarioNote', 'No evaluated simulation is available for this day. Choose another replay day.'); setText('resourceDescription', 'Only evaluated resource budgets appear here.'); restoreControlFocus(focus); return;
  }
  const baseline = selected.baseline_delay_min, scenario = selected.scenario_delay_min, benefit = selected.benefit_min ?? (baseline !== null && scenario !== null ? baseline - scenario : null);
  $('benefitStat').innerHTML = `${escapeHtml(fmt(benefit, 1))}<small> min</small>`;
  setText('benefitPercent', baseline > 0 && benefit !== null ? `${pct(benefit / baseline, 1)} of baseline` : 'Bounded scenario');
  const maxDelay = Math.max(1, ...atBudget.flatMap(item => [item.baseline_delay_min || 0, item.scenario_delay_min || 0]));
  const bars = [{ name: 'No intervention', value: baseline, active: false }, { name: policyName(state.policy), value: scenario, active: true }];
  $('scenarioBars').innerHTML = bars.map(bar => `<div class="scenario-bar-row${bar.active ? ' active' : ''}"><span>${escapeHtml(bar.name)}</span><span class="scenario-bar-track"><i style="width:${bar.value === null ? 0 : Math.min(100, bar.value / maxDelay * 100)}%"></i></span><span class="scenario-bar-value">${escapeHtml(fmt(bar.value))}</span></div>`).join('');
  $('scenarioTable').innerHTML = atBudget.map(item => { const reduction = item.benefit_min ?? (item.baseline_delay_min !== null && item.scenario_delay_min !== null ? item.baseline_delay_min - item.scenario_delay_min : null); return `<tr class="${item.policy === state.policy ? 'selected' : ''}"><td><button type="button" class="policy-choice" data-policy="${escapeHtml(item.policy)}" aria-pressed="${item.policy === state.policy}">${escapeHtml(policyName(item.policy))}</button></td><td>${escapeHtml(fmt(item.scenario_delay_min, 1))}</td><td>${escapeHtml(fmt(reduction, 1))} min</td></tr>`; }).join('');
  const hasAllocation = selected.allocations !== undefined || selected.allocation !== undefined;
  let allocations = selected.allocations || selected.allocation || {};
  if (Array.isArray(allocations)) allocations = Object.fromEntries(allocations.map(item => [item.airport, item.resources ?? item.count ?? item.units]));
  const allocationEntries = Object.entries(allocations).filter(([, value]) => number(value) > 0);
  $('allocations').innerHTML = allocationEntries.length ? allocationEntries.map(([airport, count]) => `<span class="allocation-chip">${escapeHtml(airport)} × ${escapeHtml(count)}</span>`).join('') : `<p class="allocation-empty">${hasAllocation ? 'No resources allocated for this strategy.' : 'No airport-level allocation supplied.'}</p>`;
  const cutoff = selected.cutoff ? ` Cutoff: ${clock(selected.cutoff)} UTC.` : '';
  setText('scenarioNote', selected.note || `Fixed replay day and assumptions; only the allocation changes.${cutoff} Resources cannot recover cancellations or supply missing operational constraints.`);
  setText('resourceDescription', selected.resource_description || 'A resource is a bounded hypothetical intervention; inspect the source assumptions.');
  $('scenarioTable').querySelectorAll('.policy-choice').forEach(button => button.addEventListener('click', () => choosePolicy(button.dataset.policy)));
  restoreControlFocus(focus);
}
function renderFindings() {
  const findings = state.data.findings || [];
  $('findings').innerHTML = findings.length ? findings.map((finding, index) => `<article class="finding"><div class="finding-number"><span>FINDING / ${String(index + 1).padStart(2, '0')}</span><span aria-hidden="true">↗</span></div><h3>${escapeHtml(finding.title || finding.question)}</h3><p class="finding-question">${escapeHtml(finding.question)}</p><p class="finding-result">${escapeHtml(finding.finding || finding.result)}</p><p class="finding-decision"><b>Decision implication</b>${escapeHtml(finding.decision || finding.implication || 'See source analysis.')}</p><details class="finding-context"><summary>Denominator &amp; limitations</summary><dl><dt>Denominator</dt><dd>${escapeHtml(finding.denominator || 'See generating analysis.')}</dd><dt>Limitation</dt><dd>${escapeHtml(finding.limitation || finding.limit || 'See source analysis for limitations.')}</dd></dl></details>${externalLink(finding.sql_url || state.data.meta?.analysis_url || `${repo}/blob/main/reports/eda.json`, 'Inspect the analysis', 'text-link')}</article>`).join('') : '<p class="empty-state">No analytical findings were included in this snapshot. Inspect the source analyses before drawing conclusions.</p>';
}
function renderModels() {
  const models = state.data.models || {}, metrics = Array.isArray(models) ? models : models.metrics || [];
  setText('modelSummary', models.summary || 'Compare the tabular model with seasonal and rolling baselines, then test the contribution of network features on unseen dates. The exported evaluation determines which forecast powers this replay.');
  $('modelTable').innerHTML = metrics.length ? metrics.map(metric => `<tr class="${metric.model === state.data.meta?.forecast_model ? 'preferred' : ''}"><td>${escapeHtml(metric.label || policyName(metric.model || 'Unnamed model'))}${metric.model === state.data.meta?.forecast_model ? '<span class="model-badge">Selected</span>' : ''}</td><td>${escapeHtml(metric.split || metric.fold || 'holdout')}</td><td>${escapeHtml(pp(metric.mae))}</td><td>${escapeHtml(pp(metric.rmse))}</td><td>${escapeHtml(pp(metric.calibration_mae))}</td><td>${escapeHtml(pct(metric.severe_recall ?? metric.severe_event_recall, 1))}</td><td>${number(metric.runtime_seconds ?? metric.runtime_s) === null ? '—' : `${escapeHtml(fmt(metric.runtime_seconds ?? metric.runtime_s, 2))} s`}</td></tr>`).join('') : '<tr><td class="model-empty" colspan="7">No evaluation metrics supplied. Open the model card for evidence and limits.</td></tr>';
}
function renderProvenance() {
  const meta = state.data.meta || {}, details = [];
  if (meta.source_snapshot) details.push(`Snapshot: ${meta.source_snapshot}`);
  if (meta.model_run) details.push(`Model run: ${meta.model_run}`);
  if (meta.flight_count) details.push(`${fmt(meta.flight_count)} source-scope flights`);
  if (meta.generated_at) details.push(`Exported: ${meta.generated_at}`);
  setText('snapshotDetail', details.join(' · ') || 'Inspect source manifests, generating SQL, and model-run artifacts in the public repository.');
  const items = state.data.provenance?.length ? state.data.provenance : [{ label: 'Source snapshots', url: meta.source_url || `${repo}/blob/main/data/manifest.json` }, { label: 'SQL warehouse', url: meta.sql_url || `${repo}/tree/main/dbt` }, { label: 'Model run', url: meta.model_url || `${repo}/blob/main/reports/model_evaluation.json` }, { label: 'Rebuild guide', url: `${repo}#reproduce` }];
  $('provenanceLinks').innerHTML = items.map(item => externalLink(item.url, item.label || item.name || 'Evidence')).join('');
}
function syncPlayback() {
  const playing = state.timer !== null, last = state.frame >= day().frames.length - 1;
  document.body.classList.toggle('playing', playing);
  $('playPause').disabled = day().frames.length <= 1;
  $('playPause').innerHTML = `<span aria-hidden="true">${playing ? 'Ⅱ' : '▶'}</span><span class="playback-label" aria-hidden="true">${playing ? 'Pause' : last ? 'Replay' : 'Play'}</span>`;
  $('playPause').setAttribute('aria-label', playing ? 'Pause hourly replay' : last ? 'Replay from first cutoff' : 'Play hourly replay');
}
function stopPlayback() { if (state.timer !== null) clearInterval(state.timer); state.timer = null; if (day()) syncPlayback(); }
function choosePolicy(policy) { stopPlayback(); state.policy = policy; renderScenarios(); updateQuery(); }
function bindEvents() {
  $('daySelect').addEventListener('change', event => { const preferred = clock(frame().cutoff); stopPlayback(); state.day = Number(event.target.value); selectInitialFrame(preferred); render(); });
  $('cutoffSlider').addEventListener('input', event => { stopPlayback(); state.frame = Number(event.target.value); render(); });
  $('stepBack').addEventListener('click', () => { stopPlayback(); state.frame = Math.max(0, state.frame - 1); render(); });
  $('stepNext').addEventListener('click', () => { stopPlayback(); state.frame = Math.min(day().frames.length - 1, state.frame + 1); render(); });
  $('nextScheduled').addEventListener('click', () => { const index = day().frames.findIndex((item, i) => i > state.frame && sumAvailable((item.airports || []).map(scheduled)) > 0); if (index >= 0) { stopPlayback(); state.frame = index; render(); $('cutoffSlider').focus({ preventScroll: true }); } });
  $('forecastMode').addEventListener('click', () => { stopPlayback(); state.mode = 'forecast'; render(); });
  $('outcomeMode').addEventListener('click', () => { stopPlayback(); state.mode = 'outcome'; render(); });
  $('budgetSelect').addEventListener('change', event => { stopPlayback(); state.budget = Number(event.target.value); renderScenarios(); updateQuery(); });
  $('policySelect').addEventListener('change', event => choosePolicy(event.target.value));
  $('playPause').addEventListener('click', () => {
    if (state.timer !== null) { stopPlayback(); return; }
    if (state.frame >= day().frames.length - 1) state.frame = 0;
    state.timer = setInterval(() => { state.frame = Math.min(day().frames.length - 1, state.frame + 1); if (state.frame >= day().frames.length - 1) stopPlayback(); render(); }, 1200);
    render();
  });
  window.addEventListener('popstate', () => { stopPlayback(); readUrlState(); render(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopPlayback(); });
  window.addEventListener('pagehide', stopPlayback);
  let resizeFrame;
  window.addEventListener('resize', () => { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(() => { if (frame()) renderTimeline(); }); });
  const navigation = document.querySelectorAll('.masthead nav a');
  const observer = new IntersectionObserver(entries => { for (const entry of entries) { if (entry.isIntersecting) navigation.forEach(anchor => anchor.classList.toggle('nav-active', anchor.hash === `#${entry.target.id}`)); } }, { rootMargin: '-10% 0px -65% 0px' });
  ['workspace', 'recovery', 'evidence'].forEach(id => observer.observe($(id)));
}
fetch('data/replay.json', { cache: 'no-cache' }).then(response => { if (!response.ok) throw new Error(`Snapshot request returned HTTP ${response.status}.`); return response.json(); }).then(initialize).catch(error => {
  stopPlayback(); $('app').hidden = true; $('loadMessage').hidden = false;
  $('loadMessage').classList.add('error'); $('loadMessage').setAttribute('role', 'alert');
  $('loadMessage').innerHTML = `<span class="tiny-label">REPLAY UNAVAILABLE</span><h2>The historical snapshot could not be loaded.</h2><p>Try again, or open the source and rebuild guide.</p><div class="load-actions"><button type="button" id="retrySnapshot">Try again</button>${externalLink(repo, 'Open the source', 'text-link')}</div><details><summary>Technical details</summary><p>${escapeHtml(error.message)}</p></details>`;
  $('retrySnapshot').addEventListener('click', () => location.reload());
});
