// Renders the sidebar details panel for any item type.

import { GROUPS } from "./data.js";
import { ELEMENT_ORIGINS } from "./elements.js";
import { esc, sci, friendlyMass, friendlyLength, friendlyEnergy, friendlyTime, compare } from "./format.js";

const LOG_MSUN = 30.2986;
const LOG_EV_KG = -35.749;

const IDENT = {
  visual: "Unlabelled on the poster",
  tentative: "Unlabelled · identity is a best guess",
  probable: "Identity inferred from the label",
  inferred: "Unlabelled · identity inferred",
};

export function renderIntro(el, data) {
  const n = (t) => data.items.filter((i) => i.type === t).length;
  el.innerHTML = `
    <div class="intro">
      <div class="kicker">Start here</div>
      <h1>Everything fits in one triangle</h1>
      <p>Plot anything by its <strong>size</strong> (across) and <strong>mass</strong> (up) and it lands inside three walls:</p>
      <p><span class="dot" style="--c:#ff5bd6"></span> <strong>Schwarzschild radius</strong>: squeeze anything smaller and it becomes a black hole.<br>
         <span class="dot" style="--c:#4abdff"></span> <strong>Compton limit</strong>: quantum uncertainty won't let a mass be pinned down any smaller.<br>
         <span class="dot" style="--c:#ffc24a"></span> <strong>Hubble radius</strong>: today's Hubble sphere, beyond which space recedes faster than light.</p>
      <p>The walls meet at the <strong>Big Bang</strong>. Press <strong>&#9654;</strong> or drag the time bar to watch the
         triangle grow from that instant to today, with each thing appearing when it first existed.</p>
      <p>Click any dot, or take the <strong>scale tour</strong> from smallest to largest. The <strong>Open Stars</strong> and
         <strong>Open Particles</strong> boxes zoom into stellar evolution and the particle zoo, any element's
         <strong>Show in Elements</strong> opens the periodic table, and <strong>Timeline &#8250;</strong> lays cosmic history
         out end to end.</p>
      <p class="note">${n("object")} objects · ${data.elements.elements.length} elements · ${n("stellar")} stellar-evolution entries · ${n("particle")} particles ·
         ${n("time") + n("era")} timeline entries · ${n("lp")} extra Lineweaver &amp; Patel points · ${n("erratum")} poster errors</p>
    </div>`;
}

function header(it) {
  const g = GROUPS[it.group];
  const printed = it.printed && it.printed.toLowerCase().replace(/[^a-z0-9]/g, "") !== it.name.toLowerCase().replace(/[^a-z0-9]/g, "")
    ? `<div class="printed">Printed on the poster: “${esc(it.printed)}”</div>` : "";
  const badges = [];
  if (it.hypothetical) badges.push(`<span class="badge hyp">Hypothetical</span>`);
  const ident = it.raw?.identification;
  if (ident && IDENT[ident]) badges.push(`<span class="badge ${ident === "tentative" ? "warn" : ""}">${IDENT[ident]}</span>`);
  if (it.schematic) badges.push(`<span class="badge warn">Placed for legibility, not to scale</span>`);
  const conf = it.raw?.reference?.confidence;
  if (it.raw?.reference?.width_is_estimate) badges.push(`<span class="badge warn">Width is an estimate</span>`);
  else if (conf === "low") badges.push(`<span class="badge warn">Rough real-world values</span>`);
  if (it.raw?.radioactive) badges.push(`<span class="badge">Radioactive · no stable isotope</span>`);
  if (it.raw?.reference?.representative) badges.push(`<span class="badge">Typical example</span>`);
  return `
    <div class="kicker"><span class="dot" style="--c:${g.color}"></span>${esc(g.label)} · ${esc(it.typeLabel)}</div>
    <h1>${esc(it.name)}</h1>${printed}
    ${badges.length ? `<div class="badges">${badges.join("")}</div>` : ""}`;
}

function row(label, real, drawn, cmp) {
  const delta = cmp ? `<span class="delta ${cmp.ok ? "ok" : ""}">${esc(cmp.text)}</span>` : "";
  return `<tr><td>${label}</td><td>${real ?? "—"}${drawn ? `<span class="sub">Poster: ${drawn} ${delta}</span>` : ""}</td></tr>`;
}

