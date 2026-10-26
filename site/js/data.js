// Loads ../data/*.json and flattens everything into one list of "items" the views share.
// Each item lists the views it appears in; positions are log10 values (w = width in m, m = mass in kg).
// Anything whose width follows from its mass (black holes, particles) is computed here with the same
// constants the chart uses for its walls, so it sits exactly on them at any zoom.
import { friendlyTime } from "./format.js";

export const GROUPS = {
  cosmic: { label: "Universe & galaxies", color: "#8fa8ff" },
  blackhole: { label: "Black holes", color: "#ff5bd6" },
  star: { label: "Stars & remnants", color: "#ffc24a" },
  planet: { label: "Planets & moons", color: "#3fd6c6" },
  human: { label: "Human-made", color: "#f4a261" },
  life: { label: "Life", color: "#7ee081" },
  chemistry: { label: "Atoms & molecules", color: "#c792ea" },
  particle: { label: "Particles", color: "#4abdff" },
  hypothetical: { label: "Hypothetical", color: "#b4b1c4" },
  time: { label: "Timeline", color: "#ff7a6b" },
  boundary: { label: "Boundaries", color: "#ffc24a" },
  erratum: { label: "Poster errors", color: "#ff3b3b" },
};

const CATEGORY_GROUP = {
  cosmic_structure: "cosmic", galaxy: "cosmic", star_cluster: "cosmic",
  black_hole: "blackhole",
  star: "star", stellar_remnant: "star", substellar: "star",
  planet: "planet", dwarf_planet: "planet", moon: "planet", asteroid: "planet",
  human_made: "human", everyday_object: "human",
  life: "life", cell: "life", microbe: "life",
  molecule: "chemistry", atom: "chemistry",
  particle: "particle", hypothetical: "hypothetical",
};

const LP_GROUP = {
  main_sequence_stars: "star", red_giants: "star", flea: "life", three_kelvin_bh: "blackhole",
  quantum_gravity_point: "hypothetical", visible_photons: "particle",
};

const ERRATUM_VIEW = {
  particle_legend_swap: "particles", neutrino_masses: "particles", stellar_inset_diameters: "stars",
  era_brackets: "timeline", time_marker_spacing: "timeline", density_ruler_labels: "timeline",
};

// lineweaver_patel.json same_as datasets -> item key prefixes
const SAME_AS_PREFIX = {
  objects: "object", stellar_evolution: "stellar", fundamental_particles: "particle", "main_chart.physics.horizons": "boundary",
};
const TYPE_LABEL = {
  object: "Object", stellar: "Stellar evolution", particle: "Particle", element: "Element", molecule: "Molecule",
  lp: "Lineweaver & Patel",
  time: "Moment", era: "Era", erratum: "Poster error", boundary: "Boundary",
};

async function getJSON(name) {
  const res = await fetch(`../data/${name}`);
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  return res.json();
}

const pos = (w, m) => (w == null || m == null ? null : { w, m });

