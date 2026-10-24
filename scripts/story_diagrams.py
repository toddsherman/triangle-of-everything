#!/usr/bin/env python3
"""Draw the story page's two diagrams to the chart's real geometry and write them into story/index.html.

Both use the datasets' own numbers: the walls from main_chart.json -> physics.lines, the dots from objects.json
and fundamental_particles.json, and the Hubble wall at earlier moments from cosmic_timeline.json -> history.
Axes are log10 metres and log10 kilograms at equal scale, as in the app, so the slanted walls run at 45 degrees.
Each SVG sits between <!-- diagram:NAME --> and <!-- /diagram:NAME --> markers in the page.
"""

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PAGE = ROOT / "story" / "index.html"

RED, BLUE, INK, STONE, OCHRE, PAPER, PAPER_DEEP = "#B64832", "#31566B", "#1D1C19", "#8D887E", "#B58A43", "#F4F1EA", "#E9E4D9"

main = json.loads((DATA / "main_chart.json").read_text())
L = main["physics"]["lines"]
S, C, HUB, EV = L["schwarzschild_offset"], L["compton_offset"], L["hubble_diameter_log10_m"], L["energy_log10_eV_per_kg"]
P = ((C - S) / 2, (C + S) / 2)                      # the Big Bang corner, where the two slanted walls cross


def objects():
    objs = {o["id"]: o["reference"] for o in json.loads((DATA / "objects.json").read_text())["objects"]}
    parts = {p["id"]: p["reference"] for p in json.loads((DATA / "fundamental_particles.json").read_text())["particles"]}

    def obj(key):
        r = objs[key]
        m = r["log10_mass_kg"]
        if r["width_basis"] == "schwarzschild_diameter":
            return m - S, m
        return r["log10_width_m"], m

    def particle(key):
        m = parts[key]["log10_mass_eV"] - EV
        return C - m, m                               # its Compton wavelength: on the bottom wall

    return obj, particle


class Frame:
    """Equal-scale log axes mapped to SVG pixels."""

    def __init__(self, xr, yr, scale, margin):
        self.xr, self.yr, self.s = xr, yr, scale
        self.left, self.top, self.right, self.bottom = margin
        self.w = self.left + (xr[1] - xr[0]) * scale + self.right
        self.h = self.top + (yr[1] - yr[0]) * scale + self.bottom

    def x(self, v):
        return round(self.left + (v - self.xr[0]) * self.s, 1)

    def y(self, v):
        return round(self.top + (self.yr[1] - v) * self.s, 1)

    def pt(self, p):
        return f"{self.x(p[0])},{self.y(p[1])}"

    def poly(self, pts, fill, opacity=1):
        return f'<polygon points="{" ".join(self.pt(p) for p in pts)}" fill="{fill}"' + (f' opacity="{opacity}"' if opacity != 1 else "") + "/>"

    def line(self, a, b, stroke, width, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<line x1="{self.x(a[0])}" y1="{self.y(a[1])}" x2="{self.x(b[0])}" y2="{self.y(b[1])}" stroke="{stroke}" stroke-width="{width}"{d}/>'


def sup(n):
    return str(n).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))


