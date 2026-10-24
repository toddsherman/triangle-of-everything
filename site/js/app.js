import { loadData, GROUPS } from "./data.js";
import { createTriangle, TRIANGLE_LAYERS } from "./triangle.js";
import { createStars, STARS_LAYERS } from "./stars.js";
import { createParticles, PARTICLE_LAYERS, PARTICLE_CLASSES } from "./particles.js";
import { createTimeline } from "./timeline.js";
import { createElements, ELEMENT_LAYERS, elementLegend } from "./elements.js";
import { renderIntro, renderDetails } from "./details.js";
import { createCosmicClock } from "./cosmictime.js";
import { createSound } from "./sound.js";
import { esc, sci, friendlyLength } from "./format.js";

const $ = (s) => document.querySelector(s);
const VIEWS = ["triangle", "stars", "particles", "elements", "timeline"];
const LAYERS = { triangle: TRIANGLE_LAYERS, stars: STARS_LAYERS, particles: PARTICLE_LAYERS, elements: ELEMENT_LAYERS, timeline: [] };
const FACTORIES = { triangle: createTriangle, stars: createStars, particles: createParticles, elements: createElements, timeline: createTimeline };
const LEGEND_GROUPS = Object.keys(GROUPS).filter((g) => !["time", "erratum", "boundary"].includes(g));

const state = { view: "triangle", selected: null, hidden: new Set(), tour: -1 };
const layerState = Object.fromEntries(VIEWS.map((v) => [v, Object.fromEntries(LAYERS[v].map((l) => [l.id, l.on]))]));
const charts = {};
let data, clock;

// cosmic time is always on for the triangle: u runs 0 (the Big Bang) -> 1 (today) on the clock's story scale
const time = { playing: false, u: 1, raf: 0, last: 0, follow: false };
const PLAY_SECONDS = 48;
// a rising Shepard tone while time plays; each new dot on the triangle gets a ring that closes in on it and a
// pop the moment the ring arrives
const sound = createSound();
const RING_LEAD = 0.6;           // seconds a ring takes to close in
let shownBefore = new Set();     // the dots on the triangle at the last moment, to tell what's new
const rememberShown = () => { if (charts.triangle) shownBefore = new Set(charts.triangle.visibleKeys()); };
let dueBefore = new Set();       // while playing: dots due within RING_LEAD, as of the last frame
const ringed = new Set();        // while playing: dots whose ring is on its way; they pop when they appear
const announced = [];            // when recent arrivals were announced (ms), to keep bursts readable

// ------------------------------------------------------------------------------------------ boot
async function boot() {
  const details = $("#details");
  details.innerHTML = `<p class="note">Loading data…</p>`;
  try {
    data = await loadData();
  } catch (err) {
    details.innerHTML = `<h1>Couldn't load the data</h1><p>${esc(err.message)}</p>
      <p class="note">Serve the project folder over HTTP (e.g. <code>python3 -m http.server</code> in the project root) and open <code>/site/</code>.</p>`;
    return;
  }
  renderIntro(details, data);
  clock = createCosmicClock(data.timeline.history);
  for (const it of data.items) it.appearU = clock.uOfAppeared(it.raw?.first_appeared ?? null);
  ensureChart("triangle").setMargin({ bottom: 136 });   // room for the time bar
  applyTime();                                           // open on today

  wireNavigation();
  wireControls();
  wireSearch();
  wireTour();
  wireTime();
  renderLegend();
  renderLayers();
  renderErrata();

  const fromHash = decodeURIComponent(location.hash.slice(1));
  if (data.byKey.has(fromHash)) select(fromHash, { switchView: true });
  window.addEventListener("hashchange", () => {
    const k = decodeURIComponent(location.hash.slice(1));
    if (k !== state.selected && data.byKey.has(k)) select(k, { switchView: true });
  });
}

// ------------------------------------------------------------------------------------------ views
// The triangle is home; Stars, Particles, Elements and Timeline open from it (zoom boxes, the time bar, details, search)
const canShow = (it, view) => it.views.includes(view);
const bestView = (it) => (canShow(it, state.view) ? state.view : it.views[0] ?? it.relatedView ?? state.view);

