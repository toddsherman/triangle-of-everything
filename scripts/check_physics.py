#!/usr/bin/env python3
"""Check that the datasets are physically self-consistent (stdlib only). Run after build_data.py.

  - black holes sit exactly on the Schwarzschild line, particles exactly on the Compton line
  - nothing with real values is denser than a black hole or smaller than its Compton wavelength
  - each time marker's Hubble sphere lies on the black-hole line, and 'now' is the Hubble-radius corner
  - the observable universe's width is exactly the particle horizon, which is wider than the Hubble sphere
  - Lineweaver & Patel points placed by physics sit on the line their basis names, and each same_as link
    names an entry that exists
  - every element's atom and every molecule lies inside the triangle, and the main-chart atoms that stand in for
    elements agree with them
  - first-appearance times lie within cosmic history; the history table starts where all three walls meet
    and ends at today's walls

Exits non-zero if any check fails.
"""

import json
import math
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
TOL = 1e-5          # decades; the site plots from the same numbers, so this is ~0.01 px at maximum zoom


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main():
    main_chart = load("main_chart.json")
    L = main_chart["physics"]["lines"]
    S, Q, PH, SPH, HUB, HORIZON = (L["schwarzschild_offset"], L["compton_offset"], L["photon_offset"],
                                   L["sphere_volume_log10"], L["hubble_diameter_log10_m"],
                                   L["particle_horizon_diameter_log10_m"])
    failures, notes = [], []

    def check(ok, msg):
        if not ok:
            failures.append(msg)

    for o in load("objects.json")["objects"]:
        r = o["reference"]
        if not r or r["log10_mass_kg"] is None:
            continue
        m, w = r["log10_mass_kg"], r["log10_width_m"]
        if r["width_basis"] == "schwarzschild_diameter":
            check(abs(m - w - S) < TOL, f"{o['id']}: black hole off the Schwarzschild line by {m - w - S:+.2e}")
        elif r["width_basis"] == "reduced_compton_wavelength":
            check(abs(m + w - Q) < TOL, f"{o['id']}: off the Compton line by {m + w - Q:+.2e}")
        else:
            check(m - w <= S + TOL, f"{o['id']}: denser than a black hole (M - W = {m - w:.3f} > {S:.3f})")
            check(m + w >= Q - TOL, f"{o['id']}: below the Compton limit (M + W = {m + w:.3f} < {Q:.3f})")
        if r["width_basis"] == "particle_horizon_diameter":
            check(abs(w - HORIZON) < TOL, f"{o['id']}: width {w:.6f} is not the particle horizon {HORIZON:.6f}")
        if w > HUB + TOL:
            notes.append(f"{o['id']} is wider than today's Hubble sphere, so it plots beyond the Hubble-radius wall (expected)")

    check(HORIZON > HUB, "particle horizon should be wider than the Hubble sphere")
    for h in main_chart["physics"]["horizons"]:
        line = {"hubble_radius": HUB, "particle_horizon": HORIZON}[h["id"]]
        check(abs(h["log10_diameter_m"] - line) < TOL, f"horizon {h['id']}: text block disagrees with physics.lines")

    for p in load("fundamental_particles.json")["particles"]:
        r = p["reference"]
        if r["mass_kg"]:
            m = r["log10_mass_eV"] - L["energy_log10_eV_per_kg"]
            check(abs(m + math.log10(r["reduced_compton_wavelength_m"]) - Q) < 1e-3,
                  f"particle {p['id']}: stored Compton wavelength disagrees with its mass")

    for t in load("cosmic_timeline.json")["markers"]:
        horizon = (S - (t["density_log10_kg_m3"] + SPH)) / 2
        check(abs(horizon - t["hubble_diameter_log10_m"]) < TOL,
              f"time {t['id']}: density line meets the black-hole line at {horizon:.6f}, Hubble sphere is "
              f"{t['hubble_diameter_log10_m']:.6f}")
        if t["id"] == "now":
            check(abs(t["hubble_diameter_log10_m"] - HUB) < TOL, "time now: Hubble sphere is not the Hubble-radius edge")

    # cosmic-time data: appearance times inside cosmic history, and the history ends exactly at today's walls
    timeline = load("cosmic_timeline.json")
    hist = timeline["history"]
    age = hist["age_seconds"]
    last = hist["rows"][-1]
    check(abs(last[3] - HUB) < TOL and abs(last[4] - HORIZON) < TOL, "history: last row is not today's Hubble radius / horizon")
    check(all(r[3] - r[4] < TOL for r in hist["rows"]), "history: Hubble sphere wider than the observable universe")
    apex = (Q - S) / 2
    first = hist["rows"][0]
    check(abs(first[3] - apex) < 1e-9 and abs(first[4] - apex) < 1e-9,
          f"history: first moment is not where all three walls meet ({first[3]:.6f} vs apex {apex:.6f})")
    temps = [r[5] for r in hist["rows"]]
    check(all(b <= a + 1e-9 for a, b in zip(temps, temps[1:])), "history: temperature rises somewhere (should only cool)")
    check(max(a - b for a, b in zip(temps, temps[1:])) < 0.6, "history: temperature jumps between neighbouring moments")
    for r in main_chart["regions"]:
        fa = r.get("first_appeared")
        if fa:
            check(0 < fa["seconds_after_big_bang"] <= age, f"region {r['id']}: first_appeared outside cosmic history")
    for name in ("objects.json", "lineweaver_patel.json"):
        for o in load(name)["objects"]:
            fa = o.get("first_appeared")
            if fa:
                check(0 < fa["seconds_after_big_bang"] <= age * (1 + 1e-9), f"{o['id']}: first_appeared outside cosmic history")
    objects_by_id = {o["id"]: o for o in load("objects.json")["objects"]}
    for e in load("elements.json")["elements"]:
        r = e["reference"]
        m, w = r["log10_mass_kg"], r["log10_width_m"]
        check(m - w <= S + TOL and m + w >= Q - TOL, f"element {e['symbol']}: outside the triangle")
        same = e["same_as"]
        if same:
            o = objects_by_id.get(same["id"])
            check(o is not None, f"element {e['symbol']}: same_as {same} names nothing")
            if o:
                ref = o["reference"]
                check(abs(ref["log10_mass_kg"] - m) < 1e-3 and abs(ref["log10_width_m"] - w) < 1e-3,
                      f"element {e['symbol']}: disagrees with {same['id']}")
    for mol in load("molecules.json")["molecules"]:
        r = mol["reference"]
        m, w = r["log10_mass_kg"], r["log10_width_m"]
        check(m - w <= S + TOL and m + w >= Q - TOL, f"molecule {mol['id']}: outside the triangle")
        check(w <= HUB, f"molecule {mol['id']}: wider than the Hubble sphere")
    for o in load("stellar_evolution.json")["objects"] + load("fundamental_particles.json")["particles"] + \
            load("elements.json")["elements"] + load("molecules.json")["molecules"]:
        fa = o.get("first_appeared")
        if fa:
            check(0 < fa["seconds_after_big_bang"] <= age * (1 + 1e-9), f"{o['id']}: first_appeared outside cosmic history")

    ids = {
        "objects": {o["id"] for o in load("objects.json")["objects"]},
        "stellar_evolution": {o["id"] for o in load("stellar_evolution.json")["objects"]},
        "fundamental_particles": {p["id"] for p in load("fundamental_particles.json")["particles"]},
        "main_chart.physics.horizons": {h["id"] for h in main_chart["physics"]["horizons"]},
        "main_chart.triangle": set(main_chart["triangle"]),
    }
    for o in load("lineweaver_patel.json")["objects"]:
        same = o["same_as"]
        if same:
            check(same["id"] in ids.get(same["dataset"], ()), f"LP {o['id']}: same_as {same} names nothing")
        pl, basis = o["plotted"], o["plotted"]["basis"]
        m, w = pl["log10_mass_kg"], pl["log10_width_m"]
        if basis.startswith("black_hole") or basis in ("hubble_sphere_today", "planck_point"):
            check(abs(m - w - S) < TOL, f"LP {o['id']}: off the Schwarzschild line")
        if basis.startswith("compton") or basis == "planck_point":
            check(abs(m + w - Q) < TOL, f"LP {o['id']}: off the Compton line")
        if basis.startswith("photon"):
            check(abs(m + w - PH) < TOL, f"LP {o['id']}: off the photon line")
        if basis == "hubble_sphere_today":
            check(abs(w - HUB) < TOL, f"LP {o['id']}: not at the Hubble-radius edge")

    for n in notes:
        print("note:", n)
    if failures:
        print(f"\n{len(failures)} check(s) failed:")
        for f in failures:
            print("  FAIL", f)
        sys.exit(1)
    print("all physics checks passed")


if __name__ == "__main__":
    main()
