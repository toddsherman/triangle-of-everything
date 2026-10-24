// Stellar evolution: diameter (km) vs mass (solar masses), with evolution arrows and physical limits.

import { createChart } from "./chart.js";
import { GROUPS } from "./data.js";
import { esc, friendlyMass, friendlyLength } from "./format.js";

const BIG = 200;     // "far away" in decades; lines are clipped to the view before drawing

export const STARS_LAYERS = [
  { id: "arrows", label: "Evolution arrows", on: true, color: "#ff8fe6" },
  { id: "limits", label: "Mass limits", on: true, color: "#ffc24a" },
  { id: "water", label: "Water-density line", on: true, color: "#9fd3ff" },
  { id: "labels", label: "Labels", on: true, color: "#ece8f4" },
];

export function createStars({ svgEl, tooltipEl, data, onSelect }) {
  const items = data.items.filter((i) => i.views.includes("stars"));
  const { stellar } = data;
  // exact offsets from the data, shared with how black holes are placed below
  const LOG_MSUN = Math.log10(data.main.physics.constants_si.M_sun);
  const SCHW_KM = stellar.equations.schwarzschild_offset;   // log D[km] = log M[Msun] + SCHW_KM
  const WATER = stellar.equations.water_offset;             // log M[Msun] = 3 log D[km] + WATER
  const byId = Object.fromEntries(items.map((i) => [i.id, i]));
  const ms = byId.main_sequence.raw.reference;
  const msBand = {
    a: { x: Math.log10(ms.diameter_km_range[0]), y: Math.log10(ms.mass_msun_range[0]) },
    b: { x: Math.log10(ms.diameter_km_range[1]), y: Math.log10(ms.mass_msun_range[1]) },
  };

  const position = (it) => {
    const r = it.raw.reference;
    if (r.log10_mass_msun == null) return null;
    // a black hole's diameter follows from its mass, so it lands exactly on the Schwarzschild line
    if (it.raw.category === "black_hole") return { x: r.log10_mass_msun + SCHW_KM, y: r.log10_mass_msun };
    return r.log10_diameter_km != null ? { x: r.log10_diameter_km, y: r.log10_mass_msun } : null;
  };

  // where an arrow should start/end for an item that has no single real position (the main sequence band)
  const anchor = (it) => {
    const p = position(it);
    if (p) return p;
    if (it.id === "main_sequence") return { x: msBand.a.x + (msBand.b.x - msBand.a.x) * 0.85, y: msBand.a.y + (msBand.b.y - msBand.a.y) * 0.85 };
    return null;
  };

  const chart = createChart({
    svgEl, tooltipEl, items, onSelect,
    home: { x: [0.4, 11], y: [-6.6, 3.2] },
    xTitle: "Diameter (kilometres)", yTitle: "Mass (solar masses)",
    rightAxis: { title: "Mass (kilograms)", offset: LOG_MSUN, option: "kg" },
    options: { ...Object.fromEntries(STARS_LAYERS.map((l) => [l.id, l.on])), kg: false },
    position,
    priority: (it) => (it.raw.main_chart_object_id ? 80 : 60),
    radius: () => 6,
    tooltip: (d, p) => `<strong>${esc(d.name)}</strong><span>${esc(GROUPS[d.group].label)} · true values</span><br>
      ${esc(friendlyMass(p.y + LOG_MSUN))}<br>${esc(friendlyLength(p.x + 3))} across`,
    drawLayers,
  });

  function drawLayers({ zx, zy, back, mid, front, defs, opts, selected, layer, segPath, polyPath }) {
    const angle = (a, b) => Math.atan2(zy(b.y) - zy(a.y), zx(b.x) - zx(a.x)) * 180 / Math.PI;
    if (defs.select("#st-arrow").empty()) {
      defs.append("marker").attr("id", "st-arrow").attr("viewBox", "0 0 10 10").attr("refX", 8).attr("refY", 5)
        .attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto-start-reverse")
        .append("path").attr("d", "M0,0L10,5L0,10z").attr("fill", "#ff8fe6");
    }

    // black-hole region: anything smaller than its Schwarzschild diameter
    const sA = { x: -BIG, y: -BIG - SCHW_KM }, sB = { x: BIG, y: BIG - SCHW_KM };
    const gR = layer(back, "bh");
    gR.selectAll("path.region").data([0]).join("path").attr("class", "region")
      .attr("d", polyPath([sA, sB, { x: -BIG, y: BIG }])).attr("fill", "rgba(255,91,214,.12)");
    gR.selectAll("path.edge").data([0]).join("path").attr("class", "edge").attr("d", segPath(sA, sB))
      .attr("stroke", "#ff5bd6").attr("stroke-width", 2).attr("fill", "none");
    const lblAt = { x: 3.4, y: 3.4 - SCHW_KM };
    gR.selectAll("text").data(["Black holes · Schwarzschild radius"]).join("text").attr("class", "line-label").attr("fill", "#ff5bd6")
      .attr("text-anchor", "middle")
      .attr("transform", `translate(${zx(lblAt.x)},${zy(lblAt.y)}) rotate(${angle(sA, sB)}) translate(0,-8)`).text((d) => d);

    // main-sequence band
    const gMS = layer(back, "ms");
    const msPath = segPath(msBand.a, msBand.b);
    gMS.selectAll("path").data([0]).join("path").attr("class", "ms-band").attr("d", msPath)
      .on("click", (e) => { e.stopPropagation(); onSelect(byId.main_sequence.key, { focus: false }); });
    const mA = msBand.a, mB = msBand.b;
    gMS.selectAll("text").data(["Main sequence"]).join("text").attr("class", "layer-label").attr("fill", "#ffd98a")
      .attr("text-anchor", "middle")
      .attr("transform", `translate(${(zx(mA.x) + zx(mB.x)) / 2},${(zy(mA.y) + zy(mB.y)) / 2}) rotate(${angle(mA, mB)}) translate(0,16)`)
      .text((d) => d);

    // water-density line
    const gW = layer(mid, "water", opts.water);
    const wA = { x: -10, y: -30 + WATER }, wB = { x: 20, y: 60 + WATER };
    gW.selectAll("path").data([0]).join("path").attr("class", "density").attr("d", segPath(wA, wB));
    const wl = { x: 6.6, y: 3 * 6.6 + WATER };
    gW.selectAll("text").data(["Water density"]).join("text").attr("class", "density-label").attr("text-anchor", "middle")
      .attr("transform", `translate(${zx(wl.x)},${zy(wl.y)}) rotate(${angle(wA, wB)}) translate(0,-5)`).text((d) => d);

    // mass limits
    const eq = stellar.equations;
    const gL = layer(mid, "limits", opts.limits);
    const [t0, t1] = eq.tov_limit_msun.map(Math.log10);
    const xr = zx.range();
    gL.selectAll("rect").data([0]).join("rect").attr("x", xr[0]).attr("width", xr[1] - xr[0])
      .attr("y", zy(t1)).attr("height", Math.max(1, zy(t0) - zy(t1))).attr("fill", "rgba(255,194,74,.16)");
    const ch = Math.log10(eq.chandrasekhar_limit_msun);
    gL.selectAll("line").data([0]).join("line").attr("x1", xr[0]).attr("x2", xr[1]).attr("y1", zy(ch)).attr("y2", zy(ch))
      .attr("stroke", "#ffc24a").attr("stroke-dasharray", "6 5");
    gL.selectAll("text").data([
      { t: "TOV limit · max neutron star", y: zy(t1) - 5 },
      { t: "Chandrasekhar limit · max white dwarf", y: zy(ch) + 14 },
    ]).join("text").attr("class", "layer-label").attr("fill", "#ffc24a").attr("x", xr[0] + 8).attr("text-anchor", "start")
      .attr("y", (d) => d.y).text((d) => d.t);

    // evolution arrows between objects
    const gA = layer(front, "arrows", opts.arrows);
    const arrows = stellar.transitions.map((t) => {
      const a = anchor(byId[t.from]), b = anchor(byId[t.to]);
      return a && b ? { ...t, a, b } : null;
    }).filter(Boolean);
    const curve = (d) => {
      const x1 = zx(d.a.x), y1 = zy(d.a.y), x2 = zx(d.b.x), y2 = zy(d.b.y);
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, dx = x2 - x1, dy = y2 - y1;
      const bend = 0.18;
      return { d: `M${x1},${y1}Q${mx - dy * bend},${my + dx * bend} ${x2},${y2}`, lx: mx - dy * bend / 2, ly: my + dx * bend / 2 };
    };
    const involved = (d) => selected && (selected.endsWith(`:${d.from}`) || selected.endsWith(`:${d.to}`));
    gA.selectAll("path").data(arrows, (d) => d.id).join("path").attr("class", (d) => `arrow ${involved(d) ? "hot" : ""}`)
      .attr("d", (d) => curve(d).d).attr("marker-end", "url(#st-arrow)");
    gA.selectAll("text").data(arrows.filter((d) => d.printed_label), (d) => d.id).join("text").attr("class", "arrow-label")
      .attr("x", (d) => curve(d).lx).attr("y", (d) => curve(d).ly - 6).attr("text-anchor", "middle")
      .text((d) => d.printed_label.replace(/\.+$/, "").toLowerCase());
  }

  return chart;
}