export async function loadData() {
  const [objects, main, stellar, particles, timeline, lp, errata, elements, molecules] = await Promise.all([
    getJSON("objects.json"), getJSON("main_chart.json"), getJSON("stellar_evolution.json"),
    getJSON("fundamental_particles.json"), getJSON("cosmic_timeline.json"), getJSON("lineweaver_patel.json"),
    getJSON("errata.json"), getJSON("elements.json"), getJSON("molecules.json"),
  ]);
  const L = main.physics.lines;
  const LOG_MSUN = Math.log10(main.physics.constants_si.M_sun);
  const realFromReference = (ref) => {
    if (!ref || ref.log10_mass_kg == null) return null;
    const m = ref.log10_mass_kg;
    if (ref.width_basis === "schwarzschild_diameter") return pos(m - L.schwarzschild_offset, m);
    if (ref.width_basis === "reduced_compton_wavelength") return pos(L.compton_offset - m, m);
    if (ref.width_basis === "particle_horizon_diameter") return pos(L.particle_horizon_diameter_log10_m, m);
    return pos(ref.log10_width_m, m);
  };

  const items = [];
  const add = (it) => {
    it.typeLabel = TYPE_LABEL[it.type];
    it.color = GROUPS[it.group].color;
    it.search = [it.name, it.printed, it.id, it.symbol, it.categoryLabel, GROUPS[it.group].label, it.typeLabel]
      .filter(Boolean).join(" ").toLowerCase();
    items.push(it);
  };

  for (const o of objects.objects) {
    const ref = o.reference;
    add({
      key: `object:${o.id}`, type: "object", id: o.id, name: o.name, printed: o.printed_label,
      group: o.category === "hypothetical" ? "hypothetical" : CATEGORY_GROUP[o.category],
      categoryLabel: main.categories[o.category], hypothetical: o.hypothetical, views: ["triangle"],
      real: realFromReference(ref),
      drawn: pos(o.chart.log10_width_m, o.chart.log10_mass_kg),
      schematic: o.chart.position_is_schematic, raw: o,
    });
  }

  for (const s of stellar.objects) {
    const r = s.reference;
    add({
      key: `stellar:${s.id}`, type: "stellar", id: s.id, name: s.name, printed: s.printed_label,
      group: CATEGORY_GROUP[s.category], categoryLabel: main.categories[s.category],
      views: s.main_chart_object_id ? ["stars"] : ["stars", "triangle"],
      real: r.log10_mass_msun != null && r.log10_diameter_km != null
        ? pos(r.log10_diameter_km + 3, r.log10_mass_msun + LOG_MSUN) : null,
      drawn: pos(s.chart.log10_diameter_km + 3, s.chart.log10_mass_msun + LOG_MSUN),
      // only stars the main triangle doesn't already show get their own dot there
      mainId: s.main_chart_object_id, raw: s,
    });
  }

  for (const p of particles.particles) {
    const r = p.reference;
    add({
      key: `particle:${p.id}`, type: "particle", id: p.id, name: p.name, printed: p.printed_label,
      group: "particle", categoryLabel: `${p.class[0].toUpperCase()}${p.class.slice(1)}`,
      views: ["particles", "triangle"],
      real: r.mass_eV > 0
        ? pos(L.compton_offset - (r.log10_mass_eV - L.energy_log10_eV_per_kg), r.log10_mass_eV - L.energy_log10_eV_per_kg) : null,
      drawn: pos(p.chart.log10_wavelength_m, p.chart.log10_mass_eV - L.energy_log10_eV_per_kg),
      raw: p,
    });
  }

  // the 118 elements: one item each, except where a main-chart atom already is it (folded in below)
  for (const e of elements.elements) {
    if (e.same_as) continue;
    const r = e.reference;
    add({
      key: `element:${e.id}`, type: "element", id: e.id, name: e.name, symbol: e.symbol,
      group: "chemistry", categoryLabel: e.kind, views: ["triangle"],
      real: pos(r.log10_width_m, r.log10_mass_kg), raw: e,
    });
  }

  // molecules: a curated set between the atoms and the viruses (searchable by formula, too)
  for (const mol of molecules.molecules) {
    const r = mol.reference;
    add({
      key: `molecule:${mol.id}`, type: "molecule", id: mol.id, name: mol.name, symbol: mol.formula,
      group: "chemistry", categoryLabel: mol.kind, views: ["triangle"],
      real: pos(r.log10_width_m, r.log10_mass_kg), raw: mol,
    });
  }

  // Lineweaver & Patel points: only those nothing else in the data stands for become items (the rest fold in below)
  const objectGroup = Object.fromEntries(items.filter((i) => i.type === "object").map((i) => [i.id, i.group]));
  for (const o of lp.objects) {
    if (o.same_as) continue;
    add({
      key: `lp:${o.id}`, type: "lp", id: o.id, name: o.name, printed: o.printed_label,
      group: objectGroup[o.main_chart_object_id] ?? LP_GROUP[o.id] ?? "cosmic",
      categoryLabel: "Lineweaver & Patel chart", views: ["triangle"],
      lp: pos(o.plotted.log10_width_m, o.plotted.log10_mass_kg), mainId: o.main_chart_object_id, raw: o,
    });
  }

  // the two cosmic horizons, drawn as vertical lines on the triangle; clicking a line selects its item
  const universe = objects.objects.find((o) => o.id === "observable_universe")?.reference;
  for (const h of main.physics.horizons) {
    const w = h.log10_diameter_m;
    add({
      key: `boundary:${h.id}`, type: "boundary", id: h.id, name: h.name, group: "boundary",
      categoryLabel: "Cosmic horizon", views: ["triangle"], raw: h,
      focusAt: h.id === "hubble_radius" ? pos(w, w + L.schwarzschild_offset) : pos(w, universe?.log10_mass_kg ?? w + L.schwarzschild_offset),
    });
  }

  for (const t of timeline.markers) {
    add({
      key: `time:${t.id}`, type: "time", id: t.id, name: t.seconds < 1 ? friendlyTime(t.seconds) : t.printed_text ?? friendlyTime(t.seconds),
      printed: t.printed_value ? `${t.printed_value}${t.printed_text ? ` · ${t.printed_text}` : ""}` : t.printed_text,
      group: "time", categoryLabel: "Time marker", views: ["timeline"], raw: t,
    });
  }
  for (const e of timeline.eras) {
    add({
      key: `era:${e.id}`, type: "era", id: e.id, name: titleCase(e.printed_label), printed: e.printed_label,
      group: "time", categoryLabel: "Era", hypothetical: e.hypothetical,
      views: ["timeline"], raw: e,
    });
  }
  for (const e of errata.errata) {
    add({
      key: `erratum:${e.id}`, type: "erratum", id: e.id, name: errataTitle(e), printed: e.where,
      group: "erratum", categoryLabel: "Poster error", views: [], relatedView: ERRATUM_VIEW[e.id] ?? "triangle", raw: e,
    });
  }

  const byKey = new Map(items.map((i) => [i.key, i]));
  // elements whose atom is already a main-chart object (oxygen, helium) become that object's element facts
  for (const e of elements.elements) {
    const target = e.same_as && byKey.get(`${SAME_AS_PREFIX[e.same_as.dataset]}:${e.same_as.id}`);
    if (!target) continue;
    target.element = e;
    target.symbol = e.symbol;
    target.search += ` ${e.name} ${e.symbol}`.toLowerCase();
    byKey.set(`element:${e.id}`, target);
  }
  // the other Lineweaver & Patel points join the item that already stands for them: their reading shows in its
  // details, and lp: links lead to it. (The Planck point is the Big Bang corner, which isn't an item.)
  for (const o of lp.objects) {
    const prefix = o.same_as && SAME_AS_PREFIX[o.same_as.dataset];
    const target = prefix && byKey.get(`${prefix}:${o.same_as.id}`);
    if (!target) continue;
    target.lpPoint = o;
    byKey.set(`lp:${o.id}`, target);
  }
  // back-links: main object -> inset / source-chart entries that depict it
  for (const it of items) {
    if (it.mainId && byKey.has(`object:${it.mainId}`)) {
      const target = byKey.get(`object:${it.mainId}`);
      (target.backlinks ??= []).push(it.key);
    }
  }

  const tour = items
    .filter((i) => i.type === "object" && i.raw.labeled_on_chart && !i.hypothetical && i.id !== "deimos")
    .sort((a, b) => a.raw.chart.log10_mass_kg - b.raw.chart.log10_mass_kg)
    .map((i) => i.key);

  return { items, byKey, tour, main, stellar, particles, timeline, lp, errata, elements, molecules };
}

function titleCase(s) {
  return s.replace(/\*$/, "").toLowerCase().replace(/\b(gut)\b/g, "GUT").replace(/(^|\s)\S/g, (c) => c.toUpperCase());
}

function errataTitle(e) {
  return {
    mass_axis_labels: "Mislabelled mass axis",
    particle_legend_swap: "Particle legend swapped",
    density_ruler_labels: "Density ruler labels",
    stellar_inset_diameters: "Inset diameters too large",
    width_label_10pm: "'10 pm' on the wrong tick",
    inch_and_light_second: "Inch & light-second misplaced",
    water_temperatures: "Water temperatures spread out",
    energy_axis_offset: "Energy axis offset",
    era_brackets: "Era brackets too wide",
    spelling: "Spelling & names",
    neutrino_masses: "Outdated neutrino masses",
    time_marker_spacing: "Time markers off-scale",
    pbh_inside_horizon: "Primordial black hole drawn too dense",
    dark_matter_boxes: "Dark-matter boxes approximate",
  }[e.id] ?? e.id;
}
