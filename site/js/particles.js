// Fundamental particles as a mass ladder: one column per family, mass (eV) up the side,
// with decay and "combines into" relations drawn as arcs.

import { createChart } from "./chart.js";
import { esc, friendlyEnergy } from "./format.js";

const LOG_EV_KG = -35.749;
const MASSLESS_Y = -2;           // row for massless particles, below the 10^-1 eV tick

// x position of each particle: family column, split into sub-columns
const COLUMN = {
  up: 0.75, charm: 0.75, top: 0.75, down: 1.25, strange: 1.25, bottom: 1.25,
  electron: 2.75, muon: 2.75, tau: 2.75, electron_neutrino: 3.25, muon_neutrino: 3.25, tau_neutrino: 3.25,
  photon: 5, w_boson: 4.7, z_boson: 5.3, higgs: 5,
  proton: 6.75, neutron: 7.25, meson: 7,
};
const HEADERS = [
  { x: 1, t: "Quarks", sub: [[0.75, "up-type"], [1.25, "down-type"]] },
  { x: 3, t: "Leptons", sub: [[2.75, "charged"], [3.25, "neutrinos"]] },
  { x: 5, t: "Bosons", sub: [] },
  { x: 7, t: "Hadrons", sub: [[6.75, "baryons"], [7.25, ""]] },
];

// The poster's legend colours, attached to the right families (its legend swaps leptons and hadrons).
export const PARTICLE_CLASSES = [
  { id: "quark", label: "Quarks", color: "#ffc800" },
  { id: "lepton", label: "Leptons", color: "#4abdff" },
  { id: "boson", label: "Bosons", color: "#ff712e" },
  { id: "hadron", label: "Hadrons", color: "#70ff00" },
];
const CLASS_COLOR = Object.fromEntries(PARTICLE_CLASSES.map((c) => [c.id, c.color]));

export const PARTICLE_LAYERS = [
  { id: "relations", label: "Decays & combinations", on: true, color: "#ffc24a" },
  { id: "wimp", label: "WIMP dark matter*", on: true, color: "#c9b3ff" },
  { id: "kg", label: "Mass in kilograms", on: true, color: "#ece8f4" },
  { id: "labels", label: "Labels", on: true, color: "#ece8f4" },
];