function ensureChart(view) {
  if (charts[view]) return charts[view];
  const chart = FACTORIES[view]({
    svgEl: $(`#${view}-svg`), tooltipEl: $("#tooltip"), data, onSelect: select, onOpenView: (v) => switchView(v),
    onUserZoom: () => { if (view === "triangle") time.follow = false; },   // a manual pan/zoom stops the camera following
  });
  for (const [k, v] of Object.entries(layerState[view])) chart.setOption(k, v);
  chart.setHidden(state.hidden);
  chart.setSelected(state.selected);
  charts[view] = chart;
  return chart;
}

function switchView(view) {
  if (!VIEWS.includes(view) || view === state.view) return;
  const home = view === "triangle";
  if (!home) pause();
  state.view = view;
  for (const v of VIEWS) $(`#view-${v}`).hidden = v !== view;
  $(".stage").classList.toggle("timing", home);
  $("#timebar").hidden = !home;
  $("#tour").hidden = !home;
  $("#back").hidden = home;
  $("#tooltip").hidden = true;
  const chart = ensureChart(view);
  requestAnimationFrame(() => chart.resize());
  renderLayers();
  renderLegend();
}

// ------------------------------------------------------------------------------------------ selection
function select(key, { focus = true, switchView: sw = false } = {}) {
  const it = data.byKey.get(key);
  if (!it) return;
  key = it.key;                      // a folded Lineweaver & Patel link (lp:…) lands on the item that stands for it
  state.selected = key;
  if (it.type === "lp" && !layerState.triangle.lp) setLayer("triangle", "lp", true);
  if (sw && !canShow(it, state.view)) switchView(bestView(it));
  // on the triangle, something that doesn't exist yet at the moment shown: jump to today so it can be seen
  if (state.view === "triangle" && it.appearU != null && it.appearU > time.u) goToday();
  for (const c of Object.values(charts)) c.setSelected(key);
  if (focus && canShow(it, state.view)) charts[state.view]?.focus(key);
  renderDetails($("#details"), it, data, { canShow, onSelect: select, onShowIn: showIn, onShowTime: watchAppear });
  const ti = data.tour.indexOf(key);
  if (ti >= 0) { state.tour = ti; updateTourLabel(); }
  if (decodeURIComponent(location.hash.slice(1)) !== key) history.replaceState(null, "", `#${encodeURIComponent(key)}`);
}

function showIn(key, view) {
  switchView(view);
  select(key);
}

// ------------------------------------------------------------------------------------------ controls
function wireNavigation() {
  $("#back").addEventListener("click", () => {
    switchView("triangle");
    const it = state.selected && data.byKey.get(state.selected);
    if (it && canShow(it, "triangle")) charts.triangle.focus(state.selected);
  });
  $("#open-timeline").addEventListener("click", () => switchView("timeline"));
  $("#brand").addEventListener("click", (e) => {
    e.preventDefault();
    state.selected = null;
    state.tour = -1;
    $("#tour-name").textContent = "smallest to largest";
    for (const c of Object.values(charts)) c.setSelected(null);
    history.replaceState(null, "", location.pathname);
    renderIntro($("#details"), data);
    switchView("triangle");
    goToday();
    charts.triangle.zoom("home");
  });
}

function wireControls() {
  document.querySelectorAll("[data-zoom]").forEach((b) => b.addEventListener("click", () => {
    if (state.view === "triangle") time.follow = false;
    charts[state.view]?.zoom(b.dataset.zoom);
  }));
}

