// The periodic table, coloured by where each element's atoms are made (or by kind of element).
// Each cell is the same item the triangle plots, so selecting one selects it everywhere.

import { esc, friendlyMass } from "./format.js";

// cosmic sources of the elements (elements.json -> sources), main source first in each element's list
export const ELEMENT_ORIGINS = {
  big_bang: "#6ea8ff", cosmic_rays: "#f07ad8", massive_stars: "#7ee081", low_mass_stars: "#ffd166",
  white_dwarfs: "#4dd6c9", neutron_star_mergers: "#b48cff", decay: "#ff8c69", laboratory: "#8a8799",
};
export const ELEMENT_KINDS = {
  "Alkali metal": "#ff6b6b", "Alkaline earth metal": "#ffa94d", "Transition metal": "#f5c26b",
  "Post-transition metal": "#8fa8ff", Metalloid: "#4dd6c9", Nonmetal: "#7ee081", Halogen: "#e9f27a",
  "Noble gas": "#b48cff", Lanthanide: "#f5a3c7", Actinide: "#ff8fab",
};

export const ELEMENT_LAYERS = [
  { id: "origin", label: "Colour by cosmic origin (off: by kind)", on: true, color: "#7ee081" },
];

/** Legend rows for the colouring in use: [{ label, color, count }]. */
export function elementLegend(data, byOrigin) {
  const els = data.elements.elements;
  if (byOrigin) {
    return data.elements.sources.map((s) => ({
      label: s.label, color: ELEMENT_ORIGINS[s.id], count: els.filter((e) => e.origin[0] === s.id).length,
    }));
  }
  return Object.entries(ELEMENT_KINDS).map(([k, color]) => ({ label: k, color, count: els.filter((e) => e.kind === k).length }));
}

