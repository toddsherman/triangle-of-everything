// The main triangle: log width (m) vs log mass (kg), drawn from the datasets and physics.
// Every wall and line uses the exact offsets in main_chart.json -> physics, the same numbers the data layer
// uses to place black holes and particles, so anything that belongs on a line sits on it at any zoom.

import { createChart, clipSegment } from "./chart.js";
import { GROUPS } from "./data.js";
import { esc, friendlyMass, friendlyLength, friendlyTime } from "./format.js";

const BIG = 400;     // "far away" in decades; lines are clipped to the view before drawing

const BAND_NAMES = {
  gamma_ray: "gamma rays", x_ray: "X-rays", ultraviolet: "ultraviolet", visible_light: "visible light",
  infrared: "infrared", microwaves: "microwaves", radio_waves: "radio waves",
};

const PHOTON_COLOURS = {
  gamma_ray: "#d0a2ff", x_ray: "#8fa8ff", ultraviolet: "#9b7bff", visible_light: "#ffffff",
  infrared: "#ff6b6b", microwaves: "#ffa94d", radio_waves: "#ffd43b",
};

export const TRIANGLE_LAYERS = [
  { id: "density", label: "Density lines", on: true, color: "#9fd3ff" },
  { id: "time", label: "Time since the Big Bang", on: true, color: "#ff7a6b" },
  { id: "blackholes", label: "Black-hole classes", on: true, color: "#ff5bd6" },
  { id: "photons", label: "Light spectrum", on: true, color: "#ffd43b" },
  { id: "darkmatter", label: "Dark-matter windows*", on: true, color: "#c9b3ff" },
  { id: "insets", label: "Stars & particles zoom boxes", on: true, color: "#ff4757" },
  { id: "refs", label: "Reference scales (kg, AU, ly…)", on: true, color: "#ece8f4" },
  { id: "energy", label: "Energy & temperature axis", on: true, color: "#ffc24a" },
  { id: "lp", label: "Lineweaver & Patel extras", on: true, color: "#b4b1c4" },
  { id: "labels", label: "Labels", on: true, color: "#ece8f4" },
];