const massCell = (lg) => (lg == null ? null : `${esc(friendlyMass(lg))}<span class="sub">${sci(lg)} kg</span>`);
const lenCell = (lg, basis) => (lg == null ? null
  : `${esc(friendlyLength(lg))}<span class="sub">${sci(lg)} m${basis && basis !== "diameter" ? ` · ${basis.replaceAll("_", " ")}` : ""}</span>`);

function factsFor(it, data) {
  const r = it.raw;
  switch (it.type) {
    case "object": {
      const ref = r.reference;
      const c = r.chart;
      return `<table class="facts"><tbody>
        ${row("Mass", ref ? massCell(ref.log10_mass_kg) : "Unknown", esc(friendlyMass(c.log10_mass_kg)),
          ref && compare(c.log10_mass_kg, ref.log10_mass_kg, "heavy", "light"))}
        ${row("Width", ref ? lenCell(ref.log10_width_m, ref.width_basis) : "Unknown",
          it.schematic ? null : esc(friendlyLength(c.log10_width_m)),
          ref && !it.schematic && compare(c.log10_width_m, ref.log10_width_m, "large", "small"))}
        ${ref ? row("Equivalent energy", esc(friendlyEnergy(ref.log10_mass_kg - LOG_EV_KG))) : ""}
      </tbody></table>
      ${ref?.notes ? `<p class="note">${esc(ref.notes)}</p>` : ""}`;
    }
    case "stellar": {
      const ref = r.reference, c = r.chart;
      const m = ref.log10_mass_msun != null ? ref.log10_mass_msun + LOG_MSUN : null;
      const d = ref.log10_diameter_km != null ? ref.log10_diameter_km + 3 : null;
      return `<table class="facts"><tbody>
        ${row("Mass", m != null ? massCell(m) : "Not well measured", esc(friendlyMass(c.log10_mass_msun + LOG_MSUN)),
          compare(c.log10_mass_msun + LOG_MSUN, m, "heavy", "light"))}
        ${row("Diameter", d != null ? lenCell(d) : "—", esc(friendlyLength(c.log10_diameter_km + 3)),
          compare(c.log10_diameter_km + 3, d, "large", "small"))}
      </tbody></table>
      ${ref.notes ? `<p class="note">${esc(ref.notes)}</p>` : ""}`;
    }
    case "particle": {
      const ref = r.reference;
      const legend = data.particles.legend.find((l) => l.colour === r.chart_colour);
      const mismatch = legend && legend.actual_class !== legend.printed.toLowerCase().replace(/s$/, "");
      return `<table class="facts"><tbody>
        ${row("Class", esc(it.categoryLabel))}
        ${row("Mass", ref.mass_eV ? `${esc(friendlyEnergy(ref.log10_mass_eV).replace(/eV$/, "eV/c²"))}<span class="sub">${sci(Math.log10(ref.mass_kg))} kg</span>`
          : ref.mass_eV === 0 ? "Massless" : "Upper limit only",
          esc(friendlyEnergy(r.chart.log10_mass_eV).replace(/eV$/, "eV/c²")),
          ref.mass_eV ? compare(r.chart.log10_mass_eV, ref.log10_mass_eV, "heavy", "light") : null)}
        ${ref.reduced_compton_wavelength_m ? row("Compton wavelength", lenCell(Math.log10(ref.reduced_compton_wavelength_m))) : ""}
        ${row("Charge", esc(ref.electric_charge))}
        ${row("Spin", esc(ref.spin))}
        ${ref.generation ? row("Generation", ref.generation) : ""}
      </tbody></table>
      ${ref.notes ? `<p class="note">${esc(ref.notes)}</p>` : ""}
      ${mismatch ? `<p class="note">The poster's legend calls this colour “${esc(legend.printed)}”, but it's used for ${esc(legend.actual_class)}s. The legend swaps leptons and hadrons.</p>` : ""}`;
    }
    case "element": {
      const ref = r.reference;
      return `<table class="facts"><tbody>
        ${row("Atomic number", r.atomic_number)}
        ${row("Mass", `${ref.atomic_mass_u} u<span class="sub">${sci(ref.log10_mass_kg)} kg</span>`)}
        ${row("Width", `${esc(friendlyLength(ref.log10_width_m))}<span class="sub">${sci(ref.log10_width_m)} m · van der Waals diameter${ref.width_is_estimate ? " · estimate" : ""}</span>`)}
        ${row("Kind", esc(r.kind))}
        ${row("At room temperature", `${esc(r.standard_state)}${r.state_is_predicted ? " (predicted)" : ""}`)}
        ${row("Discovered", discovered(r))}
      </tbody></table>
      ${ref.notes ? `<p class="note">${esc(ref.notes)}</p>` : ""}
      ${origins(r, data)}`;
    }
    case "lp": {
      return `<table class="facts"><tbody>
        ${row("Mass", massCell(r.plotted.log10_mass_kg))}
        ${row("Width", lenCell(r.plotted.log10_width_m))}
      </tbody></table>
      <p class="note">${lpBasis(r)}</p>`;
    }
    case "time": {
      const rho = r.friedmann_density_log10_kg_m3;
      return `<table class="facts"><tbody>
        ${row("Time after the Big Bang", `${esc(friendlyTime(r.seconds))}<span class="sub">${sci(r.log10_seconds)} s</span>`)}
        ${row("Average density then", `${sci(rho)} kg/m³<span class="sub">radiation-era estimate</span>`)}
      </tbody></table>
      <p>${esc(r.note)}</p>`;
    }
    case "era": {
      const from = data.byKey.get(`time:${r.from_marker}`), to = data.byKey.get(`time:${r.to_marker}`);
      const span = (a, b) => `${esc(friendlyTime(a.raw.seconds))} → ${esc(friendlyTime(b.raw.seconds))}`;
      const ref = r.reference_log10_seconds;
      return `<table class="facts"><tbody>
        ${row("Bracket on the poster", from && to ? span(from, to) : "—")}
        ${ref ? row("Actual timing", ref[0] === ref[1] ? esc(friendlyTime(10 ** ref[0]))
          : `${esc(friendlyTime(10 ** ref[0]))} → ${esc(friendlyTime(10 ** ref[1]))}`) : ""}
      </tbody></table>
      ${r.note ? `<p class="note">${esc(r.note)}</p>` : ""}`;
    }
    case "boundary": {
      const others = data.main.physics.horizons.filter((h) => h.id !== r.id);
      return `<p>${esc(r.definition)}</p>
      <table class="facts"><tbody>
        ${row("Radius today", `${esc(String(r.radius_gly))} billion light-years`)}
        ${row("Width on the chart", lenCell(r.log10_diameter_m))}
        ${others.map((o) => row(`vs ${esc(o.name.split(" (")[0])}`,
          `${(10 ** (r.log10_diameter_m - o.log10_diameter_m)).toFixed(2)}× as wide`)).join("")}
      </tbody></table>
      <p>${esc(r.description)}</p>
      <p class="note">Both come from the same Planck 2018 cosmology (flat ΛCDM, H₀ = ${data.main.physics.cosmology.H0_km_s_Mpc} km/s/Mpc).</p>`;
    }
    case "erratum":
      return `<p><strong>Where:</strong> ${esc(r.where)}</p><p>${esc(r.issue)}</p>
        ${r.evidence ? `<p class="note">${esc(r.evidence)}</p>` : ""}
        <p class="note">In the data: ${esc(r.handling)}</p>`;
    default:
      return "";
  }
}