def walls_diagram():
    obj, particle = objects()
    f = Frame((-40, 33), (-75, 59), 4.2, (50, 10, 12, 40))
    x0, x1, y0, y1 = f.xr[0], f.xr[1], f.yr[0], f.yr[1]
    top_end = (y1 - S, y1)                            # where each slanted wall leaves the frame
    bottom_end = (C - y0, y0)
    T, B = (HUB, HUB + S), (HUB, C - HUB)
    out = [f'<svg viewBox="0 0 {f.w:.0f} {f.h:.0f}" role="img" aria-label="The chart drawn to scale: the black-hole wall rising at 45 degrees, the quantum wall falling at 45 degrees, the Hubble wall upright on the right, with a proton, an atom, a virus, a person, Earth, the Sun, a black hole and a galaxy inside">']
    out.append(f.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], PAPER_DEEP, 0.45))
    out.append(f.poly([(x0, y0), (P[0], y0), (P[0], y1), (x0, y1)], STONE, 0.18))
    out.append(f.poly([(HUB, y0), (x1, y0), (x1, y1), (HUB, y1)], STONE, 0.14))
    out.append(f.poly([P, top_end, (P[0], y1)], RED, 0.10))
    out.append(f.poly([P, bottom_end, (P[0], y0)], BLUE, 0.10))
    out.append(f.poly([P, T, B], PAPER))
    # axes, with a tick every 20 decades
    out.append(f.line((x0, y0), (x1, y0), STONE, 1))
    out.append(f.line((x0, y0), (x0, y1), STONE, 1))
    for v in (-30, -10, 10, 30):
        out.append(f.line((v, y0), (v, y0 - 1.2), STONE, 1))
        out.append(f'<text class="dg-tick" x="{f.x(v)}" y="{f.y(y0) + 15}" text-anchor="middle">10{sup(v)}</text>')
    for v in (-60, -40, -20, 0, 20, 40):
        out.append(f.line((x0, v), (x0 + 1.2, v), STONE, 1))
        out.append(f'<text class="dg-tick" x="{f.x(x0) - 5}" y="{f.y(v) + 4}" text-anchor="end">10{sup(v)}</text>')
    out.append(f'<text class="dg-axis" x="{f.x(x1)}" y="{f.h - 6:.0f}" text-anchor="end">Width (m) →</text>')
    out.append(f'<text class="dg-axis" text-anchor="end" transform="translate(12,{f.y(y1)}) rotate(-90)">Mass (kg) →</text>')
    # the three walls
    out.append(f.line(P, top_end, RED, 2.5))
    out.append(f.line(P, bottom_end, BLUE, 2.5))
    out.append(f.line((HUB, y0), (HUB, y1), INK, 2.5))
    mid_top, mid_bottom = (-18, -18 + S), (6, C - 6)     # wall labels clear of the dots near each wall
    out.append(f'<text class="dg-wall" fill="{RED}" text-anchor="middle" transform="translate({f.x(mid_top[0])},{f.y(mid_top[1])}) rotate(-45) translate(0,-8)">Schwarzschild radius</text>')
    out.append(f'<text class="dg-wall" fill="{BLUE}" text-anchor="middle" transform="translate({f.x(mid_bottom[0])},{f.y(mid_bottom[1])}) rotate(45) translate(0,17)">Compton limit</text>')
    out.append(f'<text class="dg-wall" fill="{INK}" text-anchor="middle" transform="translate({f.x(HUB) + 13},{f.y(-8)}) rotate(90)">Hubble radius</text>')
    out.append(f'<text class="dg-region" text-anchor="middle"><tspan x="{f.x(-20)}" y="{f.y(46)}">Forbidden</tspan><tspan x="{f.x(-20)}" dy="13">by gravity</tspan></text>')
    out.append(f'<text class="dg-region" text-anchor="middle"><tspan x="{f.x(-16)}" y="{f.y(-58)}">Forbidden by</tspan><tspan x="{f.x(-16)}" dy="13">quantum uncertainty</tspan></text>')
    out.append(f'<text class="dg-region" text-anchor="middle" transform="translate({f.x((x0 + P[0]) / 2) + 4},{f.y(30)}) rotate(-90)">Below the Planck length</text>')
    # a few real things, at their real positions: (point, colour, label, dx, dy, anchor)
    dots = [
        (particle("electron"), BLUE, "electron", 7, 16, "start"),
        (particle("proton"), BLUE, "proton", -7, 4, "end"),
        (obj("oxygen_atom"), STONE, "atom", 8, 4, "start"),
        (obj("virus"), STONE, "virus", 8, 4, "start"),
        (obj("humans"), OCHRE, "you", 8, 4, "start"),
        (obj("earth"), STONE, "Earth", 8, 4, "start"),
        (obj("sun"), OCHRE, "the Sun", 8, 4, "start"),
        (obj("ton_618"), RED, "black hole", -8, -4, "end"),
        (obj("milky_way"), STONE, "galaxy", 0, 19, "middle"),
    ]
    for p, colour, label, dx, dy, anchor in dots:
        out.append(f'<circle cx="{f.x(p[0])}" cy="{f.y(p[1])}" r="4.5" fill="{colour}"/>')
        out.append(f'<text class="dg-label" x="{f.x(p[0]) + dx}" y="{f.y(p[1]) + dy}" text-anchor="{anchor}">{label}</text>')
    out.append(f'<circle cx="{f.x(P[0])}" cy="{f.y(P[1])}" r="5.5" fill="{INK}"/>')
    out.append(f'<text class="dg-label dg-strong" x="{f.x(P[0]) + 8}" y="{f.y(P[1]) + 4}">Big Bang</text>')
    out.append(f'<circle cx="{f.x(T[0])}" cy="{f.y(T[1])}" r="5" fill="{INK}"/>')
    out.append(f'<text class="dg-label" x="{f.x(T[0]) - 8}" y="{f.y(T[1]) - 6}" text-anchor="end">Hubble sphere</text>')
    out.append("</svg>")
    return "\n      ".join(out)


