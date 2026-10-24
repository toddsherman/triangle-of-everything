// A zoomable log-log scatter chart shared by the Triangle, Stars and Particles views.
// Each view supplies positions for its items plus a drawLayers() hook for lines, regions and annotations.

import { sup } from "./format.js";

const tickFmt = (d) => `10${sup(d)}`;

// Lines and regions are clipped to the visible area in data space before they become SVG, so the browser
// never has to place coordinates millions of pixels off-screen at deep zoom (which costs precision).

/** Liang-Barsky: the part of segment a-b inside box {x0,x1,y0,y1}, or null. */
export function clipSegment(a, b, box) {
  let t0 = 0, t1 = 1;
  const dx = b.x - a.x, dy = b.y - a.y;
  const p = [-dx, dx, -dy, dy];
  const q = [a.x - box.x0, box.x1 - a.x, a.y - box.y0, box.y1 - a.y];
  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) { if (q[i] < 0) return null; continue; }
    const r = q[i] / p[i];
    if (p[i] < 0) { if (r > t1) return null; if (r > t0) t0 = r; }
    else { if (r < t0) return null; if (r < t1) t1 = r; }
  }
  return [{ x: a.x + t0 * dx, y: a.y + t0 * dy }, { x: a.x + t1 * dx, y: a.y + t1 * dy }];
}

/** Sutherland-Hodgman: polygon clipped to box. */
export function clipPolygon(pts, box) {
  const edges = [
    [(p) => p.x >= box.x0, (a, b) => ({ x: box.x0, y: a.y + (b.y - a.y) * (box.x0 - a.x) / (b.x - a.x) })],
    [(p) => p.x <= box.x1, (a, b) => ({ x: box.x1, y: a.y + (b.y - a.y) * (box.x1 - a.x) / (b.x - a.x) })],
    [(p) => p.y >= box.y0, (a, b) => ({ x: a.x + (b.x - a.x) * (box.y0 - a.y) / (b.y - a.y), y: box.y0 })],
    [(p) => p.y <= box.y1, (a, b) => ({ x: a.x + (b.x - a.x) * (box.y1 - a.y) / (b.y - a.y), y: box.y1 })],
  ];
  let out = pts;
  for (const [inside, cut] of edges) {
    const input = out;
    out = [];
    for (let i = 0; i < input.length; i++) {
      const cur = input[i], prev = input[(i + input.length - 1) % input.length];
      if (inside(cur)) {
        if (!inside(prev)) out.push(cut(prev, cur));
        out.push(cur);
      } else if (inside(prev)) out.push(cut(prev, cur));
    }
    if (!out.length) break;
  }
  return out;
}