// ------------------------------------------------------------------------------------------ cosmic time
function wireTime() {
  const slider = $("#time-slider");
  $("#time-play").addEventListener("click", () => (time.playing ? pause() : play()));
  const soundBtn = $("#time-sound");
  const showSound = () => {
    soundBtn.setAttribute("aria-pressed", String(!sound.muted));
    soundBtn.title = sound.muted ? "Sound off" : "Sound on";
  };
  soundBtn.addEventListener("click", () => { sound.setMuted(!sound.muted); showSound(); });
  showSound();
  slider.addEventListener("input", () => {
    pause();
    const u = Number(slider.value) / 1000;
    const forward = u > time.u;            // dragging forward pops what appears; dragging back is quiet
    time.u = u;
    time.follow = true;
    applyTime({ listen: forward });
  });
  // milestone ticks under the slider (clicking one jumps there)
  const at = (seconds) => clock.uOfS(clock.sOf(seconds, null));
  const u = (key) => data.byKey.get(key)?.appearU;
  const milestones = [
    ["Big Bang", 0], ["Particles", at(1e-12)], ["Protons", at(1e-6)], ["Nuclei", at(960)], ["Atoms", at(1.2e13)],
    ["First stars", u("stellar:main_sequence")], ["Milky Way", u("object:milky_way")], ["Sun & Earth", u("object:sun")],
    ["Life", u("object:bacterium")], ["Humans", u("object:humans")], ["Pyramids", u("object:great_pyramid")], ["Today", 1],
  ].filter(([, v]) => v != null);
  const ticks = $("#time-ticks");
  const draw = () => {
    const w = ticks.clientWidth || 1;
    let lastRight = -Infinity;
    ticks.innerHTML = "";
    for (const [label, v] of milestones) {
      const x = v * w, half = label.length * 3.1 + 4;
      if (x - half < lastRight) continue;       // skip labels that would overlap the previous one
      lastRight = x + half;
      const el = document.createElement("span");
      el.textContent = label;
      el.style.left = `${v * 100}%`;
      el.addEventListener("click", () => { pause(); time.u = v; time.follow = v < 1; applyTime(); });
      ticks.appendChild(el);
    }
  };
  new ResizeObserver(draw).observe(ticks);
}

function play() {
  if (time.u >= 1) time.u = 0;          // from today, play starts again at the Big Bang
  time.playing = true;
  time.follow = true;
  applyTime();
  dueBefore = new Set(shownBefore);     // so dots due in the first moments get their rings too
  ringed.clear();
  time.last = performance.now();
  sound.start();
  $("#time-play").innerHTML = "&#10074;&#10074;";
  $("#time-play").setAttribute("aria-label", "Pause");
  cancelAnimationFrame(time.raf);
  time.raf = requestAnimationFrame(step);
}

function pause() {
  if (time.playing) {                   // rings in flight would land on dots that now won't appear
    ringed.clear();
    charts.triangle.clearPulses();
  }
  time.playing = false;
  cancelAnimationFrame(time.raf);
  sound.stop();
  $("#time-play").innerHTML = "&#9654;";
  $("#time-play").setAttribute("aria-label", time.u >= 1 ? "Play from the Big Bang" : "Play");
}

function step(now) {
  if (!time.playing) return;
  time.u = Math.min(1, time.u + (now - time.last) / 1000 / PLAY_SECONDS);
  time.last = now;
  applyTime({ listen: true });
  ringAhead();
  if (time.u >= 1) pause();
  else time.raf = requestAnimationFrame(step);
}

function goToday() {
  pause();
  time.u = 1;
  time.follow = false;
  applyTime();
}

/** Push the current moment to the triangle and the readout. listen: pop for anything that just appeared. */
function applyTime({ listen = false } = {}) {
  const st = clock.stateAt(time.u);
  charts.triangle.setTime(st, time.follow);
  const before = shownBefore;
  rememberShown();
  if (listen) {
    const fresh = [...shownBefore].filter((k) => !before.has(k));
    if (time.playing) {
      // playing: these rings set off early, so they arrive now, with the dots
      const landed = fresh.filter((k) => ringed.delete(k));
      if (landed.length) sound.pop(landed.map((k) => at(data.byKey.get(k)).y));
    } else {
      // dragging the slider: nothing could be foreseen, so ring now and pop as the ring arrives
      for (const it of pickArrivals(fresh)) {
        charts.triangle.pulse(at(it), it.color, RING_LEAD * 1000);
        sound.pop([at(it).y], RING_LEAD);
      }
    }
  }
  $("#time-slider").value = String(Math.round(time.u * 1000));
  const start = data.timeline.history.start;
  const first = time.u === 0;
  $("#time-when").textContent = first ? start.label : clock.label(st);
  $("#time-when").title = first ? start.explanation : "";
  $("#time-facts").textContent = first ? start.summary : `${sci(st.temp)} K · Hubble sphere ${friendlyLength(st.hub)} across`;
  // the most recent thing to appear on the triangle
  let newest = null;
  for (const it of data.items) {
    if (it.appearU == null || it.appearU > time.u || !it.views.includes("triangle") || it.type === "lp" || it.type === "boundary") continue;
    if (!it.real || it.real.w > st.hub + 1e-9) continue;   // beyond the Hubble wall then: not shown
    if (!newest || it.appearU > newest.appearU) newest = it;
  }
  $("#time-new").textContent = first ? "Earlier than this needs a theory of quantum gravity"
    : st.isNow && !time.playing ? "Press ▶ to watch the universe grow from the Big Bang"
    : newest ? `Newest: ${newest.name}` : "Nothing yet but the Big Bang";
}

