/* Recycle Condo prototype.
   Staff (A screens) log waste for a room; residents (B screens) earn points and redeem them.
   All data lives in this browser (localStorage). Prices, points rate and reward costs are placeholders. */
(() => {
  'use strict';

  /* ---------- config & data ---------- */
  const KEY = 'recycle-condo-v2';
  const CO2_PER_KG = 1.5; // placeholder estimate, kg CO2 saved per kg recycled
  const MAX_KG = 200;

  const TYPES = [
    { id: 'aluminum', en: 'Aluminum can', th: 'กระป๋องอลูมิเนียม', price: 38 },
    { id: 'water', en: 'Water bottle', th: 'ขวดน้ำ', price: 5 },
    { id: 'glass', en: 'Glass bottle', th: 'ขวดแก้ว', price: 1 },
    { id: 'books', en: 'Notebooks, books', th: 'สมุด หนังสือ', price: 1.7 },
    { id: 'steel', en: 'Steel can', th: 'กระป๋องเหล็ก', price: 2.9 },
    { id: 'pump', en: 'Pump or opaque bottle', th: 'ขวดปั๊ม / ขวดขุ่น', price: 6.8 },
    { id: 'news', en: 'Newspaper, printed paper', th: 'กระดาษหนังสือพิมพ์', price: 2.8 },
    { id: 'box', en: 'Cardboard box', th: 'ลังกระดาษ / กล่องพัสดุ', price: 2.8 },
  ];
  const ROOMS = ['A101', 'A102', 'A103', 'A104', 'A105', 'A201', 'A202', 'A203', 'A204', 'A205', 'B101', 'B102', 'B103', 'B201', 'B202', 'B203'];
  const typeOf = (id) => TYPES.find((t) => t.id === id);

  const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const DAY = 86400000;

  function seed() {
    const now = Date.now();
    const mk = (room, typeId, kg, daysAgo, price, rate = 1) => ({
      id: uid(), ts: now - daysAgo * DAY, room, typeId, kg, price, points: Math.round(kg * price * rate),
    });
    return {
      prices: Object.fromEntries(TYPES.map((t) => [t.id, t.price])),
      rate: 1, // points per baht, placeholder until the reward rate is decided
      rewards: [
        { id: 'v5', kind: 'vending', name: '฿5 off at the vending machine', cost: 50 },
        { id: 'v10', kind: 'vending', name: '฿10 off at the vending machine', cost: 100 },
        { id: 'keychain', kind: 'merch', name: 'Keychain', cost: 150 },
        { id: 'figure', kind: 'merch', name: 'Recycle mascot figure', cost: 400 },
      ],
      entries: [
        mk('A101', 'water', 3.2, 6, 5),
        mk('A101', 'box', 4.5, 3, 2.8),
        mk('A101', 'aluminum', 1.4, 1, 38),
        mk('A102', 'glass', 6, 2, 1),
      ],
      redemptions: [],
    };
  }

  /* ---------- storage ---------- */
  let memory = null;
  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* storage blocked or corrupt */ }
    return memory || seed();
  }
  function save() {
    memory = db;
    try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) { /* keep in memory only */ }
  }
  let db = load();
  save();

  let session = null; // per tab, so one browser can hold a staff tab and a resident tab
  try { session = JSON.parse(sessionStorage.getItem('rc-session')); } catch (e) { /* none */ }
  function setSession(s) {
    session = s;
    try { s ? sessionStorage.setItem('rc-session', JSON.stringify(s)) : sessionStorage.removeItem('rc-session'); } catch (e) { /* ignore */ }
  }

  /* ---------- domain helpers ---------- */
  const fmt = (n, d = 2) => Number(n).toLocaleString('en-US', { maximumFractionDigits: d });
  const points = (kg, typeId) => Math.round(kg * db.prices[typeId] * db.rate);
  const earned = (room) => db.entries.filter((e) => e.room === room).reduce((a, e) => a + e.points, 0);
  const spent = (room) => db.redemptions.filter((r) => r.room === room && r.status === 'done').reduce((a, r) => a + r.cost, 0);
  const reserved = (room) => db.redemptions.filter((r) => r.room === room && r.status === 'pending').reduce((a, r) => a + r.cost, 0);
  const balance = (room) => earned(room) - spent(room);
  const available = (room) => balance(room) - reserved(room);
  const kgTotal = (room) => db.entries.filter((e) => e.room === room).reduce((a, e) => a + e.kg, 0);
  const isToday = (ts) => new Date(ts).toDateString() === new Date().toDateString();
  const time = (ts) => new Date(ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  const dateShort = (ts) => new Date(ts).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });

  function newCode() {
    const used = new Set(db.redemptions.filter((r) => r.status === 'pending').map((r) => r.code));
    let c;
    do { c = String(Math.floor(100000 + Math.random() * 900000)); } while (used.has(c));
    return c;
  }

  /* ---------- tiny DOM helper ---------- */
  function h(tag, props, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') e.className = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? '' : v);
    }
    for (const c of kids.flat()) {
      if (c == null || c === false) continue;
      e.append(c.nodeType ? c : document.createTextNode(String(c)));
    }
    return e;
  }

  const $screen = document.getElementById('screen');
  const $back = document.getElementById('back');
  const $logout = document.getElementById('logout');
  const $toast = document.getElementById('toast');
  let toastTimer;
  function toast(msg) {
    $toast.textContent = msg;
    $toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $toast.classList.remove('show'), 1800);
  }

  /* ---------- navigation ---------- */
  let stack = []; // [{name, params}]
  let pollTimer = null;
  let draft = {}; // staff entry in progress

  function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  function go(name, params = {}) { stack.push({ name, params }); render(); }
  function setStack(items) { stack = items.map(([name, params = {}]) => ({ name, params })); render(); }
  function back() { if (stack.length > 1) { stack.pop(); render(); } }
  function homeName() { return session && session.role === 'staff' ? 'a-home' : 'b-home'; }

  function render() {
    stopPoll();
    const cur = stack[stack.length - 1];
    const fn = SCREENS[cur.name];
    $screen.replaceChildren(fn(cur.params));
    $back.hidden = stack.length < 2 || cur.name === 'login';
    $logout.hidden = !session;
    window.scrollTo(0, 0);
    $screen.focus({ preventScroll: true });
  }

  $back.addEventListener('click', back);
  $logout.addEventListener('click', () => { setSession(null); draft = {}; setStack([['login']]); });

  window.addEventListener('storage', (ev) => {
    if (ev.key !== KEY) return;
    db = load();
    const cur = stack[stack.length - 1];
    if (cur && (cur.name === 'b-pending' || cur.name === 'b-home' || cur.name === 'a-home')) render();
  });

  /* ---------- shared pieces ---------- */
  const head = (id, title, sub) => [h('p', { class: 'id' }, id), h('h1', {}, title), sub ? h('p', { class: 'soft' }, sub) : null];

  /* ---------- A0 login ---------- */
  function login() {
    const err = h('p', { class: 'err', role: 'alert' });
    const idIn = h('input', { id: 'uid', autocomplete: 'username', autocapitalize: 'characters', inputmode: 'text' });
    const pwIn = h('input', { id: 'pw', type: 'password', autocomplete: 'current-password' });
    const submit = (ev) => {
      ev.preventDefault();
      const id = idIn.value.trim();
      const ok = pwIn.value === '1234';
      if (ok && id.toLowerCase() === 'staff') {
        setSession({ role: 'staff', id: 'staff' });
        setStack([['a-home']]);
      } else if (ok && ROOMS.includes(id.toUpperCase())) {
        setSession({ role: 'resident', id: id.toUpperCase() });
        setStack([['b-home']]);
      } else {
        err.textContent = 'ID or password is not right. Check the demo accounts below.';
      }
    };
    return h('div', {},
      head('A0', 'Log in', 'Use your staff ID or your unit number.'),
      h('form', { onsubmit: submit },
        h('label', { for: 'uid' }, 'ID'), idIn,
        h('label', { for: 'pw' }, 'Password'), pwIn,
        err,
        h('button', { class: 'btn', type: 'submit' }, 'Log in')),
      h('h2', {}, 'Demo accounts'),
      h('p', { class: 'soft mono' }, 'staff / 1234'),
      h('p', { class: 'soft mono' }, 'A101 / 1234  (resident with points)'),
      h('button', {
        class: 'linkbtn', type: 'button',
        onclick: () => { db = seed(); save(); toast('Demo data reset'); },
      }, 'Reset demo data'));
  }

  /* ---------- A1 staff home ---------- */
  function aHome() {
    const today = db.entries.filter((e) => isToday(e.ts)).sort((a, b) => b.ts - a.ts);
    const kg = today.reduce((a, e) => a + e.kg, 0);
    return h('div', {},
      head('A1', 'Staff home'),
      h('div', { class: 'pair' },
        h('div', {}, h('b', {}, today.length), h('span', {}, 'entries today')),
        h('div', {}, h('b', {}, fmt(kg, 1)), h('span', {}, 'kg today'))),
      h('button', { class: 'btn', type: 'button', onclick: () => { draft = {}; go('a-room'); } }, 'Log waste'),
      h('button', { class: 'btn ghost', type: 'button', onclick: () => go('a-redeem') }, 'Confirm a redemption'),
      h('button', { class: 'btn ghost', type: 'button', onclick: () => go('a-prices') }, 'Price list'),
      h('h2', {}, 'Today\'s entries'),
      today.length
        ? h('ul', { class: 'list' }, today.slice(0, 12).map((e) =>
          h('li', {}, h('div', { class: 'row static' },
            h('span', { class: 'l' }, `${e.room} · ${typeOf(e.typeId).en}`, h('small', {}, `${time(e.ts)} · ${fmt(e.kg)} kg`)),
            h('span', { class: 'r' }, `${e.points} pts`)))))
        : h('p', { class: 'soft' }, 'Nothing logged yet today. Tap "Log waste" to add the first entry.'));
  }

  /* ---------- A2 pick room ---------- */
  function aRoom() {
    const list = h('ul', { class: 'list' });
    const paint = (q) => {
      const hits = ROOMS.filter((r) => r.includes(q.trim().toUpperCase()));
      list.replaceChildren(...(hits.length
        ? hits.map((r) => h('li', {}, h('button', {
          class: 'row', type: 'button',
          onclick: () => { draft = { room: r }; go('a-type'); },
        }, h('span', { class: 'l' }, r), h('span', { class: 'r' }, `${balance(r)} pts`))))
        : [h('li', {}, h('p', { class: 'soft', style: 'padding:12px 2px;margin:0' }, 'No unit matches. Check the number and try again.'))]));
    };
    const input = h('input', { id: 'q', type: 'search', placeholder: 'e.g. A101', autocomplete: 'off', oninput: (e) => paint(e.target.value) });
    paint('');
    return h('div', {},
      head('A2', 'Pick room', 'Search by unit number.'),
      h('label', { for: 'q' }, 'Unit'), input,
      h('h2', {}, 'Rooms'), list);
  }

  /* ---------- A3 pick type ---------- */
  function aType() {
    return h('div', {},
      head('A3', 'Pick type', `Room ${draft.room}`),
      h('ul', { class: 'list' }, TYPES.map((t) =>
        h('li', {}, h('button', {
          class: 'row', type: 'button',
          onclick: () => { draft.typeId = t.id; draft.kg = draft.kg && draft.keepKg ? draft.kg : 1; go('a-weight'); },
        }, h('span', { class: 'l' }, t.en, h('small', {}, t.th)), h('span', { class: 'r' }, `฿${fmt(db.prices[t.id], 1)}/kg`))))));
  }

  /* ---------- A4 weight ---------- */
  function aWeight() {
    const t = typeOf(draft.typeId);
    const input = h('input', { id: 'kg', type: 'number', inputmode: 'decimal', min: '0', max: String(MAX_KG), step: '0.1', value: String(draft.kg || 1) });
    const live = h('p', { class: 'big' });
    const next = h('button', { class: 'btn', type: 'button', onclick: () => go('a-review') }, 'Review');
    const err = h('p', { class: 'err', role: 'alert' });
    const update = () => {
      const kg = parseFloat(input.value);
      const valid = Number.isFinite(kg) && kg > 0 && kg <= MAX_KG;
      draft.kg = valid ? Math.round(kg * 100) / 100 : 0;
      live.textContent = valid ? `${points(draft.kg, draft.typeId)} pts` : '— pts';
      next.disabled = !valid;
      err.textContent = input.value !== '' && !valid ? `Enter a weight above 0 and up to ${MAX_KG} kg.` : '';
    };
    const bump = (d) => {
      const kg = Math.max(0, Math.round(((parseFloat(input.value) || 0) + d) * 10) / 10);
      input.value = String(kg);
      update();
    };
    input.addEventListener('input', update);
    update();
    return h('div', {},
      head('A4', 'Weight', `${draft.room} · ${t.en}`),
      h('label', { for: 'kg' }, 'Weight in kg'),
      h('div', { class: 'stepper' },
        h('button', { type: 'button', 'aria-label': 'Minus 0.5 kg', onclick: () => bump(-0.5) }, '−'),
        input,
        h('button', { type: 'button', 'aria-label': 'Plus 0.5 kg', onclick: () => bump(0.5) }, '+')),
      err,
      h('p', { class: 'soft', style: 'margin-top:20px' }, `At ฿${fmt(db.prices[t.id], 1)}/kg this earns`),
      live,
      next);
  }

  /* ---------- A5 review ---------- */
  function aReview() {
    const t = typeOf(draft.typeId);
    const pts = points(draft.kg, draft.typeId);
    const submit = () => {
      const entry = { id: uid(), ts: Date.now(), room: draft.room, typeId: draft.typeId, kg: draft.kg, price: db.prices[draft.typeId], points: pts };
      db.entries.push(entry);
      save();
      draft.last = entry;
      go('a-saved');
    };
    return h('div', {},
      head('A5', 'Review', 'Check the entry before saving.'),
      h('dl', { class: 'kv' },
        h('dt', {}, 'Room'), h('dd', {}, draft.room),
        h('dt', {}, 'Type'), h('dd', {}, t.en),
        h('dt', {}, 'Weight'), h('dd', {}, `${fmt(draft.kg)} kg`),
        h('dt', {}, 'Price'), h('dd', {}, `฿${fmt(db.prices[draft.typeId], 1)}/kg`),
        h('dt', {}, 'Points'), h('dd', {}, h('b', {}, pts))),
      h('button', { class: 'btn', type: 'button', onclick: submit }, 'Save entry'),
      h('button', { class: 'btn ghost', type: 'button', onclick: back }, 'Change weight'));
  }

  /* ---------- A6 saved ---------- */
  function aSaved() {
    const e = draft.last;
    const t = typeOf(e.typeId);
    return h('div', {},
      head('A6', 'Saved'),
      h('p', {}, `${fmt(e.kg)} kg of ${t.en.toLowerCase()} recorded for ${e.room}.`),
      h('dl', { class: 'kv' },
        h('dt', {}, 'Points added'), h('dd', {}, `+${e.points}`),
        h('dt', {}, 'Room total'), h('dd', {}, `${balance(e.room)} pts`),
        h('dt', {}, 'Buyer'), h('dd', {}, h('span', { class: 'mark' }, 'matched by type, list TBD'))),
      h('button', {
        class: 'btn', type: 'button',
        onclick: () => setStack([['a-home'], ['a-type']]),
      }, 'Add another for the same room'),
      h('button', { class: 'btn ghost', type: 'button', onclick: () => { draft = {}; setStack([['a-home']]); } }, 'Home'));
  }

  /* ---------- A7 price list ---------- */
  function aPrices() {
    const inputs = {};
    const field = (id, label, value, step, note) => {
      inputs[id] = h('input', { id: `f-${id}`, type: 'number', min: '0', step, inputmode: 'decimal', value: String(value) });
      return h('div', { class: 'f' }, h('label', { for: `f-${id}` }, label, note ? h('small', {}, note) : null), inputs[id]);
    };
    const onSave = () => {
      const num = (el, fallback) => { const v = parseFloat(el.value); return Number.isFinite(v) && v >= 0 ? v : fallback; };
      TYPES.forEach((t) => { db.prices[t.id] = num(inputs['p-' + t.id], db.prices[t.id]); });
      db.rate = num(inputs.rate, db.rate);
      db.rewards.forEach((r) => { r.cost = Math.round(num(inputs['c-' + r.id], r.cost)); });
      save();
      toast('Saved');
      back();
    };
    return h('div', {},
      head('A7', 'Price list', 'One price per type. Update it when the buyer\'s price changes.'),
      h('h2', {}, 'Buyer price, ฿ per kg'),
      h('div', { class: 'fields' }, TYPES.map((t) => field('p-' + t.id, t.en, db.prices[t.id], '0.1', t.th))),
      h('h2', {}, 'Reward rate'),
      h('div', { class: 'fields' }, field('rate', 'Points per ฿', db.rate, '0.1', 'Placeholder until decided')),
      h('h2', {}, 'Reward cost, points'),
      h('div', { class: 'fields' }, db.rewards.map((r) => field('c-' + r.id, r.name, r.cost, '1', r.kind === 'merch' ? 'Merch · placeholder' : 'Vending · placeholder'))),
      h('p', { class: 'soft', style: 'margin-top:12px' }, 'Changes apply to new entries only. Saved entries keep the price they were recorded at.'),
      h('button', { class: 'btn', type: 'button', onclick: onSave }, 'Save prices'));
  }

  /* ---------- A8 confirm redemption ---------- */
  function aRedeem() {
    const out = h('div', {});
    const input = h('input', { id: 'code', inputmode: 'numeric', maxlength: '6', autocomplete: 'off', placeholder: '6-digit code' });
    const find = (ev) => {
      ev.preventDefault();
      const code = input.value.trim();
      const r = db.redemptions.find((x) => x.code === code && x.status === 'pending');
      if (!r) {
        out.replaceChildren(h('p', { class: 'err', role: 'alert' }, 'No open request has this code. Ask the resident to check it, or to request again.'));
        return;
      }
      const bal = balance(r.room);
      const enough = bal >= r.cost;
      out.replaceChildren(...[
        h('h2', {}, 'Request'),
        h('dl', { class: 'kv' },
          h('dt', {}, 'Room'), h('dd', {}, r.room),
          h('dt', {}, 'Reward'), h('dd', {}, r.name),
          h('dt', {}, 'Cost'), h('dd', {}, `${r.cost} pts`),
          h('dt', {}, 'Room balance'), h('dd', {}, `${bal} pts`)),
        enough ? null : h('p', { class: 'err', role: 'alert' }, 'The room does not have enough points for this reward.'),
        h('button', {
          class: 'btn', type: 'button', disabled: !enough,
          onclick: () => {
            r.status = 'done'; r.doneAt = Date.now(); save();
            toast(`Confirmed. ${r.cost} pts deducted from ${r.room}.`);
            setStack([['a-home']]);
          },
        }, r.kind === 'merch' ? 'Confirm and hand over' : 'Confirm and deduct points'),
      ].filter(Boolean));
    };
    return h('div', {},
      head('A8', 'Confirm redemption', 'Enter the code the resident shows you.'),
      h('form', { onsubmit: find },
        h('label', { for: 'code' }, 'Resident code'), input,
        h('button', { class: 'btn', type: 'submit' }, 'Find request')),
      out);
  }

  /* ---------- B1 resident home ---------- */
  function bHome() {
    const room = session.id;
    const mine = db.entries.filter((e) => e.room === room).sort((a, b) => b.ts - a.ts);
    const open = db.redemptions.filter((r) => r.room === room && r.status === 'pending');
    const kg = kgTotal(room);
    return h('div', {},
      head('B1', `Unit ${room}`),
      h('p', { class: 'soft', style: 'margin:0' }, 'Points balance'),
      h('p', { class: 'big' }, balance(room)),
      open.length ? h('p', { class: 'soft' }, `${reserved(room)} pts are held for open requests.`) : null,
      h('div', { class: 'pair' },
        h('div', {}, h('b', {}, fmt(kg, 1)), h('span', {}, 'kg recycled')),
        h('div', {}, h('b', {}, fmt(kg * CO2_PER_KG, 1)), h('span', {}, 'kg CO₂ saved, estimate'))),
      h('button', { class: 'btn', type: 'button', onclick: () => go('b-rewards') }, 'Redeem points'),
      open.length ? [
        h('h2', {}, 'Open requests'),
        h('ul', { class: 'list' }, open.map((r) => h('li', {}, h('button', {
          class: 'row', type: 'button', onclick: () => go('b-pending', { id: r.id }),
        }, h('span', { class: 'l' }, r.name, h('small', {}, `Code ${r.code}`)), h('span', { class: 'r' }, `${r.cost} pts`))))),
      ] : null,
      h('h2', {}, 'Recent entries'),
      mine.length
        ? h('ul', { class: 'list' }, mine.slice(0, 6).map((e) => h('li', {}, h('div', { class: 'row static' },
          h('span', { class: 'l' }, typeOf(e.typeId).en, h('small', {}, `${dateShort(e.ts)} · ${fmt(e.kg)} kg`)),
          h('span', { class: 'r' }, `+${e.points}`)))))
        : h('p', { class: 'soft' }, 'No entries yet. Hand your sorted recycling to the juristic office to start earning points.'));
  }

  /* ---------- B2 rewards ---------- */
  function bRewards() {
    const room = session.id;
    const link = (title, sub, name) => h('li', {}, h('button', { class: 'row', type: 'button', onclick: () => go(name) },
      h('span', { class: 'l' }, title, h('small', {}, sub)), h('span', { class: 'r' }, '›')));
    return h('div', {},
      head('B2', 'Rewards', `${available(room)} points available`),
      h('ul', { class: 'list' },
        link('Vending discount', 'Get a code for the condo vending machine', 'b-vending'),
        link('Merch', 'Keychain or recycle mascot figure', 'b-merch')));
  }

  /* ---------- B3 / B4 reward lists ---------- */
  function rewardList(kind, id, title, sub) {
    const room = session.id;
    const avail = available(room);
    const items = db.rewards.filter((r) => r.kind === kind);
    return h('div', {},
      head(id, title, sub),
      h('p', { class: 'soft' }, `${avail} points available`),
      h('ul', { class: 'list' }, items.map((r) => h('li', {}, h('button', {
        class: 'row', type: 'button', disabled: avail < r.cost,
        onclick: () => {
          const rec = { id: uid(), room, kind, name: r.name, cost: r.cost, code: newCode(), status: 'pending', ts: Date.now() };
          db.redemptions.push(rec); save();
          stack.pop(); // replace the list so Back returns to Rewards
          go('b-pending', { id: rec.id });
        },
      }, h('span', { class: 'l' }, r.name, h('small', {}, avail < r.cost ? `Needs ${r.cost - avail} more points` : 'Tap to get a code')),
      h('span', { class: 'r' }, `${r.cost} pts`, h('br'), h('span', { class: 'mark' }, 'placeholder')))))));
  }
  const bVending = () => rewardList('vending', 'B3', 'Vending discount', 'Points are held now and deducted when the code is used.');
  const bMerch = () => rewardList('merch', 'B4', 'Merch', 'Staff hand it over at the office.');

  /* ---------- B5 / B6 code + claim ---------- */
  function bPending({ id }) {
    const r = db.redemptions.find((x) => x.id === id);
    if (!r) return h('div', {}, head('B5', 'Request not found'), h('button', { class: 'btn', type: 'button', onclick: () => setStack([['b-home']]) }, 'Home'));
    const isMerch = r.kind === 'merch';
    const check = () => {
      const cur = db.redemptions.find((x) => x.id === id);
      if (cur && cur.status === 'done') setStack([['b-home'], ['b-balance', { id }]]);
    };
    check();
    pollTimer = setInterval(() => { db = load(); check(); }, 2000);
    return h('div', {},
      head(isMerch ? 'B6' : 'B5', isMerch ? 'Claim at office' : 'Show code'),
      h('p', {}, r.name),
      h('div', { class: 'code', 'aria-label': `Code ${r.code.split('').join(' ')}` }, r.code),
      h('p', { class: 'soft' }, isMerch
        ? 'Show this code at the juristic office. Staff confirm it and hand over the item.'
        : 'Use this code at the vending machine, or give it to staff. Points are deducted when it is confirmed.'),
      h('p', { class: 'soft' }, `${r.cost} points are held until then. This page updates by itself once it is confirmed.`),
      h('button', {
        class: 'btn ghost', type: 'button',
        onclick: () => {
          db.redemptions = db.redemptions.filter((x) => x.id !== id); save();
          toast('Request cancelled. Points released.');
          setStack([['b-home']]);
        },
      }, 'Cancel this request'));
  }

  /* ---------- B7 balance updated ---------- */
  function bBalance({ id }) {
    const r = db.redemptions.find((x) => x.id === id);
    return h('div', {},
      head('B7', 'Balance updated'),
      r ? h('p', {}, `${r.name} confirmed. ${r.cost} points deducted.`) : null,
      h('p', { class: 'soft', style: 'margin:0' }, 'New balance'),
      h('p', { class: 'big' }, balance(session.id)),
      h('button', { class: 'btn', type: 'button', onclick: () => setStack([['b-home']]) }, 'Back to home'));
  }

  const SCREENS = {
    login, 'a-home': aHome, 'a-room': aRoom, 'a-type': aType, 'a-weight': aWeight, 'a-review': aReview,
    'a-saved': aSaved, 'a-prices': aPrices, 'a-redeem': aRedeem,
    'b-home': bHome, 'b-rewards': bRewards, 'b-vending': bVending, 'b-merch': bMerch, 'b-pending': bPending, 'b-balance': bBalance,
  };

  /* ---------- boot ---------- */
  setStack([[session ? homeName() : 'login']]);
})();