export function createChart(cfg) {
  const {
    svgEl, tooltipEl, items, home, onSelect,
    equalAspect = true,
    yOnly = false,
    margin = { top: 16, right: 16, bottom: 74, left: 64 },
    xTitle = "", yTitle = "",
    xTicks = true,
    yTickFilter = () => true,
    position,                       // (item, opts) => {x, y, marker?} | null
    tooltip,                        // (item, p) => html
    priority = () => 0,             // label priority; higher wins space
    radius = () => 5,
    color = (it) => it.color,
    pointClass = () => "",
    drawLayers = () => {},
    focusPoint = () => null,        // (item) => {x, y} to centre on for items that aren't drawn as points
    onUserZoom = () => {},          // called when the user (not code) pans or zooms
    rightAxis = null,               // { title, offset, option } -> value = y + offset
    options = {},
  } = cfg;

  const svg = d3.select(svgEl);
  svg.selectAll("*").remove();
  const state = { hidden: new Set(), selected: null, t: d3.zoomIdentity, opts: { ...options } };
  let bx, by, pw = 0, ph = 0;

  const defs = svg.append("defs");
  const clipId = `clip-${svgEl.id}`;
  const clipRect = defs.append("clipPath").attr("id", clipId).append("rect");
  const plot = svg.append("g").attr("clip-path", `url(#${clipId})`);
  const gGrid = plot.append("g").attr("class", "grid");
  const gBack = plot.append("g");
  const gMid = plot.append("g");
  const gPoints = plot.append("g");
  const gLabels = plot.append("g");
  const gFront = plot.append("g");
  const gPulses = plot.append("g");           // rings drawing the eye to points that just appeared
  const gOutside = svg.append("g");           // unclipped: headers and notes outside the plot area
  const gx = svg.append("g").attr("class", "axis");
  const gy = svg.append("g").attr("class", "axis");
  const gr = svg.append("g").attr("class", "axis right");
  const xT = svg.append("text").attr("class", "axis-title").attr("text-anchor", "middle").text(xTitle);
  const yT = svg.append("text").attr("class", "axis-title").attr("text-anchor", "middle").text(yTitle);
  const rT = svg.append("text").attr("class", "axis-title").attr("text-anchor", "middle").text(rightAxis?.title ?? "");

  const MIN_K = 0.6, MAX_K = 150;
  const zoom = d3.zoom().scaleExtent([MIN_K, MAX_K]).on("zoom", (e) => {
    state.t = e.transform;
    if (e.sourceEvent) onUserZoom();
    render();
  });
  svg.call(zoom).on("dblclick.zoom", null);

  function layout() {
    const { width, height } = svgEl.getBoundingClientRect();
    if (!width || !height) return;
    const right = margin.right + (rightAxis && state.opts[rightAxis.option] ? 52 : 0);
    pw = Math.max(50, width - margin.left - right);
    ph = Math.max(50, height - margin.top - margin.bottom);
    const [x0, x1] = home.x, [y0, y1] = home.y;
    if (equalAspect) {
      const k = Math.min(pw / (x1 - x0), ph / (y1 - y0));
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      bx = d3.scaleLinear().domain([cx - pw / (2 * k), cx + pw / (2 * k)]).range([margin.left, margin.left + pw]);
      by = d3.scaleLinear().domain([cy - ph / (2 * k), cy + ph / (2 * k)]).range([margin.top + ph, margin.top]);
    } else {
      bx = d3.scaleLinear().domain(home.x).range([margin.left, margin.left + pw]);
      by = d3.scaleLinear().domain(home.y).range([margin.top + ph, margin.top]);
    }
    clipRect.attr("x", margin.left).attr("y", margin.top).attr("width", pw).attr("height", ph);
    gx.attr("transform", `translate(0,${margin.top + ph})`);
    gy.attr("transform", `translate(${margin.left},0)`);
    gr.attr("transform", `translate(${margin.left + pw},0)`);
    xT.attr("x", margin.left + pw / 2).attr("y", margin.top + ph + 38);
    yT.attr("transform", `translate(16,${margin.top + ph / 2}) rotate(-90)`);
    rT.attr("transform", `translate(${margin.left + pw + 46},${margin.top + ph / 2}) rotate(90)`);
    render();
  }

  const scales = () => ({ zx: yOnly ? bx : state.t.rescaleX(bx), zy: state.t.rescaleY(by) });
  const pos = (it) => position(it, state.opts);
  const visible = (it) => !state.hidden.has(it.group) && pos(it);

  const ctx2d = document.createElement("canvas").getContext("2d");
  const textWidth = (s, bold) => {
    ctx2d.font = `${bold ? "bold 13px" : "11px"} "Helvetica Neue", Helvetica, Arial, sans-serif`;
    return ctx2d.measureText(s).width;
  };

  function placeLabels(zx, zy, shown) {
    const prio = (it) => (it.key === state.selected ? 1e5 : 0) + priority(it);
    const boxes = [];
    const out = new Map();
    const xmin = margin.left, xmax = margin.left + pw, ymin = margin.top, ymax = margin.top + ph;
    for (const it of [...shown].sort((a, b) => prio(b) - prio(a))) {
      const sel = it.key === state.selected;
      if (state.opts.labels === false && !sel) continue;
      const p = pos(it);
      const x = zx(p.x), y = zy(p.y);
      if (x < xmin || x > xmax || y < ymin || y > ymax) continue;
      const w = textWidth(it.name, sel) + 2, h = sel ? 15 : 13;
      const cands = [[x + 9, y - h / 2], [x - 9 - w, y - h / 2], [x - w / 2, y - h - 8], [x - w / 2, y + 8]];
      for (const [lx, ly] of cands) {
        const box = [lx, ly, lx + w, ly + h];
        if (box[0] < xmin || box[2] > xmax || box[1] < ymin || box[3] > ymax) continue;
        if (boxes.some((b) => !(box[2] < b[0] || box[0] > b[2] || box[3] < b[1] || box[1] > b[3]))) continue;
        boxes.push(box);
        out.set(it.key, { x: lx, y: ly + h - 3 });
        break;
      }
    }
    return out;
  }

  const symbol = (it, p) => d3.symbol(p.marker === "limit" ? d3.symbolTriangle : d3.symbolCircle,
    Math.PI * radius(it) ** 2 * (p.marker === "limit" ? 1.6 : 1))();

  function render(animate = false) {
    if (!bx) return;
    const { zx, zy } = scales();
    const plotBox = { x0: margin.left, x1: margin.left + pw, y0: margin.top, y1: margin.top + ph };

    // axes and grid (integer decades only)
    const xt = xTicks ? zx.ticks(Math.max(4, Math.round(pw / 70))).filter(Number.isInteger) : [];
    const yt = zy.ticks(Math.max(4, Math.round(ph / 45))).filter((d) => Number.isInteger(d) && yTickFilter(d));
    gx.call(d3.axisBottom(zx).tickValues(xt).tickFormat(tickFmt));
    gy.call(d3.axisLeft(zy).tickValues(yt).tickFormat(tickFmt));
    gGrid.selectAll("line.v").data(xt).join("line").attr("class", "v")
      .attr("x1", (d) => zx(d)).attr("x2", (d) => zx(d)).attr("y1", plotBox.y0).attr("y2", plotBox.y1);
    gGrid.selectAll("line.h").data(yt).join("line").attr("class", "h")
      .attr("y1", (d) => zy(d)).attr("y2", (d) => zy(d)).attr("x1", plotBox.x0).attr("x2", plotBox.x1);
    const showRight = rightAxis && state.opts[rightAxis.option];
    gr.style("display", showRight ? null : "none");
    rT.style("display", showRight ? null : "none");
    if (showRight) {
      const [lo, hi] = zy.domain().map((v) => v + rightAxis.offset).sort((a, b) => a - b);
      const vals = d3.ticks(lo, hi, Math.max(4, Math.round(ph / 45))).filter(Number.isInteger);
      gr.call(d3.axisRight(d3.scaleLinear().domain(zy.domain().map((v) => v + rightAxis.offset)).range(zy.range()))
        .tickValues(vals).tickFormat(tickFmt));
    }

    // visible data-space box (plus a margin) for clipping, and path builders that use it
    const [vx0, vx1] = zx.domain(), [vy0, vy1] = zy.domain().slice().sort((a, b) => a - b);
    const px = (vx1 - vx0) * 0.1, py = (vy1 - vy0) * 0.1;
    const view = { x0: vx0 - px, x1: vx1 + px, y0: vy0 - py, y1: vy1 + py };
    const toPx = (p) => `${zx(p.x)},${zy(p.y)}`;
    const segPath = (a, b) => { const c = clipSegment(a, b, view); return c ? `M${toPx(c[0])}L${toPx(c[1])}` : ""; };
    const polyPath = (pts) => { const c = clipPolygon(pts, view); return c.length > 2 ? `M${c.map(toPx).join("L")}Z` : ""; };
    const linePath = (pts) => pts.slice(1).map((p, i) => segPath(pts[i], p)).join("");

    drawLayers({ zx, zy, back: gBack, mid: gMid, front: gFront, outside: gOutside, defs, opts: state.opts,
      selected: state.selected, plot: plotBox, animate, pos, layer, view, segPath, polyPath, linePath });

    const shown = items.filter(visible);
    const tf = (d) => {
      const p = pos(d);
      return `translate(${zx(p.x)},${zy(p.y)})${p.marker === "limit" ? " rotate(180)" : ""}`;
    };
    const pts = gPoints.selectAll("path").data(shown, (d) => d.key).join(
      (enter) => enter.append("path").attr("transform", tf)
        .on("mouseenter", (e, d) => showTip(e, d))
        .on("mousemove", moveTip)
        .on("mouseleave", hideTip)
        .on("click", (e, d) => { e.stopPropagation(); onSelect(d.key, { focus: false }); }),
    );
    pts.attr("d", (d) => symbol(d, pos(d)))
      .attr("fill", color)
      .attr("class", (d) => `pt ${pointClass(d)} ${d.key === state.selected ? "selected" : ""}`);
    (animate ? pts.transition().duration(900) : pts).attr("transform", tf);
    gPoints.selectAll("path.selected").raise();

    const placed = placeLabels(zx, zy, shown);
    const labs = gLabels.selectAll("text").data(shown.filter((d) => placed.has(d.key)), (d) => d.key)
      .join((enter) => enter.append("text").attr("opacity", 0));
    labs.attr("class", (d) => `pt-label ${d.key === state.selected ? "selected" : ""}`).text((d) => d.name);
    (animate ? labs.attr("opacity", 0).transition().delay(700).duration(300) : labs)
      .attr("x", (d) => placed.get(d.key).x).attr("y", (d) => placed.get(d.key).y).attr("opacity", 1);
  }

  /** Get-or-create a named <g> inside a parent selection, shown only when `on` is true. */
  function layer(parent, name, on = true) {
    let g = parent.select(`g.L-${name}`);
    if (g.empty()) g = parent.append("g").attr("class", `L-${name}`);
    g.style("display", on ? null : "none");
    return g;
  }

  function showTip(e, d) {
    tooltipEl.innerHTML = tooltip(d, pos(d));
    tooltipEl.hidden = false;
    moveTip(e);
  }
  function moveTip(e) {
    const r = svgEl.getBoundingClientRect();
    tooltipEl.style.left = `${Math.min(e.clientX - r.left + 14, r.width - 270)}px`;
    tooltipEl.style.top = `${e.clientY - r.top + 14}px`;
  }
  function hideTip() { tooltipEl.hidden = true; }

  new ResizeObserver(layout).observe(svgEl);
  layout();

  return {
    setHidden(hidden) { state.hidden = hidden; render(); },
    setSelected(key) { state.selected = key; render(); },
    setOption(name, value, silent = false) {
      state.opts[name] = value;
      if (rightAxis && name === rightAxis.option) layout(); else if (!silent) render();
    },
    redraw: () => render(),
    setMargin(partial) { Object.assign(margin, partial); layout(); },
    /** Jump (no animation) so the data ranges xr, yr fill the plot, keeping equal scales. */
    fit(xr, yr) {
      if (!bx) layout();
      const x0 = bx(xr[0]), x1 = bx(xr[1]), y0 = by(yr[1]), y1 = by(yr[0]);
      const k = Math.max(MIN_K, Math.min(MAX_K, Math.min(pw / (x1 - x0), ph / (y1 - y0))));
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      svg.interrupt().call(zoom.transform, d3.zoomIdentity.translate(margin.left + pw / 2 - k * cx, margin.top + ph / 2 - k * cy).scale(k));
    },
    has: (key) => items.some((i) => i.key === key && (pos(i) || focusPoint(i))),
    /** Keys of the points drawn right now, or with some options changed (e.g. at another cosmic moment). */
    visibleKeys: (patch = {}) => items.filter((i) => !state.hidden.has(i.group) && position(i, { ...state.opts, ...patch }))
      .map((i) => i.key),
    /** Would this point be drawn with these options changed? */
    shows(key, patch = {}) {
      const it = items.find((i) => i.key === key);
      return !!it && !state.hidden.has(it.group) && !!position(it, { ...state.opts, ...patch });
    },
    /** Point out a spot: a ring starting just outside the plot closes in on data point p over ms and vanishes
     *  as it arrives. It follows p while the camera moves. */
    pulse(p, stroke, ms) {
      if (!bx) return;
      const { zx: sx, zy: sy } = scales();
      const far = 8 + Math.max(...[[0, 0], [pw, 0], [0, ph], [pw, ph]]
        .map(([cx, cy]) => Math.hypot(margin.left + cx - sx(p.x), margin.top + cy - sy(p.y))));
      gPulses.append("circle").attr("class", "pulse").attr("stroke", stroke)
        .transition().duration(Math.max(0, ms)).ease(d3.easeLinear)
        .tween("pulse", function () {
          const ring = d3.select(this);
          return (t) => {
            const { zx, zy } = scales();
            ring.attr("cx", zx(p.x)).attr("cy", zy(p.y)).attr("r", 5 + (far - 5) * (1 - d3.easeQuadIn(t)))
              .attr("stroke-width", 1.5 + 1.5 * t).attr("opacity", 0.4 + 0.6 * t);
          };
        })
        .remove();
    },
    clearPulses() { gPulses.selectAll("circle").interrupt().remove(); },
    focus(key, minZoom = 4) {
      if (!bx) layout();
      const it = items.find((i) => i.key === key);
      const p = it && (pos(it) ?? focusPoint(it));
      if (!p) return;
      const k = Math.max(state.t.k, p.k ?? minZoom);   // focusPoint can ask for a closer zoom
      const cx = margin.left + pw / 2, cy = margin.top + ph / 2;
      const tx = yOnly ? 0 : cx - k * bx(p.x);
      svg.transition().duration(900).call(zoom.transform, d3.zoomIdentity.translate(tx, cy - k * by(p.y)).scale(k));
    },
    zoom(how) {
      if (how === "home") svg.transition().duration(700).call(zoom.transform, d3.zoomIdentity);
      else svg.transition().duration(300).call(zoom.scaleBy, how === "in" ? 1.6 : 1 / 1.6);
    },
    resize: layout,
  };
}
