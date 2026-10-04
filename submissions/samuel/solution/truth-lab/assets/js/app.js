/* RavenStack Churn Truth Lab — estático, offline. Nenhum número analítico é recalculado aqui:
   todo valor vem pré-calculado de data/truth_lab_data.js (gerado por solution/build_truth_lab_data.py
   a partir dos outputs validados). No navegador há só formatação, geometria de gráficos e o
   break-even sobre o custo informado pelo usuário. Interface em português, números em pt-BR;
   os rótulos canônicos (labels globais, SOURCE/GRAIN/COVERAGE/LIMITATION) ficam em inglês. */
(function () {
  'use strict';

  const D = window.TRUTH_LAB_DATA;
  const M = D.metrics;
  const errors = [];
  window.addEventListener('error', e => errors.push(String(e.message || e)));

  // ---------------------------------------------------------------- helpers
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const group = s => s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const fmt = n => (n == null ? '—' : (n < 0 ? '-' : '') + group(String(Math.abs(Math.round(n)))));
  const fmtd = (n, d = 1) => {
    if (n == null) return '—';
    const [i, f] = Math.abs(n).toFixed(d).split('.');
    return (n < 0 ? '-' : '') + group(i) + (f ? ',' + f : '');
  };
  const pct = (x, d = 1) => (x == null ? '—' : (100 * x).toFixed(d).replace('.', ',') + '%');

  function m(id, text, cls) {
    if (!M[id]) throw new Error('Métrica desconhecida ' + id);
    return `<span class="${cls || ''}" data-m="${id}">${text != null ? text : esc(M[id].display)}<i class="mi" aria-hidden="true">i</i></span>`;
  }
  function info(id) {
    if (!M[id]) throw new Error('Métrica desconhecida ' + id);
    return `<i class="mi" data-m="${id}" tabindex="0" role="button" aria-label="SOURCE, GRAIN, COVERAGE e LIMITATION">i</i>`;
  }
  const LABEL = {
    mrr: 'MRR proxy — not consolidated revenue',
    scenario: 'Scenario — not forecast',
    priority: 'Business priority — not predicted churn risk',
    state: 'Observable contract state — commercial semantics not validated',
    observed: 'Observed — not validated as higher risk',
    usage: 'Usage coverage = 22.27% inside observed subscription lifecycle',
  };
  const label = (k, cls) => `<span class="label ${cls || ''}">${LABEL[k]}</span>`;
  const DEF_TEXT = D.usage_definition.active_account_rule_pt;
  const FORMULA = 'Uso por conta ativa = soma de usage_count no período ÷ nº de contas com ≥ 1 registro de assinatura ativo na data de fim do período';

  // ---------------------------------------------------------------- painel de metadados
  function openPanel(id) {
    const x = M[id];
    if (!x) return;
    $('#panel-eyebrow').textContent = 'Métrica · ' + id;
    $('#panel-value').textContent = x.display;
    $('#panel-source').textContent = x.source;
    $('#panel-grain').textContent = x.grain;
    $('#panel-coverage').textContent = x.coverage;
    $('#panel-limitation').textContent = x.limitation;
    $('#panel').classList.add('on'); $('#scrim').classList.add('on');
    $('#panel').setAttribute('aria-hidden', 'false');
  }
  function closePanel() {
    $('#panel').classList.remove('on'); $('#scrim').classList.remove('on');
    $('#panel').setAttribute('aria-hidden', 'true');
  }
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-m]');
    if (t && !e.target.closest('select, input, a.acct, button')) openPanel(t.getAttribute('data-m'));
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closePanel();
    if (e.key === 'Enter' && e.target.matches('.mi[data-m]')) openPanel(e.target.getAttribute('data-m'));
  });
  $('#scrim').addEventListener('click', closePanel);
  $('#panel-close').addEventListener('click', closePanel);

  // ---------------------------------------------------------------- tooltip
  const tip = $('#tooltip');
  function showTip(html, ev) {
    tip.innerHTML = html; tip.classList.add('on');
    const x = Math.min(ev.clientX + 16, window.innerWidth - 360), y = Math.max(ev.clientY - 20, 10);
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  const hideTip = () => tip.classList.remove('on');

  // ---------------------------------------------------------------- svg
  const NS = 'http://www.w3.org/2000/svg';
  function svg(w, h, cls) {
    const s = document.createElementNS(NS, 'svg');
    s.setAttribute('viewBox', `0 0 ${w} ${h}`); s.setAttribute('width', '100%');
    s.setAttribute('preserveAspectRatio', 'xMinYMin meet'); s.setAttribute('role', 'img');
    if (cls) s.setAttribute('class', cls);
    return s;
  }
  function el(name, attrs, parent, text) {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

  // ================================================================ 01 VERDADE DO CHURN
  function renderTruth() {
    $('#view-truth').innerHTML = `
      <div class="block">
        <p class="eyebrow">RavenStack · Churn Truth Lab</p>
        <h1 class="hero">A RavenStack está medindo eventos diferentes como churn.</h1>
        <p class="lede">Por isso, com os dados disponíveis, não conseguimos confirmar que o aumento dos eventos registrados representa aumento da perda real de clientes.</p>
      </div>

      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow">Verdade do churn</p><h2 class="section" id="truth-title">Três sinais de churn + uma checagem de estado observável.</h2>
          <p class="subhead">Quatro respostas diferentes.</p></div>
          <div class="labels">${label('state', 'ghost')}</div>
        </div>
        <div class="defs">
          <div class="def"><div class="num">${m('def_flag')}</div><div class="what">accounts.churn_flag = true</div><div class="grain">sinal de churn · flag de conta · 500 contas</div></div>
          <div class="def"><div class="num">${m('def_event')}</div><div class="what">contas com ≥ 1 churn event</div><div class="grain">sinal de churn · evento → conta · 600 eventos</div></div>
          <div class="def"><div class="num">${m('def_end')}</div><div class="what">contas com ≥ 1 fim de assinatura</div><div class="grain">sinal de churn · registro → conta · 486 encerrados</div></div>
          <div class="def"><div class="num zero">${m('def_zero')}</div><div class="what">contas que terminam 2024 sem nenhum registro de assinatura ativo</div><div class="grain">checagem de estado observável · 31/12/2024</div></div>
        </div>
        <div class="insights">
          <div class="insight">Essas métricas não são intercambiáveis.</div>
          <div class="insight">As 110 contas flagged ainda possuem registros de subscription ativos com MRR proxy positivo.</div>
        </div>
      </div>

      <div class="block">
        <div class="section-head">
          <div><h3>Como os três sinais de churn se sobrepõem ${info('upset')}</h3>
          <p>Cada coluna é uma combinação exata; cada conta é contada uma vez. Sobreposições inclusivas:
            flag ∩ evento = ${m('ov_fe')} · flag ∩ fim = ${m('ov_fn')} · evento ∩ fim = ${m('ov_en')} · os três = ${m('ov_all')}.</p></div>
        </div>
        <div class="card"><div id="upset" class="chart-wrap"></div></div>
      </div>

      <div class="block">
        <div class="rootcause">
          <div>
            <h3>Causa raiz de gestão</h3>
            <p class="verdict">Os dados não sustentam um target confiável de perda de cliente.</p>
            <p>Flags, eventos e fins de assinatura identificam populações diferentes.</p>
          </div>
          <div>
            <h3>Causa do cancelamento individual</h3>
            <p class="verdict">NOT IDENTIFIABLE</p>
            <p>Uso, suporte, variáveis econômicas e de segmento não separam os desfechos de forma confiável.</p>
          </div>
        </div>
      </div>

      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow muted">Qualidade de dados / alinhamento semântico</p>
          <h2 class="section">Por que uma previsão não é suportada hoje</h2>
          <p>Estas são propriedades dos registros, não causas de churn. Por isso aqui não há modelo, score nem lista de alerta.</p></div>
        </div>
        <div class="dq">
          <div class="stats c4">
            <div class="stat"><div class="v">${m('dq_usage_pre')}</div><div class="k">das linhas de uso são anteriores ao signup da conta</div><div class="s">13.198 / 25.000</div></div>
            <div class="stat"><div class="v">${m('dq_ticket_pre')}</div><div class="k">dos tickets de suporte são anteriores ao signup da conta</div><div class="s">1.077 / 2.000</div></div>
            <div class="stat"><div class="v">${m('dq_inlife')}</div><div class="k">das linhas de uso caem dentro da vida observada da assinatura</div><div class="s">5.568 / 25.000</div></div>
            <div class="stat"><div class="v">${m('dq_reason_p')}</div><div class="k">reason_code × feedback_text preenchido — nenhuma associação detectável</div><div class="s">452 eventos</div></div>
          </div>
        </div>
      </div>`;
    drawUpset($('#upset'));
  }

  function drawUpset(host) {
    const sets = [['flag', 'churn_flag', 110], ['event', '≥ 1 churn event', 352], ['end', '≥ 1 fim de assinatura', 312]];
    const combos = D.upset.slice().sort((a, b) => b.accounts - a.accounts);
    const W = 1080, left = 300, top = 210, rowH = 44, H = top + rowH * 3 + 8;
    const s = svg(W, H);
    const colW = (W - left - 20) / combos.length;
    const maxC = Math.max(...combos.map(c => c.accounts));
    const ink = css('--ink'), acc = css('--accent'), faint = css('--line-2');
    combos.forEach((c, i) => {
      const x = left + i * colW + colW / 2;
      const h = (c.accounts / maxC) * (top - 46);
      const none = !c.flag && !c.event && !c.end;
      const all3 = c.flag && c.event && c.end;
      el('rect', { x: x - 17, y: top - 18 - h, width: 34, height: h, rx: 4, fill: all3 ? acc : none ? faint : ink }, s);
      el('text', { x, y: top - 26 - h, 'text-anchor': 'middle', 'font-size': 15, 'font-weight': 700, fill: ink }, s, c.accounts);
      const ys = [];
      sets.forEach(([k], r) => {
        const y = top + r * rowH + rowH / 2;
        const on = c[k];
        if (on) ys.push(y);
        el('circle', { cx: x, cy: y, r: 8, fill: on ? (all3 ? acc : ink) : '#e7e7e2' }, s);
      });
      if (ys.length > 1) el('line', { x1: x, x2: x, y1: Math.min(...ys), y2: Math.max(...ys), stroke: all3 ? acc : ink, 'stroke-width': 3 }, s);
      const hit = el('rect', { x: x - colW / 2, y: 0, width: colW, height: H, fill: 'transparent' }, s);
      const desc = none ? 'em nenhum dos três' : 'somente ' + sets.filter(([k]) => c[k]).map(([, l]) => l).join(' + ');
      hit.addEventListener('mousemove', ev => showTip(`<b>${c.accounts} contas</b><br>${esc(desc)}`, ev));
      hit.addEventListener('mouseleave', hideTip);
    });
    const maxS = 352;
    sets.forEach(([, lab, n], r) => {
      const y = top + r * rowH + rowH / 2;
      if (r % 2 === 0) el('rect', { x: 0, y: y - rowH / 2, width: W, height: rowH, fill: '#fafaf8' }, s).parentNode.insertBefore(s.lastChild, s.firstChild);
      const bw = (n / maxS) * 120;
      el('rect', { x: 250 - bw, y: y - 9, width: bw, height: 18, rx: 3, fill: css('--neutral-bar') }, s);
      el('text', { x: 4, y: y + 5, 'font-size': 14, 'font-weight': 600, fill: ink }, s, lab);
      el('text', { x: 286, y: y + 5, 'font-size': 13, 'text-anchor': 'end', fill: css('--muted'), 'font-family': css('--mono') }, s, n);
    });
    el('text', { x: 4, y: 24, 'font-size': 12, 'font-weight': 700, fill: css('--muted'), 'letter-spacing': '.08em' }, s, 'CONTAS POR COMBINAÇÃO EXATA');
    host.appendChild(s);
  }

  // ================================================================ 02 DENOMINADOR
  const DIMS = [['ALL', 'TODAS'], ['industry', 'INDÚSTRIA'], ['country', 'PAÍS'], ['plan_tier', 'PLANO']];
  const dstate = { dim: 'ALL', level: null };
  const levelsOf = dim => Object.keys(D.usage).filter(k => k.startsWith(dim + ':')).map(k => k.split(':')[1]);
  const seriesKey = () => (dstate.dim === 'ALL' ? 'ALL' : `${dstate.dim}:${dstate.level}`);

  function renderDenominator() {
    $('#view-denominator').innerHTML = `
      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow">Denominador</p><h2 class="section">O uso é estável. A base cresceu.</h2>
          <p>Product lê o uso total. Por conta ativa e por assinatura ativa, o mesmo uso cai a cada trimestre — em todos os segmentos.</p></div>
          <div class="labels">${label('usage', 'ghost')}</div>
        </div>
        <div class="controls">
          <div class="seg-control" id="dim-control">${DIMS.map(([k, l]) => `<button data-dim="${k}" class="${k === 'ALL' ? 'on' : ''}">${l}</button>`).join('')}</div>
          <span class="footnote" style="margin:0">Conta ativa = ≥ 1 registro de assinatura ativo na data de fim do período ${info('usage_chart')}</span>
        </div>
        <div class="chips" id="level-chips"></div>
        <div class="multiples" id="multiples" style="margin-top:18px"></div>
        <p class="footnote" id="formula"><b>${FORMULA}</b> (start_date ≤ fim do período e end_date vazio ou posterior). O uso por assinatura ativa usa os registros ativos como denominador. Numerador: todas as linhas de uso datadas no período, sem filtro pela vida da assinatura.</p>
      </div>

      <div class="block">
        <div class="section-head">
          <div><h3>Uso por conta ativa, 2023H2 → 2024H2 ${info('seg_change')}</h3>
          <p>Os 15 segmentos caem. A direção se mantém; o percentual depende da regra de conta ativa acima.</p></div>
        </div>
        <div class="card"><div id="seg-change"></div></div>
      </div>

      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow">Taxas observadas por segmento</p><h2 class="section">Onde a taxa observada é maior</h2>
          <p>Alvo: accounts.churn_flag. Só segmentos com N ≥ 30 contas (regra pré-definida). Nenhuma dimensão atinge p &lt; 0,05; menor q = 0,28.</p></div>
          <div class="labels">${label('observed', 'dark')}</div>
        </div>
        <div class="card">
          <div class="controls" style="justify-content:space-between;margin-bottom:6px">
            <h3 style="margin:0">Taxa de churn_flag com IC 95% ${info('seg_forest')}</h3>
            <div class="seg-control" id="forest-toggle"><button data-f="top" class="on">TOP 5</button><button data-f="all">TODOS N ≥ 30</button></div>
          </div>
          <div id="forest"></div>
          <p class="footnote">Alemanha (DE): 8 / 25 = 32,0% — excluída pela regra pré-definida N ≥ 30.
          DevTools e canal event: <b>qualitative discovery oversample</b> (sobreamostra qualitativa) nas entrevistas de saída. É onde a taxa observada é maior, mas a diferença não é robusta o bastante para direcionar investimento de retenção.</p>
        </div>
      </div>`;
    $$('#dim-control button').forEach(b => b.addEventListener('click', () => {
      dstate.dim = b.dataset.dim; dstate.level = dstate.dim === 'ALL' ? null : levelsOf(dstate.dim)[0];
      $$('#dim-control button').forEach(x => x.classList.toggle('on', x === b));
      drawDenominator();
    }));
    $$('#forest-toggle button').forEach(b => b.addEventListener('click', () => {
      $$('#forest-toggle button').forEach(x => x.classList.toggle('on', x === b)); drawForest(b.dataset.f);
    }));
    drawDenominator(); drawSegChange(); drawForest('top');
  }

  function drawDenominator() {
    const chips = $('#level-chips');
    chips.innerHTML = dstate.dim === 'ALL' ? '<span class="count">Todas as 500 contas</span>'
      : levelsOf(dstate.dim).map(l => `<button class="chip ${l === dstate.level ? 'on' : ''}" data-l="${esc(l)}">${esc(l)}</button>`).join('');
    $$('.chip', chips).forEach(c => c.addEventListener('click', () => { dstate.level = c.dataset.l; drawDenominator(); }));
    const ser = D.usage[seriesKey()];
    const host = $('#multiples'); host.innerHTML = '';
    host.setAttribute('data-series', seriesKey());
    [['usage_total', 'Uso total', 'soma de usage_count', ''],
      ['per_active_account', 'Uso / conta ativa', 'por conta ativa no fim do trimestre', '= soma de usage_count ÷ contas com ≥ 1 registro ativo na data de fim do período'],
      ['per_active_subscription', 'Uso / assinatura ativa', 'por registro ativo no fim do trimestre', '= soma de usage_count ÷ registros de assinatura ativos na data de fim do período']].forEach(([k, t, sub, f]) => {
      const first = ser.find(r => r[k] != null), last = ser[ser.length - 1];
      const ch = first && last[k] != null ? last[k] / first[k] - 1 : null;
      const card = document.createElement('div'); card.className = 'card';
      card.innerHTML = `<div class="chart-title"><b>${t}</b><span>${sub}</span></div>
        <div><span class="big" data-k="${k}">${k === 'usage_total' ? fmt(last[k]) : fmtd(last[k])}</span>
        <span class="chg ${ch != null && ch < -0.05 ? 'down' : 'flat'}">${ch == null ? '' : (ch >= 0 ? '+' : '') + (100 * ch).toFixed(0) + '% vs ' + first.quarter}</span></div>
        ${f ? `<div class="formula" data-formula="${k}">${f}</div>` : ''}`;
      host.appendChild(card);
      lineChart(card, ser, k, t);
    });
  }

  function lineChart(host, ser, key, title) {
    const W = 360, H = 200, p = { l: 50, r: 26, t: 16, b: 28 };
    const s = svg(W, H);
    const vals = ser.map(r => r[key]).filter(x => x != null);
    const max = Math.max(...vals) * 1.08;
    const x = i => p.l + (i * (W - p.l - p.r)) / (ser.length - 1);
    const y = v => p.t + (1 - v / max) * (H - p.t - p.b);
    [0, 0.5, 1].forEach(f => {
      const v = max * f / 1.08, yy = y(v);
      el('line', { x1: p.l, x2: W - p.r, y1: yy, y2: yy, class: 'grid-line' }, s);
      el('text', { x: p.l - 6, y: yy + 4, 'text-anchor': 'end', class: 'tick' }, s, v >= 1000 ? fmtd(v / 1000, 1).replace(',0', '') + ' mil' : Math.round(v));
    });
    ser.forEach((r, i) => { if (i % 2 === 0 || i === ser.length - 1) el('text', { x: x(i), y: H - 8, 'text-anchor': 'middle', class: 'tick' }, s, r.quarter.replace('20', "'")); });
    const pts = ser.map((r, i) => (r[key] == null ? null : [x(i), y(r[key])])).filter(Boolean);
    const col = key === 'usage_total' ? css('--ink') : css('--accent');
    el('path', { d: 'M' + pts.map(q => q.join(',')).join('L'), fill: 'none', stroke: col, 'stroke-width': 2.5, 'stroke-linejoin': 'round' }, s);
    ser.forEach((r, i) => {
      if (r[key] == null) return;
      el('circle', { cx: x(i), cy: y(r[key]), r: 4.5, fill: '#fff', stroke: col, 'stroke-width': 2 }, s);
      const hit = el('circle', { cx: x(i), cy: y(r[key]), r: 14, fill: 'transparent' }, s);
      const v = key === 'usage_total' ? fmt(r[key]) : fmtd(r[key]);
      hit.addEventListener('mousemove', ev => showTip(
        `<b>${v}</b> · ${r.quarter}<br>${esc(title)}<br>uso ${fmt(r.usage_total)} · contas ativas ${r.active_accounts} · assinaturas ativas ${r.active_subscriptions}` +
        `<span class="def">DENOMINATOR DEFINITION — ${esc(DEF_TEXT)}</span>`, ev));
      hit.addEventListener('mouseleave', hideTip);
    });
    host.appendChild(s);
  }

  function drawSegChange() {
    const rows = D.segment_usage_change.slice().sort((a, b) => a.change_pct - b.change_pct);
    const W = 1080, rowH = 30, H = rows.length * rowH + 30, left = 200, mid = 560;
    const s = svg(W, H);
    const scale = v => (Math.abs(v) / 95) * (mid - left - 30);
    const dimName = { industry: 'INDÚSTRIA', country: 'PAÍS', plan_tier: 'PLANO' };
    rows.forEach((r, i) => {
      const y = 10 + i * rowH;
      el('text', { x: left - 12, y: y + 17, 'text-anchor': 'end', 'font-size': 13, fill: css('--ink-2') }, s, `${r.level}`);
      el('text', { x: 6, y: y + 17, 'font-size': 11, fill: css('--faint'), 'letter-spacing': '.06em' }, s, dimName[r.segment]);
      const w = scale(r.change_pct);
      el('rect', { x: mid - w, y: y + 6, width: w, height: 16, rx: 3, fill: css('--accent'), opacity: 0.85 }, s);
      el('text', { x: mid - w - 8, y: y + 18, 'text-anchor': 'end', 'font-size': 12.5, 'font-weight': 700, fill: css('--ink'), 'font-family': css('--mono') }, s, `${r.change_pct}%`);
      el('text', { x: mid + 16, y: y + 18, 'font-size': 12, fill: css('--muted'), 'font-family': css('--mono') }, s,
        `${fmtd(r.usage_per_active_account_2023H2)} → ${fmtd(r.usage_per_active_account_2024H2)} por conta ativa`);
    });
    el('line', { x1: mid, x2: mid, y1: 4, y2: H - 10, stroke: css('--ink'), 'stroke-width': 1.5 }, s);
    $('#seg-change').appendChild(s);
  }

  const DIM_PT = { industry: 'indústria', country: 'país', 'acquisition channel': 'canal de aquisição', plan: 'plano', trial: 'trial', seats: 'seats', 'signup cohort': 'coorte de signup' };
  function segName(r) {
    if (r.dimension === 'trial') return r.segment === 'True' ? 'Trial' : 'Não trial';
    if (r.dimension === 'acquisition channel') return 'canal ' + r.segment;
    if (r.dimension === 'seats') return r.segment.replace('-', '–') + ' seats';
    return r.segment;
  }
  function drawForest(mode) {
    const elig = D.segments.filter(r => r.eligible).sort((a, b) => b.rate - a.rate);
    const rows = mode === 'top' ? elig.slice(0, 5) : elig;
    const host = $('#forest');
    host.setAttribute('data-rows', rows.length);
    const scaleMax = 0.5, W = 300, H = 26;
    const bar = r => {
      const s = svg(W, H); s.setAttribute('style', 'display:block;width:100%;height:26px'); s.setAttribute('preserveAspectRatio', 'none');
      const x = v => 6 + (v / scaleMax) * (W - 12);
      el('line', { x1: x(0.22), x2: x(0.22), y1: 0, y2: H, stroke: css('--line-2'), 'stroke-dasharray': '3 3' }, s);
      el('line', { x1: x(r.ci_low), x2: x(r.ci_high), y1: H / 2, y2: H / 2, stroke: css('--ink'), 'stroke-width': 2 }, s);
      el('circle', { cx: x(r.rate), cy: H / 2, r: 6, fill: css('--accent') }, s);
      return s.outerHTML;
    };
    const oversample = r => (r.segment === 'DevTools' || r.segment === 'event') ? '<span class="tag">Qualitative discovery oversample</span>' : '';
    host.innerHTML = `<div class="forest-row head"><div>Segmento</div><div>Churned / total</div><div>Taxa observada · IC 95% (0–50%, tracejado = 22,0%)</div><div>Veredito</div></div>` +
      rows.map(r => `<div class="forest-row">
        <div class="seg"><b>${esc(segName(r))}</b><span>${esc(DIM_PT[r.dimension] || r.dimension)}</span>${oversample(r)}</div>
        <div class="kn">${r.churned} / ${r.total}</div>
        <div class="ci" style="display:flex;align-items:center;gap:14px"><b style="min-width:58px;font-size:17px" ${M['seg_' + r.segment] ? `data-m="seg_${esc(r.segment)}"` : ''}>${pct(r.rate)}</b><span style="flex:1;min-width:200px">${bar(r)}</span><span class="mono" style="color:var(--muted);white-space:nowrap;font-size:12px">${pct(r.ci_low)}–${pct(r.ci_high)}</span></div>
        <div class="verdict">OBSERVED — NOT VALIDATED AS HIGHER RISK</div></div>`).join('') +
      `<div class="forest-row overall"><div class="seg"><b>Geral</b><span>todas as contas</span></div><div class="kn">110 / 500</div>
        <div class="ci"><b style="font-size:17px">${m('seg_overall')}</b></div><div class="verdict">REFERÊNCIA</div></div>`;
  }

  // ================================================================ 03 FILAS DE AÇÃO
  const qstate = { filter: 'ALL', search: '', sort: 'active_mrr', dir: -1 };
  const review = {};
  const REVIEW_STATES = ['ACTIVE', 'CONTRACTION', 'CANCELLATION SCHEDULED', 'CHURNED', 'DATA ERROR', 'NEEDS REVIEW'];
  const QROWS = D.accounts.filter(a => a.queues.length);
  const FILTERS = [['ALL', 'TODAS'], ['V1', 'V1'], ['V2', 'V2'], ['V3', 'V3'], ['V3-W1', 'V3-W1'], ['WAVE 1', 'ONDA 1']];
  const COLS = [
    ['id', 'account_id', 'txt'], ['queues', 'filas', 'txt'], ['active_mrr', 'MRR proxy ativo', 'num'], ['exposed_mrr', 'MRR proxy exposto', 'num'],
    ['active_records', 'registros ativos', 'num'], ['ended_records', 'registros encerrados', 'num'], ['churn_events', 'churn events', 'num'],
    ['industry', 'indústria', 'txt'], ['country', 'país', 'txt'], ['plan', 'plano', 'txt'], ['review', 'estado de revisão V1', 'txt'],
  ];

  function renderQueues() {
    const c = D.concentration;
    const s10 = c.top10.share, s20 = c.top20.share - c.top10.share, s50 = c.top50.share - c.top20.share, rest = 1 - c.top50.share;
    $('#view-queues').innerHTML = `
      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow">Filas de ação</p><h2 class="section">Quem CS / RevOps revisa primeiro — e por quê</h2>
          <p>Três filas com regras declaradas. A prioridade vem de reconciliação de dados, valor e exposição de renovação manual — nunca de uma previsão.</p></div>
          <div class="labels">${label('priority', 'dark')}</div>
        </div>
        <div class="queues">
          <div class="queue"><div class="qid">V1</div><div class="qname">Reconciliação de status</div>
            <div class="qbig">${m('v1_accounts')}</div><div class="qunit">contas · churn_flag = true e MRR proxy ativo &gt; 0</div>
            <div class="qrow"><span>MRR proxy ativo</span><b>${m('v1_mrr')}</b></div>
            <div class="qrow"><span>Participação no MRR proxy ativo</span><b>${m('v1_share')}</b></div>
            <div class="qact">Reconciliar o status comercial em até 14 dias.</div></div>
          <div class="queue"><div class="qid">V2</div><div class="qname">Cobertura de valor</div>
            <div class="qbig">${m('v2_accounts')}</div><div class="qunit">contas · top 50 por MRR proxy ativo</div>
            <div class="qrow"><span>MRR proxy ativo</span><b>${m('v2_mrr')}</b></div>
            <div class="qrow"><span>Participação no MRR proxy ativo</span><b>${m('v2_share')}</b></div>
            <div class="qact">Dono, comprador econômico, champion, data de renovação, revisão de valor.</div></div>
          <div class="queue"><div class="qid">V3-W1</div><div class="qname">Prontidão de renovação manual</div>
            <div class="qbig">${m('w1_accounts')}</div><div class="qunit">contas · top 50 da V3 por exposição · ${m('w1_records')} registros</div>
            <div class="qrow"><span>MRR proxy exposto</span><b>${m('w1_mrr')}</b></div>
            <div class="qrow"><span>Participação na exposição V3</span><b>${m('w1_share_v3')}</b></div>
            <div class="qact">Capturar data de renovação e dono por fonte interna.</div></div>
        </div>
        <div class="wave">
          <div><div class="wlab">Onda dos primeiros 30 dias</div><div class="wbig">${m('wave1')}</div><div class="sub">contas únicas · V1 ∪ V2 ∪ V3-W1 · não 210</div></div>
          <div class="overlaps">
            <div><div class="ov">${m('wv_12')}</div><div class="ol">V1 ∩ V2</div></div>
            <div><div class="ov">${m('wv_1w')}</div><div class="ol">V1 ∩ V3-W1</div></div>
            <div><div class="ov">${m('wv_2w')}</div><div class="ol">V2 ∩ V3-W1</div></div>
            <div><div class="ov">${m('wv_all')}</div><div class="ol">as três</div></div>
          </div>
        </div>
      </div>

      <div class="block grid2">
        <div class="card">
          <h3>V1 · estados de revisão para preenchimento humano</h3>
          <div class="states">${REVIEW_STATES.map(x => `<span class="state">${x}</span>`).join('')}</div>
          <p class="note">Nada vem preenchido. Quem revisa registra o estado verificado de cada conta na tabela abaixo; ele sai junto na exportação CSV.</p>
        </div>
        <div class="card">
          <h3>V2 · concentração do MRR proxy ativo</h3>
          <div class="stack">
            <div style="width:${s10 * 100}%;background:var(--ink)"></div>
            <div style="width:${s20 * 100}%;background:#5a606c"></div>
            <div style="width:${s50 * 100}%;background:var(--accent)"></div>
            <div style="width:${rest * 100}%;background:#d9dae0;color:var(--ink-2)">Posições 51–500</div>
          </div>
          <div class="legend"><span><i style="background:var(--ink)"></i>Top 10</span><span><i style="background:#5a606c"></i>Posições 11–20</span><span><i style="background:var(--accent)"></i>Posições 21–50</span></div>
          <div class="stats c3" style="border-top:0">
            <div class="stat" style="padding-top:6px"><div class="v" style="font-size:34px">${m('conc_top10')}</div><div class="k">Top 10</div></div>
            <div class="stat" style="padding-top:6px"><div class="v" style="font-size:34px">${m('conc_top20')}</div><div class="k">Top 20</div></div>
            <div class="stat" style="padding-top:6px"><div class="v" style="font-size:34px">${m('conc_top50')}</div><div class="k">Top 50</div></div>
          </div>
          <ul class="checklist" style="margin-top:14px"><li>Dono</li><li>Comprador econômico</li><li>Champion</li><li>Data de renovação</li><li>Revisão de valor</li></ul>
        </div>
      </div>

      <div class="block">
        <div class="section-head">
          <div><h3>V3 · de qualquer registro sem auto-renew até a exposição econômica</h3>
          <p>21 contas têm só exposição de trial com MRR zero entre seus registros auto_renew=false. Essas 21 contas têm outras assinaturas pagas ativas — saem da V3 econômica, não da base de clientes.</p></div>
          <div class="labels">${label('state', 'ghost')}</div>
        </div>
        <div class="flow">
          <div class="step"><div class="fv">${m('v3_any_accounts')}</div><div class="fk">contas têm ao menos um registro ativo auto_renew=false</div><div class="fs">${m('v3_any_records')} registros · inclui trials com MRR zero</div></div>
          <div class="arrow">−</div>
          <div class="step"><div class="fv">${m('v3_zero_only')}</div><div class="fk">contas cuja exposição auto_renew=false é só de trials com MRR zero</div><div class="fs">26 registros · outras assinaturas pagas ativas</div></div>
          <div class="arrow">=</div>
          <div class="step final"><div class="fv">${m('v3_accounts')}</div><div class="fk">V3 econômica · ${m('v3_records')} registros</div><div class="fs">${m('v3_mrr')} de MRR proxy · ${m('v3_share')} do ativo</div></div>
        </div>
      </div>

      <div class="block">
        <div class="section-head">
          <div><h3>Contas das filas ${info('queue_table')}</h3><p>Busque, ordene, filtre e exporte. Clique numa conta para abrir o brief.</p></div>
        </div>
        <div class="table-wrap">
          <div class="table-tools">
            <div class="controls">
              <input class="search" id="q-search" type="search" placeholder="Buscar conta, indústria, país…" aria-label="Buscar contas">
              <div class="seg-control" id="q-filter">${FILTERS.map(([f, l]) => `<button data-f="${f}" class="${f === 'ALL' ? 'on' : ''}">${l}</button>`).join('')}</div>
            </div>
            <div class="controls"><span class="count" id="q-count"></span><button class="btn" id="q-export">Exportar CSV</button></div>
          </div>
          <div class="table-scroll"><table id="q-table"><thead><tr>${COLS.map(([k, l, t]) => `<th data-k="${k}" class="${t === 'num' ? 'num' : ''}">${l}</th>`).join('')}</tr></thead><tbody></tbody></table></div>
        </div>
        <p class="footnote">${LABEL.priority} · ${LABEL.mrr}. A tabela cobre V1 ∪ V2 ∪ V3 (${QROWS.length} contas).</p>
      </div>

      <div class="block">
        <div class="section-head"><div><p class="eyebrow">Roadmap</p><h2 class="section">30 / 60 / 90</h2></div></div>
        <div class="roadmap">
          <div><div class="rw">0–30 dias</div><div class="rt">Verdade + triagem</div><ul><li>Definição canônica de churn; churn_flag fora do board</li><li>V1 reconciliada em 14 dias</li><li>Donos para a V2</li><li>Datas de renovação da V3-W1 por fonte interna</li><li>Pesquisa de saída aberta no lugar dos reason codes</li></ul></div>
          <div><div class="rw">31–60 dias</div><div class="rt">Lifecycle + renovações</div><ul><li>contract_id, product_id, predecessor, renewal_due_date</li><li>Datas de pedido e de efetivação do cancelamento</li><li>Classificação mensal de movimentos</li><li>Rotina de renovação; entrevistas de saída</li></ul></div>
          <div><div class="rw">61–90 dias</div><div class="rt">Lançamento do experimento</div><ul><li>Piloto pré-registrado em 314 contas sem contaminação</li><li>Sorteio 157 / 157 antes de qualquer contato com o cliente</li><li>Redesenho da telemetria de adoção</li><li>KPIs de retenção v1</li></ul></div>
        </div>
      </div>`;

    $('#q-search').addEventListener('input', e => { qstate.search = e.target.value.trim().toLowerCase(); drawTable(); });
    $$('#q-filter button').forEach(b => b.addEventListener('click', () => {
      qstate.filter = b.dataset.f; $$('#q-filter button').forEach(x => x.classList.toggle('on', x === b)); drawTable();
    }));
    $$('#q-table th').forEach(th => th.addEventListener('click', () => {
      const k = th.dataset.k; if (k === 'review') return;
      qstate.dir = qstate.sort === k ? -qstate.dir : (COLS.find(c => c[0] === k)[2] === 'num' ? -1 : 1); qstate.sort = k; drawTable();
    }));
    $('#q-export').addEventListener('click', exportCsv);
    drawTable();
  }

  function filteredRows() {
    let rows = QROWS.filter(a => {
      const f = qstate.filter;
      if (f === 'WAVE 1') return a.wave1;
      if (f !== 'ALL' && !a.queues.includes(f)) return false;
      return true;
    });
    if (qstate.search) rows = rows.filter(a => [a.id, a.name, a.industry, a.country, a.plan].join(' ').toLowerCase().includes(qstate.search));
    const k = qstate.sort, d = qstate.dir;
    rows.sort((a, b) => {
      const x = k === 'queues' ? a.queues.join() : a[k], y = k === 'queues' ? b.queues.join() : b[k];
      return (x > y ? 1 : x < y ? -1 : 0) * d || (a.id > b.id ? 1 : -1);
    });
    return rows;
  }
  function drawTable() {
    const rows = filteredRows();
    $('#q-count').textContent = `${rows.length} contas`;
    $('#q-table').setAttribute('data-rows', rows.length);
    $$('#q-table th').forEach(th => th.classList.toggle('sorted', th.dataset.k === qstate.sort));
    $('#q-table tbody').innerHTML = rows.map(a => `<tr>
      <td class="mono"><a class="acct" data-acct="${a.id}">${a.id}</a></td>
      <td>${a.queues.map(q => `<span class="qpill ${q.replace('-', '')}">${q}</span>`).join('')}</td>
      <td class="num mono">${fmt(a.active_mrr)}</td><td class="num mono">${a.exposed_mrr ? fmt(a.exposed_mrr) : '—'}</td>
      <td class="num mono">${a.active_records}</td><td class="num mono">${a.ended_records}</td><td class="num mono">${a.churn_events}</td>
      <td>${esc(a.industry)}</td><td>${esc(a.country)}</td><td>${esc(a.plan)}</td>
      <td>${a.queues.includes('V1') ? `<select data-review="${a.id}" aria-label="Estado de revisão V1 de ${a.id}"><option value="">—</option>${REVIEW_STATES.map(s => `<option ${review[a.id] === s ? 'selected' : ''}>${s}</option>`).join('')}</select>` : ''}</td></tr>`).join('');
    $$('#q-table select[data-review]').forEach(s => s.addEventListener('change', () => { review[s.dataset.review] = s.value; }));
    $$('#q-table a.acct').forEach(x => x.addEventListener('click', () => { location.hash = 'brief/' + x.dataset.acct; }));
  }
  function buildCsv(rows) {
    const head = ['account_id', 'queues', 'first_wave', 'active_mrr_proxy', 'exposed_mrr_proxy', 'active_records', 'ended_records', 'churn_events', 'industry', 'country', 'plan', 'v1_review_state', 'label'];
    const q = v => `"${String(v).replace(/"/g, '""')}"`;
    const lines = [head.join(',')].concat(rows.map(a => [a.id, a.queues.join(' '), a.wave1 ? 'yes' : '', a.active_mrr, a.exposed_mrr, a.active_records, a.ended_records,
      a.churn_events, a.industry, a.country, a.plan, review[a.id] || '', LABEL.priority].map(q).join(',')));
    return lines.join('\r\n');
  }
  function exportCsv() {
    const csv = buildCsv(filteredRows());
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `ravenstack_action_queues_${qstate.filter.replace(/\s/g, '').toLowerCase()}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    return csv;
  }

  // ================================================================ 04 BRIEF DA CONTA
  const BY_ID = Object.fromEntries(D.accounts.map(a => [a.id, a]));
  const DEFAULT_ACCOUNT = D.accounts.filter(a => a.queues.includes('V1')).sort((a, b) => b.active_mrr - a.active_mrr)[0].id;
  let currentAccount = DEFAULT_ACCOUNT;

  function renderBriefShell() {
    $('#view-brief').innerHTML = `
      <div class="section-head" style="margin-bottom:22px">
        <div><p class="eyebrow">Brief da conta</p><h2 class="section">Uma conta, cinco tabelas, uma visão</h2>
        <p>Só fatos: valor, lifecycle, produto, suporte e flags de qualidade de dados, mais perguntas fixas para o CSM.</p></div>
        <div class="controls"><input class="search" id="b-search" list="b-list" placeholder="Account ID, ex.: A-5a215a" aria-label="Encontrar conta">
        <datalist id="b-list">${D.accounts.map(a => `<option value="${a.id}">${esc(a.name)} · ${esc(a.industry)}</option>`).join('')}</datalist>
        <button class="btn ghost" id="b-go">Abrir</button></div>
      </div>
      <div id="brief-body"></div>`;
    const go = () => { const v = $('#b-search').value.trim(); if (BY_ID[v]) location.hash = 'brief/' + v; else $('#b-search').style.borderColor = 'var(--red)'; };
    $('#b-go').addEventListener('click', go);
    $('#b-search').addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
    $('#b-search').addEventListener('change', go);
  }

  function renderBrief(id) {
    const a = BY_ID[id]; if (!a) return;
    currentAccount = id;
    const yn = b => `<span class="yn ${b ? 'yes' : ''}">${b ? 'SIM' : 'NÃO'}</span>`;
    const subs = a.subscriptions;
    const activeSubs = subs.filter(s => !s.end);
    const state = a.active_records > 0 ? `≥ 1 registro ativo (${a.active_records}) em 31/12/2024` : 'nenhum registro ativo em 31/12/2024';
    const qs = [
      'Confirmar o status comercial atual.', 'Confirmar a data de renovação.', 'Quem é o comprador econômico?', 'Quem é o champion interno?',
      'Que resultado a conta está tentando alcançar?',
      a.auto_renew_active.off > 0 ? `O não auto-renew é intencional? (${a.auto_renew_active.off} registros ativos auto_renew=false)` : 'O não auto-renew é intencional? (n/a — nenhum registro ativo auto_renew=false)',
    ];
    $('#brief-body').innerHTML = `
      <div class="brief-head" data-account="${a.id}">
        <div><div class="bid">${a.id}</div><div class="bname">${esc(a.name)}</div>
          <div class="brief-meta">
            <div><span>País</span><b>${esc(a.country)}</b></div><div><span>Indústria</span><b>${esc(a.industry)}</b></div>
            <div><span>Signup</span><b>${a.signup}</b></div><div><span>Faixa de valor</span><b>${a.value_band}</b></div>
            <div><span>Canal</span><b>${esc(a.channel)}</b></div><div><span>Filas</span><b style="white-space:nowrap">${a.queues.length ? a.queues.map(q => `<span class="qpill ${q.replace('-', '')}">${q}</span>`).join('') : '—'}</b></div>
          </div></div>
        <div class="labels">${a.queues.length ? label('priority', 'dark') : ''}</div>
      </div>
      <div class="brief-grid">
        <div class="card"><h3>Valor ${info('brief_value')}</h3><div class="kv">
          <div>MRR proxy ativo</div><div>${fmt(a.active_mrr)}</div><div>Posição de valor (de 500)</div><div>${a.value_rank}</div>
          <div>Registros ativos</div><div>${a.active_records}</div><div>Registros encerrados</div><div>${a.ended_records}</div>
          <div>Exposição de renovação manual (MRR proxy)</div><div>${a.exposed_mrr ? fmt(a.exposed_mrr) : '0'}</div>
          <div>Registros expostos (MRR proxy &gt; 0)</div><div>${a.exposed_records}</div></div>
          <p class="footnote">${LABEL.mrr}</p></div>
        <div class="card"><h3>Lifecycle ${info('brief_lifecycle')}</h3><div class="kv">
          <div>Estado observável</div><div>${state}</div>
          <div>Mix de auto-renew (ativos)</div><div>${a.auto_renew_active.on} on · ${a.auto_renew_active.off} off</div>
          <div>Planos ativos ao mesmo tempo</div><div>${a.plans_active.join(' · ') || '—'}</div>
          <div>Primeiro início · último início</div><div>${subs.length ? subs[0].start + ' · ' + subs[subs.length - 1].start : '—'}</div>
          <div>Churn events</div><div>${a.churn_events}</div><div>accounts.churn_flag</div><div>${a.churn_flag ? 'true' : 'false'}</div></div>
          <p class="footnote">${LABEL.state}</p></div>
        <div class="card"><h3>Produto ${info('brief_product')}</h3><div class="kv">
          <div>Eventos de uso (soma)</div><div>${fmt(a.usage.usage_count)}</div><div>Linhas de uso</div><div>${fmt(a.usage.usage_rows)}</div>
          <div>Features distintas</div><div>${a.usage.features ?? '—'}</div><div>Erros</div><div>${fmt(a.usage.errors)}</div>
          <div>Linhas dentro do lifecycle da assinatura</div><div>${a.usage.in_life_share == null ? '—' : pct(a.usage.in_life_share)}</div></div>
          <p class="footnote">${LABEL.usage}</p></div>
        <div class="card"><h3>Suporte ${info('brief_support')}</h3><div class="kv">
          <div>Tickets</div><div>${a.support.tickets}</div><div>Escalações</div><div>${a.support.escalations}</div>
          <div>First response (média, min)</div><div>${a.support.frt == null ? '—' : fmtd(a.support.frt)}</div>
          <div>Resolução (média, h)</div><div>${a.support.resolution == null ? '—' : fmtd(a.support.resolution)}</div>
          <div>CSAT (média, observado 3–5)</div><div>${a.support.csat == null ? '—' : fmtd(a.support.csat, 2)}</div>
          <div>Tickets sem CSAT</div><div>${a.support.csat_missing}</div></div></div>
        <div class="card"><h3>Qualidade de dados ${info('brief_dq')}</h3><div class="kv" id="b-flags">
          <div>Uso antes do signup</div><div>${yn(a.flags.usage_before_signup)}</div>
          <div>Ticket antes do signup</div><div>${yn(a.flags.ticket_before_signup)}</div>
          <div>Sobreposição de planos</div><div>${yn(a.flags.multiple_plan_overlap)}</div>
          <div>Divergência flag / evento / fim</div><div>${yn(a.flags.churn_flag_event_end_mismatch)}</div>
          <div>Só exposição sem auto-renew de valor zero</div><div>${yn(a.flags.non_auto_renew_zero_mrr_only)}</div></div>
          <p class="footnote">Flags descritivas. Nunca somadas nem ordenadas.</p></div>
        <div class="card"><h3>Preparação do CSM</h3><ol class="qs">${qs.map(q => `<li>${esc(q)}</li>`).join('')}</ol></div>
        <div class="card wide"><h3>Registros de assinatura (${subs.length}; ${activeSubs.length} ativos) ${info('brief_lifecycle')}</h3>
          <div class="table-scroll" style="max-height:300px"><table class="mini"><thead><tr><th>registro</th><th>plano</th><th>início</th><th>fim</th><th class="num">MRR proxy</th><th>trial</th><th>auto-renew</th><th>cobrança</th></tr></thead>
          <tbody>${subs.map(s => `<tr><td class="mono">${s.id}</td><td>${s.plan}</td><td class="mono">${s.start}</td><td class="mono">${s.end || '—'}</td><td class="num mono">${fmt(s.mrr)}</td><td>${s.trial ? 'sim' : ''}</td><td>${s.auto_renew ? 'on' : 'off'}</td><td>${s.billing}</td></tr>`).join('')}</tbody></table></div>
          ${a.events.length ? `<div class="sep"></div><h3>Churn events (${a.events.length})</h3><table class="mini"><thead><tr><th>data</th><th>reason_code</th><th>feedback_text</th><th>reativação</th></tr></thead><tbody>${a.events.map(e => `<tr><td class="mono">${e.date}</td><td>${esc(e.reason)}</td><td>${e.feedback ? esc(e.feedback) : '—'}</td><td>${e.reactivation ? 'sim' : ''}</td></tr>`).join('')}</tbody></table>
          <p class="footnote">reason_code não tem associação detectável com feedback_text nos 452 eventos preenchidos (p = 0,955).</p>` : ''}
        </div>
      </div>`;
    $('#b-search').value = a.id; $('#b-search').style.borderColor = '';
  }

  // ================================================================ 05 LABORATÓRIO DE IMPACTO
  function renderImpact() {
    const ex = [5, 10, 15].map(p => D.impact[p]);
    $('#view-impact').innerHTML = `
      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow">Laboratório de impacto</p><h2 class="section">O que a exposição de renovação manual pode representar</h2>
          <p>Base: exposição de renovação manual da V3, ${m('impact_base')} de MRR proxy. O controle responde “se uma intervenção preservasse, no fim, X% dela, que valor estaria associado?” — não afirma que alguma intervenção vá preservar.</p></div>
        </div>
        <div class="disclaimer" id="disclaimer"><span>SCENARIO — NOT FORECAST</span><span>NO PROBABILITY</span><span>NO CAUSAL ESTIMATE</span></div>
        <div class="impact" style="margin-top:20px">
          <div class="card">
            <h3>Percentual da exposição V3 preservado ${info('impact_slider')}</h3>
            <div class="slider-val"><span id="s-pct">10</span>%</div>
            <input type="range" min="0" max="20" step="1" value="10" id="s-range" aria-label="Percentual da exposição V3 preservado">
            <div class="ticks">${Array.from({ length: 21 }, (_, i) => (i % 5 === 0 ? `<span class="${[5, 10, 15].includes(i) ? 'mark' : ''}">${i}%</span>` : '')).filter(Boolean).join('')}</div>
            <div class="outs">
              <div><div class="v" id="s-month"></div><div class="k">MRR proxy condicional por mês</div></div>
              <div><div class="v" id="s-year"></div><div class="k">Proxy anualizado (× 12)</div></div>
            </div>
            <table class="examples mini"><thead><tr><th>Exemplo validado</th><th class="num">MRR proxy / mês</th><th class="num">Anualizado</th></tr></thead>
              <tbody>${ex.map(r => `<tr><td class="mono">${r.pct}%</td><td class="num mono">${fmt(r.monthly)}</td><td class="num mono">${fmt(r.annualized)}</td></tr>`).join('')}</tbody></table>
            <p class="footnote">${LABEL.scenario}. ${LABEL.mrr}.</p>
          </div>
          <div class="card">
            <h3>Break-even ${info('break_even')}</h3>
            <span class="label warn">Custo hipotético informado pelo usuário</span>
            <p class="note">Custo mensal do programa (em unidades de MRR proxy). Não vem preenchido.</p>
            <input class="cost-input" id="be-cost" inputmode="decimal" placeholder="ex.: 50000" aria-label="Custo mensal do programa">
            <div class="outs" style="grid-template-columns:1fr"><div><div class="v" id="be-out">—</div><div class="k">Parcela da exposição V3 que precisaria ser preservada para cobrir o custo<br><span class="mono">custo_do_programa ÷ 2.023.778</span></div></div></div>
          </div>
        </div>
      </div>

      <div class="block">
        <div class="levels">
          <div class="card level"><div class="ln">NÍVEL 1 · FATO</div><div class="lt">${m('v3_mrr')} de MRR proxy</div><p class="note">em exposição de renovação manual (388 contas, 764 registros).</p></div>
          <div class="card level"><div class="ln">NÍVEL 2 · CENÁRIO CONDICIONAL</div><div class="lt">5% · 10% · 15%</div><p class="note">101.189 · 202.378 · 303.567 de MRR proxy por mês, se preservados. Scenario — not forecast.</p></div>
          <div class="card level"><div class="ln">NÍVEL 3 · EFEITO REAL</div><div class="lt">Só o piloto mede</div><p class="note">Randomizado, pré-registrado, lido no vencimento contratual.</p></div>
        </div>
      </div>

      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow">Cartão do experimento</p><h2 class="section">Piloto de renovação futuro</h2></div>
          <div class="labels"><span class="label warn">Premissas hipotéticas de taxa base</span></div>
        </div>
        <div class="grid2">
          <div class="card">
            <div class="stats c3" style="border-top:0">
              <div class="stat" style="padding-top:0"><div class="v">${m('pilot_pop')}</div><div class="k">contas · V3 − V2 − V3-W1</div></div>
              <div class="stat" style="padding-top:0"><div class="v">${m('pilot_arm')}</div><div class="k">tratamento / controle</div></div>
              <div class="stat" style="padding-top:0"><div class="v">90 d</div><div class="k">só a janela de lançamento</div></div>
            </div>
            <div class="sep"></div>
            <div class="kv">
              <div>Estratificação</div><div>tercil de exposição · cobrança · pertencer à V1</div>
              <div>Resultado principal</div><div>renovação no vencimento contratual</div>
              <div>Secundário</div><div>MRR proxy retido · contraction</div>
              <div>Data de renovação</div><div>fonte interna, nos dois braços, antes do tratamento</div>
              <div>Análise</div><div>intention-to-treat</div>
            </div>
          </div>
          <div class="card">
            <h3>Efeito mínimo detectável · ~80% de poder · bicaudal, alfa 0,05</h3>
            <div class="kv">
              <div>Não renovação de base de 10% (premissa)</div><div>${m('mde_0.1')}</div>
              <div>Não renovação de base de 15% (premissa)</div><div>${m('mde_0.15')}</div>
              <div>Não renovação de base de 20% (premissa)</div><div>${m('mde_0.2')}</div>
            </div>
            <p class="note">A taxa base é uma premissa, não um dado observado. O piloto não terá resultado em 90 dias: é lido quando um número pré-registrado de contratos tiver vencido.</p>
          </div>
        </div>
      </div>`;
    const range = $('#s-range');
    const upd = () => {
      const r = D.impact[+range.value];
      $('#s-pct').textContent = r.pct; $('#s-month').textContent = fmt(r.monthly); $('#s-year').textContent = fmt(r.annualized);
    };
    range.addEventListener('input', upd); upd();
    $('#be-cost').addEventListener('input', e => {
      const c = parseFloat(e.target.value.replace(/\./g, '').replace(',', '.').replace(/[^0-9.]/g, ''));
      $('#be-out').textContent = isFinite(c) && c > 0 ? (100 * c / M.impact_base.value).toFixed(2).replace('.', ',') + '%' : '—';
    });
  }

  // ================================================================ 06 CONFIANÇA DOS DADOS
  function renderConfidence() {
    const hs = M.health.value;
    $('#view-confidence').innerHTML = `
      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow">Confiança dos dados</p><h2 class="section">O que os dados conseguem e não conseguem sustentar</h2>
          <p>Status por dimensão. RED significa que o campo ou o significado não existe nos registros; não é julgamento sobre nenhum cliente.</p></div>
        </div>
        <div class="matrix">${D.confidence.map(c => `<div class="tile ${c.status}" ${c.metric ? `data-m="${c.metric}"` : ''}>
          <div class="td">${esc(c.dimension)}</div><div class="tdet">${esc(c.detail)}</div><div class="ts">${c.status}${c.metric ? '<i class="mi" aria-hidden="true">i</i>' : ''}</div></div>`).join('')}</div>
      </div>

      <div class="block card">
        <div class="readiness">
          <div><h3>Prontidão para health score ${info('health')}</h3>
            <div class="rnums"><div><div class="rv" style="color:var(--green)">${hs.green}</div><div class="rk">GREEN</div></div>
            <div><div class="rv" style="color:var(--muted)">${hs.partial}</div><div class="rk">PARTIAL</div></div>
            <div><div class="rv" style="color:var(--red)">${hs.red}</div><div class="rk">RED</div></div></div>
            <p class="note">${hs.green} GREEN · ${hs.partial} PARTIAL · ${hs.red} RED. Não construir health score agora.</p></div>
          <div class="items">${D.health_items.map(i => `<div><span>${esc(i.item)}</span><b class="${i.status}">${i.status}</b></div>`).join('')}</div>
        </div>
      </div>

      <div class="block">
        <div class="section-head">
          <div><p class="eyebrow">Semântica das assinaturas</p><h2 class="section">Um registro de assinatura não é um contrato validado</h2>
          <p>The schema does not establish that each subscription record maps one-to-one to a commercial contract.</p></div>
        </div>
        <div class="grid2">
          <div class="card">
            <div class="eqrow"><div><div class="eq">${m('sub_flag')}</div><div class="k">assinaturas com churn_flag = true</div></div><div class="eqsign">=</div><div><div class="eq">${m('sub_end')}</div><div class="k">assinaturas com end_date</div></div></div>
            <p class="note" style="margin-top:16px">Exatamente os mesmos 486 registros. Nenhum registro com churn_flag = false tem end_date. O churn_flag da assinatura não representa um novo target independente.</p>
          </div>
          <div class="card">
            <div class="stats c3" style="border-top:0; grid-template-columns:1fr 1fr">
              <div class="stat" style="padding-top:0"><div class="v">~${m('sub_per_acc')}</div><div class="k">registros de assinatura ativos por conta no fim da observação</div></div>
              <div class="stat" style="padding-top:0"><div class="v">${m('sub_all3')}</div><div class="k">contas com registros Basic, Pro e Enterprise ativos ao mesmo tempo</div></div>
            </div>
          </div>
        </div>
      </div>`;
  }

  // ================================================================ roteador
  const VIEWS = ['truth', 'denominator', 'queues', 'brief', 'impact', 'confidence'];
  function route() {
    const h = (location.hash || '#truth').slice(1);
    const [view, arg] = h.split('/');
    const name = VIEWS.includes(view) ? view : 'truth';
    VIEWS.forEach(v => $('#view-' + v).classList.toggle('active', v === name));
    $$('#nav a').forEach(a => a.classList.toggle('active', a.dataset.view === name));
    if (name === 'brief') renderBrief(arg && BY_ID[arg] ? arg : currentAccount);
    closePanel(); hideTip();
    window.scrollTo(0, 0);
  }

  renderTruth(); renderDenominator(); renderQueues(); renderBriefShell(); renderBrief(DEFAULT_ACCOUNT); renderImpact(); renderConfidence();
  window.addEventListener('hashchange', route);
  route();
  const metaParam = (location.search.match(/[?&]meta=([^&]+)/) || [])[1];
  if (metaParam) openPanel(decodeURIComponent(metaParam));   // ex.: index.html?meta=v3_mrr#queues

  // ================================================================ autoteste (index.html?selftest=1)
  const FORBIDDEN = ['high churn risk', 'predicted churn risk', 'predicted risk', 'churn probability', 'likelihood to churn', 'likely to churn',
    'revenue at risk', 'expected loss', 'expected savings', 'still paying', 'real churn = 0', 'zero customers churned', 'risk score',
    'continuam pagando', 'continua pagando', 'probabilidade de churn', 'receita em risco', 'alto risco', 'risco previsto', 'perda esperada', 'economia esperada',
    'four definitions', 'quatro definições', 'unsafe', 'at stake', 'receita'];
  const ALLOWED = ['business priority — not predicted churn risk'];
  function forbiddenHits(text) {
    let t = text.toLowerCase();
    ALLOWED.forEach(a => { t = t.split(a).join(' '); });
    const hits = FORBIDDEN.filter(f => t.includes(f));
    if (t.replace(/not consolidated revenue/g, '').includes('revenue')) hits.push('revenue');
    if (/(r\$|us\$|\bbrl\b|\busd\b|\$\s?\d)/i.test(text)) hits.push('currency symbol');
    return hits;
  }
  window.__truthLab = { buildCsv, filteredRows, forbiddenHits, errors };

  if (/selftest=1/.test(location.search)) {
    document.body.classList.add('selftest');
    const R = [];
    const ok = (name, cond, detail) => R.push({ name, pass: !!cond, detail: detail == null ? '' : String(detail) });
    const consoleErrors = [];
    const ce = console.error; console.error = (...a) => { consoleErrors.push(a.join(' ')); ce.apply(console, a); };
    try {
      VIEWS.forEach(v => { location.hash = v; route(); ok(`view ${v} renders`, $('#view-' + v).classList.contains('active') && $('#view-' + v).textContent.length > 200, $('#view-' + v).textContent.length); });
      ok('headline', $('#view-truth h1').textContent === 'A RavenStack está medindo eventos diferentes como churn.');
      ok('signals + observable-state title', $('#truth-title').textContent === 'Três sinais de churn + uma checagem de estado observável.' && $('#view-truth .subhead').textContent === 'Quatro respostas diferentes.');
      ok('root cause kept as two levels', $('#view-truth').textContent.includes('Os dados não sustentam um target confiável de perda de cliente.') && $('#view-truth').textContent.includes('NOT IDENTIFIABLE'));
      ok('"não é suportada" wording', $('#view-truth').textContent.includes('Por que uma previsão não é suportada hoje'));
      ok('impact title wording', $('#view-impact h2').textContent === 'O que a exposição de renovação manual pode representar');
      ok('outcome card wording', $('#view-confidence').textContent.includes('110 / 352 / 312 = três populações de churn conflitantes. 0 = checagem do estado observável no fim.'));
      ok('F-22 formula next to the metric', /contas com ≥ 1 registro ativo na data de fim do período/.test($('[data-formula="per_active_account"]').textContent) && $('#formula').textContent.includes('Uso por conta ativa = soma de usage_count'));
      const ids = [...new Set($$('[data-m]').map(e => e.getAttribute('data-m')))];
      const incomplete = ids.filter(i => !M[i] || !['source', 'grain', 'coverage', 'limitation'].every(k => M[i][k] && String(M[i][k]).length > 2));
      ok('metadata: every data-m has SOURCE/GRAIN/COVERAGE/LIMITATION', ids.length > 40 && incomplete.length === 0, `${ids.length} ids; incomplete: ${incomplete.join(',')}`);
      openPanel('v3_mrr');
      ok('metadata panel opens with all four fields', $('#panel').classList.contains('on') && $('#panel-source').textContent && $('#panel-limitation').textContent.includes('MRR proxy'), $('#panel-value').textContent);
      closePanel();
      const all = VIEWS.map(v => $('#view-' + v).textContent).join(' ');
      ['110', '352', '312', '75', '72', '227', '50', '2.073.153', '2.781.650', '2.023.778', '873.996', '20,4%', '27,4%', '19,9%', '43,2%', '176', '409', '899', '388', '764', '21',
        '314', '157 / 157', '52,8%', '53,9%', '22,27%', 'p = 0,955', '486', '418 / 500', '8,4%', '14,3%', '35 / 113', '29 / 96', '29 / 109', '25 / 97', '33 / 134', '110 / 500',
        '31,0%', '30,2%', '26,6%', '25,8%', '24,6%', '22,0%', '8 / 25', '101.189', '202.378', '303.567', '1.214.267', '2.428.534', '3.642.800', '~7,4 pp', '~9,4 pp', '~11,0 pp']
        .forEach(n => ok(`number on screen: ${n}`, all.includes(n)));
      location.hash = 'denominator'; route();
      const before = $('#multiples').getAttribute('data-series');
      $('#dim-control button[data-dim="industry"]').click();
      $$('#level-chips .chip').find(c => c.dataset.l === 'DevTools').click();
      ok('denominator filter switches series', before === 'ALL' && $('#multiples').getAttribute('data-series') === 'industry:DevTools', $('#multiples').getAttribute('data-series'));
      const tt = $$('#multiples circle').length;
      ok('usage charts draw 3 × 8 points', tt >= 48, tt);
      $('#forest-toggle button[data-f="all"]').click();
      ok('segment toggle shows all N≥30', +$('#forest').getAttribute('data-rows') > 5, $('#forest').getAttribute('data-rows'));
      ok('Germany excluded from ranking', !$('#forest').textContent.includes('8 / 25') && $('#view-denominator').textContent.includes('8 / 25'));
      ok('segment verdict label present', $('#forest').textContent.includes('OBSERVED — NOT VALIDATED AS HIGHER RISK'));
      location.hash = 'queues'; route();
      const cnt = f => { $(`#q-filter button[data-f="${f}"]`).click(); return +$('#q-table').getAttribute('data-rows'); };
      ok('filter V1 = 110', cnt('V1') === 110); ok('filter V2 = 50', cnt('V2') === 50); ok('filter V3 = 388', cnt('V3') === 388);
      ok('filter V3-W1 = 50', cnt('V3-W1') === 50); ok('filter WAVE 1 = 176', cnt('WAVE 1') === 176);
      cnt('ALL');
      $('#q-search').value = 'devtools'; $('#q-search').dispatchEvent(new Event('input'));
      const dv = +$('#q-table').getAttribute('data-rows');
      ok('search filters rows', dv > 0 && dv < QROWS.length && filteredRows().every(a => a.industry === 'DevTools'), dv);
      $('#q-search').value = ''; $('#q-search').dispatchEvent(new Event('input'));
      qstate.sort = 'active_mrr'; qstate.dir = -1; drawTable();
      ok('sort by active MRR proxy desc', filteredRows()[0].value_rank === 1, filteredRows()[0].id);
      $('#q-table th[data-k="id"]').click();
      ok('header click sorts by account_id', filteredRows()[0].id < filteredRows()[1].id);
      cnt('V1');
      const csv = buildCsv(filteredRows());
      ok('CSV export: header + 110 rows', csv.split('\r\n').length === 111 && csv.startsWith('account_id,'), csv.split('\r\n').length);
      ok('V1 review state not pre-filled', $$('#q-table select[data-review]').every(s => s.value === ''));
      ok('priority label on queues page', $('#view-queues').textContent.includes('Business priority — not predicted churn risk'));
      location.hash = 'brief/A-5a215a'; route();
      ok('account brief opens by id', $('.brief-head').getAttribute('data-account') === 'A-5a215a');
      ok('brief shows 5 data-quality flags', $$('#b-flags .yn').length === 5);
      ok('brief CSM prep has 6 questions', $$('.qs li').length === 6);
      $('#b-search').value = 'A-2e4581'; $('#b-go').click(); route();
      ok('brief search opens another account', $('.brief-head').getAttribute('data-account') === 'A-2e4581');
      location.hash = 'impact'; route();
      const sim = p => { $('#s-range').value = p; $('#s-range').dispatchEvent(new Event('input')); return [$('#s-month').textContent, $('#s-year').textContent]; };
      ok('simulator 5%', sim(5).join('|') === '101.189|1.214.267', sim(5)); ok('simulator 10%', sim(10).join('|') === '202.378|2.428.534', sim(10));
      ok('simulator 15%', sim(15).join('|') === '303.567|3.642.800', sim(15)); ok('simulator 0%', sim(0)[0] === '0');
      ok('break-even empty by default', $('#be-cost').value === '' && $('#be-out').textContent === '—');
      $('#be-cost').value = '50000'; $('#be-cost').dispatchEvent(new Event('input'));
      ok('break-even 50.000 → 2,47%', $('#be-out').textContent === '2,47%', $('#be-out').textContent);
      ok('permanent scenario disclaimer', /SCENARIO — NOT FORECAST/.test($('#disclaimer').textContent) && /NO PROBABILITY/.test($('#disclaimer').textContent) && /NO CAUSAL ESTIMATE/.test($('#disclaimer').textContent));
      location.hash = 'confidence'; route();
      ok('confidence matrix has 10 tiles', $$('.tile').length === 10);
      ok('health readiness 0/2/8', $('#view-confidence').textContent.includes('0 GREEN · 2 PARTIAL · 8 RED'));
      const text = VIEWS.map(v => $('#view-' + v).innerText || $('#view-' + v).textContent).join('\n') + $('.rail').textContent;
      const hits = forbiddenHits(text);
      ok('forbidden-phrase scan of rendered UI', hits.length === 0, hits.join(','));
      const res = performance.getEntriesByType('resource').map(r => r.name);
      const ext = res.filter(u => !u.startsWith('file:'));
      ok('no external requests', ext.length === 0, `${res.length} resources; external: ${ext.join(' ')}`);
    } catch (e) { ok('self-test crashed', false, e && e.stack); }
    ok('no window errors', errors.length === 0, errors.join(' | '));
    ok('no console errors', consoleErrors.length === 0, consoleErrors.join(' | '));
    location.hash = 'truth'; route();
    const failed = R.filter(r => !r.pass);
    const out = $('#selftest-results');
    out.setAttribute('data-status', failed.length ? 'FAIL' : 'PASS');
    out.textContent = `SELFTEST ${failed.length ? 'FAIL' : 'PASS'} ${R.length - failed.length}/${R.length}\n` + R.map(r => `${r.pass ? 'PASS' : 'FAIL'} | ${r.name}${r.detail ? ' | ' + r.detail : ''}`).join('\n');
  }
})();