/** Where a dot sits on the triangle, in chart coordinates (log width, log mass). */
const at = (it) => { const p = it.real ?? it.lp; return { x: p.w, y: p.m }; };

/** Which of these new dots to announce: a burst gets at most three (its lightest, middle and heaviest), and no
 *  more than seven go off in any 0.6 s, so the rings and pops stay readable. */
function pickArrivals(keys) {
  const now = performance.now();
  while (announced.length && now - announced[0] > 600) announced.shift();
  const room = Math.min(3, 7 - announced.length);
  const its = keys.map((k) => data.byKey.get(k)).filter((it) => it?.real ?? it?.lp).sort((a, b) => at(a).y - at(b).y);
  if (room <= 0 || !its.length) return [];
  const pick = its.length <= room ? its : [its[0], its[its.length >> 1], its[its.length - 1]].slice(0, room);
  for (const _ of pick) announced.push(now);
  return pick;
}

/** While playing: find dots due within RING_LEAD seconds and set their rings off now, each timed to arrive the
 *  moment its dot appears. */
function ringAhead() {
  const to = Math.min(1, time.u + RING_LEAD / PLAY_SECONDS);
  const due = new Set(charts.triangle.visibleKeys({ moment: clock.stateAt(to) }));
  const fresh = [...due].filter((k) => !dueBefore.has(k) && !shownBefore.has(k));
  dueBefore = due;
  for (const it of pickArrivals(fresh)) {
    // when it appears: things only ever appear as time runs on (they exist, and the Hubble wall only grows)
    let lo = time.u, hi = to;
    for (let i = 0; i < 12; i++) {
      const mid = (lo + hi) / 2;
      if (charts.triangle.shows(it.key, { moment: clock.stateAt(mid) })) hi = mid; else lo = mid;
    }
    ringed.add(it.key);
    charts.triangle.pulse(at(it), it.color, (hi - time.u) * PLAY_SECONDS * 1000);
  }
}

/** From the details panel: rewind to just before something first existed and play. */
function watchAppear(key) {
  const it = data.byKey.get(key);
  if (it?.appearU == null) return;
  switchView("triangle");
  time.u = Math.max(0, it.appearU - 0.04);
  play();
}

function wireSearch() {
  const input = $("#search"), list = $("#search-results");
  let results = [], active = 0;
  const close = () => { list.hidden = true; };
  const choose = (i) => {
    const it = results[i];
    if (!it) return;
    close();
    input.value = "";
    input.blur();
    select(it.key, { switchView: true });
  };
  const draw = () => {
    list.innerHTML = results.length
      ? results.map((it, i) => `<li role="option" data-i="${i}" aria-selected="${i === active}">
          <span class="dot" style="--c:${it.color}"></span>${esc(it.name)}<span class="type">${esc(it.typeLabel)}</span></li>`).join("")
      : `<li class="empty">No matches</li>`;
    list.hidden = false;
  };
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    if (!q) return close();
    const words = q.split(/\s+/);
    results = data.items
      .filter((it) => words.every((w) => it.search.includes(w)))
      // an element's symbol ("fe") first, then names that start with the query
      .sort((a, b) => ((b.symbol?.toLowerCase() === q) - (a.symbol?.toLowerCase() === q))
        || (b.name.toLowerCase().startsWith(q) - a.name.toLowerCase().startsWith(q)) || a.name.localeCompare(b.name))
      .slice(0, 14);
    active = 0;
    draw();
  });
  input.addEventListener("keydown", (e) => {
    if (list.hidden) return;
    if (e.key === "ArrowDown") { active = Math.min(active + 1, results.length - 1); draw(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = Math.max(active - 1, 0); draw(); e.preventDefault(); }
    else if (e.key === "Enter") { choose(active); e.preventDefault(); }
    else if (e.key === "Escape") close();
  });
  list.addEventListener("mousedown", (e) => {
    const li = e.target.closest("li[data-i]");
    if (li) { e.preventDefault(); choose(Number(li.dataset.i)); }
  });
  input.addEventListener("blur", () => setTimeout(close, 120));
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== input) { e.preventDefault(); input.focus(); }
  });
}