function lpBasis(o) {
  return o.plotted.basis === "read_from_chart"
    ? "Read from the Lineweaver &amp; Patel chart (radius in cm, mass in grams), accurate to about ±0.2 decades."
    : `Placed by physics rather than read off their image: ${esc(o.plotted.basis.replaceAll("_", " "))}. `
      + "Lineweaver &amp; Patel plot radius; here everything uses full width, so points on a wall stay exactly on it.";
}

const discovered = (e) => (e.discovered === "ancient" ? "Known since ancient times" : String(e.discovered));

/** The cosmic sources of an element's atoms, main source first. */
function origins(e, data) {
  const source = Object.fromEntries(data.elements.sources.map((s) => [s.id, s]));
  return `<div class="kicker" style="margin-top:12px">Where its atoms come from</div>
    <ul class="origins">${e.origin.map((id) => `<li><span class="dot" style="--c:${ELEMENT_ORIGINS[id]}"></span>
      <strong>${esc(source[id].label)}</strong><span class="sub">${esc(source[id].description)}</span></li>`).join("")}</ul>
    ${e.origin_note ? `<p class="note">${esc(e.origin_note)}</p>` : ""}`;
}

/** For a main-chart atom that is also an element of the periodic table (oxygen, helium). */
function elementFacts(it, data) {
  const e = it.element;
  if (!e) return "";
  return `<div class="infobox"><div class="kicker">The element</div>
    <strong>${esc(e.name)} · ${esc(e.symbol)} · atomic number ${e.atomic_number}</strong>
    <span class="sub">${esc(e.kind)} · ${esc(e.standard_state)} at room temperature · discovered ${discovered(e).toLowerCase()}</span></div>
    ${origins(e, data)}`;
}