export function createElements({ svgEl, tooltipEl, data, onSelect }) {
  const svg = d3.select(svgEl);
  svg.selectAll("*").remove();
  const sourceLabel = Object.fromEntries(data.elements.sources.map((s) => [s.id, s.label]));
  // one cell per element; oxygen and helium select the main-chart atoms that stand for them
  const cells = data.elements.elements.map((e) => ({ e, key: data.byKey.get(`element:${e.id}`)?.key }));
  const cellOf = Object.fromEntries(cells.map((c) => [c.key, c]));
  const state = { selected: null, t: d3.zoomIdentity, opts: Object.fromEntries(ELEMENT_LAYERS.map((l) => [l.id, l.on])) };
  const margin = { top: 64, right: 16, bottom: 16, left: 34 };   // top clears the floating controls
  const ROWS = 9.5, COLS = 18;
  // the lanthanide and actinide rows (9, 10) sit half a cell below period 7
  const rowY = (r) => (r <= 7 ? r - 1 : r - 1.5);
  let cell = 0, ox = 0, oy = 0;

  const g = svg.append("g");
  const gNums = g.append("g").attr("class", "el-nums");
  const gCaption = g.append("g").attr("class", "el-caption");
  const gCells = g.append("g");
  const zoom = d3.zoom().scaleExtent([0.8, 6]).on("zoom", (e) => { state.t = e.transform; render(); });
  svg.call(zoom).on("dblclick.zoom", null);

  function layout() {
    const { width, height } = svgEl.getBoundingClientRect();
    if (!width || !height) return;
    const pw = width - margin.left - margin.right, ph = height - margin.top - margin.bottom;
    cell = Math.max(14, Math.min(pw / COLS, ph / ROWS));
    ox = margin.left + (pw - cell * COLS) / 2;
    oy = margin.top + Math.max(0, (ph - cell * ROWS) / 2);
    render();
  }

  const colorOf = (e) => (state.opts.origin ? ELEMENT_ORIGINS[e.origin[0]] : ELEMENT_KINDS[e.kind]);

  function render() {
    if (!cell) return;
    const { k, x: tx, y: ty } = state.t;
    const c = cell * k, gap = Math.max(1, c * 0.06);
    const X = (col) => tx + k * (ox + (col - 1) * cell);
    const Y = (row) => ty + k * (oy + rowY(row) * cell);

    const sel = gCells.selectAll("g.el").data(cells, (d) => d.e.id).join((enter) => {
      const el = enter.append("g").attr("class", "el")
        .on("click", (ev, d) => { ev.stopPropagation(); if (d.key) onSelect(d.key, { focus: false }); })
        .on("mouseenter", (ev, d) => tip(ev, d.e)).on("mousemove", moveTip).on("mouseleave", hideTip);
      el.append("rect").attr("class", "el-box");
      el.append("g").attr("class", "el-stripe");
      el.append("text").attr("class", "el-z");
      el.append("text").attr("class", "el-sym").attr("text-anchor", "middle");
      el.append("text").attr("class", "el-name").attr("text-anchor", "middle");
      return el;
    });
    sel.attr("transform", (d) => `translate(${X(d.e.table.column)},${Y(d.e.table.row)})`)
      .classed("selected", (d) => d.key === state.selected)
      .classed("lab", (d) => d.e.origin[0] === "laboratory");
    sel.select("rect").attr("x", gap / 2).attr("y", gap / 2).attr("width", c - gap).attr("height", c - gap)
      .attr("rx", Math.min(6, c * 0.08)).attr("fill", (d) => colorOf(d.e)).attr("stroke", (d) => colorOf(d.e));
    // origin mode: a stripe along the bottom shares the cell between the element's sources
    sel.select("g.el-stripe").selectAll("rect")
      .data((d) => (state.opts.origin && d.e.origin.length > 1 ? d.e.origin.map((s, i, a) => ({ s, i, n: a.length })) : []))
      .join("rect")
      .attr("x", (s) => gap / 2 + (c - gap) * s.i / s.n).attr("width", (s) => (c - gap) / s.n)
      .attr("y", c - gap / 2 - c * 0.1).attr("height", c * 0.1).attr("fill", (s) => ELEMENT_ORIGINS[s.s]);
    sel.select(".el-z").attr("x", c * 0.1).attr("y", c * 0.24).attr("font-size", c * 0.17).text((d) => d.e.atomic_number);
    sel.select(".el-sym").attr("x", c / 2).attr("y", c * 0.62).attr("font-size", c * 0.34).text((d) => d.e.symbol);
    sel.select(".el-name").attr("x", c / 2).attr("y", c * 0.82).attr("font-size", Math.min(12, c * 0.13))
      .text((d) => (c >= 54 ? d.e.name : ""));

    // the f-block placeholders in group 3, period and group numbers
    const nums = [
      ...[1, 2, 3, 4, 5, 6, 7].map((p) => ({ id: `p${p}`, t: p, x: X(1) - 8, y: Y(p) + c / 2 + 4, a: "end" })),
      ...d3.range(1, 19).map((grp) => {
        const top = Math.min(...cells.filter((d) => d.e.table.group === grp).map((d) => d.e.table.row));
        return { id: `g${grp}`, t: grp, x: X(grp) + c / 2, y: Y(top) - 6, a: "middle" };
      }),
      { id: "la", t: "57–71", x: X(3) + c / 2, y: Y(6) + c / 2 + 4, a: "middle", cls: "el-ph" },
      { id: "ac", t: "89–103", x: X(3) + c / 2, y: Y(7) + c / 2 + 4, a: "middle", cls: "el-ph" },
    ];
    gNums.selectAll("text").data(nums, (d) => d.id).join("text").attr("class", (d) => d.cls ?? "")
      .attr("x", (d) => d.x).attr("y", (d) => d.y).attr("text-anchor", (d) => d.a)
      .attr("font-size", (d) => Math.max(9, Math.min(13, c * (d.cls ? 0.16 : 0.2))))
      .text((d) => (d.cls && c < 40 ? "" : d.t));   // the f-block ranges need a cell wide enough to hold them

    // a caption in the gap above the transition metals
    const lines = state.opts.origin
      ? ["Where the atoms come from", "Colour: the main source · stripe: every source"]
      : ["Kinds of element", "Click any element for its details"];
    gCaption.selectAll("text").data(lines).join("text").attr("text-anchor", "middle")
      .attr("class", (d, i) => (i ? "el-caption-sub" : "el-caption-title"))
      .attr("x", X(3) + 5 * c).attr("y", (d, i) => Y(1) + c * 0.55 + i * Math.max(14, c * 0.3))
      .attr("font-size", (d, i) => Math.max(10, Math.min(i ? 13 : 20, c * (i ? 0.2 : 0.32))))
      .text((d) => (c * 10 > d.length * 7 ? d : ""));
  }

  function tip(ev, e) {
    tooltipEl.innerHTML = `<strong>${esc(e.name)} · ${esc(e.symbol)} · ${e.atomic_number}</strong>
      <span>${esc(e.kind)} · ${e.origin.map((s) => esc(sourceLabel[s])).join(", ")}</span><br>
      ${esc(friendlyMass(e.reference.log10_mass_kg))} · ${e.reference.atomic_mass_u} u`;
    tooltipEl.hidden = false;
    moveTip(ev);
  }
  function moveTip(ev) {
    const r = svgEl.getBoundingClientRect();
    tooltipEl.style.left = `${Math.min(ev.clientX - r.left + 14, r.width - 270)}px`;
    tooltipEl.style.top = `${ev.clientY - r.top + 14}px`;
  }
  function hideTip() { tooltipEl.hidden = true; }

  new ResizeObserver(layout).observe(svgEl);
  layout();

  return {
    setSelected(key) { state.selected = key; render(); },
    setHidden() {},
    setOption(name, value) { state.opts[name] = value; render(); },
    has: (key) => !!cellOf[key],
    focus(key) {
      if (!cell) layout();
      const d = cellOf[key];
      if (!d) return;
      const { width, height } = svgEl.getBoundingClientRect();
      const k = Math.max(state.t.k, 1.6);
      const cx = ox + (d.e.table.column - 0.5) * cell, cy = oy + (rowY(d.e.table.row) + 0.5) * cell;
      svg.transition().duration(800).call(zoom.transform, d3.zoomIdentity.translate(width / 2 - k * cx, height / 2 - k * cy).scale(k));
    },
    zoom(how) {
      if (how === "home") svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity);
      else svg.transition().duration(300).call(zoom.scaleBy, how === "in" ? 1.5 : 1 / 1.5);
    },
    resize: layout,
  };
}
