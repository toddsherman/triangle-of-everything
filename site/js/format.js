// Number formatting for log10 quantities: scientific notation plus a human-friendly unit.

const SUP = { "-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹" };
export const sup = (n) => String(n).split("").map((c) => SUP[c] ?? c).join("");

const LOG_MSUN = 30.2986;
const LOG_MEARTH = 24.7761;
const LOG_EV_KG = -35.749;
const LOG_LY = 15.976;
const LOG_AU = 11.175;

const longCompact = new Intl.NumberFormat("en", { notation: "compact", compactDisplay: "long", maximumSignificantDigits: 3 });
const plain = new Intl.NumberFormat("en", { maximumSignificantDigits: 3 });

export function sci(log10, digits = 3) {
  if (log10 == null || !Number.isFinite(log10)) return "—";
  let e = Math.floor(log10);
  let m = Math.pow(10, log10 - e);
  if (Number(m.toPrecision(digits)) >= 10) { m = 1; e += 1; }
  if (e >= -2 && e <= 4) return plain.format(Math.pow(10, log10));
  return `${Number(m.toPrecision(digits))} × 10${sup(e)}`;
}

/** A plain number (10^log) that reads well: 1.2, 340, 5.6 million, 3 × 10¹⁸. */
export function nice(log10) {
  if (log10 > -3 && log10 < 15) return log10 >= 4 ? longCompact.format(Math.pow(10, log10)) : plain.format(Math.pow(10, log10));
  return sci(log10);
}

const PREFIX_G = [[-3, "mg"], [-6, "µg"], [-9, "ng"], [-12, "pg"], [-15, "fg"], [-18, "ag"], [-21, "zg"], [-24, "yg"]];

export function friendlyMass(logKg) {
  if (logKg == null) return "";
  if (logKg >= 28.5) return `${nice(logKg - LOG_MSUN)} solar masses`;
  if (logKg >= 21.5) return `${nice(logKg - LOG_MEARTH)} Earth masses`;
  if (logKg >= 3) return `${nice(logKg - 3)} tonnes`;
  if (logKg >= 0) return `${nice(logKg)} kg`;
  if (logKg >= -3) return `${nice(logKg + 3)} g`;
  const logG = logKg + 3;
  if (logG >= -24) {
    for (const [p, name] of PREFIX_G) if (logG >= p) return `${nice(logG - p)} ${name}`;
  }
  const logEv = logKg - LOG_EV_KG;
  for (const [p, name] of [[9, "GeV"], [6, "MeV"], [3, "keV"], [0, "eV"]]) if (logEv >= p) return `${nice(logEv - p)} ${name}/c²`;
  return `${sci(logEv)} eV/c²`;
}

const PREFIX_M = [[3, "km"], [0, "m"], [-2, "cm"], [-3, "mm"], [-6, "µm"], [-9, "nm"], [-12, "pm"], [-15, "fm"]];

export function friendlyLength(logM) {
  if (logM == null) return "";
  if (logM >= 16) return `${nice(logM - LOG_LY)} light-years`;
  if (logM >= 12.5) return `${nice(logM - LOG_AU)} AU`;
  for (const [p, name] of PREFIX_M) if (logM >= p) return `${nice(logM - p)} ${name}`;
  return `${sci(logM)} m`;
}

export function friendlyEnergy(logEv) {
  if (logEv == null) return "";
  for (const [p, name] of [[12, "TeV"], [9, "GeV"], [6, "MeV"], [3, "keV"], [0, "eV"], [-3, "meV"], [-6, "µeV"]]) {
    if (logEv >= p && logEv < p + 3) return `${nice(logEv - p)} ${name}`;
  }
  return `${sci(logEv)} eV`;
}

const YEAR = 3.156e7;
// Times under a second get the largest SI unit that keeps the number at 1 or more, down to the smallest SI
// prefix (quecto, 10^-30 s). Before that SI runs out, and the natural unit is the Planck time.
const PLANCK_TIME = 5.391247e-44;
const SI_TIMES = [[1e-3, "millisecond"], [1e-6, "microsecond"], [1e-9, "nanosecond"], [1e-12, "picosecond"],
  [1e-15, "femtosecond"], [1e-18, "attosecond"], [1e-21, "zeptosecond"], [1e-24, "yoctosecond"],
  [1e-27, "rontosecond"], [1e-30, "quectosecond"]];
const count = (n, unit) => {
  const text = n >= 1e6 ? longCompact.format(n) : plain.format(n);   // 18.6 million, 1,860, 3.74
  return `${text} ${unit}${text === "1" ? "" : "s"}`;
};

export function friendlyTime(seconds) {
  if (seconds == null) return "";
  const lg = Math.log10(seconds);
  if (seconds < 1) {
    const si = SI_TIMES.find(([unit]) => seconds >= unit * 0.9995);   // 999.6 fs reads as 1 picosecond
    return si ? count(seconds / si[0], si[1]) : count(seconds / PLANCK_TIME, "Planck time");
  }
  if (seconds < 120) return count(seconds, "second");
  if (seconds < 7200) return `${plain.format(seconds / 60)} minutes`;
  if (seconds < YEAR) return `${plain.format(seconds / 86400)} days`;
  const ly = lg - Math.log10(YEAR);
  if (ly < 15) return `${nice(ly)} years`;
  return `${sci(ly)} years`;
}

/** "drawn 12× too heavy" style comparison of a drawn (chart) value with the real one. */
export function compare(chartLog, realLog, bigger, smaller) {
  if (chartLog == null || realLog == null) return null;
  const d = chartLog - realLog;
  if (Math.abs(d) < 0.3) return { ok: true, text: "drawn about right" };
  const factor = Math.pow(10, Math.abs(d));
  const f = factor >= 1000 ? `10${sup(Math.round(Math.abs(d)))}` : plain.format(factor);
  return { ok: false, text: `drawn ${f}× too ${d > 0 ? bigger : smaller}` };
}

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