export function createParticles({ svgEl, tooltipEl, data, onSelect }) {
  const items = data.items.filter((i) => i.views.includes("particles"));
  const { particles } = data;
  const byId = Object.fromEntries(items.map((i) => [i.id, i]));

  const position = (it) => {
    const r = it.raw.reference, x = COLUMN[it.id];
    if (r.mass_eV > 0) return { x, y: r.log10_mass_eV };
    if (r.mass_upper_limit_eV) return { x, y: Math.log10(r.mass_upper_limit_eV), marker: "limit" };
    if (r.mass_eV === 0) return { x, y: MASSLESS_Y };
    return null;
  };

  const chart = createChart({
    svgEl, tooltipEl, items, onSelect,
    home: { x: [0, 9.3], y: [-2.6, 12.6] },
    equalAspect: false, yOnly: true, xTicks: false,
    margin: { top: 88, right: 16, bottom: 74, left: 64 },   // room for column headers under the controls
    xTitle: "", yTitle: "Mass (electronvolts / c²)",
    yTickFilter: (d) => d >= -1,
    rightAxis: { title: "Mass (kilograms)", offset: LOG_EV_KG, option: "kg" },
    options: Object.fromEntries(PARTICLE_LAYERS.map((l) => [l.id, l.on])),
    position,
    priority: (it) => (it.raw.reference.generation ? 60 : 50),
    radius: () => 7,
    color: (it) => CLASS_COLOR[it.raw.class],
    tooltip: (d, p) => {
      const r = d.raw.reference;
      const m = r.mass_eV > 0 ? `${friendlyEnergy(p.y)}/c²` : p.marker === "limit" ? `less than ${friendlyEnergy(p.y)}/c²` : "massless";
      return `<strong>${esc(d.name)}</strong><span>${esc(d.categoryLabel)} · charge ${esc(r.electric_charge)} · spin ${esc(r.spin)}</span><br>${esc(m)}`;
    },
    drawLayers,
  });

  function drawLayers({ zx, zy, back, mid, outside, opts, selected, plot, layer, pos }) {
    // column guides and headers
    const gC = layer(back, "columns");
    const cols = HEADERS.map((h) => ({ ...h, x0: zx(h.x - 0.85), x1: zx(h.x + 0.85) }));
    gC.selectAll("rect").data(cols, (d) => d.t).join("rect").attr("class", "column")
      .attr("x", (d) => d.x0).attr("width", (d) => d.x1 - d.x0).attr("y", plot.y0).attr("height", plot.y1 - plot.y0);
    const gH = layer(outside, "headers");
    gH.selectAll("text.h").data(cols, (d) => d.t).join("text").attr("class", "col-header h")
      .attr("x", (d) => zx(d.x)).attr("y", plot.y0 - 26).attr("text-anchor", "middle").text((d) => d.t);
    // sub-column labels only when the columns are wide enough to hold them
    const roomy = zx(0.5) - zx(0) > 62;
    const subs = roomy ? HEADERS.flatMap((h) => h.sub.filter(([, t]) => t).map(([x, t]) => ({ x, t }))) : [];
    gH.selectAll("text.s").data(subs, (d) => d.t).join("text").attr("class", "col-sub s")
      .attr("x", (d) => zx(d.x)).attr("y", plot.y0 - 10).attr("text-anchor", "middle").text((d) => d.t);

    // massless row
    const gM = layer(back, "massless");
    const my = zy(-1.55);
    gM.selectAll("line").data([0]).join("line").attr("x1", plot.x0).attr("x2", plot.x1).attr("y1", my).attr("y2", my)
      .attr("class", "massless-line");
    gM.selectAll("text").data(["massless"]).join("text").attr("class", "layer-label").attr("fill", "#a39cb5")
      .attr("x", plot.x0 + 8).attr("y", zy(MASSLESS_Y) + 4).text((d) => d);

    // WIMP dark matter band in the hypothetical column
    const gW = layer(back, "wimp", opts.wimp);
    const wimp = particles.regions.find((r) => r.id === "wimp_dark_matter");
    const [w0, w1] = wimp.chart_log10_mass_eV_range;
    gW.selectAll("rect").data([0]).join("rect").attr("class", "wimp")
      .attr("x", zx(8.3)).attr("width", zx(8.9) - zx(8.3)).attr("y", zy(w1)).attr("height", zy(w0) - zy(w1));
    gW.selectAll("text").data(["WIMP dark matter*"]).join("text").attr("class", "layer-label").attr("fill", "#c9b3ff")
      .attr("text-anchor", "middle").attr("transform", `translate(${zx(8.6) + 4},${(zy(w0) + zy(w1)) / 2}) rotate(-90)`)
      .text((d) => d);

    // relations: faint for all, bright for the selected particle
    const gR = layer(mid, "relations", opts.relations);
    const links = [];
    for (const r of particles.relations) {
      const a = byId[r.from] && pos(byId[r.from]);
      if (!a) continue;
      for (const to of r.to) {
        const b = byId[to] && pos(byId[to]);
        if (b) links.push({ id: `${r.from}>${to}`, type: r.type, from: r.from, to, a, b });
      }
    }
    const hot = (d) => selected === `particle:${d.from}` || selected === `particle:${d.to}`;
    const arc = (d) => {
      const x1 = zx(d.a.x), y1 = zy(d.a.y), x2 = zx(d.b.x), y2 = zy(d.b.y);
      const bend = x1 === x2 ? 40 : 0.2 * Math.hypot(x2 - x1, y2 - y1);
      return `M${x1},${y1}Q${(x1 + x2) / 2 + bend},${(y1 + y2) / 2} ${x2},${y2}`;
    };
    gR.selectAll("path").data(links, (d) => d.id).join("path")
      .attr("class", (d) => `rel ${d.type} ${hot(d) ? "hot" : ""}`).attr("d", arc);
    gR.selectAll("path.hot").raise();
  }

  return chart;
}