def growth_diagram():
    hist = json.loads((DATA / "cosmic_timeline.json").read_text())["history"]["rows"]

    def hub_at(t):
        for a, b in zip(hist, hist[1:]):
            if a[0] <= t <= b[0]:
                k = (math.log10(t) - math.log10(a[0])) / (math.log10(b[0]) - math.log10(a[0]))
                return a[3] + k * (b[3] - a[3])
        return hist[-1][3]

    f = Frame((-54, 34), (-72, 57), 3.4, (8, 10, 8, 30))   # room left of the corner for its label
    moments = [(hub_at(1e-30), "10⁻³⁰ seconds"), (hub_at(1), "1 second"), (HUB, "today")]
    fills = [(STONE, 0.55), ("#D4CEC2", 0.75), (PAPER_DEEP, 1)]
    out = [f'<svg viewBox="0 0 {f.w:.0f} {f.h:.0f}" role="img" aria-label="The triangle at three moments, to scale: tiny at 10 to the minus 30 seconds, most of its final size by one second, and today">']
    for (h, _), (fill, op) in reversed(list(zip(moments, fills))):
        out.append(f.poly([P, (h, h + S), (h, C - h)], fill, op))
    out.append(f.line(P, (f.yr[1] - S, f.yr[1]), RED, 2))
    out.append(f.line(P, (C - f.yr[0], f.yr[0]), BLUE, 2))
    for i, (h, label) in enumerate(moments):
        today = i == len(moments) - 1
        out.append(f.line((h, h + S), (h, C - h), INK, 2.5 if today else 1.5, None if today else "4 3"))
        # below and left of where the wall meets the bottom one, clear of both lines
        out.append(f'<text class="dg-label{" dg-strong" if today else ""}" x="{f.x(h) - 6}" y="{f.y(C - h) + 16}" text-anchor="end">{label}</text>')
    out.append(f'<circle cx="{f.x(P[0])}" cy="{f.y(P[1])}" r="5" fill="{INK}"/>')
    out.append(f'<text class="dg-label dg-strong" x="{f.x(P[0]) - 9}" y="{f.y(P[1]) + 5}" text-anchor="end">Big Bang</text>')
    out.append("</svg>")
    return "\n      ".join(out)


html = PAGE.read_text()
for name, svg in (("walls", walls_diagram()), ("growth", growth_diagram())):
    pattern = re.compile(rf"(<!-- diagram:{name} -->\n)(.*?)(\n\s*<!-- /diagram:{name} -->)", re.S)
    if not pattern.search(html):
        raise SystemExit(f"story/index.html: no diagram:{name} markers")
    html = pattern.sub(lambda m: m.group(1) + "      " + svg + m.group(3), html)
PAGE.write_text(html)
print("wrote both diagrams into", PAGE.relative_to(ROOT))