/** Where Lineweaver & Patel's chart puts this item, for items that stand in for one of their points. */
function lpReading(it) {
  const o = it.lpPoint;
  if (!o) return "";
  const as = o.name.toLowerCase() !== it.name.toLowerCase() ? ` as “${esc(o.name)}”` : "";
  return `<div class="infobox"><div class="kicker">On Lineweaver &amp; Patel's chart${as}</div>
    <strong>${esc(friendlyMass(o.plotted.log10_mass_kg))} · ${esc(friendlyLength(o.plotted.log10_width_m))} across</strong>
    <span class="sub">${lpBasis(o)}</span></div>`;
}

const BASIS = { this_object: "this object", first_of_its_kind: "first of its kind", physics: "physics estimate" };

/** When something (or the first of its kind) came into existence, from the data's first_appeared. */
function appeared(it) {
  const a = it.raw?.first_appeared;
  if (!a) return "";
  const when = a.label[0].toUpperCase() + a.label.slice(1);
  return `<div class="appeared"><div class="kicker">First appeared</div>
    <strong>${esc(when)}</strong> <span class="hint">${esc(BASIS[a.basis] ?? a.basis)}${a.confidence === "low" ? " · uncertain" : ""}</span>
    ${a.note ? `<span class="sub">${esc(a.note)}</span>` : ""}</div>`;
}

export function renderDetails(el, it, data, { canShow, onSelect, onShowIn, onShowTime }) {
  const desc = it.raw?.description ?? it.raw?.meaning ?? "";
  const links = [];
  if (it.mainId && data.byKey.has(`object:${it.mainId}`)) links.push(data.byKey.get(`object:${it.mainId}`));
  for (const k of it.backlinks ?? []) links.push(data.byKey.get(k));
  if (it.type === "era") {
    for (const k of [`time:${it.raw.from_marker}`, `time:${it.raw.to_marker}`]) if (data.byKey.has(k)) links.push(data.byKey.get(k));
  }
  const views = [["triangle", "Show on the triangle"], ["stars", "Show in Stars"], ["particles", "Show in Particles"],
    ["elements", "Show in Elements"], ["timeline", "Show on the timeline"]].filter(([v]) => canShow(it, v));
  if (it.type === "erratum") views.push([it.relatedView, `Open ${it.relatedView[0].toUpperCase()}${it.relatedView.slice(1)}`]);

  el.innerHTML = `
    ${header(it)}
    ${desc && it.type !== "erratum" && it.type !== "boundary" ? `<p>${esc(desc)}</p>` : ""}
    ${factsFor(it, data)}
    ${elementFacts(it, data)}
    ${lpReading(it)}
    ${appeared(it)}
    ${links.length ? `<div class="kicker" style="margin-top:12px">Also appears as</div>
      <div class="linkchips">${links.map((l) => `<button class="linkchip" data-key="${esc(l.key)}">
        <span class="dot" style="--c:${l.color}"></span>${esc(l.name)} <span class="hint">${esc(l.typeLabel)}</span></button>`).join("")}</div>` : ""}
    <div class="actions">${views.map(([v, label]) => `<button data-show="${v}">${label}</button>`).join("")}
      ${it.appearU != null && it.real && canShow(it, "triangle") ? `<button data-time>&#9654; Watch it appear</button>` : ""}</div>`;

  el.querySelectorAll(".linkchip").forEach((b) => b.addEventListener("click", () => onSelect(b.dataset.key, { fly: true, switchView: true })));
  el.querySelectorAll("[data-show]").forEach((b) => b.addEventListener("click", () => onShowIn(it.key, b.dataset.show)));
  el.querySelector("[data-time]")?.addEventListener("click", () => onShowTime(it.key));
}