function wireTour() {
  const step = (d) => {
    const n = data.tour.length;
    state.tour = state.tour < 0 ? (d > 0 ? 0 : n - 1) : (state.tour + d + n) % n;
    if (state.view !== "triangle") switchView("triangle");
    select(data.tour[state.tour]);
  };
  $("#tour-prev").addEventListener("click", () => step(-1));
  $("#tour-next").addEventListener("click", () => step(1));
}

function updateTourLabel() {
  const it = data.byKey.get(data.tour[state.tour]);
  $("#tour-name").textContent = `${state.tour + 1}/${data.tour.length} · ${it.name}`;
}

// ------------------------------------------------------------------------------------------ sidebar
function renderLegend() {
  const panel = $("#legend-panel");
  panel.hidden = state.view === "timeline";
  const counts = {};
  for (const it of data.items) if (canShow(it, state.view)) counts[it.group] = (counts[it.group] ?? 0) + 1;
  const el = $("#legend");
  if (state.view === "particles") {
    el.innerHTML = PARTICLE_CLASSES.map((c) => `<button disabled><span class="dot" style="--c:${c.color}"></span>${esc(c.label)}</button>`).join("");
    return;
  }
  if (state.view === "elements") {
    el.innerHTML = elementLegend(data, layerState.elements.origin).map((c) => `<button disabled>
      <span class="dot" style="--c:${c.color}"></span>${esc(c.label)}<span class="count">${c.count}</span></button>`).join("");
    return;
  }
  el.innerHTML = LEGEND_GROUPS.filter((g) => counts[g]).map((id) => `<button data-group="${id}" aria-pressed="${!state.hidden.has(id)}">
      <span class="dot" style="--c:${GROUPS[id].color}"></span>${esc(GROUPS[id].label)}<span class="count">${counts[id]}</span></button>`).join("");
  el.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    const g = b.dataset.group;
    state.hidden.has(g) ? state.hidden.delete(g) : state.hidden.add(g);
    b.setAttribute("aria-pressed", String(!state.hidden.has(g)));
    for (const c of Object.values(charts)) c.setHidden(state.hidden);
    rememberShown();                       // showing a group again isn't something new appearing
  }));
}

function setLayer(view, id, on) {
  layerState[view][id] = on;
  charts[view]?.setOption(id, on);
  if (view === "triangle") rememberShown();
  if (view === state.view) { renderLayers(); renderLegend(); }
}

function renderLayers() {
  const list = LAYERS[state.view];
  $("#layers-panel").hidden = list.length === 0;
  $("#layers").innerHTML = list.map((l) => `<label class="toggle">
      <input type="checkbox" data-layer="${l.id}" ${layerState[state.view][l.id] ? "checked" : ""}>
      <span class="sw" style="--c:${l.color}"></span>${esc(l.label)}</label>`).join("");
  $("#layers").querySelectorAll("input").forEach((inp) => inp.addEventListener("change", () => {
    setLayer(state.view, inp.dataset.layer, inp.checked);
  }));
}

function renderErrata() {
  const errata = data.items.filter((i) => i.type === "erratum");
  $("#errata").innerHTML = errata.map((e) => `<button class="erratum" data-key="${esc(e.key)}">${esc(e.name)}</button>`).join("");
  $("#errata").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => select(b.dataset.key)));
}

boot();
