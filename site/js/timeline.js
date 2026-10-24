// Cosmic timeline on a log-time axis: the poster's era brackets vs when things actually happened,
// plus every time marker. The second axis shows the universe's mean density at each moment.

import { sup, esc, friendlyTime } from "./format.js";

const tickFmt = (d) => `10${sup(d)}`;
const rhoAt = (logT) => 8.65 - 2 * logT;        // radiation-era Friedmann estimate, kg/m^3

export function createTimeline({ svgEl, tooltipEl, data, onSelect }) {
  const svg = d3.select(svgEl);
  svg.selectAll("*").remove();
  const markers = data.items.filter((i) => i.type === "time");
  const eras = data.items.filter((i) => i.type === "era");
  const byId = Object.fromEntries(markers.map((m) => [m.id, m]));
  const state = { selected: null, t: d3.zoomIdentity };
  const margin = { top: 52, right: 24, bottom: 150, left: 120 };   // bottom clears the tour bar
  let bx, pw = 0, ph = 0;

  const defs = svg.append("defs");
  const clip = defs.append("clipPath").attr("id", "tl-clip").append("rect");
  const plot = svg.append("g").attr("clip-path", "url(#tl-clip)");
  const gGrid = plot.append("g").attr("class", "grid");
  const gEras = plot.append("g");
  const gMarks = plot.append("g");
  const gRows = svg.append("g");
  const gx = svg.append("g").attr("class", "axis");
  const gd = svg.append("g").attr("class", "axis");
  const xT = svg.append("text").attr("class", "axis-title").attr("text-anchor", "middle").text("Time since the Big Bang (seconds)");
  const dT = svg.append("text").attr("class", "axis-title").attr("text-anchor", "middle").text("Average density of the universe then (kg/m³)");

  const zoom = d3.zoom().scaleExtent([0.8, 60]).on("zoom", (e) => { state.t = e.transform; render(); });
  svg.call(zoom).on("dblclick.zoom", null);

  const ctx2d = document.createElement("canvas").getContext("2d");
  const textWidth = (s) => { ctx2d.font = `12px "Helvetica Neue", Helvetica, Arial, sans-serif`; return ctx2d.measureText(s).width; };

  function layout() {
    const { width, height } = svgEl.getBoundingClientRect();
    if (!width || !height) return;
    pw = Math.max(50, width - margin.left - margin.right);
    ph = Math.max(120, height - margin.top - margin.bottom);
    bx = d3.scaleLinear().domain([-46, 103]).range([margin.left, margin.left + pw]);
    clip.attr("x", margin.left).attr("y", margin.top).attr("width", pw).attr("height", ph);
    gx.attr("transform", `translate(0,${margin.top + ph})`);
    gd.attr("transform", `translate(0,${margin.top + ph + 46})`);
    xT.attr("x", margin.left + pw / 2).attr("y", margin.top + ph + 34);
    dT.attr("x", margin.left + pw / 2).attr("y", margin.top + ph + 82);
    render();
  }

  function render() {
    if (!bx) return;
    const zx = state.t.rescaleX(bx);
    const y0 = margin.top, y1 = margin.top + ph;
    const rowPoster = y0 + 34, rowActual = y0 + 84, laneTop = y0 + 138;

    const ticks = zx.ticks(Math.max(4, Math.round(pw / 70))).filter(Number.isInteger);
    gx.call(d3.axisBottom(zx).tickValues(ticks).tickFormat(tickFmt));
    const [l, r] = zx.domain();
    const dScale = d3.scaleLinear().domain([rhoAt(l), rhoAt(r)]).range(zx.range());
    const dTicks = dScale.ticks(Math.max(4, Math.round(pw / 90))).filter(Number.isInteger);
    gd.call(d3.axisBottom(dScale).tickValues(dTicks).tickFormat(tickFmt));
    gGrid.selectAll("line").data(ticks).join("line")
      .attr("x1", (d) => zx(d)).attr("x2", (d) => zx(d)).attr("y1", y0).attr("y2", y1);

    gRows.selectAll("text").data([
      { t: "On the poster", y: rowPoster }, { t: "Actually", y: rowActual }, { t: "Moments", y: laneTop + 4 },
    ]).join("text").attr("class", "row-label").attr("x", margin.left - 12).attr("y", (d) => d.y + 4)
      .attr("text-anchor", "end").text((d) => d.t);

    // era bars: poster bracket (from/to markers) and actual timing
    const bars = [];
    for (const e of eras) {
      const a = byId[e.raw.from_marker], b = byId[e.raw.to_marker];
      if (a && b) bars.push({ key: e.key, item: e, row: "poster", x0: a.raw.log10_seconds, x1: b.raw.log10_seconds, y: rowPoster });
      const ref = e.raw.reference_log10_seconds;
      if (ref) bars.push({ key: e.key, item: e, row: "actual", x0: ref[0], x1: ref[1], y: rowActual });
    }
    const eb = gEras.selectAll("g.era").data(bars, (d) => `${d.key}-${d.row}`).join((enter) => {
      const g = enter.append("g").attr("class", "era")
        .on("click", (e, d) => { e.stopPropagation(); onSelect(d.key, { focus: false }); })
        .on("mouseenter", (e, d) => tip(e, `<strong>${esc(d.item.name)}</strong><span>${d.row === "poster" ? "Bracket on the poster" : "Actual timing"}</span><br>
          ${esc(friendlyTime(10 ** d.x0))}${d.x1 !== d.x0 ? ` → ${esc(friendlyTime(10 ** d.x1))}` : ""}`))
        .on("mousemove", moveTip).on("mouseleave", hideTip);
      g.append("rect");
      g.append("text");
      return g;
    });
    eb.classed("selected", (d) => d.key === state.selected).classed("hyp", (d) => d.item.hypothetical);
    eb.select("rect").attr("x", (d) => zx(d.x0) - (d.x1 === d.x0 ? 5 : 0)).attr("y", (d) => d.y - 13)
      .attr("width", (d) => Math.max(10, zx(d.x1) - zx(d.x0))).attr("height", 26).attr("rx", 6);
    eb.select("text").attr("x", (d) => Math.max(zx(d.x0), margin.left) + 8).attr("y", (d) => d.y + 4)
      .text((d) => (zx(d.x1) - Math.max(zx(d.x0), margin.left) > textWidth(d.item.name) + 16 ? d.item.name : ""));

    // markers: a line, a dot and a label placed in the first free lane
    const lanes = [];
    const placed = [...markers].sort((a, b) => a.raw.log10_seconds - b.raw.log10_seconds).map((m) => {
      const x = zx(m.raw.log10_seconds);
      const label = m.raw.printed_text ?? friendlyTime(m.raw.seconds);
      const w = textWidth(label) + 14;
      const flip = x + w > margin.left + pw;          // near the right edge: put the label on the left
      const start = flip ? x - w : x;
      let lane = 0;
      while (lanes[lane] != null && lanes[lane] > start - 4) lane++;
      lanes[lane] = start + w;
      return { m, x, label, flip, ly: laneTop + 24 + lane * 22 };
    });
    const mk = gMarks.selectAll("g.mark").data(placed, (d) => d.m.key).join((enter) => {
      const g = enter.append("g").attr("class", "mark")
        .on("click", (e, d) => { e.stopPropagation(); onSelect(d.m.key, { focus: false }); })
        .on("mouseenter", (e, d) => tip(e, `<strong>${esc(d.label)}</strong><span>${esc(friendlyTime(d.m.raw.seconds))} after the Big Bang</span><br>${esc(d.m.raw.note)}`))
        .on("mousemove", moveTip).on("mouseleave", hideTip);
      g.append("line");
      g.append("circle");
      g.append("text");
      return g;
    });
    mk.classed("selected", (d) => d.m.key === state.selected).classed("now", (d) => d.m.id === "now");
    mk.select("line").attr("x1", (d) => d.x).attr("x2", (d) => d.x).attr("y1", laneTop).attr("y2", y1);
    mk.select("circle").attr("cx", (d) => d.x).attr("cy", laneTop).attr("r", 5);
    mk.select("text").attr("x", (d) => (d.flip ? d.x - 7 : d.x + 7)).attr("y", (d) => d.ly)
      .attr("text-anchor", (d) => (d.flip ? "end" : "start")).text((d) => d.label);
  }

  function tip(e, html) { tooltipEl.innerHTML = html; tooltipEl.hidden = false; moveTip(e); }
  function moveTip(e) {
    const r = svgEl.getBoundingClientRect();
    tooltipEl.style.left = `${Math.min(e.clientX - r.left + 14, r.width - 270)}px`;
    tooltipEl.style.top = `${e.clientY - r.top + 14}px`;
  }
  function hideTip() { tooltipEl.hidden = true; }

  new ResizeObserver(layout).observe(svgEl);
  layout();

  const centerOf = (key) => {
    const it = data.byKey.get(key);
    if (!it) return null;
    if (it.type === "time") return it.raw.log10_seconds;
    const a = byId[it.raw.from_marker], b = byId[it.raw.to_marker];
    return a && b ? (a.raw.log10_seconds + b.raw.log10_seconds) / 2 : null;
  };

  return {
    setSelected(key) { state.selected = key; render(); },
    setHidden() {},
    setOption() {},
    has: (key) => centerOf(key) != null,
    focus(key) {
      if (!bx) layout();
      const c = centerOf(key);
      if (c == null) return;
      const k = Math.max(state.t.k, 2.5);
      svg.transition().duration(900).call(zoom.transform, d3.zoomIdentity.translate(margin.left + pw / 2 - k * bx(c), 0).scale(k));
    },
    zoom(how) {
      if (how === "home") svg.transition().duration(700).call(zoom.transform, d3.zoomIdentity);
      else svg.transition().duration(300).call(zoom.scaleBy, how === "in" ? 1.6 : 1 / 1.6);
    },
    resize: layout,
  };
}
