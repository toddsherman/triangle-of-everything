// Cosmic time for the slider. Real time spans 61 decades before "today", so the slider runs on a "story"
// scale: log time after the Big Bang for the first half of cosmic history, then log time *before today*,
// with anchors that give each era a fair share of the bar. State at any moment is interpolated from
// cosmic_timeline.json -> history (flat LambdaCDM).

import { friendlyTime } from "./format.js";

const YEAR = 3.156e7;

export function createCosmicClock(history) {
  const AGE = history.age_seconds;
  const HALF = Math.log10(AGE / 2);
  const S_END = 2 * HALF - Math.log10(YEAR);          // one year ago; anything later counts as today

  /** Story coordinate: log seconds after the Big Bang early on, mirrored log time-before-today later. */
  const sOf = (t, yearsAgo) => {
    const lookback = yearsAgo != null ? yearsAgo * YEAR : AGE - t;
    if (lookback <= YEAR) return S_END;
    if (lookback < AGE / 2) return 2 * HALF - Math.log10(lookback);
    return Math.log10(t);
  };
  const ago = (years) => sOf(null, years);

  // anchors: (story coordinate, slider position) - piecewise linear between them
  const ANCHORS = [
    // starts the instant the three walls meet (the first history row)
    [Math.log10(history.rows[0][0]), 0], [-12, 0.25], [0, 0.35], [Math.log10(1.2e13), 0.47], [Math.log10(1e9 * YEAR), 0.57],
    [HALF, 0.63], [ago(4.6e9), 0.69], [ago(5e8), 0.77], [ago(3e5), 0.87], [ago(5e3), 0.93], [S_END, 1],
  ];
  const lerp = (x, xs, ys) => {
    if (x <= xs[0]) return ys[0];
    for (let i = 1; i < xs.length; i++) {
      if (x <= xs[i]) return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1]);
    }
    return ys[ys.length - 1];
  };
  const AS = ANCHORS.map((a) => a[0]), AU = ANCHORS.map((a) => a[1]);
  const uOfS = (s) => lerp(s, AS, AU);
  const sOfU = (u) => lerp(u, AU, AS);

  // history rows -> story coordinate (the last row is today)
  const rows = history.rows.map((r) => ({
    s: r[1] === 0 ? S_END : sOf(r[0], r[1]), t: r[0], rho: r[2], hub: r[3], horizon: r[4], temp: r[5],
  }));
  rows[rows.length - 1].s = S_END + 1e-9;
  const rowS = rows.map((r) => r.s);
  const column = Object.fromEntries(["rho", "hub", "horizon", "temp"].map((k) => [k, rows.map((r) => r[k])]));

  function stateAt(u) {
    u = Math.min(1, Math.max(0, u));
    const s = sOfU(u);
    const isNow = u >= 1;
    const pick = (key) => (isNow ? rows[rows.length - 1][key] : lerp(s, rowS, column[key]));
    let t, yearsAgo;
    if (isNow) { t = AGE; yearsAgo = 0; }
    else if (s <= HALF) { t = 10 ** s; yearsAgo = (AGE - t) / YEAR; }
    else { const lb = 10 ** (2 * HALF - s); t = AGE - lb; yearsAgo = lb / YEAR; }
    return { u, s, t, yearsAgo, isNow, rho: pick("rho"), hub: pick("hub"), horizon: pick("horizon"), temp: pick("temp") };
  }

  function label(st) {
    if (st.isNow) return "Today";
    if (st.yearsAgo < AGE / YEAR / 2) return yearsAgoLabel(st.yearsAgo);
    return `${friendlyTime(st.t)} after the Big Bang`;
  }

  return {
    AGE, sOf, uOfS, stateAt, label,
    /** Slider position at which an item first exists (null = always shown). */
    uOfAppeared: (a) => (a ? uOfS(sOf(a.seconds_after_big_bang, a.years_ago)) : null),
  };
}

function yearsAgoLabel(y) {
  const fmt = (v) => new Intl.NumberFormat("en", { maximumSignificantDigits: 3 }).format(v);
  if (y >= 1e9) return `${fmt(y / 1e9)} billion years ago`;
  if (y >= 1e6) return `${fmt(y / 1e6)} million years ago`;
  if (y >= 1e3) return `${fmt(y / 1e3)} thousand years ago`;
  return `${fmt(y)} years ago`;
}