export function createTriangle({ svgEl, tooltipEl, data, onSelect, onOpenView, onUserZoom }) {
  const items = data.items.filter((i) => i.views.includes("triangle"));
  const { main, timeline } = data;
  const L = main.physics.lines;
  const SCHW = L.schwarzschild_offset;          // black holes:   M = W + SCHW
  const COMP = L.compton_offset;                // quantum limit: M = -W + COMP
  const PHOTON = L.photon_offset;               // photons:       M = -W + PHOTON
  const SPHERE = L.sphere_volume_log10;         // M = 3W + log rho + SPHERE
  const HUB = L.hubble_diameter_log10_m;
  const HORIZON = L.particle_horizon_diameter_log10_m;   // edge of the observable universe
  const P = { x: (COMP - SCHW) / 2, y: (COMP + SCHW) / 2 };   // Big Bang apex: the two walls cross
  // the Hubble wall (and so the top and bottom corners) move with cosmic time; see corners() below

  // the observable universe sits on its own edge (the dashed line), the one thing allowed past the Hubble wall
  const onHorizon = (it) => it.raw?.reference?.width_basis === "particle_horizon_diameter";
  /** Does this item exist at the moment shown, inside the wall that bounds it? */
  const visibleAt = (it, p, moment) => {
    if (!moment) return true;
    if (it.appearU == null || it.appearU > moment.u + 1e-9) return false;         // doesn't exist yet
    return p.w <= (onHorizon(it) ? moment.horizon : moment.hub) + 1e-9;           // beyond the Hubble wall then
  };

  // zoom boxes: bounding boxes of the stars (not the planets) and particles the two detail views hold
  const bbox = (its, pad) => ({
    items: its,
    a: { x: Math.min(...its.map((i) => i.real.w)) - pad, y: Math.max(...its.map((i) => i.real.m)) + pad },
    b: { x: Math.max(...its.map((i) => i.real.w)) + pad, y: Math.min(...its.map((i) => i.real.m)) - pad },
  });
  const STARLIKE = new Set(["star", "stellar_remnant", "substellar", "black_hole"]);
  const zoomBoxes = [
    { view: "stars", ...bbox(data.items.filter((i) => i.type === "stellar" && i.real && STARLIKE.has(i.raw.category)), 0.6) },
    { view: "particles", ...bbox(data.items.filter((i) => i.type === "particle" && i.real), 0.6) },
  ];
  // a few elements everyone knows get first claim on label space among the 118
  const FAMILIAR = new Set(["hydrogen", "carbon", "nitrogen", "iron", "gold", "uranium"]);

  const position = (it, opts) => {
    if (it.type === "boundary") return null;            // drawn as lines, not dots
    // Lineweaver & Patel points only with their layer
    const p = it.type === "lp" ? (opts.lp ? it.lp : null) : it.real;
    if (!p || !visibleAt(it, p, opts.moment)) return null;
    return { x: p.w, y: p.m };
  };

  const chart = createChart({
    svgEl, tooltipEl, items, onSelect, onUserZoom,
    home: { x: [-38, 31], y: [-72, 58] },
    xTitle: "Width (metres)", yTitle: "Mass (kilograms)",
    rightAxis: { title: "Energy (electronvolts)", offset: L.energy_log10_eV_per_kg, option: "energy" },
    options: Object.fromEntries(TRIANGLE_LAYERS.map((l) => [l.id, l.on])),
    position,
    priority: (it) => ({ object: it.raw?.labeled_on_chart ? 100 : 40, particle: 70, stellar: 60, lp: 5,
      element: FAMILIAR.has(it.id) ? 30 : 10 }[it.type] ?? 0) - (it.hypothetical ? 30 : 0),
    // atoms (including the poster's oxygen and helium) are small dots, like the other elements
    radius: (it) => (it.type === "element" || it.element || it.type === "lp" ? 3.5 : it.type === "object" ? 5.5 : 4.5),
    pointClass: (it) => `${it.type === "lp" ? "lp" : ""} ${it.hypothetical && it.type !== "lp" ? "hyp" : ""}`,
    tooltip: (d, p) => {
      const where = d.type === "lp" ? `Lineweaver & Patel · ${d.raw.plotted.basis.replaceAll("_", " ")}` : "true values";
      return `<strong>${esc(d.name)}</strong><span>${esc(GROUPS[d.group].label)} · ${esc(where)}</span><br>
        ${esc(friendlyMass(p.y))}<br>${esc(friendlyLength(p.x))} across`;
    },
    // horizons: zoom in far enough that the Hubble wall and the dashed edge separate; anything not shown at
    // this moment still gets a place to look
    focusPoint: (it) => (it.focusAt ? { x: it.focusAt.w, y: it.focusAt.m, k: 16 } : it.real ? { x: it.real.w, y: it.real.m } : null),
    drawLayers,
  });

  /** The walls at a moment: today by default, or the cosmic-time state being shown. */
  function corners(time) {
    const hub = time ? time.hub : HUB, horizon = time ? time.horizon : HORIZON;
    return { hub, horizon, T: { x: hub, y: hub + SCHW }, B: { x: hub, y: COMP - hub } };
  }

  function drawLayers({ zx, zy, back, mid, front, defs, opts, selected, plot, layer, segPath, polyPath }) {
    // opts.moment: the cosmic-time state being shown (null = today); opts.time is the time-lines layer toggle
    const { hub, horizon, T, B } = corners(opts.moment);
    const past = opts.moment && !opts.moment.isNow;
    // cosmic-time mode: layers show a kind of thing only once it exists, and nothing beyond the Hubble wall
    const tNow = past ? opts.moment.t : null;                           // seconds after the Big Bang (null = today)
    const exists = (fa) => tNow == null || !fa || tNow >= fa.seconds_after_big_bang;
    const inside = { x0: -BIG, x1: hub, y0: -3 * BIG, y1: 3 * BIG };
    const clipIn = (a, b) => { const c = clipSegment(a, b, inside); return c ? { a: c[0], b: c[1] } : null; };
    const angle = (a, b) => Math.atan2(zy(b.y) - zy(a.y), zx(b.x) - zx(a.x)) * 180 / Math.PI;
    const fits = (a, b, text) => Math.hypot(zx(b.x) - zx(a.x), zy(b.y) - zy(a.y)) > text.length * 6.6 + 12;
    const tri = polyPath([P, T, B]);
    const midY = plot.y0 + (plot.y1 - plot.y0) * 0.72;   // vertical-line labels sit below centre, clear of focused dots
    const along = (a, b, t) => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });

    let triClip = defs.select("#tri-clip path");
    if (triClip.empty()) triClip = defs.append("clipPath").attr("id", "tri-clip").append("path");
    triClip.attr("d", tri || "M0,0");
    if (defs.select("#tri-grad").empty()) {
      const g = defs.append("linearGradient").attr("id", "tri-grad").attr("gradientUnits", "userSpaceOnUse");
      g.append("stop").attr("offset", "0%").attr("stop-color", "#2a1550");
      g.append("stop").attr("offset", "100%").attr("stop-color", "#16244a");
    }
    // the gradient follows the true triangle corners, not the clipped shape, so colours don't shift while zooming
    defs.select("#tri-grad").attr("x1", zx(P.x)).attr("y1", zy(B.y)).attr("x2", zx(T.x)).attr("y2", zy(T.y));

    // --- forbidden regions and the allowed triangle
    const regions = [
      { id: "tri", d: tri, fill: "url(#tri-grad)" },
      { id: "gravity", d: polyPath([P, { x: BIG, y: BIG + SCHW }, { x: BIG, y: 3 * BIG }, { x: P.x, y: 3 * BIG }]), fill: "rgba(255,91,214,.10)" },
      { id: "quantum", d: polyPath([P, { x: BIG, y: COMP - BIG }, { x: BIG, y: -3 * BIG }, { x: P.x, y: -3 * BIG }]), fill: "rgba(74,189,255,.10)" },
      { id: "planck", d: polyPath([{ x: -BIG, y: -3 * BIG }, { x: P.x, y: -3 * BIG }, { x: P.x, y: 3 * BIG }, { x: -BIG, y: 3 * BIG }]), fill: "rgba(0,0,0,.45)" },
      { id: "beyond", d: polyPath([T, { x: BIG, y: BIG + SCHW }, { x: BIG, y: COMP - BIG }, B]), fill: "rgba(255,194,74,.06)" },
    ];
    const gR = layer(back, "regions");
    gR.selectAll("path").data(regions, (d) => d.id).join("path").attr("d", (d) => d.d).attr("fill", (d) => d.fill);
    const rl = [
      { t: "Forbidden by gravity", x: -18, y: 34, a: 0 },
      { t: "Forbidden by quantum uncertainty", x: -14, y: -52, a: 0 },
      { t: "Sub-Planckian", x: P.x - 1.2, y: 14, a: -90 },
      { t: "Beyond the Hubble radius", x: hub + 1.6, y: -8, a: 90 },
    ];
    gR.selectAll("text").data(rl).join("text").attr("class", "region-label").attr("text-anchor", "middle")
      .attr("transform", (d) => `translate(${zx(d.x)},${zy(d.y)}) rotate(${d.a})`).text((d) => d.t);

    // --- density lines: a sphere of width W at density rho has M = 3W + log rho + log(pi/6)
    const densityLine = (logRho) => {
      const c = logRho + SPHERE;
      const w0 = (COMP - c) / 4, w1 = (SCHW - c) / 2;     // where it meets the Compton and Schwarzschild walls
      return { c, w0, w1, at: (w) => ({ x: w, y: 3 * w + c }) };
    };
    const gD = layer(mid, "density", opts.density).attr("clip-path", "url(#tri-clip)");
    const dens = main.physics.densities.map((d) => {
      const Ld = densityLine(d.log10_kg_m3);
      return { ...d, ...Ld, a: Ld.at(Ld.w0 - 5), b: Ld.at(Ld.w1 + 5), lp: Ld.at(Ld.w0 + (Ld.w1 - Ld.w0) * 0.62) };
    });
    gD.selectAll("path").data(dens, (d) => d.id).join("path").attr("class", "density").attr("d", (d) => segPath(d.a, d.b));
    gD.selectAll("text").data(dens, (d) => d.id).join("text").attr("class", "density-label").attr("text-anchor", "middle")
      .attr("transform", (d) => `translate(${zx(d.lp.x)},${zy(d.lp.y)}) rotate(${angle(d.a, d.b)}) translate(0,-5)`)
      .text((d) => d.name);

    // --- time lines: the universe's mean density at each moment (LambdaCDM). Each meets the black-hole wall
    //     at the Hubble sphere of that moment.
    const gT = layer(mid, "time", opts.time);
    const times = timeline.markers.filter((m) => !past || m.seconds <= tNow).map((m) => {
      const Ld = densityLine(m.density_log10_kg_m3);
      return { ...m, ...Ld, from: Ld.at(Ld.w0), hz: Ld.at(Ld.w1) };
    });
    gT.selectAll("path").data(times, (d) => d.id).join("path").attr("class", "timeline").attr("d", (d) => segPath(d.from, d.hz));
    gT.selectAll("circle").data(times, (d) => d.id).join("circle").attr("r", 4).attr("fill", "#ff7a6b")
      .attr("cx", (d) => zx(d.hz.x)).attr("cy", (d) => zy(d.hz.y));
    // stack labels whose dots coincide (the far-future moments share the de Sitter horizon)
    const used = [];
    const timeLabels = times.map((d) => {
      const x = zx(d.hz.x) - 8;
      let y = zy(d.hz.y) - 6;
      while (used.some((u) => Math.abs(u.x - x) < 120 && Math.abs(u.y - y) < 13)) y -= 14;
      used.push({ x, y });
      return { ...d, lx: x, ly: y };
    });
    gT.selectAll("text").data(timeLabels, (d) => d.id).join("text").attr("class", "time-label")
      .attr("x", (d) => d.lx).attr("y", (d) => d.ly).attr("text-anchor", "end")
      .text((d) => (d.seconds < 1 ? friendlyTime(d.seconds) : d.printed_text ?? friendlyTime(d.seconds)));   // units, not exponents

    // --- cosmic-time mode: the universe's mean density at this moment, drawn up to the Hubble corner
    const gNow = layer(mid, "cosmic-now", past);
    const nowLine = past ? densityLine(opts.moment.rho) : null;
    gNow.selectAll("path").data(past ? [0] : []).join("path").attr("class", "cosmic-now")
      .attr("d", () => segPath(nowLine.at(nowLine.w0), nowLine.at(nowLine.w1)));

    // --- the three walls
    const edges = [
      { id: "schw", a: P, b: { x: BIG, y: BIG + SCHW }, c: "#ff5bd6", t: "Schwarzschild radius", at: { x: -22, y: -22 + SCHW }, off: 16 },   // inside the wall, clear of the bands
      { id: "comp", a: P, b: { x: BIG, y: COMP - BIG }, c: "#4abdff", t: "Compton limit", at: { x: -16, y: COMP + 16 } },
      { id: "hub", a: { x: hub, y: BIG }, b: { x: hub, y: -BIG }, c: "#ffc24a", t: "Hubble radius", at: { x: hub, y: 20 } },
    ];
    const gE = layer(mid, "edges");
    gE.selectAll("path").data(edges, (d) => d.id).join("path").attr("d", (d) => segPath(d.a, d.b))
      .attr("stroke", (d) => d.c).attr("stroke-width", 2).attr("fill", "none");
    gE.selectAll("text").data(edges, (d) => d.id).join("text").attr("class", "line-label").attr("fill", (d) => d.c)
      .attr("text-anchor", "middle")
      // vertical walls keep their label at the middle of the visible plot so it never scrolls away
      .attr("transform", (d) => (d.id === "hub"
        ? `translate(${zx(d.at.x)},${midY}) rotate(-90) translate(0,14)`
        : `translate(${zx(d.at.x)},${zy(d.at.y)}) rotate(${angle(d.a, d.b)}) translate(0,${d.off ?? -8})`))
      .text((d) => d.t);

    // --- the two cosmic horizons: Hubble radius (the solid wall above) and the observable universe's edge.
    //     Both lines are clickable; a wide transparent stroke makes them easy to hit.
    const gH = layer(mid, "horizons");
    const horizons = [
      { key: "boundary:hubble_radius", x: hub, cls: "" },
      { key: "boundary:particle_horizon", x: horizon, cls: "horizon-line" },
    ].map((h) => ({ ...h, d: segPath({ x: h.x, y: BIG }, { x: h.x, y: -BIG }), on: selected === h.key }));
    gH.selectAll("path.horizon-line").data(horizons.filter((h) => h.cls), (d) => d.key).join("path")
      .attr("class", (d) => `horizon-line ${d.on ? "selected" : ""}`).attr("d", (d) => d.d);
    gH.selectAll("path.hit").data(horizons, (d) => d.key).join("path").attr("class", "hit").attr("d", (d) => d.d)
      .on("click", (e, d) => { e.stopPropagation(); onSelect(d.key, { focus: false }); });
    gE.selectAll("path").classed("selected", (d) => d.id === "hub" && selected === "boundary:hubble_radius");
    // label the dashed line only once it has pulled far enough away from the Hubble wall to read
    const roomy = zx(horizon) - zx(hub) > 30;
    gH.selectAll("text").data(roomy ? [0] : []).join("text").attr("class", "line-label horizon-label")
      .attr("text-anchor", "middle").attr("transform", `translate(${zx(horizon)},${midY}) rotate(-90) translate(0,16)`)
      .text("Observable universe edge");

    // --- black-hole classes: bands lying exactly on the Schwarzschild wall
    const gBH = layer(mid, "bh", opts.blackholes);
    const { G, c: LIGHT } = main.physics.constants_si;
    const bh = main.regions.filter((r) => r.kind === "bracket_along_schwarzschild_line").flatMap((r) => {
      if (!exists(r.first_appeared)) return [];
      let [lo, hi] = r.reference_log10_mass_kg_range;
      // primordial black holes form with about the mass inside the horizon (c^3 t / G), so the band grows
      if (tNow != null && r.id === "black_holes_primordial") hi = Math.min(hi, Math.log10(LIGHT ** 3 * tNow / G));
      const seg = hi > lo ? clipIn({ x: lo - SCHW, y: lo }, { x: hi - SCHW, y: hi }) : null;
      return seg ? [{ ...r, ...seg }] : [];
    });
    gBH.selectAll("path").data(bh, (d) => d.id).join("path").attr("class", (d) => `bh-band ${d.hypothetical ? "hyp" : ""}`)
      .attr("d", (d) => segPath(d.a, d.b));
    gBH.selectAll("text").data(bh, (d) => d.id).join("text").attr("class", "layer-label").attr("fill", "#ff9fe6")
      .attr("text-anchor", "middle")
      .attr("transform", (d) => { const m = along(d.a, d.b, 0.5); return `translate(${zx(m.x)},${zy(m.y)}) rotate(${angle(d.a, d.b)}) translate(0,-16)`; })
      .text((d) => {
        const t = d.printed_label.replace("SUPER MASSIVE", "Supermassive").replace("STELLAR MASS", "Stellar-mass")
          .replace("PRIMORDIAL", "Primordial").replace("BLACK HOLES", "black holes");
        return fits(d.a, d.b, t) ? t : "";
      });

    // --- the electromagnetic spectrum: a photon of wavelength W has mass-equivalent h/(lambda c)
    const gP = layer(mid, "photons", opts.photons);
    const photonRegion = main.regions.find((r) => r.id === "energy_states_of_photon");
    const photonsExist = exists(photonRegion.first_appeared);
    const spectrum = !photonsExist ? [] : photonRegion.bands.flatMap((b) => {
      const [lo, hi] = b.reference_wavelength_m;
      const w0 = lo == null ? -16 : Math.log10(lo), w1 = hi == null ? 4 : Math.log10(hi);
      const seg = clipIn({ x: w0, y: PHOTON - w0 }, { x: w1, y: PHOTON - w1 });   // no wavelength wider than the Hubble sphere
      return seg ? [{ ...b, ...seg }] : [];
    });
    gP.selectAll("path").data(spectrum, (d) => d.id).join("path").attr("class", "photon-band")
      .attr("stroke", (d) => PHOTON_COLOURS[d.id]).attr("d", (d) => segPath(d.a, d.b));
    gP.selectAll("text").data(spectrum, (d) => d.id).join("text").attr("class", "layer-label").attr("text-anchor", "middle")
      .attr("fill", (d) => PHOTON_COLOURS[d.id])
      .attr("transform", (d) => { const m = along(d.a, d.b, 0.5); return `translate(${zx(m.x)},${zy(m.y)}) rotate(${angle(d.a, d.b)}) translate(0,-9)`; })
      .text((d) => {
        const t = d.printed_label.toLowerCase().replace(/(^|\s)\S/g, (c) => c.toUpperCase());
        return fits(d.a, d.b, t) ? t : "";
      });

    // --- the peak of the universe's background light (Wien's law: lambda = b / T), sliding down the photon
    //     line as the universe cools: gamma rays early on, near-infrared at recombination, microwaves today
    const tempK = past ? 10 ** opts.moment.temp : main.physics.constants_si.T_cmb_K;
    const lam = Math.log10(timeline.history.wien_b_m_K / tempK);
    const band = photonRegion.bands.find(({ reference_wavelength_m: [lo, hi] }) =>
      (lo == null || 10 ** lam >= lo) && (hi == null || 10 ** lam < hi));
    const peak = photonsExist && lam <= hub ? [{ x: lam, y: PHOTON - lam }] : [];
    const gL = layer(front, "light-peak", opts.photons);
    gL.selectAll("circle").data(peak).join("circle").attr("class", "light-peak").attr("r", 7)
      .attr("stroke", band ? PHOTON_COLOURS[band.id] : "#fff").attr("cx", (d) => zx(d.x)).attr("cy", (d) => zy(d.y));
    gL.selectAll("text").data(peak).join("text").attr("class", "line-label light-peak-label")
      .attr("x", (d) => zx(d.x) + 12).attr("y", (d) => zy(d.y) - 8)
      .text(past ? `Background light peaks here · ${BAND_NAMES[band?.id] ?? ""}` : "Cosmic microwave background (peak)");

    // --- dark matter: published macro windows on the nuclear-density line
    const gDM = layer(back, "dm", opts.darkmatter);
    const macro = main.physics.macro_dark_matter;
    const nuc = densityLine(Math.log10(macro.density_kg_m3));
    const windows = macro.windows_kg.map(([m0, m1], i) => {
      const y0 = Math.log10(m0), y1 = Math.log10(m1);
      const seg = clipIn({ x: (y0 - nuc.c) / 3, y: y0 }, { x: (y1 - nuc.c) / 3, y: y1 });
      return { id: `w${i}`, d: seg ? segPath(seg.a, seg.b) : "" };
    });
    gDM.selectAll("path").data(windows, (d) => d.id).join("path").attr("class", "dm-window").attr("d", (d) => d.d);
    const dmLabelAt = { x: (Math.log10(macro.windows_kg[0][1]) - nuc.c) / 3, y: Math.log10(macro.windows_kg[0][1]) };
    gDM.selectAll("text").data(windows[0].d ? [0] : []).join("text").attr("class", "layer-label").attr("fill", "#c9b3ff")
      .attr("x", zx(dmLabelAt.x) + 10).attr("y", zy(dmLabelAt.y) + 4)
      .text("Macro dark-matter windows* (nuclear density)");

    // --- zoom boxes that open the Stars and Particles views, once something inside them exists
    //     (cut off at the Hubble wall while the universe is still smaller than the box)
    const gZ = layer(back, "zoom", opts.insets);
    const boxes = zoomBoxes.filter((z) => z.a.x < hub && z.items.some((i) => visibleAt(i, i.real, opts.moment)))
      .map((z) => ({ ...z, b: { x: Math.min(z.b.x, hub), y: z.b.y } }));
    const gb = gZ.selectAll("g.zb").data(boxes, (d) => d.view).join((enter) => {
      const g = enter.append("g").attr("class", "zb").on("click", (e, d) => { e.stopPropagation(); onOpenView(d.view); });
      g.append("rect");
      g.append("text").attr("class", "zoom-label");
      return g;
    });
    gb.select("rect").attr("x", (d) => zx(d.a.x)).attr("y", (d) => zy(d.a.y))
      .attr("width", (d) => zx(d.b.x) - zx(d.a.x)).attr("height", (d) => zy(d.b.y) - zy(d.a.y));
    gb.select("text").attr("x", (d) => zx(d.b.x) + 6).attr("y", (d) => zy(d.a.y) + 14)
      .text((d) => `Open ${d.view[0].toUpperCase()}${d.view.slice(1)} ›`);

    // --- reference scales along the left and bottom edges
    const gRef = layer(front, "refs", opts.refs);
    let lastY = Infinity;
    const massRefs = main.reference_lines.mass.filter((r) => !r.label.includes("/c^2")).map((r) => ({ ...r, py: zy(r.true_log10_kg) }))
      .filter((r) => r.py > plot.y0 + 6 && r.py < plot.y1 - 6).sort((a, b) => b.py - a.py)
      .filter((r) => { const ok = lastY - r.py > 13; if (ok) lastY = r.py; return ok; });
    const mr = gRef.selectAll("g.mref").data(massRefs, (d) => d.label).join((e) => {
      const g = e.append("g").attr("class", "mref"); g.append("line"); g.append("text"); return g;
    });
    mr.select("line").attr("x1", plot.x0).attr("x2", plot.x0 + 8).attr("y1", (d) => d.py).attr("y2", (d) => d.py);
    mr.select("text").attr("x", plot.x0 + 11).attr("y", (d) => d.py + 4).text((d) => d.label.replace(" = 2*10^30 Kg", ""));
    let lastX = -Infinity;
    const widthRefs = main.reference_lines.width.map((r) => ({ ...r, pxx: zx(r.true_log10_m) }))
      .filter((r) => r.pxx > plot.x0 + 6 && r.pxx < plot.x1 - 6).sort((a, b) => a.pxx - b.pxx)
      .filter((r) => { const ok = r.pxx - lastX > 13; if (ok) lastX = r.pxx; return ok; });
    const wr = gRef.selectAll("g.wref").data(widthRefs, (d) => d.label).join((e) => {
      const g = e.append("g").attr("class", "wref"); g.append("line"); g.append("text"); return g;
    });
    wr.select("line").attr("x1", (d) => d.pxx).attr("x2", (d) => d.pxx).attr("y1", plot.y1).attr("y2", plot.y1 - 8);
    wr.select("text").attr("transform", (d) => `translate(${d.pxx + 4},${plot.y1 - 11}) rotate(-90)`)
      .text((d) => d.label.replace("1light", "1 light"));

    // --- energy / temperature annotations on the right edge (E = mc^2)
    const gEn = layer(front, "energy", opts.energy);
    let lastE = Infinity;
    const en = main.reference_lines.energy.filter((r) => r.true_log10_eV != null).map((r) => {
      const v = Array.isArray(r.true_log10_eV) ? (r.true_log10_eV[0] + r.true_log10_eV[1]) / 2 : r.true_log10_eV;
      return { ...r, py: zy(v - L.energy_log10_eV_per_kg) };
    }).filter((r) => r.py > plot.y0 + 6 && r.py < plot.y1 - 6).sort((a, b) => b.py - a.py)
      .filter((r) => { const ok = lastE - r.py > 13; if (ok) lastE = r.py; return ok; });
    const er = gEn.selectAll("g.eref").data(en, (d) => d.label).join((e) => {
      const g = e.append("g").attr("class", "eref"); g.append("line"); g.append("text"); return g;
    });
    er.select("line").attr("x1", plot.x1).attr("x2", plot.x1 - 8).attr("y1", (d) => d.py).attr("y2", (d) => d.py);
    er.select("text").attr("x", plot.x1 - 11).attr("y", (d) => d.py + 4).attr("text-anchor", "end")
      .text((d) => d.label.replace(" (MAXIMUM ENERGY)", "").replace("*", "").toLowerCase()
        .replace(/(^|\s)\S/g, (c) => c.toUpperCase()));

    // --- the two corners that physics pins down
    // at the very start the Hubble corner sits on the apex: one point, one label
    const meeting = past && zx(T.x) - zx(P.x) < 30;
    const cornerMarks = [
      { id: "bigbang", p: P, t: meeting ? "Big Bang · all three walls meet" : "Big Bang · Planck point", dx: 10, anchor: "start" },
      ...(meeting ? [] : [{ id: "hubble", p: T, t: past ? "Hubble sphere then" : "Hubble sphere today", dx: -10, anchor: "end" }]),
    ];
    const gPP = layer(front, "corners");
    gPP.selectAll("circle").data(cornerMarks, (d) => d.id).join("circle").attr("r", 6).attr("fill", "#fff")
      .attr("cx", (d) => zx(d.p.x)).attr("cy", (d) => zy(d.p.y));
    gPP.selectAll("text").data(cornerMarks, (d) => d.id).join("text").attr("class", "line-label").attr("fill", "#fff")
      .attr("text-anchor", (d) => d.anchor).attr("x", (d) => zx(d.p.x) + d.dx).attr("y", (d) => zy(d.p.y) + 4)
      .text((d) => d.t);
  }

  /** Show the universe at a cosmic-time state (null = today, static). follow: frame the triangle as it was. */
  function setTime(time, follow) {
    chart.setOption("moment", time, follow && !!time);
    if (!time || !follow) { if (!time) chart.redraw(); return; }
    const { hub, horizon, T, B } = corners(time);
    const span = Math.max(hub, horizon) - P.x;
    const pad = Math.max(0.8, span * 0.12);
    chart.fit([P.x - pad, Math.max(hub, horizon) + pad], [B.y - pad, T.y + pad]);
  }

  return { ...chart, setTime };
}
