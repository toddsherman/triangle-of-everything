#!/usr/bin/env python3
"""Build the "Triangle of Everything" datasets.

Every reading below was transcribed by hand from the two source images:

  Triangle_of_Everything.png  (7300 x 7639) - the illustrated poster ("main chart")
  b6y2fthj95ie1.png           (2121 x 3000) - Lineweaver & Patel, "All objects" plot

Pixel coordinates are in full-resolution source pixels (origin top-left).
Axis calibrations are least-squares fits to tick marks detected in the images.

Two kinds of values are kept strictly apart:
  chart.*      - what the image shows (derived from where an icon sits on the axes)
  reference.*  - standard real-world values compiled for this dataset (NOT read
                 from the image) so the site can also plot physically accurate data.

Run:  python3 scripts/build_data.py      (stdlib only; writes ./data)
"""

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"

MAIN_IMG = {"file": "Triangle_of_Everything.png", "width": 7300, "height": 7639}
LP_IMG = {"file": "b6y2fthj95ie1.png", "width": 2121, "height": 3000}

# --- physical constants (SI) -------------------------------------------------
G = 6.674e-11
C = 2.998e8
HBAR = 1.0546e-34
M_SUN = 1.989e30
M_EARTH = 5.972e24
M_JUP = 1.898e27
R_SUN_KM = 6.957e5
R_EARTH_KM = 6371.0
R_JUP_KM = 69911.0
EV_KG = 1.78266e-36          # 1 eV/c^2 in kg
K_EV = 8.617e-5              # Boltzmann constant, eV per kelvin
LY = 9.4607e15
PC = 3.0857e16
H_PLANCK = 2 * math.pi * HBAR
K_B = 1.380649e-23
T_CMB = 2.7255

# --- cosmology: flat LambdaCDM, Planck 2018 (TT,TE,EE+lowE+lensing+BAO) -----
H0_KM_S_MPC = 67.66
OMEGA_M = 0.3111
OMEGA_R = 9.15e-5                       # photons + relativistic neutrinos
OMEGA_L = 1 - OMEGA_M - OMEGA_R
H0 = H0_KM_S_MPC * 1e3 / (PC * 1e6)     # s^-1
RHO_CRIT = 3 * H0**2 / (8 * math.pi * G)

# --- exact line offsets (log10, SI). The site reads these instead of rounding its own. ----
# Width W is a full width (diameter) in metres, mass M in kg.
LOG_SCHW = math.log10(C**2 / (4 * G))       # black holes:  M = W + LOG_SCHW   (W = 4GM/c^2)
LOG_COMPTON = math.log10(HBAR / C)          # quantum limit: M = -W + LOG_COMPTON (W = hbar/Mc)
LOG_PHOTON = math.log10(H_PLANCK / C)       # photons: E/c^2 = h/(lambda c), W = lambda
LOG_SPHERE = math.log10(math.pi / 6)        # sphere of diameter W has volume (pi/6) W^3
LOG_HUBBLE_W = math.log10(2 * C / H0)       # diameter of today's Hubble sphere
NUCLEAR_DENSITY = 3.6e17                    # kg/m^3, as used by Jacobs, Starkman & Lynn (2015)


def _particle_horizon_diameter(a_min=1e-35, steps=200_000):
    """Diameter (m) of the observable universe today: twice the comoving particle horizon c * integral dt/a,
    i.e. c * integral da / (a^2 H(a)), for the same flat LambdaCDM model."""
    hub = lambda a: H0 * math.sqrt(OMEGA_R / a**4 + OMEGA_M / a**3 + OMEGA_L)
    chi = a_min / (H0 * math.sqrt(OMEGA_R))     # radiation era below a_min: integral of da / sqrt(Omega_r) / H0
    x0, x1 = math.log(a_min), 0.0
    dx = (x1 - x0) / steps
    f = lambda x: 1 / (math.exp(x) * hub(math.exp(x)))      # integrand in ln a
    total = 0.5 * (f(x0) + f(x1)) + sum(f(x0 + i * dx) for i in range(1, steps))
    return 2 * C * (chi + total * dx)


PARTICLE_HORIZON_D = _particle_horizon_diameter()
LOG_PARTICLE_HORIZON_W = math.log10(PARTICLE_HORIZON_D)
GLY_M = 1e9 * LY


def lg(v):
    return None if v in (None, 0) else round(math.log10(v), 6)


def r3(v):
    return None if v is None else round(v, 3)


def schwarzschild_diameter_m(mass_kg):
    return 4 * G * mass_kg / C**2


def norm(px, img):
    return [round(px[0] / img["width"], 5), round(px[1] / img["height"], 5)]


def point(px, img):
    return {"px": [round(px[0], 1), round(px[1], 1)], "norm": norm(px, img)}


def fit(pairs):
    """Least squares px = a + b*value; returns (a, b)."""
    n = len(pairs)
    sv = sum(v for v, _ in pairs)
    sp = sum(p for _, p in pairs)
    svv = sum(v * v for v, _ in pairs)
    svp = sum(v * p for v, p in pairs)
    b = (n * svp - sv * sp) / (n * svv - sv * sv)
    return (sp - b * sv) / n, b


class Axis:
    """Linear log-axis: value = (px - a) / b."""

    def __init__(self, name, unit, pixel_axis, pairs, note=""):
        self.name, self.unit, self.pixel_axis, self.note = name, unit, pixel_axis, note
        self.a, self.b = fit(pairs)
        self.pairs = pairs

    def value(self, px):
        return (px - self.a) / self.b

    def pixel(self, value):
        return self.a + self.b * value

    def residual(self):
        return max(abs(self.value(p) - v) for v, p in self.pairs)

    def describe(self):
        return {
            "quantity": self.name,
            "unit": self.unit,
            "pixel_axis": self.pixel_axis,
            "formula": f"value = ({self.pixel_axis} - {self.a:.2f}) / {self.b:.4f}",
            "px_at_zero": round(self.a, 2),
            "px_per_decade": round(self.b, 4),
            "max_tick_residual_decades": round(self.residual(), 3),
            "calibration_ticks": [{"value": v, "px": p} for v, p in self.pairs],
            "note": self.note,
        }


# =============================================================================
# MAIN CHART calibration (tick marks detected by colour in the full image)
# =============================================================================
WIDTH_TICKS_X = [2197.5, 2336.0, 2474.5, 2613.5, 2752.0, 2890.5, 3029.0, 3167.5, 3306.5, 3444.5,
                 3583.5, 3722.0, 3860.5, 3999.5, 4137.5, 4276.5, 4415.5, 4553.5, 4692.5, 4830.5]
MASS_TICKS_Y = [1793.0, 1931.5, 2070.0, 2208.5, 2347.0, 2485.5, 2623.5, 2762.5, 2900.5, 3039.5,
                3177.5, 3316.5, 3454.5, 3593.5, 3731.5, 3870.5, 4008.5, 4147.5, 4285.5, 4424.5,
                4562.5, 4701.5, 4839.5, 4978.5, 5116.5, 5255.5, 5393.5, 5532.5, 5670.5, 5810.5,
                5948.5, 6087.5, 6225.5, 6367.5, 6505.5]
ENERGY_TICKS_Y = [4399.0, 4537.5, 4676.0, 4814.0, 4953.0, 5091.0, 5230.0, 5368.0, 5507.0, 5645.0,
                  5784.0, 5922.5, 6061.0, 6199.0, 6338.0, 6476.0, 6615.0, 6753.5, 6892.0, 7030.5]

W_AX = Axis("log10 width", "m", "x", [(-33 + 3 * i, x) for i, x in enumerate(WIDTH_TICKS_X)],
            "Bottom axis 'WIDTH 10^n m'. Printed labels -33..24 sit on these ticks and are correct.")
M_AX = Axis("log10 mass", "kg", "y", [(48 - 3 * i, y) for i, y in enumerate(MASS_TICKS_Y)],
            "Right axis 'MASS 10^n kg'. Tick values verified by the solar-mass, tonne and kg reference "
            "lines; several printed labels above 0 are wrong (see errata).")
E_AX = Axis("log10 energy", "eV", "y", [(27 - 3 * i, y) for i, y in enumerate(ENERGY_TICKS_Y)],
            "Left axis 'ENERGY 10^n eV' (also used as temperature). It is the mass axis shifted by "
            "~35.4 decades (E = mc^2; the exact shift is 35.75).")


def main_values(px):
    w, m = W_AX.value(px[0]), M_AX.value(px[1])
    return {
        "log10_width_m": r3(w),
        "log10_mass_kg": r3(m),
        "log10_energy_eV": r3(E_AX.value(px[1])),
        "log10_density_proxy_kg_m3": r3(m - 3 * w),
    }


# Density ruler along the top (tall ticks every 9 decades; ticks are slanted along density lines).
DENSITY_TALL_TICKS_X = [3211.5, 3349.5, 3487.5, 3625.5, 3763.5, 3902.0, 4040.5, 4178.5, 4316.5,
                        4454.5, 4592.5, 4730.5, 4868.5, 5006.5, 5144.5, 5282.5, 5420.5, 5558.5,
                        5692.5, 5830.5, 5967.5, 6106.5, 6244.5, 6382.5, 6517.5, 6655.5, 6792.5]
DENSITY_PRINTED = {0: 92, 1: 83, 2: 74, 3: 65, 4: 57, 5: 48, 6: 39, 7: 30, 8: 21, 9: 12, 10: 3,
                   11: -6, 12: -15, 13: -24, 14: -33, 15: -42, 16: -51, 17: -60, 23: -120, 26: -147}
D_AX = Axis("log10 density", "g/L (= kg/m^3)", "x at ruler row y~1197",
            [(93 - 9 * i, x) for i, x in enumerate(DENSITY_TALL_TICKS_X)],
            "Top ruler 'DENSITY 10^n g/L'. Values taken as a uniform 9 decades per tall tick, anchored "
            "on the printed '3' (water). Only valid along the ruler row; density lines run diagonally.")
DENSITY_RULER_Y = 1197

# =============================================================================
# MAIN CHART objects
# =============================================================================
# ref widths: 'diameter' unless width_basis says otherwise. Confidence: high | medium | low.
MAIN_OBJECTS = [
    # --- cosmic structure ---------------------------------------------------
    dict(id="observable_universe", label="OBSERVABLE UNIVERSE", name="Observable Universe",
         category="cosmic_structure", icon=(4900, 1605), label_px=(5254, 1591),
         ref=dict(mass_kg=1.5e53, width_basis="particle_horizon_diameter", confidence="medium",
                  notes="Ordinary (baryonic) matter only; with dark matter ~9e53 kg. Width = diameter of the particle "
                        "horizon (~93 billion ly), computed from the same LambdaCDM model as the Hubble radius - about "
                        "3x the Hubble sphere, so it plots on the dashed observable-universe edge."),
         desc="Everything close enough that its light has reached us since the Big Bang - about 93 billion light-years across."),
    dict(id="bootes_void", label="BOOTES VOID", name="Boötes Void", category="cosmic_structure",
         icon=(4880, 1725), label_px=(4657, 1707),
         ref=dict(mass_kg=1e46, width_m=3.1e24, confidence="low",
                  notes="Diameter ~330 million ly (~100 Mpc). Mass is a rough estimate (underdense matter in that volume)."),
         desc="One of the largest known cosmic voids: a nearly empty region ~330 million light-years across in the direction of Boötes."),
    dict(id="laniakea_supercluster", label="LANIKEA SUPERCLUSTER", name="Laniakea Supercluster",
         category="cosmic_structure", icon=(4850, 1810), label_px=(4590, 1815),
         ref=dict(mass_kg=1e17 * M_SUN, width_m=160e6 * PC, confidence="medium",
                  notes="~1e17 solar masses, ~520 million ly (160 Mpc) across."),
         desc="The galaxy supercluster that contains the Milky Way (printed on the chart as 'LANIKEA')."),
    dict(id="el_gordo", label="EL GORDO", name="El Gordo (ACT-CL J0102-4915)", category="cosmic_structure",
         icon=(4750, 1935), label_px=(4943, 1958),
         ref=dict(mass_kg=2e15 * M_SUN, width_m=1.1e23, confidence="low",
                  notes="~2e15 solar masses; width ~2 x r200 (~3.6 Mpc)."),
         desc="A massive pair of colliding galaxy clusters about 7 billion light-years away - one of the heaviest distant clusters known."),
    dict(id="milky_way", label="MILKY WAY", name="Milky Way", category="galaxy",
         icon=(4680, 2065), label_px=(4885, 2062),
         ref=dict(mass_kg=1.5e12 * M_SUN, width_m=1e5 * LY, confidence="medium",
                  notes="Total mass including dark-matter halo; width = stellar disc (~100,000 ly)."),
         desc="Our home galaxy, a barred spiral about 100,000 light-years across."),
    dict(id="smc_galaxy", label="SMC GALAXY", name="Small Magellanic Cloud", category="galaxy",
         icon=(4665, 2200), label_px=(4885, 2210),
         ref=dict(mass_kg=7e9 * M_SUN, width_m=18900 * LY, confidence="medium",
                  notes="~7e9 solar masses, ~19,000 ly across."),
         desc="A dwarf galaxy orbiting the Milky Way, visible to the naked eye from the Southern Hemisphere."),
    dict(id="globular_clusters", label="GLOBULAR CLUSTERS", name="Globular clusters", category="star_cluster",
         icon=(4555, 2375), label_px=(4855, 2395),
         ref=dict(mass_kg=3e5 * M_SUN, width_m=1e18, confidence="medium", representative=True,
                  notes="Typical: 1e5-1e6 solar masses, ~100 ly across."),
         desc="Dense, spherical swarms of hundreds of thousands of old stars orbiting a galaxy."),
    # --- black holes ----------------------------------------------------------
    dict(id="ton_618", label="TON618", name="TON 618", category="black_hole", subcategory="supermassive",
         icon=(4435, 2055), label_px=(4252, 2073),
         ref=dict(mass_kg=6.6e10 * M_SUN, width_basis="schwarzschild_diameter", confidence="medium",
                  notes="~6.6e10 solar masses."),
         desc="A hyper-luminous quasar powered by one of the most massive black holes known."),
    dict(id="cygnus_a", label="CYGNUS-A", name="Cygnus A", category="black_hole", subcategory="supermassive",
         icon=(4270, 2200), label_px=(4103, 2222),
         ref=dict(mass_kg=2.5e9 * M_SUN, width_basis="schwarzschild_diameter", confidence="medium",
                  notes="Central black hole ~2.5e9 solar masses (the radio galaxy itself is far larger)."),
         desc="A powerful radio galaxy whose central supermassive black hole drives jets hundreds of thousands of light-years long."),
    dict(id="sagittarius_a_star", label="SAG A", name="Sagittarius A*", category="black_hole", subcategory="supermassive",
         icon=(4105, 2385), label_px=(4235, 2405),
         ref=dict(mass_kg=4.3e6 * M_SUN, width_basis="schwarzschild_diameter", confidence="high",
                  notes="~4.3e6 solar masses."),
         desc="The supermassive black hole at the centre of the Milky Way, imaged by the Event Horizon Telescope in 2022."),
    dict(id="lb_1", label="LB1", name="LB-1", category="black_hole", subcategory="stellar",
         icon=(3975, 2510), label_px=(4075, 2535),
         ref=dict(mass_kg=70 * M_SUN, width_basis="schwarzschild_diameter", confidence="low",
                  notes="The 2019 claim of a ~70 solar-mass black hole; later analyses favour a much smaller black hole or none."),
         desc="A binary system announced in 2019 as hosting a surprisingly heavy stellar black hole; the claim has since been disputed."),
    dict(id="v616_monocerotis", label="MONOCEROTIS", name="V616 Monocerotis (A0620-00)", category="black_hole",
         subcategory="stellar", ident="probable", icon=(3885, 2595), label_px=(3873, 2683),
         ref=dict(mass_kg=6.6 * M_SUN, width_basis="schwarzschild_diameter", confidence="medium",
                  notes="Identification inferred from the label 'MONOCEROTIS'; ~6.6 solar masses."),
         desc="Probably V616 Monocerotis, one of the nearest known stellar-mass black holes (~3,000 light-years away)."),
    dict(id="primordial_black_hole", label=None, name="Primordial black hole", category="black_hole",
         subcategory="primordial", hypothetical=True, ident="inferred", icon=(3116, 3367),
         ref=dict(mass_kg=1e14, width_basis="schwarzschild_diameter", confidence="low", representative=True,
                  notes="Hypothetical. Mass chosen near where the poster draws it; a black hole's width follows "
                        "from its mass (Schwarzschild diameter), so it sits exactly on the black-hole line. "
                        "The poster draws it slightly inside the forbidden region."),
         desc="Unlabelled icon on the Schwarzschild line inside the 'primordial black holes*' band: a hypothetical black hole formed in the early universe."),
    # --- stars & planets (inside the stellar-evolution zoom box) -------------
    dict(id="neutron_star", label=None, name="Neutron star", category="stellar_remnant", ident="tentative",
         icon=(3960, 2626), ref=dict(mass_kg=1.4 * M_SUN, width_m=2.4e4, confidence="medium", representative=True),
         desc="Unlabelled small dark sphere (tentative): a collapsed stellar core ~20 km across, denser than an atomic nucleus."),
    dict(id="white_dwarfs", schematic=True, label=None, name="White dwarfs", category="stellar_remnant", ident="tentative",
         icon=(4220, 2540), extra_icons=[(4235, 2520), (4205, 2560)],
         ref=dict(mass_kg=0.6 * M_SUN, width_m=1.7e7, confidence="medium", representative=True),
         desc="Unlabelled white spheres (tentative): Earth-sized remnants of Sun-like stars, supported by electron degeneracy pressure."),
    dict(id="sun", label="SUN", name="Sun", category="star", icon=(4150, 2605), label_px=(4375, 2535),
         ref=dict(mass_kg=M_SUN, width_m=1.3927e9, confidence="high"),
         desc="Our star: a G-type main-sequence star holding 99.8% of the Solar System's mass."),
    dict(id="red_dwarfs", schematic=True, label=None, name="Red dwarfs", category="star", ident="tentative",
         icon=(4268, 2628), extra_icons=[(4240, 2640), (4295, 2615)],
         ref=dict(mass_kg=0.122 * M_SUN, width_m=2.14e8, confidence="medium", representative=True,
                  notes="Values for Proxima Centauri."),
         desc="Unlabelled red spheres (tentative): small cool stars, the most common kind in the galaxy. The 'STARS & PLANETS' arrow points here."),
    dict(id="brown_dwarf", label=None, name="Brown dwarf", category="substellar", ident="tentative",
         icon=(4122, 2678), ref=dict(mass_kg=0.04 * M_SUN, width_m=1.4e8, confidence="medium", representative=True),
         desc="Unlabelled banded sphere (tentative): a 'failed star' of ~13-80 Jupiter masses, too light to fuse hydrogen."),
    dict(id="jupiter", label="JUPITER", name="Jupiter", category="planet", icon=(4079, 2757), label_px=(4316, 2799),
         ref=dict(mass_kg=M_JUP, width_m=1.3982e8, confidence="high"),
         desc="The largest planet, more than twice as massive as all the other planets combined."),
    dict(id="saturn", label=None, name="Saturn", category="planet", ident="visual", icon=(4085, 2820),
         ref=dict(mass_kg=5.683e26, width_m=1.1646e8, confidence="high"),
         desc="Unlabelled ringed planet: the gas giant whose average density is lower than water's."),
    dict(id="uranus", schematic=True, label=None, name="Uranus", category="planet", ident="visual", icon=(4164, 2852),
         ref=dict(mass_kg=8.681e25, width_m=5.0724e7, confidence="high"),
         desc="Unlabelled cyan planet: the ice giant that rotates on its side."),
    dict(id="neptune", schematic=True, label=None, name="Neptune", category="planet", ident="visual", icon=(4201, 2852),
         ref=dict(mass_kg=1.024e26, width_m=4.9244e7, confidence="high"),
         desc="Unlabelled blue planet: the outermost ice giant."),
    dict(id="earth", label="EARTH", name="Earth", category="planet", icon=(4033, 2902), label_px=(4259, 2917),
         ref=dict(mass_kg=M_EARTH, width_m=1.2742e7, confidence="high"),
         desc="Our home planet - the densest planet in the Solar System."),
    dict(id="venus", schematic=True, label=None, name="Venus", category="planet", ident="tentative", icon=(3852, 2927),
         ref=dict(mass_kg=4.867e24, width_m=1.2104e7, confidence="high"),
         desc="Unlabelled tan planet with an arrow pointing at Earth (tentative: Venus, Earth's near-twin in size)."),
    dict(id="mercury", schematic=True, label=None, name="Mercury", category="planet", ident="tentative", icon=(4128, 2947),
         ref=dict(mass_kg=3.301e23, width_m=4.879e6, confidence="high"),
         desc="Unlabelled grey planet (tentative): the smallest planet."),
    dict(id="mars", schematic=True, label=None, name="Mars", category="planet", ident="tentative", icon=(4162, 2947),
         ref=dict(mass_kg=6.417e23, width_m=6.779e6, confidence="high"),
         desc="Unlabelled orange planet (tentative): about half Earth's diameter."),
    dict(id="moon", label="MOON", name="Moon", category="moon", icon=(4002, 2994), label_px=(4227, 3008),
         ref=dict(mass_kg=7.342e22, width_m=3.4748e6, confidence="high"),
         desc="Earth's natural satellite, about a quarter of Earth's diameter."),
    dict(id="pluto", schematic=True, label=None, name="Pluto", category="dwarf_planet", ident="tentative", icon=(3813, 2987),
         ref=dict(mass_kg=1.303e22, width_m=2.3772e6, confidence="high"),
         desc="Unlabelled pale body with an arrow pointing at the Moon (tentative: Pluto)."),
    dict(id="ceres", schematic=True, label=None, name="Ceres", category="dwarf_planet", ident="tentative", icon=(4092, 3078),
         ref=dict(mass_kg=9.38e20, width_m=9.39e5, confidence="high"),
         desc="Unlabelled small grey body (tentative): the largest object in the asteroid belt."),
    dict(id="enceladus", label="ENCELADUS", name="Enceladus", category="moon", icon=(3957, 3130), label_px=(4256, 3131),
         ref=dict(mass_kg=1.08e20, width_m=5.04e5, confidence="high"),
         desc="A small icy moon of Saturn that sprays water from a subsurface ocean."),
    dict(id="phobos", label="PHOBOS & DEIMOS", name="Phobos", category="moon", icon=(3965, 3287), label_px=(4170, 3305),
         ref=dict(mass_kg=1.0659e16, width_m=2.25e4, confidence="high", notes="Mean diameter."),
         desc="The larger of Mars's two small, lumpy moons."),
    dict(id="deimos", label="PHOBOS & DEIMOS", name="Deimos", category="moon", icon=(3928, 3358), label_px=(4170, 3305),
         ref=dict(mass_kg=1.4762e15, width_m=1.24e4, confidence="high", notes="Mean diameter."),
         desc="The smaller, outer moon of Mars."),
    dict(id="itokawa", label="ITOKAWA", name="25143 Itokawa", category="asteroid", icon=(3834, 3453), label_px=(4124, 3449),
         ref=dict(mass_kg=3.51e10, width_m=330, confidence="high", notes="Mean diameter; 535 x 294 x 209 m."),
         desc="A peanut-shaped rubble-pile asteroid sampled by Japan's Hayabusa probe in 2005."),
    # --- human scale -----------------------------------------------------------
    dict(id="great_pyramid", label="GREAT PYRAMID", name="Great Pyramid of Giza", category="human_made",
         icon=(3820, 3541), label_px=(4162, 3553),
         ref=dict(mass_kg=6e9, width_m=230.3, width_basis="base_side", confidence="medium"),
         desc="The largest of the Giza pyramids, built around 2560 BCE."),
    dict(id="las_vegas_sphere", label="LAS VEGAS SPHERE", name="Sphere (Las Vegas)", category="human_made",
         icon=(3777, 3666), label_px=(4151, 3675),
         ref=dict(mass_kg=1e7, width_m=157, confidence="low", notes="Width (516 ft) is reliable; mass is an order-of-magnitude estimate."),
         desc="A spherical entertainment venue opened in 2023, wrapped in LED panels - 157 m wide and 112 m tall."),
    dict(id="giant_sequoia", label=None, name="Tree", category="life", ident="visual",
         icon=(3771, 3732),
         ref=dict(mass_kg=1.9e6, width_m=11, width_basis="trunk_base_diameter", confidence="low",
                  notes="Values for General Sherman (height 84 m); the chart position (~1e6 kg, ~11 m) fits a giant sequoia."),
         desc="Unlabelled tree icon between the Sphere and the whale; its position (~1e6 kg, ~11 m) matches a giant sequoia, the most massive tree species."),
    dict(id="blue_whale", label="BLUE WHALE", name="Blue whale", category="life", icon=(3820, 3802), label_px=(4042, 3831),
         ref=dict(mass_kg=1.5e5, width_m=25, width_basis="length", confidence="medium"),
         desc="The largest animal known to have ever lived, up to ~30 m long."),
    dict(id="hippopotamus", label=None, name="Hippopotamus", category="life", ident="visual", icon=(3721, 3833),
         ref=dict(mass_kg=1.5e3, width_m=3.5, width_basis="length", confidence="medium"),
         desc="Unlabelled hippopotamus beside the blue whale."),
    dict(id="humans", label="HUMANS", name="Humans", category="life", icon=(3732, 3932), label_px=(3952, 3945),
         ref=dict(mass_kg=70, width_m=1.7, width_basis="height", confidence="medium", representative=True),
         desc="Homo sapiens - a typical adult is about 1.7 m tall and 70 kg."),
    dict(id="soccer_ball", label=None, name="Soccer ball", category="everyday_object", ident="visual", icon=(3711, 4035),
         ref=dict(mass_kg=0.43, width_m=0.22, confidence="high"),
         desc="Unlabelled football (soccer ball); a regulation size-5 ball is ~22 cm across and ~430 g."),
    dict(id="hedgehog", label="HEDGEHOG", name="Hedgehog", category="life", icon=(3675, 4068), label_px=(3934, 4084),
         ref=dict(mass_kg=0.8, width_m=0.25, width_basis="length", confidence="medium"),
         desc="A small spiny mammal, typically 15-30 cm long."),
    dict(id="penny", label="PENNY", name="US penny", category="everyday_object", icon=(3637, 4131), label_px=(3856, 4152),
         ref=dict(mass_kg=2.5e-3, width_m=0.01905, confidence="high"),
         desc="A US one-cent coin: 19.05 mm across, 2.5 g."),
    dict(id="ladybug", label="LADYBUGS", name="Ladybug", category="life", icon=(3577, 4240), label_px=(3871, 4255),
         ref=dict(mass_kg=2e-5, width_m=7e-3, width_basis="length", confidence="medium"),
         desc="A small beetle (family Coccinellidae), typically 5-8 mm long."),
    dict(id="grain_of_salt", label="GRAIN OF SALT", name="Grain of salt", category="everyday_object",
         icon=(3551, 4385), label_px=(3877, 4394),
         ref=dict(mass_kg=6e-8, width_m=3e-4, confidence="medium"),
         desc="A single crystal of table salt, about 0.3 mm on a side. It sits on the 1 Planck-mass line."),
    # --- microscopic ------------------------------------------------------------
    dict(id="red_blood_cell", label="RED BLOOD CELL", name="Red blood cell", category="cell",
         icon=(3494, 4526), label_px=(3856, 4540),
         ref=dict(mass_kg=1e-13, width_m=7.5e-6, confidence="medium"),
         desc="A disc-shaped cell ~7.5 µm across that carries oxygen around the body."),
    dict(id="bacterium", label="BACTERIUM", name="Bacterium", category="microbe", icon=(3458, 4718), label_px=(3719, 4751),
         ref=dict(mass_kg=1e-15, width_m=2e-6, width_basis="length", confidence="medium", notes="E. coli."),
         desc="A single-celled microbe; E. coli is about 2 µm long and weighs about a picogram."),
    dict(id="virus", label="VIRUS", name="Virus", category="microbe", icon=(3370, 4842), label_px=(3618, 4886),
         ref=dict(mass_kg=1e-18, width_m=1e-7, confidence="medium", notes="SARS-CoV-2 (the icon is a coronavirus)."),
         desc="A virus particle - SARS-CoV-2, for example, is about 100 nm across and weighs about a femtogram."),
    dict(id="rna_strand", label="RNA STRAND", name="RNA strand", category="molecule", icon=(3376, 5010), label_px=(3636, 5028),
         ref=dict(mass_kg=5.5e-22, width_m=3e-8, width_basis="extent", confidence="low", representative=True,
                  notes="Representative ~1,000-nucleotide RNA (~330 kDa); real RNAs span orders of magnitude."),
         desc="A strand of ribonucleic acid; its size depends entirely on its length, so values are representative."),
    dict(id="oxygen_atom", label="OXYGEN ATOM", name="Oxygen atom", category="atom", icon=(3366, 5150), label_px=(3621, 5157),
         ref=dict(mass_kg=16 * 1.6605e-27, width_m=3.04e-10, width_basis="van_der_waals_diameter", confidence="high"),
         desc="Element 8, the third most abundant element in the universe."),
    dict(id="helium_atom", label="HELIUM ATOM", name="Helium atom", category="atom", icon=(3366, 5265), label_px=(3576, 5260),
         ref=dict(mass_kg=4.0026 * 1.6605e-27, width_m=2.8e-10, width_basis="van_der_waals_diameter", confidence="high"),
         desc="Element 2, mostly forged in the first minutes after the Big Bang."),
    dict(id="fundamental_particles", label="FUNDAMENTAL PARTICLES", name="Fundamental particles", category="particle",
         icon=(3190, 5445), label_px=(3586, 5458),
         ref=dict(mass_kg=9.109e-31, width_m=HBAR / (9.109e-31 * C), width_basis="reduced_compton_wavelength",
                  confidence="high", representative=True, notes="Electron used as the representative particle."),
         desc="Quarks, leptons and bosons - this corner of the triangle is expanded in the 'Fundamental Particles' inset.",
         links={"inset": "fundamental_particles"}),
    dict(id="x_y_bosons", label="X & Y BOSON*", name="X and Y bosons", category="particle", hypothetical=True,
         icon=(2260, 4520), label_px=(2456, 4528),
         ref=dict(mass_kg=1e24 * EV_KG, width_m=HBAR / (1e24 * EV_KG * C), width_basis="reduced_compton_wavelength",
                  confidence="low", notes="Grand-unified-theory scale, ~1e15 GeV/c^2. Never observed."),
         desc="Hypothetical bosons of grand unified theories, near 10^24 eV on the energy axis; never observed."),
    dict(id="dark_exoplanets", schematic=True, label="DARK EXOPLANETS*", name="Dark exoplanets", category="hypothetical", hypothetical=True,
         icon=(4535, 2740), label_px=(4663, 2828), ref=None,
         desc="Marked hypothetical on the chart and drawn as a question-mark icon; no position is physically implied."),
]

# Categories used for colouring/filtering.
CATEGORIES = {
    "cosmic_structure": "Universe-scale structures (voids, superclusters, clusters)",
    "galaxy": "Galaxies",
    "star_cluster": "Star clusters",
    "black_hole": "Black holes (supermassive, stellar, primordial)",
    "stellar_remnant": "Neutron stars and white dwarfs",
    "star": "Stars",
    "substellar": "Brown dwarfs",
    "planet": "Planets",
    "dwarf_planet": "Dwarf planets",
    "moon": "Moons",
    "asteroid": "Asteroids",
    "human_made": "Human-made structures",
    "life": "Living things",
    "everyday_object": "Everyday objects",
    "cell": "Cells",
    "microbe": "Microbes and viruses",
    "molecule": "Molecules",
    "atom": "Atoms",
    "particle": "Particles",
    "hypothetical": "Hypothetical objects",
}


def build_reference(ref):
    if ref is None:
        return None
    out = dict(ref)
    basis = out.setdefault("width_basis", "diameter")
    if basis == "particle_horizon_diameter":
        out["width_m"] = PARTICLE_HORIZON_D
    if basis == "schwarzschild_diameter":
        out["width_m"] = schwarzschild_diameter_m(out["mass_kg"])
    m, w = out.get("mass_kg"), out.get("width_m")
    out["mass_kg"] = float(f"{m:.7g}") if m else m
    out["width_m"] = float(f"{w:.7g}") if w else w
    out["log10_mass_kg"] = lg(m)
    out["log10_width_m"] = lg(w)
    out["log10_density_proxy_kg_m3"] = r3(math.log10(m) - 3 * math.log10(w)) if m and w else None
    out.setdefault("representative", False)
    out.setdefault("notes", "")
    order = ["mass_kg", "width_m", "width_basis", "log10_mass_kg", "log10_width_m",
             "log10_density_proxy_kg_m3", "confidence", "representative", "notes"]
    return {k: out[k] for k in order}


def build_main_objects():
    rows = []
    for o in MAIN_OBJECTS:
        labeled = o.get("label") is not None
        icons = [o["icon"]] + o.get("extra_icons", [])
        rows.append({
            "id": o["id"],
            "name": o["name"],
            "printed_label": o.get("label"),
            "category": o["category"],
            "subcategory": o.get("subcategory"),
            "hypothetical": o.get("hypothetical", False),
            "labeled_on_chart": labeled,
            "identification": o.get("ident", "printed" if labeled else "visual"),
            "image": {
                "icon": point(o["icon"], MAIN_IMG),
                "all_icons_px": [list(p) for p in icons],
                "label": point(o["label_px"], MAIN_IMG) if o.get("label_px") else None,
            },
            "chart": {**main_values(o["icon"]), "position_is_schematic": o.get("schematic", False)},
            "reference": build_reference(o.get("ref")),
            "description": o["desc"],
            "links": o.get("links", {}),
            "first_appeared": first_appeared(o["id"], (o.get("ref") or {}).get("mass_kg")),
        })
    return rows


# =============================================================================
# MAIN CHART scales, boundaries, regions, texts
# =============================================================================
def mass_reference_lines():
    # (label, y px, true value kg, kind)
    tick = dict(zip(range(48, -55, -3), MASS_TICKS_Y))
    rows = [
        ("1 T Solar Masses", 2055.5, 1e12 * M_SUN, "dotted"),
        ("1 B Solar Masses", 2193.5, 1e9 * M_SUN, "dotted"),
        ("1 M Solar Masses", 2332.0, 1e6 * M_SUN, "dotted"),
        ("1000 Solar Masses", 2470.0, 1e3 * M_SUN, "dotted"),
        ("1 Solar mass = 2*10^30 Kg", 2608.5, M_SUN, "dotted"),
        ("1 gigatonne", tick[12], 1e12, "tick"),
        ("1 megatonne", tick[9], 1e9, "tick"),
        ("1 kilotonne", tick[6], 1e6, "tick"),
        ("1 tonne", tick[3], 1e3, "tick"),
        ("1 kg", tick[0], 1.0, "tick"),
        ("1 lb", 4026.0, 0.45359, "dotted"),
        ("1 oz", 4080.0, 0.028350, "dotted"),
        ("1 gram", tick[-3], 1e-3, "tick"),
        ("1 mg", tick[-6], 1e-6, "tick"),
        ("1 PLANCK MASS", 4377.0, 2.176e-8, "dotted (extends across the chart)"),
        ("1 µg", tick[-9], 1e-9, "tick"),
        ("1 ng", tick[-12], 1e-12, "tick"),
        ("1 pg", tick[-15], 1e-15, "tick"),
        ("1 TeV/c^2 (1.8*10^-21 g)", 5091.5, 1e12 * EV_KG, "dotted"),
        ("1 GeV/c^2", 5230.0, 1e9 * EV_KG, "dotted"),
        ("1 MeV/c^2", 5368.0, 1e6 * EV_KG, "dotted"),
        ("1 KeV/c^2", 5506.5, 1e3 * EV_KG, "dotted"),
        ("1 eV/c^2", 5645.0, EV_KG, "dotted"),
    ]
    out = []
    for label, y, val, kind in rows:
        out.append({"label": label, "kind": kind, "y_px": y, "y_norm": round(y / MAIN_IMG["height"], 5),
                    "true_value_kg": float(f"{val:.4g}"), "true_log10_kg": lg(val),
                    "chart_log10_kg": r3(M_AX.value(y)),
                    "offset_decades": r3(M_AX.value(y) - math.log10(val))})
    return out


MASS_PRINTED_LABELS = {48: "42", 45: "39", 42: "36", 39: "33", 36: "30", 33: "27", 30: "24", 27: "21",
                       24: "18", 21: "15", 18: "12", 15: "15", 12: "15", 9: "12", 6: "9", 3: "3", -51: None,
                       -54: None}


def mass_ticks():
    out = []
    for v, y in zip(range(48, -55, -3), MASS_TICKS_Y):
        printed = MASS_PRINTED_LABELS.get(v, str(v))
        out.append({"value": v, "y_px": y, "printed_label": printed,
                    "printed_label_correct": printed is None or printed == str(v)})
    return out


def width_reference_lines():
    tick = dict(zip(range(-33, 25, 3), WIDTH_TICKS_X))
    rows = [
        ("1 PLANCK LENGTH", 2116.0, 1.616e-35, "dotted vertical line"),
        ("10 pm", tick[-12], 1e-11, "label at tick"),
        ("1 nm", tick[-9], 1e-9, "label at tick"),
        ("1 µm", tick[-6], 1e-6, "label at tick"),
        ("1 mm", tick[-3], 1e-3, "label at tick"),
        ("1 inch", 3684.5, 0.0254, "dotted"),
        ("1 meter", tick[0], 1.0, "label at tick"),
        ("1 km", tick[3], 1e3, "label at tick"),
        ("1 mile", 3877.0, 1609.34, "dotted"),
        ("1000 km", tick[6], 1e6, "label at tick"),
        ("1M km", tick[9], 1e9, "label at tick"),
        ("1light-second", 4153.0, C, "dotted"),
        ("1 AU", 4227.5, 1.496e11, "dotted"),
        ("1light-year", 4451.0, LY, "dotted"),
        ("1 parsec", 4473.0, PC, "dotted"),
        ("1,000 ly", 4589.0, 1e3 * LY, "dotted"),
        ("1 kpc", 4610.5, 1e3 * PC, "dotted"),
        ("1M ly", 4727.0, 1e6 * LY, "dotted"),
        ("1 Mpc", 4748.0, 1e6 * PC, "dotted"),
        ("1B ly", 4865.0, 1e9 * LY, "dotted"),
        ("1 Gpc", 4885.5, 1e9 * PC, "dotted"),
    ]
    out = []
    for label, x, val, kind in rows:
        out.append({"label": label, "kind": kind, "x_px": x, "x_norm": round(x / MAIN_IMG["width"], 5),
                    "true_value_m": float(f"{val:.4g}"), "true_log10_m": lg(val),
                    "chart_log10_m": r3(W_AX.value(x)),
                    "offset_decades": r3(W_AX.value(x) - math.log10(val))})
    return out


def energy_annotations():
    # (label, y px or [y0,y1] bracket, kind, true value eV or [lo,hi], text px, note)
    rows = [
        ("1 PLANCK ENERGY", 4375.0, "dotted", 1.22e28, (1493, 4384), "Planck energy 1.22e19 GeV."),
        ("GRAND UNIFICATION THEORY*", (4400, 4486), "bracket", (1e24, 1e25), (1465, 4449),
         "Hypothetical; GUT scale ~1e15-1e16 GeV."),
        ("ELECTROWEAK", (4495, 5131), "bracket", (1e11, 1e24), (1623, 4810),
         "Span between the GUT scale and electroweak symmetry breaking (~100 GeV)."),
        ("LARGE HADRON COLLIDER (MAXIMUM ENERGY)", 5069.0, "arrow", 1.36e13, (1416, 5065),
         "13.6 TeV collision energy."),
        ("FUNDAMENTAL PARTICLES", (5145, 5443), "bracket", (5.11e5, 1.73e11), (1503, 5302),
         "Electron (0.511 MeV) to top quark (173 GeV); neutrinos are lighter."),
        ("1 B K", 5414.5, "dotted", 1e9 * K_EV, (1645, 5413), "Temperature expressed as kT."),
        ("1 M °C ≈ 1 M K", 5553.5, "dotted", 1e6 * K_EV, (1563, 5554), "Temperature expressed as kT."),
        ("100 °C", 5685.0, "dotted", 373.15 * K_EV, (1645, 5671),
         "Drawn ~0.6 decade higher than kT for 373 K so the bracket is legible."),
        ("LIQUID WATER RANGE", (5694, 5729), "bracket", (273.15 * K_EV, 373.15 * K_EV), (1552, 5712), ""),
        ("0 °C", 5738.0, "dotted", 273.15 * K_EV, (1666, 5756), "Drawn ~0.4 decade low."),
        ("SUPERCONDUCTIVITY", (5763, 5816), "bracket", (1 * K_EV, 150 * K_EV), (1552, 5806),
         "Known superconductors: critical temperatures ~1-150 K."),
        ("1 Kelvin (-272 °C)", 5829.5, "dotted", K_EV, (1628, 5852), ""),
        ("BOSE-EINSTEIN CONDENSATE", (6214, 6317), "bracket", (1e-7 * K_EV, 1e-6 * K_EV), (1617, 6260),
         "Lab BECs form at ~100 nK-1 µK; drawn ~2 decades lower."),
        ("QUANTUM TUNNELING*", (6395, 6500), "bracket", None, (1648, 6421),
         "Asterisk = hypothetical per the chart's legend; no specific energy implied."),
        ("ZERO-POINT ENERGY", 7145.0, "arrow", None, (1473, 7145), "Points at the bottom of the axis."),
    ]
    out = []
    for label, y, kind, val, tpx, note in rows:
        if isinstance(y, tuple):
            chart = [r3(E_AX.value(y[0])), r3(E_AX.value(y[1]))]
            ypx = list(y)
        else:
            chart = r3(E_AX.value(y))
            ypx = y
        if isinstance(val, tuple):
            true = [lg(val[0]), lg(val[1])]
        else:
            true = lg(val) if val else None
        out.append({"label": label, "kind": kind, "y_px": ypx, "chart_log10_eV": chart,
                    "true_log10_eV": true, "text": point(tpx, MAIN_IMG), "note": note})
    return out


def energy_ticks():
    printed = {27: None, 24: "24", 21: "21", 18: "18", 15: "15", 12: "12", 9: "9 (1 GeV)", 6: "6 (1 MeV)",
               3: "3 (1 KeV)", 0: "0 (1 eV)", -3: "-3 (1 meV)", -6: "-6", -9: "-9", -12: "-12"}
    return [{"value": v, "y_px": y, "printed_label": printed.get(v)}
            for v, y in zip(range(27, -31, -3), ENERGY_TICKS_Y)]


def density_ruler():
    out = []
    for i, x in enumerate(DENSITY_TALL_TICKS_X):
        val = 93 - 9 * i
        printed = DENSITY_PRINTED.get(i)
        out.append({"x_px_at_row_1195": x, "value_uniform_scale": val, "printed_label": printed,
                    "printed_matches_uniform": printed is None or printed == val})
    return out


DENSITY_LINES = [
    # (id, printed label, label px, x where the line crosses the ruler, true log10 kg/m^3, note)
    ("planck_density", "1 PLANCK DENSITY", (3058, 1620), 3199, 96.71, "Planck density 5.16e96 kg/m^3."),
    ("plasma_density", "PLASMA DENSITY", (4295, 1470), 4386, None,
     "Unspecified on the chart; the line sits near 10^16-10^17 g/L (nuclear density is ~2.3e17 kg/m^3)."),
    ("water_density", "WATER DENSITY", (4500, 1470), 4591, 3.0,
     "Continues down-left as the blue dotted 'ATOMIC DENSITY LINE' through the everyday objects."),
    ("false_vacuum", "“FALSE” VACUUM", (4715, 1470), 4806, None, "Speculative; no value implied."),
    ("true_vacuum", "TRUE VACUUM", (6762, 1450), 6831, None,
     "Same dotted line as '1 googol seconds'; it reaches the bottom corner labelled HEAT DEATH OF THE UNIVERSE."),
]


def density_lines():
    out = []
    for lid, label, lpx, xr, true, note in DENSITY_LINES:
        out.append({"id": lid, "printed_label": label, "label": point(lpx, MAIN_IMG),
                    "ruler_crossing_px": [xr, DENSITY_RULER_Y],
                    "chart_log10_g_per_L": r3(D_AX.value(xr)), "true_log10_kg_m3": true, "note": note})
    return out


# Atomic/water density line: one straight blue dotted line (slope 3) from the microbes to the top.
ATOMIC_LINE = [(3494, 4526), (4480, 1560)]

TRIANGLE = {
    "big_bang_apex": (2125, 4375),
    "top_vertex": (4922, 1585),
    "bottom_vertex": (4920, 7155),
}


def boundaries():
    def line(pts):
        return [point(p, MAIN_IMG) for p in pts]

    apex = TRIANGLE["big_bang_apex"]
    av = main_values(apex)
    return [
        {"id": "schwarzschild_radius", "printed_label": "SCHWARZSCHILD RADIUS",
         "meaning": "Objects cannot be smaller than their own black-hole size; the upper-left edge of the triangle.",
         "equation": f"log10 M[kg] = log10 W[m] + {LOG_SCHW:.6f}  (W = Schwarzschild diameter 4GM/c^2)",
         "chart_fit": "log10 M = log10 W + 26.6 (apex to observable universe)",
         "polyline": line([apex, TRIANGLE["top_vertex"]]),
         "extends_beyond": "Continues up-right past the observable universe as the edge of the lighter 'future' band."},
        {"id": "compton_limit", "printed_label": "COMPTON LIMIT",
         "meaning": "Quantum uncertainty forbids localising a mass in less than its Compton wavelength; lower-left edge.",
         "equation": f"log10 M[kg] = -log10 W[m] {LOG_COMPTON:.6f}  (W = reduced Compton wavelength hbar/Mc)",
         "chart_fit": "log10 M = -log10 W - 42.5",
         "polyline": line([apex, TRIANGLE["bottom_vertex"]])},
        {"id": "hubble_radius", "printed_label": "HUBBLE RADIUS",
         "meaning": "Nothing larger than the observable universe can be seen; the vertical right edge.",
         "equation": f"log10 W[m] = {LOG_HUBBLE_W:.6f} (diameter of today's Hubble sphere, 2c/H0). The poster draws it at ~25.97.",
         "polyline": line([TRIANGLE["top_vertex"], TRIANGLE["bottom_vertex"]])},
        {"id": "planck_mass_line", "printed_label": "1 PLANCK MASS",
         "meaning": "Horizontal red dotted line through the apex and the grain of salt.",
         "equation": "log10 M[kg] = -7.66", "polyline": line([(2125, 4377), (5650, 4377)])},
        {"id": "planck_length_line", "printed_label": "1 PLANCK LENGTH",
         "meaning": "Vertical red dotted line through the apex.",
         "equation": "log10 W[m] = -34.79", "polyline": line([(2116, 4380), (2116, 7150)])},
        {"id": "planck_energy_line", "printed_label": "1 PLANCK ENERGY",
         "meaning": "Horizontal dotted line on the energy axis meeting the apex.",
         "equation": "log10 E[eV] = 28.09", "polyline": line([(1780, 4375), (2125, 4375)])},
        {"id": "atomic_density_line", "printed_label": "ATOMIC DENSITY LINE / WATER DENSITY",
         "meaning": "Blue dotted line of constant (~water/atomic) density that the everyday objects, planets and stars follow.",
         "equation": "log10 M[kg] ~= 3 log10 W[m] + 3.7 (chart); water: 3 log10 W + 3.0 (cube) or + 2.72 (sphere)",
         "polyline": line(ATOMIC_LINE)},
        {"id": "true_vacuum_heat_death_line", "printed_label": "TRUE VACUUM / 1 googol seconds",
         "meaning": "Red dotted density line from the top ruler to the bottom corner labelled HEAT DEATH OF THE UNIVERSE.",
         "polyline": line([(6962, 800), (4918, 7155)])},
        {"id": "big_bang_apex", "printed_label": "BIG BANG",
         "meaning": "Where the Schwarzschild and Compton limits meet: the Planck mass at the Planck length.",
         "point": point(apex, MAIN_IMG), "chart": av,
         "reference": {"log10_mass_kg": round((LOG_COMPTON + LOG_SCHW) / 2, 6),
                       "log10_width_m": round((LOG_COMPTON - LOG_SCHW) / 2, 6),
                       "note": "Exact crossing of the two walls: half the Planck mass at twice the Planck length "
                               "(with W = 4GM/c^2 and W = hbar/Mc)."}},
    ]


BH_BRACKETS = [
    ("primordial", "PRIMORDIAL BLACK HOLES*", True, (3064, 3120), (3472, 2718), (3204, 2864),
     (5e11, 3 * M_SUN), "Hypothetical; formed in the early universe. Lighter than ~5e11 kg they would have "
     "evaporated by now; the range shown stops where stellar black holes begin."),
    ("stellar_mass", "STELLAR MASS BLACK HOLES", False, (3485, 2693), (3899, 2303), (3600, 2449),
     (3 * M_SUN, 150 * M_SUN), "Formed by collapse of massive stars (~3 to ~150 solar masses)."),
    ("supermassive", "SUPER MASSIVE BLACK HOLES", False, (3905, 2278), (4314, 1882), (4021, 2034),
     (1e5 * M_SUN, 1e11 * M_SUN), "Found at galaxy centres (~1e5 to ~1e11 solar masses)."),
]


def project_to_schwarzschild(px):
    """Mass at the foot of the perpendicular from a bracket point onto log M = log W + 26.6."""
    v = main_values(px)
    return r3((v["log10_width_m"] + v["log10_mass_kg"] + 26.6) / 2)


def regions():
    out = []
    for rid, label, hyp, p0, p1, tpx, ref, note in BH_BRACKETS:
        out.append({
            "id": f"black_holes_{rid}", "printed_label": label, "kind": "bracket_along_schwarzschild_line",
            "hypothetical": hyp,
            "bracket": [point(p0, MAIN_IMG), point(p1, MAIN_IMG)], "text": point(tpx, MAIN_IMG),
            "chart_log10_mass_kg_range": [project_to_schwarzschild(p0), project_to_schwarzschild(p1)],
            "reference_log10_mass_kg_range": [lg(ref[0]), lg(ref[1])] if ref else None,
            "first_appeared": first_appeared(f"black_holes_{rid}", ref[0] if ref else None),
            "note": note + " Chart range = bracket ends projected onto the Schwarzschild line.",
        })
    dm_boxes = [
        ("dark_matter_upper", [(3470, 3022), (3960, 3022), (3905, 3216), (3279, 3216)]),
        ("dark_matter_lower", [(3189, 3373), (3830, 3373), (3459, 4149), (2345, 4149)]),
    ]
    for rid, poly in dm_boxes:
        ys = [p[1] for p in poly]
        out.append({
            "id": rid, "printed_label": "DARK MATTER* (areas not yet excluded)", "kind": "dashed_polygon",
            "hypothetical": True, "polygon": [point(p, MAIN_IMG) for p in poly],
            "text": point((3110, 3727), MAIN_IMG),
            "chart_log10_mass_kg_range": [r3(M_AX.value(max(ys))), r3(M_AX.value(min(ys)))],
            "note": "Speckled area with dashed borders; the gap between the two boxes is drawn as excluded.",
        })
    out.append({
        "id": "quark_gluon_plasma", "printed_label": "QUARK-GLUON PLASMA", "kind": "colour_gradient",
        "text": point((2868, 4270), MAIN_IMG),
        "approx_ellipse": {"center": point((2850, 4300), MAIN_IMG), "radius_px": [500, 450]},
        "note": "Warm-coloured glow next to the Big Bang apex; the image gives no hard edge. "
                "Physically: matter hotter than ~150 MeV (first ~10 µs after the Big Bang).",
    })
    domains = [
        ("biology", "BIOLOGY", (4208, 4231), ["virus", "bacterium", "red_blood_cell", "ladybug", "hedgehog",
                                               "humans", "hippopotamus", "blue_whale", "giant_sequoia"]),
        ("chemistry", "CHEMISTRY", (3886, 5200), ["helium_atom", "oxygen_atom", "rna_strand"]),
        ("astrophysics", "ASTROPHYSICS", (4552, 3179), ["itokawa", "deimos", "phobos", "enceladus", "moon",
                                                         "earth", "jupiter", "sun", "globular_clusters",
                                                         "milky_way", "observable_universe"]),
    ]
    by_id = {o["id"]: o for o in MAIN_OBJECTS}
    for rid, label, tpx, members in domains:
        ms = [main_values(by_id[m]["icon"])["log10_mass_kg"] for m in members]
        out.append({"id": f"domain_{rid}", "printed_label": label, "kind": "domain_label",
                    "text": point(tpx, MAIN_IMG), "member_object_ids": members,
                    "chart_log10_mass_kg_range": [min(ms), max(ms)]})
    photons = [
        ("gamma_ray", "GAMMA RAY", (3056, 5575), (None, 1e-11), (1e5, None)),
        ("x_ray", "X-RAY", (3196, 5605), (1e-11, 1e-8), (1e2, 1e5)),
        ("ultraviolet", "ULTRAVIOLET", (3236, 5735), (1e-8, 4e-7), (3.1, 1.24e2)),
        ("visible_light", "VISIBLE LIGHT", (3261, 5770), (3.8e-7, 7.5e-7), (1.65, 3.26)),
        ("infrared", "INFRARED", (3316, 5785), (7.5e-7, 1e-3), (1.24e-3, 1.65)),
        ("microwaves", "MICROWAVES", (3491, 6005), (1e-3, 1.0), (1.24e-6, 1.24e-3)),
        ("radio_waves", "RADIO WAVES", (3591, 6105), (1.0, None), (None, 1.24e-6)),
    ]
    out.append({
        "id": "energy_states_of_photon", "printed_label": "ENERGY STATES OF PHOTON", "kind": "bracketed_label_list",
        "text": point((3166, 5995), MAIN_IMG),
        "bracket": [point((2916, 5655), MAIN_IMG), point((3491, 6245), MAIN_IMG)],
        "note": "Labels run along the Compton limit below the particles; they are spaced for legibility, "
                "not at their true wavelengths. A rainbow ribbon runs from the particles toward the radio end.",
        "first_appeared": first_appeared("energy_states_of_photon"),
        "bands": [{"id": b, "printed_label": lab, "text": point(t, MAIN_IMG),
                   "reference_wavelength_m": list(wl), "reference_photon_energy_eV": list(en)}
                  for b, lab, t, wl, en in photons],
    })
    return out


ZOOM_BOXES = [
    {"id": "stellar_evolution_zoom", "inset": "stellar_evolution",
     "main_box_px": [(3896, 2485), (4321, 2900)], "inset_frame_px": [(605.5, 625.5), (1855.5, 1875.0)],
     "note": "Red box around the stars and planets; red connector lines lead to the STELLAR EVOLUTION inset."},
    {"id": "fundamental_particles_zoom", "inset": "fundamental_particles",
     "main_box_px": [(2828, 5112), (3256, 5525)], "inset_frame_px": [(601.0, 2678.5), (1850.5, 3928.5)],
     "decorative_icons_px": [(2885, 5155), (2995, 5245), (3030, 5285), (3190, 5445)],
     "note": "Red box at the bottom of the Compton limit; leads to the FUNDAMENTAL PARTICLES inset."},
]


def zoom_boxes():
    out = []
    for z in ZOOM_BOXES:
        (x0, y0), (x1, y1) = z["main_box_px"]
        a, b = main_values((x0, y1)), main_values((x1, y0))
        entry = {"id": z["id"], "inset": z["inset"],
                 "main_box": [point((x0, y0), MAIN_IMG), point((x1, y1), MAIN_IMG)],
                 "main_box_chart_range": {"log10_width_m": [a["log10_width_m"], b["log10_width_m"]],
                                          "log10_mass_kg": [a["log10_mass_kg"], b["log10_mass_kg"]]},
                 "inset_frame": [point(p, MAIN_IMG) for p in z["inset_frame_px"]], "note": z["note"]}
        if "decorative_icons_px" in z:
            entry["decorative_icons"] = [point(p, MAIN_IMG) for p in z["decorative_icons_px"]]
        out.append(entry)
    return out


TEXTS = [
    ("TIME", "axis_title", (3416, 348)), ("10^n s since Big Bang", "axis_unit", (3862, 488)),
    ("DENSITY", "axis_title", (3535, 1519)), ("10^n g/L", "axis_unit", (3540, 1660)),
    ("WIDTH", "axis_title", (2419, 6654)), ("10^n m", "axis_unit", (2380, 6800)),
    ("MASS", "axis_title", (5432, 6654)), ("10^n kg", "axis_unit", (5420, 6800)),
    ("ENERGY", "axis_title", (904, 6654)), ("10^n eV", "axis_unit", (860, 6800)),
    ("SCHWARZSCHILD RADIUS", "boundary_title", (2822, 3544)), ("COMPTON LIMIT", "boundary_title", (2674, 4902)),
    ("HUBBLE RADIUS", "boundary_title", (5021, 4987)), ("OBSERVABLE UNIVERSE", "title", (5254, 1591)),
    ("BIG BANG", "title", (1889, 4295)), ("HEAT DEATH OF THE UNIVERSE", "title", (5305, 7215)),
    ("STELLAR EVOLUTION", "inset_title", (997, 2080)), ("FUNDAMENTAL PARTICLES", "inset_title", (1116, 4146)),
    ("*Asterisk means still hypothetical", "legend", (775, 4413)),
    ("STARS & PLANETS", "group_label", (4640, 2550)),
]


# =============================================================================
# COSMIC TIMELINE (top of the main chart)
# =============================================================================
TIME_MARKERS = [
    # (id, printed number, printed text, line-top px, number-label px, true seconds, note)
    ("planck_time", None, "1 PLANCK TIME", (3266, 807), (3259, 958), 5.39e-44, "The earliest meaningful time."),
    ("end_of_gut_era", "-32", None, (3614, 807), (3673, 841), 1e-32, "Approximate end of inflation / GUT era."),
    ("end_of_electroweak_era", "-11", None, (4307, 807), (4356, 848), 1e-11, "Electroweak symmetry breaks (~1e-12 s)."),
    ("one_microsecond", "-6", "1 microsecond", (4583, 807), (4625, 848), 1e-6, "Quarks bind into hadrons."),
    ("sixteen_minutes", "3", "16 minutes", (4859, 807), (4903, 848), 960, "Big Bang nucleosynthesis ends (~20 min)."),
    ("recombination", "13", "380,000 years", (5134, 807), (5176, 848), 380000 * 3.156e7,
     "Atoms form; the cosmic microwave background is released."),
    ("now", "17", "NOW", (5214, 807), (5293, 848), 13.8e9 * 3.156e7, "Age of the universe, 13.8 billion years."),
    ("hundred_trillion_years", "21", "100 T years", (5413, 807), (5468, 848), 1e14 * 3.156e7,
     "Roughly when the last stars burn out."),
    ("googol_seconds", "100", "1 googol seconds", (6962, 800), (7045, 848), 1e100,
     "Far future; this dotted line is also labelled TRUE VACUUM and ends at HEAT DEATH OF THE UNIVERSE."),
]

ERAS = [
    # (id, printed label, from marker, to marker, bracket px x0..x1, text px, reference seconds, note)
    ("gut_era", "GUT ERA*", "planck_time", "end_of_gut_era", (3266, 3604), (3431, 652), (5.39e-44, 1e-36),
     "Hypothetical grand-unification epoch."),
    ("electroweak_era", "ELECTROWEAK ERA", "end_of_gut_era", "end_of_electroweak_era", (3618, 4294), (3956, 652),
     (1e-36, 1e-12), ""),
    ("big_bang_nucleosynthesis", "BIG BANG NUCLEOSYNTHESIS", "end_of_electroweak_era", "sixteen_minutes",
     (4314, 4876), (4625, 627), (10, 1200),
     "Bracket spans 1e-11 s to 1e3 s on the chart; nucleosynthesis itself ran from ~10 s to ~20 min."),
    ("recombination_era", "RECOMBINATION ERA", "sixteen_minutes", "hundred_trillion_years", (4903, 5463),
     (5231, 627), (1.2e13, 1.2e13),
     "Bracket spans 1e3 s to 1e21 s on the chart; recombination itself happened at ~380,000 years."),
    ("heat_death", "HEAT DEATH OF THE UNIVERSE", "hundred_trillion_years", "googol_seconds", (6797, 6955),
     (6652, 662), (None, None), "Arrow pointing right (to the far future)."),
]


def friedmann_log_density(t):
    """Radiation-era estimate rho = 3/(32 pi G t^2), kg/m^3."""
    return 8.65 - 2 * math.log10(t)


def _hubble_rate(a):
    return H0 * math.sqrt(OMEGA_R / a**4 + OMEGA_M / a**3 + OMEGA_L)


def _build_lcdm_table(a_min=1e-35, a_max=1e6, steps=200_000):
    """Cosmic time t(a) for flat LambdaCDM, integrating dt = dln(a) / H(a) from deep in the radiation era."""
    x0, x1 = math.log(a_min), math.log(a_max)
    dx = (x1 - x0) / steps
    t = 1 / (2 * _hubble_rate(a_min))          # pure radiation: t = 1/(2H)
    table = [(t, a_min)]
    prev = 1 / _hubble_rate(a_min)
    for i in range(1, steps + 1):
        a = math.exp(x0 + i * dx)
        cur = 1 / _hubble_rate(a)
        t += 0.5 * (prev + cur) * dx
        prev = cur
        table.append((t, a))
    return table


LCDM_TABLE = _build_lcdm_table()


def lcdm_scale_factor(t):
    """Scale factor at cosmic time t (s) within the table; radiation-only below it."""
    tab = LCDM_TABLE
    if t <= tab[0][0]:
        return math.sqrt(2 * H0 * math.sqrt(OMEGA_R) * t)
    lo, hi = 0, len(tab) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if tab[mid][0] < t: lo = mid
        else: hi = mid
    (t0, a0), (t1, a1) = tab[lo], tab[hi]
    f = (math.log(t) - math.log(t0)) / (math.log(t1) - math.log(t0))
    return math.exp(math.log(a0) + f * (math.log(a1) - math.log(a0)))


def lcdm_age():
    """Cosmic time at a = 1 (today)."""
    tab = LCDM_TABLE
    lo, hi = 0, len(tab) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if tab[mid][1] < 1: lo = mid
        else: hi = mid
    (t0, a0), (t1, a1) = tab[lo], tab[hi]
    return t0 + (t1 - t0) * (math.log(1) - math.log(a0)) / (math.log(a1) - math.log(a0))


YEAR_S = 3.156e7
PLANCK_TIME = 5.39e-44

# The instant all three walls meet. The black-hole wall (W = 4GM/c^2) and the quantum wall (W = hbar/Mc) cross at
# W = 2 Planck lengths; the Hubble sphere (W = 2c/H = 4ct in the radiation era) is that wide at t = W/(4c),
# half the Planck time. Uses the same rounded offsets the site uses, so the first frame is exactly one point.
APEX_W = (round(LOG_COMPTON, 6) - round(LOG_SCHW, 6)) / 2
T_MEET = 10**APEX_W / (4 * C)

# When each thing (or the first of its kind) appeared. Kinds:
#   ("after_s", seconds after the Big Bang) | ("after_yr", years after) | ("ago_yr", years before today)
#   ("pbh",) formation time of a primordial black hole of the object's mass, t ~ GM/c^3 | ("now",) shown as today
# then: basis (this_object | first_of_its_kind | physics), confidence, note.
FIRST_APPEARED = {
    # cosmic structure
    "observable_universe": (("now",), "this_object", "high", "Plotted as it is today; its edge has been growing since the Big Bang (the dashed line)."),
    "bootes_void": (("after_yr", 3e9), "first_of_its_kind", "low", "Voids deepen as matter drains into the cosmic web; big ones emerge over the first few billion years."),
    "laniakea_supercluster": (("after_yr", 5e9), "first_of_its_kind", "low", "Superclusters are still assembling; their outlines emerge over billions of years."),
    "el_gordo": (("ago_yr", 7.3e9), "this_object", "medium", "Seen as it was 7.3 billion years ago (redshift 0.87), already assembled."),
    "milky_way": (("ago_yr", 13.3e9), "this_object", "medium", "Its oldest stars are ~13 billion years old; the disc built up over the following billions of years."),
    "smc_galaxy": (("ago_yr", 12e9), "this_object", "low", "Its oldest stars are roughly 10-12 billion years old."),
    "globular_clusters": (("ago_yr", 12.8e9), "first_of_its_kind", "medium", "The oldest Milky Way globular clusters are about 12.5-13 billion years old."),
    # black holes
    "ton_618": (("ago_yr", 10.8e9), "this_object", "medium", "Seen as it was 10.8 billion years ago (redshift 2.2), already enormous."),
    "cygnus_a": (("after_yr", 7e8), "first_of_its_kind", "low", "Billion-solar-mass black holes (quasars) existed within ~700 million years of the Big Bang; Cygnus A's own history is unknown."),
    "sagittarius_a_star": (("after_yr", 1e9), "this_object", "low", "Thought to have grown with the young Milky Way; its exact age is unknown."),
    "lb_1": (("after_yr", 2e8), "first_of_its_kind", "low", "Stellar black holes first formed when the earliest massive stars collapsed, ~200 million years after the Big Bang."),
    "v616_monocerotis": (("after_yr", 2e8), "first_of_its_kind", "low", "Stellar black holes first formed when the earliest massive stars collapsed, ~200 million years after the Big Bang."),
    "primordial_black_hole": (("pbh",), "physics", "low", "If primordial black holes exist, one forms when its mass fits inside the horizon: t ~ GM/c^3."),
    # stars and remnants
    "neutron_star": (("after_yr", 2e8), "first_of_its_kind", "low", "The first supernovae, ~200 million years after the Big Bang, left the first neutron stars."),
    "white_dwarfs": (("after_yr", 3e8), "first_of_its_kind", "low", "Stars of a few solar masses live tens to hundreds of millions of years before leaving white dwarfs."),
    "sun": (("ago_yr", 4.603e9), "this_object", "high", "Formed 4.6 billion years ago from a collapsing cloud of gas and dust."),
    "red_dwarfs": (("ago_yr", 13e9), "first_of_its_kind", "low", "Small, long-lived stars; the oldest known are ~13 billion years old."),
    "brown_dwarf": (("ago_yr", 13e9), "first_of_its_kind", "low", "Formed like stars, from the earliest generations of star formation."),
    # solar system
    "jupiter": (("ago_yr", 4.6e9), "this_object", "high", "The first planet to form, within a few million years of the Sun."),
    "saturn": (("ago_yr", 4.5e9), "this_object", "high", ""),
    "uranus": (("ago_yr", 4.5e9), "this_object", "high", ""),
    "neptune": (("ago_yr", 4.5e9), "this_object", "high", ""),
    "earth": (("ago_yr", 4.54e9), "this_object", "high", ""),
    "venus": (("ago_yr", 4.5e9), "this_object", "high", ""),
    "mercury": (("ago_yr", 4.5e9), "this_object", "high", ""),
    "mars": (("ago_yr", 4.5e9), "this_object", "high", ""),
    "moon": (("ago_yr", 4.51e9), "this_object", "high", "Probably formed from the debris of a giant impact on the young Earth."),
    "pluto": (("ago_yr", 4.5e9), "this_object", "high", ""),
    "ceres": (("ago_yr", 4.5e9), "this_object", "high", ""),
    "enceladus": (("ago_yr", 4.5e9), "this_object", "low", "Some studies suggest Saturn's inner moons could be as young as ~100 million years."),
    "phobos": (("ago_yr", 4.3e9), "this_object", "low", "Origin debated: captured asteroid or debris from an impact on Mars."),
    "deimos": (("ago_yr", 4.3e9), "this_object", "low", "Origin debated: captured asteroid or debris from an impact on Mars."),
    "itokawa": (("ago_yr", 1.5e9), "this_object", "low", "A rubble pile that reassembled after its parent asteroid was shattered; estimates vary widely."),
    # human-made and everyday
    "great_pyramid": (("ago_yr", 4586), "this_object", "high", "Built around 2560 BCE."),
    "las_vegas_sphere": (("ago_yr", 3), "this_object", "high", "Opened in September 2023."),
    "penny": (("ago_yr", 233), "first_of_its_kind", "high", "The first US cent was struck in 1793; today's zinc version dates from 1982."),
    "soccer_ball": (("ago_yr", 163), "first_of_its_kind", "low", "Association football's rules were standardised in 1863."),
    "grain_of_salt": (("ago_yr", 3.5e9), "first_of_its_kind", "low", "Salt crystals form when seawater evaporates; Earth's oldest evaporite deposits are ~3.5 billion years old."),
    # life
    "giant_sequoia": (("ago_yr", 3.85e8), "first_of_its_kind", "medium", "The first trees grew about 385 million years ago; General Sherman itself is ~2,200 years old."),
    "blue_whale": (("ago_yr", 4.5e6), "first_of_its_kind", "low", "Baleen whales became giants within roughly the last 4.5 million years."),
    "hippopotamus": (("ago_yr", 2.5e6), "first_of_its_kind", "low", "The modern hippo genus goes back a few million years."),
    "humans": (("ago_yr", 3e5), "first_of_its_kind", "medium", "Homo sapiens appeared about 300,000 years ago."),
    "hedgehog": (("ago_yr", 1.5e7), "first_of_its_kind", "low", "Hedgehogs have looked much the same for ~15 million years."),
    "ladybug": (("ago_yr", 1.4e8), "first_of_its_kind", "low", "Ladybird beetles are thought to date from the Cretaceous; their exact origin is uncertain."),
    "red_blood_cell": (("ago_yr", 5e8), "first_of_its_kind", "low", "Haemoglobin-filled red cells evolved in early vertebrates, roughly 500 million years ago."),
    "bacterium": (("ago_yr", 3.8e9), "first_of_its_kind", "medium", "Life on Earth is at least ~3.5-3.8 billion years old."),
    "virus": (("ago_yr", 3.5e9), "first_of_its_kind", "low", "Viruses leave no fossils; they are probably nearly as old as cellular life."),
    # molecules, atoms, particles
    "rna_strand": (("ago_yr", 4.0e9), "first_of_its_kind", "low", "RNA may predate DNA and proteins (the 'RNA world'), ~4 billion years ago."),
    "oxygen_atom": (("after_yr", 2e8), "first_of_its_kind", "medium", "Oxygen is forged in stars; the first supernovae spread it ~200 million years after the Big Bang."),
    "helium_atom": (("after_yr", 1e5), "first_of_its_kind", "medium", "Helium nuclei formed in the first minutes; neutral helium atoms ~100,000 years later, before hydrogen atoms."),
    "fundamental_particles": (("after_s", 1e-12), "first_of_its_kind", "medium", "Quarks, leptons and the W and Z gained their masses when the Higgs field switched on, ~10^-12 s after the Big Bang."),
    "x_y_bosons": (("after_s", 1e-36), "first_of_its_kind", "low", "Hypothetical: would belong to the grand-unification era, before ~10^-36 s."),
    # stellar-evolution inset (objects not already in the table above)
    "main_sequence": (("after_yr", 1e8), "first_of_its_kind", "low", "The first stars lit up ~100-200 million years after the Big Bang."),
    "red_giants": (("after_yr", 3e8), "first_of_its_kind", "low", "Stars swell into red giants as they run out of core hydrogen."),
    "super_giants": (("after_yr", 1.5e8), "first_of_its_kind", "low", "Massive first stars swelled into supergiants within a few million years of forming."),
    "wr_stars": (("after_yr", 1.5e8), "first_of_its_kind", "low", "Massive stars strip to Wolf-Rayet stars within a few million years."),
    "beta_pictoris_b": (("ago_yr", 2.3e7), "this_object", "medium", "Its star is about 20-25 million years old."),
    # Lineweaver & Patel points without a poster counterpart
    "flea": (("ago_yr", 1.65e8), "first_of_its_kind", "low", "Flea-like insects are known from ~165 million years ago."),
    "quantum_gravity_point": (("after_s", PLANCK_TIME), "physics", "high", "The Planck time, the earliest moment physics can describe."),
    "visible_photons": (("after_s", 1e-12), "first_of_its_kind", "medium", "Light as we know it separated from the weak force at the electroweak transition."),
    "three_kelvin_bh": (("pbh",), "physics", "low", "Hypothetical: only a primordial black hole could be this light; t ~ GM/c^3."),
    "smallest_observable_pbh": (("pbh",), "physics", "low", "Hypothetical primordial black hole; t ~ GM/c^3."),
    "hubble_radius": (("now",), "this_object", "high", "Today's Hubble sphere."),
}
FIRST_APPEARED["main_sequence_stars"] = FIRST_APPEARED["main_sequence"]
# layers that describe kinds of things, so cosmic-time mode can show them only once they exist
FIRST_APPEARED.update({
    "energy_states_of_photon": (("after_s", 1e-12), "first_of_its_kind", "medium",
                                "Light as we know it separated from the weak force at the electroweak transition."),
    "black_holes_primordial": (("pbh",), "physics", "low",
                               "Hypothetical. A primordial black hole forms with about the mass inside the horizon, "
                               "M ~ c^3 t / G, so the band grows along the wall as time passes."),
    "black_holes_stellar_mass": (("after_yr", 2e8), "first_of_its_kind", "low",
                                 "The earliest massive stars collapsed ~200 million years after the Big Bang."),
    "black_holes_supermassive": (("after_yr", 7e8), "first_of_its_kind", "low",
                                 "Quasars powered by billion-solar-mass black holes existed by ~700 million years."),
})
for _pid in ("top", "higgs", "z_boson", "w_boson", "bottom", "tau", "charm", "muon", "strange", "tau_neutrino",
             "down", "up", "electron", "muon_neutrino", "electron_neutrino", "photon"):
    FIRST_APPEARED["particle:" + _pid] = (("after_s", 1e-12), "first_of_its_kind", "medium",
                                          "Elementary particles took their present form when the Higgs field switched on, ~10^-12 s after the Big Bang.")
for _pid in ("proton", "neutron", "meson"):
    FIRST_APPEARED["particle:" + _pid] = (("after_s", 1e-6), "first_of_its_kind", "medium",
                                          "Quarks bound into protons, neutrons and mesons about a microsecond after the Big Bang.")


def _when_label(seconds, years_ago):
    if years_ago is not None and years_ago < 6e9:
        for div, unit in ((1e9, "billion years ago"), (1e6, "million years ago"), (1e3, "thousand years ago")):
            if years_ago >= div:
                return f"{years_ago / div:.3g} {unit}"
        return f"{years_ago:.3g} years ago"
    yrs = seconds / YEAR_S
    if yrs >= 1e9: return f"{yrs / 1e9:.3g} billion years after the Big Bang"
    if yrs >= 1e6: return f"{yrs / 1e6:.3g} million years after the Big Bang"
    if yrs >= 1e3: return f"{yrs / 1e3:.3g} thousand years after the Big Bang"
    if seconds >= 3600: return f"{seconds / 3600:.3g} hours after the Big Bang"
    if seconds >= 60: return f"{seconds / 60:.3g} minutes after the Big Bang"
    if seconds >= 1: return f"{seconds:.3g} seconds after the Big Bang"
    return f"10^{math.log10(seconds):.0f} seconds after the Big Bang"


def first_appeared(key, mass_kg=None):
    spec = FIRST_APPEARED.get(key)
    return appearance(spec, mass_kg) if spec else None


def appearance(spec, mass_kg=None):
    """(when, basis, confidence, note) -> first_appeared record. when: ("now",), ("pbh",), ("after_s", s),
    ("after_yr", years) or ("ago_yr", years)."""
    (kind, *val), basis, conf, note = spec
    age = lcdm_age()
    if kind == "now":
        return {"seconds_after_big_bang": age, "years_ago": 0.0, "log10_seconds": round(math.log10(age), 6),
                "label": "today", "basis": basis, "confidence": conf, "note": note}
    if kind == "pbh":
        t = G * mass_kg / C**3
        years_ago = None
    elif kind == "after_s":
        t, years_ago = val[0], None
    elif kind == "after_yr":
        t, years_ago = val[0] * YEAR_S, None
    else:
        years_ago = val[0]
        t = age - years_ago * YEAR_S
    if years_ago is None and t > age / 2:
        years_ago = (age - t) / YEAR_S
    # full precision: recent events differ from the age of the universe only in the last few digits
    return {"seconds_after_big_bang": t, "years_ago": float(f"{years_ago:.6g}") if years_ago is not None else None,
            "log10_seconds": round(math.log10(t), 6), "label": _when_label(t, years_ago),
            "basis": basis, "confidence": conf, "note": note}


def _build_chi():
    """Comoving particle horizon chi(a) = c * integral da/(a^2 H), on the same grid as LCDM_TABLE."""
    a_min, a_max, steps = 1e-35, 1e6, 200_000
    x0, x1 = math.log(a_min), math.log(a_max)
    dx = (x1 - x0) / steps
    chi = C * a_min / (H0 * math.sqrt(OMEGA_R))
    out = [chi]
    prev = 1 / (a_min * _hubble_rate(a_min))
    for i in range(1, steps + 1):
        a = math.exp(x0 + i * dx)
        cur = 1 / (a * _hubble_rate(a))
        chi += C * 0.5 * (prev + cur) * dx
        prev = cur
        out.append(chi)
    return out


# Effective number of relativistic species g*(T) (energy density), Standard Model. Species drop out gradually
# as the temperature falls below their mass, so g* is interpolated smoothly (log-log) between these points;
# a step function would make the temperature jump up where a species disappears.
G_STAR = [(1e4, 106.75), (1e2, 100.0), (10, 86.25), (2, 76.0), (0.5, 62.0), (0.25, 55.0), (0.15, 30.0),
          (0.1, 17.25), (0.05, 12.0), (0.01, 10.75), (1e-3, 10.75), (2e-4, 6.0), (5e-5, 3.6), (1e-5, 3.363)]


def g_star(T_gev):
    if T_gev >= G_STAR[0][0]: return G_STAR[0][1]
    if T_gev <= G_STAR[-1][0]: return G_STAR[-1][1]
    for (t1, g1), (t2, g2) in zip(G_STAR, G_STAR[1:]):
        if t2 <= T_gev <= t1:
            f = (math.log(T_gev) - math.log(t1)) / (math.log(t2) - math.log(t1))
            return math.exp(math.log(g1) + f * (math.log(g2) - math.log(g1)))
K_B_GEV = 8.617e-14     # Boltzmann constant in GeV per kelvin
WIEN_B = 2.897771955e-3  # m K: thermal spectrum peaks at lambda = b / T


def radiation_temperature_K(rho_kg_m3):
    """Temperature of radiation with this mass density: rho c^2 = (pi^2/30) g* (kT)^4 / (hbar c)^3, with g*(T)."""
    g = 106.75
    for _ in range(40):
        kT = (30 * rho_kg_m3 * C**2 * (HBAR * C)**3 / (math.pi**2 * g)) ** 0.25      # joules
        T = kT / K_B
        g = 0.5 * g + 0.5 * g_star(T * K_B_GEV)     # damped fixed-point iteration
    return T


def cosmic_history(samples=700):
    """The universe at evenly spaced 'story' times: log time after the Big Bang for the first half of cosmic
    history, then log time before today (so both the first second and the last century get room)."""
    chi = _build_chi()
    tab = LCDM_TABLE
    age = lcdm_age()
    half = math.log10(age / 2)
    s0, s1 = math.log10(T_MEET), 2 * half - math.log10(YEAR_S)
    rows = []
    for i in range(samples):
        s_ = s0 + (s1 - s0) * i / (samples - 1)
        if s_ <= half:
            t, ago = 10**s_, None
        else:
            lb = 10 ** (2 * half - s_)
            t, ago = age - lb, lb / YEAR_S
        lo, hi = 0, len(tab) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if tab[mid][0] < t: lo = mid
            else: hi = mid
        (t0, a0), (t1, a1) = tab[lo], tab[hi]
        f = (math.log(t) - math.log(t0)) / (math.log(t1) - math.log(t0))
        a = math.exp(math.log(a0) + f * (math.log(a1) - math.log(a0)))
        ch = math.exp(math.log(chi[lo]) + f * (math.log(chi[hi]) - math.log(chi[lo])))
        hub = _hubble_rate(a)
        rho = 3 * hub**2 / (8 * math.pi * G)
        # early on everything is radiation, so its density sets the temperature (with the species present then);
        # later the photons simply cool as the universe stretches
        temp = radiation_temperature_K(rho) if t < 1e9 else T_CMB / a
        rows.append([float(f"{t:.7g}"), float(f"{ago:.7g}") if ago is not None else None,
                     round(math.log10(rho), 5),
                     round(math.log10(2 * C / hub), 5), round(math.log10(2 * a * ch), 5),
                     round(math.log10(temp), 4)])
    # first row exactly at the apex: Hubble sphere and observable universe both 2 Planck lengths across
    hub0 = 2 * C / 10**APEX_W
    a0 = math.sqrt(2 * H0 * math.sqrt(OMEGA_R) * T_MEET)
    rho0 = 3 * hub0**2 / (8 * math.pi * G)
    rows[0] = [T_MEET, None, round(math.log10(rho0), 5), APEX_W, APEX_W, round(math.log10(radiation_temperature_K(rho0)), 4)]
    rows.append([age, 0.0, round(math.log10(RHO_CRIT), 6), round(LOG_HUBBLE_W, 6),
                 round(LOG_PARTICLE_HORIZON_W, 6), round(math.log10(T_CMB), 4)])
    return {
        "start": {
            "seconds_after_big_bang": T_MEET,
            "log10_width_m": APEX_W, "log10_mass_kg": APEX_W + round(LOG_SCHW, 6),
            "label": "The Big Bang: all three walls meet",
            "summary": f"{T_MEET:.2g} s (half the Planck time) · 2 Planck lengths across · half the Planck mass",
            "explanation": "The Hubble sphere is exactly as small as quantum uncertainty allows and as dense as gravity "
                           "allows, so the three walls cross at one point. Earlier than this they would cross over and "
                           "the triangle turns inside out: that needs a theory of quantum gravity. Where exactly they meet "
                           "depends on factor-of-2 conventions (diameter vs radius, hbar vs h); this chart's put it at half "
                           "the Planck time.",
        },
        "description": "The universe at 700 moments from the instant the three walls meet (half the Planck time) to today "
                       "(flat LambdaCDM, Planck 2018). "
                       "Sample spacing is even in log time after the Big Bang up to half the age of the universe, "
                       "then even in log time before today. The last row is today exactly.",
        "columns": ["seconds_after_big_bang", "years_ago", "log10_mean_density_kg_m3", "log10_hubble_diameter_m",
                    "log10_observable_universe_diameter_m", "log10_radiation_temperature_K"],
        "age_seconds": age,
        "temperature_note": "Radiation temperature. Before 1e9 s (~30 years) it is computed from the radiation "
                            "density with the Standard Model's count of relativistic species g*(T) (106.75 above "
                            "the top-quark mass, falling smoothly to 3.36 after electron-positron annihilation); "
                            "afterwards it is T_cmb / a.",
        "wien_b_m_K": WIEN_B,
        "rows": rows,
    }


def lcdm_state(t, now=False):
    """(log10 mean density kg/m^3, log10 Hubble-sphere diameter m) at time t; now=True uses a = 1 exactly."""
    if now:
        hub = H0
    elif t >= LCDM_TABLE[-1][0]:                 # far future (a > 1e6): only the cosmological constant is left
        hub = H0 * math.sqrt(OMEGA_L)
    else:
        hub = _hubble_rate(lcdm_scale_factor(t))
    rho = 3 * hub**2 / (8 * math.pi * G)
    return round(math.log10(rho), 6), round(math.log10(2 * C / hub), 6)


def timeline():
    markers = []
    for mid, num, text, top, npx, t, note in TIME_MARKERS:
        cross_x = top[0] - (DENSITY_RULER_Y - top[1]) / 3.1
        rho, hubble_w = lcdm_state(t, now=(mid == "now"))
        markers.append({
            "id": mid, "printed_value": num, "printed_text": text,
            "log10_seconds": r3(math.log10(t)), "seconds": float(f"{t:.4g}"),
            "line_top": point(top, MAIN_IMG), "number_label": point(npx, MAIN_IMG),
            "chart_density_at_ruler_log10_g_per_L": r3(D_AX.value(cross_x)),
            "friedmann_density_log10_kg_m3": r3(friedmann_log_density(t)),
            "density_log10_kg_m3": rho,
            "hubble_diameter_log10_m": hubble_w,
            "note": note,
        })
    eras = []
    for eid, label, a, b, (x0, x1), tpx, ref, note in ERAS:
        eras.append({
            "id": eid, "printed_label": label, "from_marker": a, "to_marker": b,
            "hypothetical": label.endswith("*"),
            "bracket": [point((x0, 703), MAIN_IMG), point((x1, 703), MAIN_IMG)],
            "text": point(tpx, MAIN_IMG),
            "reference_log10_seconds": [lg(ref[0]), lg(ref[1])] if ref[0] else None,
            "note": note,
        })
    return {
        "description": "The top of the poster doubles as a timeline: each red dotted 'time' line is drawn "
                       "parallel to the density lines because the universe's average density falls as it ages "
                       "(rho ~ 3/(32 pi G t^2)). The tick ruler under the time labels is the DENSITY axis.",
        "time_axis_title": "TIME 10^n s since Big Bang",
        "density_model": "density_log10_kg_m3 is the mean density of a flat LambdaCDM universe (Planck 2018: "
                         f"H0 = {H0_KM_S_MPC}, Omega_m = {OMEGA_M}, Omega_r = {OMEGA_R}), i.e. 3H^2/(8 pi G). "
                         "hubble_diameter_log10_m = 2c/H at that time; the sphere of that diameter at that density "
                         "sits exactly on the black-hole line. 'now' uses a = 1 exactly; the model age is "
                         f"{lcdm_age() / 3.156e7 / 1e9:.2f} Gyr. friedmann_density_log10_kg_m3 is the radiation-only "
                         "formula, which is wrong after ~50,000 years.",
        "markers": markers,
        "eras": eras,
        "density_ruler": {
            "title": "DENSITY 10^n g/L",
            "row_y_px": DENSITY_RULER_Y,
            "calibration": D_AX.describe(),
            "minor_tick_step_decades": 3,
            "tall_ticks": density_ruler(),
        },
        "density_lines": density_lines(),
        "history": cosmic_history(),
    }


# =============================================================================
# STELLAR EVOLUTION inset
# =============================================================================
SD_AX = Axis("log10 diameter", "km", "x", list(zip(range(3, 11), [749.5, 887.5, 1025.5, 1163.5, 1302.5, 1440.5,
                                                                   1578.5, 1717.0])),
             "Top axis 'DIAMETER 10^n km' (frame spans 2..11).")
SM_AX = Axis("log10 mass", "solar masses", "y", list(zip(range(2, -6, -1), [766.5, 904.5, 1043.5, 1181.5, 1319.5,
                                                                             1458.0, 1596.5, 1734.5])),
             "Left axis 'MASS 10^n solar masses' (frame spans -6..3).")


def stellar_values(px):
    return {"log10_diameter_km": r3(SD_AX.value(px[0])), "log10_mass_msun": r3(SM_AX.value(px[1]))}


STELLAR_OBJECTS = [
    # (id, printed label, name, category, icons, label px, ref mass Msun, ref diameter km, confidence, notes, desc, main id)
    ("black_holes", "BLACK HOLES", "Stellar black holes", "black_hole", [(842, 780), (649, 954)], (770, 778),
     10, 4 * G * 10 * M_SUN / C**2 / 1e3, "medium", "Representative 10 solar masses; diameter = Schwarzschild diameter.",
     "Region above the Schwarzschild line; the W.R.-star arrow ends at a black hole.", "v616_monocerotis"),
    ("neutron_stars", "NEUTRON STARS", "Neutron stars", "stellar_remnant", [(706, 978), (692, 1021), (682, 1057)],
     (752, 1146), 1.4, 24, "medium", "Typical 1.4 solar masses, ~12 km radius.",
     "Collapsed cores held up by neutron degeneracy; arrows from white dwarfs and red giants point here.", "neutron_star"),
    ("white_dwarfs", "WHITE DWARFS", "White dwarfs", "stellar_remnant", [(1107, 1060), (1140, 1074), (1179, 1103)],
     (1033, 1146), 0.6, 1.7e4, "medium", "Typical 0.6 solar masses.",
     "Earth-sized remnants of Sun-like stars.", "white_dwarfs"),
    ("sun", "SUN", "Sun", "star", [(1343, 1045)], (1408, 1081), 1.0, 1.3927e6, "high", "",
     "Our star; an arrow shows it will expand into a red giant.", "sun"),
    ("main_sequence", "MAIN SEQUENCE", "Main-sequence stars", "star",
     [(1296, 1131), (1293, 1203), (1418, 967), (1443, 917)], (1358, 942), None, None, "medium",
     "Range ~0.08-100 solar masses; diameters ~1.4e5-3e7 km.",
     "Stars fusing hydrogen in their cores, drawn as a diagonal band from red dwarfs up to massive blue stars.", None),
    ("red_giants", "RED GIANTS", "Red giants", "star",
     [(1604, 1045), (1655, 1043), (1761, 992), (1787, 1035)], (1783, 1096), 1.08, 2 * 25.4 * R_SUN_KM, "medium",
     "Values for Arcturus.", "Swollen, cool stars late in life.", None),
    ("super_giants", "SUPER GIANTS", "Supergiants", "star",
     [(1501, 825), (1608, 859), (1694, 902), (1737, 856), (1529, 753)], (1844, 802), 18, 2 * 764 * R_SUN_KM, "medium",
     "Values for Betelgeuse.", "The largest stars, evolved from massive main-sequence stars.", None),
    ("wr_stars", "W.R. STARS", "Wolf-Rayet stars", "star", [(1353, 778), (1339, 859)], (1189, 791),
     20, 2 * 5 * R_SUN_KM, "low", "Representative: ~20 solar masses, ~5 solar radii.",
     "Very hot massive stars that have shed their outer layers; an arrow shows them collapsing to black holes.", None),
    ("brown_dwarfs", "BROWN DWARFS", "Brown dwarfs", "substellar", [(1200, 1207), (1234, 1237), (1253, 1253)],
     (1479, 1250), 0.04, 1.4e5, "medium", "Representative ~40 Jupiter masses, about Jupiter's size.",
     "Objects too light to fuse hydrogen (~13-80 Jupiter masses).", "brown_dwarf"),
    ("beta_pictoris_b", "BETA PICTORIS B", "Beta Pictoris b", "planet", [(1201, 1332)], (1425, 1317),
     11 * M_JUP / M_SUN, 2 * 1.46 * R_JUP_KM, "medium", "Mass estimates ~9-13 Jupiter masses.",
     "A young super-Jupiter imaged directly around the star Beta Pictoris.", None),
    ("jupiter", "JUPITER", "Jupiter", "planet", [(1193, 1472)], (1319, 1458), M_JUP / M_SUN, 1.3982e5, "high", "",
     "Largest planet in the Solar System.", "jupiter"),
    ("saturn", "SATURN", "Saturn", "planet", [(1197, 1561)], (1345, 1545), 5.683e26 / M_SUN, 1.1646e5, "high", "",
     "Ringed gas giant, less dense than water.", "saturn"),
    ("uranus", "URANUS, NEPTUNE", "Uranus", "planet", [(1107, 1677)], (1372, 1655), 8.681e25 / M_SUN, 5.0724e4,
     "high", "Left of the two icons (tentative).", "Ice giant.", "uranus"),
    ("neptune", "URANUS, NEPTUNE", "Neptune", "planet", [(1138, 1677)], (1372, 1655), 1.024e26 / M_SUN, 4.9244e4,
     "high", "Right of the two icons (tentative).", "Ice giant.", "neptune"),
    ("kepler_22b", "KEPLER 22-B", "Kepler-22b", "planet", [(1083, 1761)], (1272, 1731), None, 2 * 2.38 * R_EARTH_KM,
     "medium", "Radius ~2.4 Earth radii; only upper limits exist for its mass.",
     "A planet in its star's habitable zone, ~600 light-years away.", None),
    ("earth", "EARTH, VENUS", "Earth", "planet", [(1028, 1844)], (1233, 1813), M_EARTH / M_SUN, 1.2742e4, "high", "",
     "One icon is drawn for both Earth and Venus.", "earth"),
    ("venus", "EARTH, VENUS", "Venus", "planet", [(1028, 1844)], (1233, 1813), 4.867e24 / M_SUN, 1.2104e4, "high", "",
     "Shares the Earth icon.", "venus"),
]

STELLAR_TRANSITIONS = [
    # (id, from, to, printed label, polyline px, meaning)
    ("wr_collapse", "wr_stars", "black_holes", None, [(1495, 785), (950, 775)],
     "Massive Wolf-Rayet stars collapse into black holes."),
    ("red_giants_decay", "red_giants", "neutron_stars", "DECAYS INTO..", [(1720, 1020), (1300, 975), (805, 970)],
     "Drawn from the red giants to the neutron stars (massive stars end as neutron stars; Sun-like ones as white dwarfs)."),
    ("white_dwarf_to_neutron_star", "white_dwarfs", "neutron_stars", None, [(1040, 1060), (770, 1060)],
     "Arrow from the white dwarfs toward the neutron stars (a white dwarf pushed past the Chandrasekhar limit collapses)."),
    ("sun_to_red_giant", "sun", "red_giants", None, [(1380, 1045), (1550, 1045)],
     "The Sun will swell into a red giant in ~5 billion years."),
    ("main_sequence_to_supergiants", "main_sequence", "super_giants", "EXPANDS INTO..", [(1465, 925), (1650, 925)],
     "Massive main-sequence stars expand into supergiants."),
    ("degenerate_track", "brown_dwarfs", "white_dwarfs", "DEGENERATE MATTER", [(1350, 1395), (1240, 1300), (1145, 1190)],
     "Dashed line: for degenerate objects, radius shrinks as mass grows (gas giants -> brown dwarfs -> white dwarfs)."),
]

STELLAR_LINES = [
    ("tov_limit", "TOLMAN-OPPENHEIMER-VOLKOFF LIMIT", [(675, 973), (1855, 973)], (2174, 935), "dotted horizontal",
     "Maximum neutron-star mass, ~2.2-2.9 solar masses.", (2.2, 2.9)),
    ("chandrasekhar_limit", "CHANDRASEKHAR LIMIT", [(1072, 1007), (1855, 1007)], (2159, 1018), "dotted horizontal",
     "Maximum white-dwarf mass, ~1.44 solar masses.", (1.44, 1.44)),
    ("schwarzschild_radius", "SCHWARZSCHILD RADIUS", [(957, 670), (610, 1028)], (850, 420), "region edge",
     "Edge of the black-hole region.", None),
    ("water_density_line", "WATER DENSITY / WATER DENSITY LINE",
     [(1484, 630), (1440, 775), (1380, 925), (1333, 1075), (1285, 1225), (1232, 1375), (1188, 1525),
      (1156, 1625), (1111, 1775), (1078, 1873)], (1474, 400),
     "blue dotted (traced from pixels)",
     "Constant density of water (slope ~3 in log space); passes the Sun, Jupiter and Saturn (~0.7-1.4 g/cm^3).", None),
]


# Ranges for groups the inset draws as a band rather than a single object.
STELLAR_RANGES = {"main_sequence": {"mass_msun_range": [0.08, 100], "diameter_km_range": [1.4e5, 2.8e7]}}


def stellar_inset():
    objs = []
    for (oid, label, name, cat, icons, lpx, msun, dkm, conf, notes, desc, main_id) in STELLAR_OBJECTS:
        objs.append({
            "id": oid, "name": name, "printed_label": label, "category": cat,
            "image": {"icon": point(icons[0], MAIN_IMG), "all_icons_px": [list(p) for p in icons],
                      "label": point(lpx, MAIN_IMG)},
            "chart": stellar_values(icons[0]),
            "reference": {"mass_msun": float(f"{msun:.4g}") if msun else None,
                          "diameter_km": float(f"{dkm:.4g}") if dkm else None,
                          "log10_mass_msun": lg(msun), "log10_diameter_km": lg(dkm),
                          "confidence": conf, "notes": notes, **STELLAR_RANGES.get(oid, {})},
            "description": desc, "main_chart_object_id": main_id,
            "first_appeared": first_appeared(main_id or oid),
        })
    lines = []
    for lid, label, poly, tpx, style, meaning, ref in STELLAR_LINES:
        entry = {"id": lid, "printed_label": label, "style": style, "polyline": [point(p, MAIN_IMG) for p in poly],
                 "text": point(tpx, MAIN_IMG), "meaning": meaning}
        if ref:
            entry["chart_log10_mass_msun"] = r3(SM_AX.value(poly[0][1]))
            entry["reference_mass_msun_range"] = list(ref)
        lines.append(entry)
    return {
        "title": "STELLAR EVOLUTION",
        "description": "Zoom of the stars-and-planets region: diameter vs mass, with arrows showing how stars evolve.",
        "frame": [point((605.5, 625.5), MAIN_IMG), point((1855.5, 1875.0), MAIN_IMG)],
        "axes": {"x": SD_AX.describe(), "y": SM_AX.describe()},
        "equations": {
            "schwarzschild_radius": "log10 D[km] = log10 M[Msun] + schwarzschild_offset  (D = 4GM/c^2)",
            "schwarzschild_offset": round(math.log10(4 * G * M_SUN / C**2 / 1e3), 6),
            "water_density_line": "log10 M[Msun] = 3 log10 D[km] + water_offset  (sphere at 1000 kg/m^3)",
            "water_offset": round(math.log10(1000 * math.pi / 6 * 1e9 / M_SUN), 6),
            "tov_limit_msun": [2.2, 2.9],
            "chandrasekhar_limit_msun": 1.44,
        },
        "objects": objs,
        "transitions": [{"id": t, "from": a, "to": b, "printed_label": lab,
                         "polyline": [point(p, MAIN_IMG) for p in poly], "meaning": m}
                        for t, a, b, lab, poly, m in STELLAR_TRANSITIONS],
        "lines": lines,
        "region_labels": [
            {"printed_label": "BLACK HOLES", "text": point((770, 778), MAIN_IMG)},
            {"printed_label": "GAS GIANTS", "text": point((1078, 1422), MAIN_IMG)},
            {"printed_label": "TERRESTRIAL PLANETS", "text": point((892, 1737), MAIN_IMG)},
            {"printed_label": "MAIN SEQUENCE", "text": point((1358, 942), MAIN_IMG)},
        ],
    }


# =============================================================================
# FUNDAMENTAL PARTICLES inset
# =============================================================================
PL_AX = Axis("log10 wavelength", "m", "x", list(zip(range(-18, -10), [742.5, 880.0, 1017.5, 1155.5, 1293.5, 1431.0,
                                                                     1568.5, 1706.5])),
             "Top axis 'WAVELENGTH 10^n m' (frame spans -19..-10). Particles sit near their reduced Compton wavelength.")
PM_AX = Axis("log10 mass", "eV", "y", list(zip(range(11, 3, -1), [2819.0, 2957.0, 3095.5, 3234.0, 3372.0, 3510.5,
                                                                   3648.5, 3787.5])),
             "Left axis 'MASS 10^n eV' (frame spans 3..12).")

LEGEND = {
    "green": {"printed": "LEPTON", "hex": "#70ff00", "used_for": ["proton", "neutron", "meson"],
              "actual_class": "hadron"},
    "orange": {"printed": "BOSON", "hex": "#ff712e", "used_for": ["higgs", "z_boson", "w_boson", "photon"],
               "actual_class": "boson"},
    "blue": {"printed": "HADRONS", "hex": "#4abdff",
             "used_for": ["tau", "muon", "electron", "tau_neutrino", "muon_neutrino", "electron_neutrino"],
             "actual_class": "lepton"},
    "yellow": {"printed": "QUARKS", "hex": "#ffc800", "used_for": ["top", "bottom", "charm", "strange", "down", "up"],
               "actual_class": "quark"},
}

PARTICLES = [
    # (id, printed label, name, class, chart colour, dot px, label px, mass eV, mass note, charge, spin, generation, desc)
    ("top", "TOP", "Top quark", "quark", "yellow", (705, 2785), (754, 2725), 172.57e9, "", "+2/3", "1/2", 3,
     "The heaviest known elementary particle; decays before it can form hadrons."),
    ("higgs", "HIGGS", "Higgs boson", "boson", "orange", (735, 2812), (799, 2737), 125.2e9, "", "0", "0", None,
     "Excitation of the Higgs field, which gives other particles mass; discovered at CERN in 2012."),
    ("z_boson", "Z", "Z boson", "boson", "orange", (750, 2830), (808, 2795), 91.188e9, "", "0", "1", None,
     "Neutral carrier of the weak force."),
    ("w_boson", "W", "W boson", "boson", "orange", (771, 2845), (825, 2815), 80.369e9, "", "±1", "1", None,
     "Charged carrier of the weak force; drives radioactive beta decay."),
    ("bottom", "BOTTOM", "Bottom quark", "quark", "yellow", (938, 3019), (1030, 2924), 4.18e9, "", "-1/3", "1/2", 3,
     "Third-generation down-type quark."),
    ("tau", "TAU", "Tau lepton", "lepton", "blue", (988, 3059), (1017, 3001), 1.77693e9, "", "-1", "1/2", 3,
     "The heaviest charged lepton, ~3,500 times the electron's mass."),
    ("charm", "CHARM", "Charm quark", "quark", "yellow", (1008, 3088), (1092, 2995), 1.273e9, "", "+2/3", "1/2", 2,
     "Second-generation up-type quark."),
    ("proton", "PROTON", "Proton", "hadron", "green", (1039, 3133), (1120, 3033), 938.272e6, "", "+1", "1/2", None,
     "Composite particle (two up quarks + one down) at the heart of every atom."),
    ("neutron", "NEUTRON", "Neutron", "hadron", "green", (1075, 3166), (1178, 3052), 939.565e6, "", "0", "1/2", None,
     "Composite particle (one up + two down quarks); free neutrons decay in ~15 minutes."),
    ("meson", "MESON", "Meson (pion)", "hadron", "green", (1120, 3200), (1197, 3104), 139.57e6,
     "Charged pion used as the representative meson.", "±1", "0", None,
     "Quark-antiquark pairs; pions are the lightest."),
    ("muon", "MUON", "Muon", "lepton", "blue", (1156, 3236), (1217, 3149), 105.658e6, "", "-1", "1/2", 2,
     "A heavy cousin of the electron that lives ~2.2 µs."),
    ("strange", "STRANGE", "Strange quark", "quark", "yellow", (1181, 3252), (1275, 3149), 93.5e6, "", "-1/3", "1/2", 2,
     "Second-generation down-type quark."),
    ("tau_neutrino", "NEUTRINO (TAU)", "Tau neutrino", "lepton", "blue", (1225, 3310), (1371, 3187), None,
     "Chart position matches the old direct upper limit (<18.2 MeV); oscillation data imply < ~1 eV.", "0", "1/2", 3,
     "The neutrino partner of the tau."),
    ("down", "DOWN", "Down quark", "quark", "yellow", (1324, 3414), (1403, 3335), 4.70e6, "", "-1/3", "1/2", 1,
     "Light quark; two of them are in every neutron."),
    ("up", "UP", "Up quark", "quark", "yellow", (1376, 3451), (1416, 3393), 2.16e6, "", "+2/3", "1/2", 1,
     "The lightest quark; two of them are in every proton."),
    ("electron", "ELECTRON", "Electron", "lepton", "blue", (1470, 3554), (1577, 3445), 0.51099895e6, "", "-1", "1/2", 1,
     "The lightest charged particle; fills the shells of every atom."),
    ("muon_neutrino", "NEUTRINO (MUON)", "Muon neutrino", "lepton", "blue", (1513, 3593), (1673, 3419), None,
     "Chart position matches the old direct upper limit (<0.19 MeV).", "0", "1/2", 2,
     "The neutrino partner of the muon."),
    ("photon", "PHOTON (GAMMA RAY)", "Photon (gamma ray)", "boson", "orange", (1573, 3666), (1718, 3567), 0.0,
     "Massless; plotted at a gamma-ray energy (~10^5 eV).", "0", "1", None,
     "The particle of light and carrier of electromagnetism."),
    ("electron_neutrino", "NEUTRINO (ELECTRON)", "Electron neutrino", "lepton", "blue", (1834, 3912), (1956, 3818), None,
     "Upper limit < 0.45 eV (KATRIN); the chart places it near 10^3 eV.", "0", "1/2", 1,
     "The lightest known massive particle; trillions pass through you every second."),
]

PARTICLE_RELATIONS = [
    # (type, from, [to...], note)
    ("decays_into", "top", ["w_boson", "bottom"], "~100% of top decays."),
    ("decays_into", "higgs", ["bottom", "w_boson", "tau", "z_boson", "photon"], "Main channels: bb (~58%), WW* (~21%), tau tau (~6%), ZZ* (~3%), gamma gamma (~0.2%)."),
    ("decays_into", "z_boson", ["electron", "muon", "tau", "up", "down", "charm", "strange", "bottom"], "Fermion-antifermion pairs (and neutrino pairs)."),
    ("decays_into", "w_boson", ["electron", "electron_neutrino", "muon", "muon_neutrino", "tau", "tau_neutrino", "up", "down", "charm", "strange"], "Lepton + neutrino (~33%) or quark pairs (~67%)."),
    ("decays_into", "bottom", ["charm", "w_boson"], "Via a virtual W."),
    ("decays_into", "tau", ["tau_neutrino", "w_boson"], "Via a virtual W, giving hadrons or a lighter lepton + neutrinos."),
    ("decays_into", "charm", ["strange", "w_boson"], "Via a virtual W."),
    ("decays_into", "muon", ["electron", "muon_neutrino", "electron_neutrino"], "Lifetime ~2.2 µs."),
    ("decays_into", "strange", ["up", "w_boson"], "Via a virtual W."),
    ("decays_into", "neutron", ["proton", "electron", "electron_neutrino"], "Free neutron beta decay, ~15 min."),
    ("decays_into", "meson", ["muon", "muon_neutrino"], "Charged pion decay."),
    ("combines_into", "up", ["proton", "neutron", "meson"], "Proton = uud, neutron = udd."),
    ("combines_into", "down", ["proton", "neutron", "meson"], "Proton = uud, neutron = udd."),
]


# Current upper limits for particles whose mass is unmeasured (eV).
MASS_UPPER_LIMITS_EV = {"electron_neutrino": 0.45, "muon_neutrino": 1.9e5, "tau_neutrino": 1.82e7}


def particles_inset():
    out = []
    for (pid, label, name, cls, colour, dot, lpx, ev, mnote, q, spin, gen, desc) in PARTICLES:
        kg = ev * EV_KG if ev else None
        out.append({
            "id": pid, "name": name, "printed_label": label, "class": cls,
            "chart_colour": colour, "legend_says": LEGEND[colour]["printed"],
            "image": {"icon": point(dot, MAIN_IMG), "label": point(lpx, MAIN_IMG)},
            "chart": {"log10_wavelength_m": r3(PL_AX.value(dot[0])), "log10_mass_eV": r3(PM_AX.value(dot[1]))},
            "reference": {
                "mass_eV": float(f"{ev:.6g}") if ev is not None else None,
                "log10_mass_eV": lg(ev) if ev else None,
                "mass_kg": float(f"{kg:.4g}") if kg else None,
                "reduced_compton_wavelength_m": float(f"{HBAR / (kg * C):.4g}") if kg else None,
                "mass_upper_limit_eV": MASS_UPPER_LIMITS_EV.get(pid),
                "electric_charge": q, "spin": spin, "generation": gen, "notes": mnote,
            },
            "description": desc,
            "first_appeared": first_appeared("particle:" + pid),
        })
    return {
        "title": "FUNDAMENTAL PARTICLES",
        "description": "Zoom of the bottom of the Compton limit: particles placed by mass along their Compton wavelength, "
                       "with arrows showing heavier particles decaying into lighter ones and quarks combining into hadrons.",
        "frame": [point((601.0, 2678.5), MAIN_IMG), point((1850.5, 3928.5), MAIN_IMG)],
        "axes": {"x": PL_AX.describe(), "y": PM_AX.describe()},
        "legend": [{"colour": c, **v, "legend_position": point(p, MAIN_IMG)}
                   for (c, v), p in zip(LEGEND.items(), [(1911, 3204), (1911, 3316), (1911, 3423), (1911, 3541)])],
        "legend_note": "The printed legend swaps two labels: green dots are hadrons (proton, neutron, meson) and "
                       "blue dots are leptons (electron, muon, tau, neutrinos). 'actual_class' gives the correct class.",
        "particles": out,
        "relations": [{"type": t, "from": a, "to": b, "note": n,
                       "source": "standard physics; the chart draws these as unlabelled arrows"}
                      for t, a, b, n in PARTICLE_RELATIONS],
        "chart_arrow_labels": [
            {"printed_label": "DECAYS INTO..", "text": point((1043, 3618), MAIN_IMG),
             "description": "Gold arrows from the top/Higgs/Z/W cluster sweeping down to lighter particles."},
            {"printed_label": "COMBINES INTO...", "text": point((1506, 2892), MAIN_IMG),
             "description": "Purple arrows from the up/down quarks curving back up to proton, neutron and meson."},
        ],
        "regions": [
            {"id": "wimp_dark_matter", "printed_label": "WIMP DARK MATTER*", "hypothetical": True,
             "polygon": [point(p, MAIN_IMG) for p in [(895, 2680), (1159, 2680), (1017, 3033), (818, 2892)]],
             "text": point((1008, 2770), MAIN_IMG),
             "chart_log10_mass_eV_range": [r3(PM_AX.value(3033)), r3(PM_AX.value(2680))],
             "note": "Speckled band between two dashed lines (~3 GeV to ~1 TeV)."},
        ],
        "lines": [
            {"id": "atomic_density_line", "printed_label": "ATOMIC DENSITY LINE", "style": "blue dotted",
             "polyline": [point(p, MAIN_IMG) for p in [(1841, 2680), (1410, 3927)]]},
        ],
    }


# =============================================================================
# LINEWEAVER & PATEL "All objects" chart
# =============================================================================
LR_AX = Axis("log10 radius", "cm", "x", [(-40, 432), (-20, 735), (-10, 886), (0, 1038), (10, 1189), (20, 1341),
                                          (30, 1492), (40, 1644), (50, 1795)],
             "Bottom axis 'log(physical radius) [cm]'. Top axis is the same in Mpc (offset 24.49).")
LM_AX = Axis("log10 mass", "g", "y", [(60, 490), (50, 645), (40, 802), (30, 958), (20, 1113), (10, 1270), (0, 1430),
                                       (-10, 1582), (-20, 1740), (-30, 1895), (-40, 2052), (-50, 2208)],
             "Inner left axis 'log(mass) [g]'. Outer left = log(M/M_sun) (offset -33.30); right = log(mass) [GeV] (offset +23.75).")


def lp_values(px):
    r, m = LR_AX.value(px[0]), LM_AX.value(px[1])
    return {"log10_radius_cm": r3(r), "log10_mass_g": r3(m), "log10_mass_msun": r3(m - 33.299),
            "log10_mass_GeV": r3(m + 23.749),
            # same quantities in the poster's units: width = 2r in metres, mass in kg
            "log10_width_m": r3(r - 2 + math.log10(2)), "log10_mass_kg": r3(m - 3)}


LP_OBJECTS = [
    # (id, printed label, name, kind, px, label px, main-chart id)
    ("hubble_radius", "Hubble radius", "Hubble sphere today", "dot", (1468, 543), (1620, 547), "observable_universe"),
    ("voids", "voids", "Cosmic voids", "ellipse", (1440, 633), (1583, 603), "bootes_void"),
    ("superclusters", "superclusters", "Superclusters", "ellipse", (1433, 640), (1635, 653), "laniakea_supercluster"),
    ("galaxy_clusters", "galaxy clusters", "Galaxy clusters", "ellipse", (1400, 680), (1632, 705), "el_gordo"),
    ("milky_way", "Milky Way", "Milky Way", "dot", (1385, 720), (1583, 757), "milky_way"),
    ("galaxies", "galaxies", "Galaxies", "ellipse", (1370, 750), (1535, 808), "smc_galaxy"),
    ("globular_clusters", "globular clusters", "Globular clusters", "ellipse", (1325, 833), (1595, 860), "globular_clusters"),
    ("main_sequence_stars", "main sequence stars", "Main-sequence stars", "ellipse", (1202, 898), (1615, 912), None),
    ("red_giants", "red giants", "Red giants", "ellipse", (1230, 902), (1505, 963), None),
    ("sun", "Sun", "Sun", "dot", (1202, 905), (1255, 930), "sun"),
    ("brown_dwarfs", "BD", "Brown dwarfs", "ellipse", (1188, 928), (1240, 965), "brown_dwarf"),
    ("white_dwarfs", "WD", "White dwarfs", "ellipse", (1170, 907), (1142, 968), "white_dwarfs"),
    ("neutron_stars", "NS", "Neutron stars", "dot", (1130, 897), (1083, 985), "neutron_star"),
    ("planets", "planets", "Planets", "ellipse", (1177, 970), (1460, 1015), "jupiter"),
    ("earth", "Earth", "Earth", "dot", (1171, 992), (1228, 1018), "earth"),
    ("moons_and_dwarf_planets", "moons and dwarf planets", "Moons and dwarf planets", "ellipse", (1130, 1140), (1612, 1066), "moon"),
    ("whale", "whale", "Whale", "dot", (1080, 1295), (1147, 1297), "blue_whale"),
    ("human", "human", "Human", "dot", (1063, 1350), (1133, 1360), "humans"),
    ("flea", "flea", "Flea", "dot", (1022, 1477), (1070, 1480), None),
    ("bacterium", "bacterium", "Bacterium", "dot", (970, 1617), (1070, 1617), "bacterium"),
    ("covid_virus", "COVID virus", "SARS-CoV-2 virus", "dot", (957, 1658), (1040, 1665), "virus"),
    ("atoms", "atoms", "Atoms", "ellipse", (913, 1780), (978, 1772), "oxygen_atom"),
    ("top_quark", "t", "Top quark", "open_dot", (795, 1762), (752, 1677), "fundamental_particles"),
    ("higgs_boson", "H0", "Higgs boson", "open_dot", (798, 1765), (785, 1667), "fundamental_particles"),
    ("w_boson", "W±", "W boson", "open_dot", (803, 1768), (818, 1712), "fundamental_particles"),
    ("neutron", "n", "Neutron", "open_dot", (843, 1809), (845, 1755), "fundamental_particles"),
    ("proton", "p", "Proton", "open_dot", (843, 1809), (873, 1783), "fundamental_particles"),
    ("electron", "e", "Electron", "open_dot", (907, 1876), (940, 1847), "fundamental_particles"),
    ("neutrino", "ν", "Neutrino", "open_dot", (979, 1950), (1003, 1917), "fundamental_particles"),
    ("visible_photons", None, "Visible-light photons (rainbow bars)", "rainbow", (952, 1926), None, None),
    ("quantum_gravity_point", "QG", "Planck point (quantum gravity)", "open_dot", (540, 1497), (480, 1497), None),
    ("smallest_observable_pbh", "smallest observable PBH", "Smallest observable primordial black hole", "dot",
     (843, 1190), (768, 1080), "primordial_black_hole"),
    ("three_kelvin_bh", "3K BH", "Black hole with a 3 K Hawking temperature", "dot", (1003, 1025), (965, 970), None),
]

LP_TIME_LINES = [
    # (id, printed label, seconds, top px, label px)
    ("planck", "Planck 10^-43 s", 5.39e-44, (905, 365), (855, 530)),
    ("gut", "GUT 10^-32 s", 1e-32, (1000, 365), (945, 480)),
    ("ew", "EW 10^-11 s", 1e-11, (1240, 365), (1190, 470)),
    ("nuclear", "nuclear 10^-6 s", 1e-6, (1300, 365), (1240, 500)),
    ("atomic", "atomic 10^3 s", 1e3, (1375, 365), (1330, 440)),
    ("recombination", "recomb. 10^13 s", 1e13, (1465, 365), (1420, 480)),
    ("now", "now", 4.35e17, (1530, 365), (1500, 410)),
]


# The one entry elsewhere in the datasets that already stands for each LP point, as (dataset, id). A site should
# show that entry (with the LP reading in its details) instead of drawing a second, near-identical point.
# LP points left out have no counterpart. main_chart_object_id is looser: it names the main-chart icon nearest
# in meaning (all particles share "fundamental_particles", the Hubble sphere maps to the observable universe).
LP_SAME_AS = {
    "hubble_radius": ("main_chart.physics.horizons", "hubble_radius"),
    "main_sequence_stars": ("stellar_evolution", "main_sequence"),
    "red_giants": ("stellar_evolution", "red_giants"),
    "top_quark": ("fundamental_particles", "top"),
    "higgs_boson": ("fundamental_particles", "higgs"),
    "w_boson": ("fundamental_particles", "w_boson"),
    "neutron": ("fundamental_particles", "neutron"),
    "proton": ("fundamental_particles", "proton"),
    "electron": ("fundamental_particles", "electron"),
    "quantum_gravity_point": ("main_chart.triangle", "big_bang_apex"),
}
LP_NO_COUNTERPART = {"flea", "neutrino", "visible_photons", "three_kelvin_bh"}   # the neutrinos are only upper limits


def lp_same_as(oid, main_id):
    if oid in LP_NO_COUNTERPART:
        return None
    dataset, target = LP_SAME_AS.get(oid, ("objects", main_id))
    return {"dataset": dataset, "id": target}


# ---------------------------------------------------------------------------------------------------- elements
# PubChem periodic table (https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON, read 2026-10-24):
# Z | symbol | name | atomic mass (u) | van der Waals radius (pm; blank above Es) | standard state | kind | discovered.
# Atomic mass is the standard atomic weight, or the mass of the longest-lived isotope when there is no stable one.
PUBCHEM_ELEMENTS = """
1|H|Hydrogen|1.0080|120|Gas|Nonmetal|1766
2|He|Helium|4.00260|140|Gas|Noble gas|1868
3|Li|Lithium|7.0|182|Solid|Alkali metal|1817
4|Be|Beryllium|9.012183|153|Solid|Alkaline earth metal|1798
5|B|Boron|10.81|192|Solid|Metalloid|1808
6|C|Carbon|12.011|170|Solid|Nonmetal|Ancient
7|N|Nitrogen|14.007|155|Gas|Nonmetal|1772
8|O|Oxygen|15.999|152|Gas|Nonmetal|1774
9|F|Fluorine|18.99840316|135|Gas|Halogen|1670
10|Ne|Neon|20.180|154|Gas|Noble gas|1898
11|Na|Sodium|22.9897693|227|Solid|Alkali metal|1807
12|Mg|Magnesium|24.305|173|Solid|Alkaline earth metal|1808
13|Al|Aluminum|26.981538|184|Solid|Post-transition metal|Ancient
14|Si|Silicon|28.085|210|Solid|Metalloid|1854
15|P|Phosphorus|30.97376200|180|Solid|Nonmetal|1669
16|S|Sulfur|32.07|180|Solid|Nonmetal|Ancient
17|Cl|Chlorine|35.45|175|Gas|Halogen|1774
18|Ar|Argon|39.9|188|Gas|Noble gas|1894
19|K|Potassium|39.0983|275|Solid|Alkali metal|1807
20|Ca|Calcium|40.08|231|Solid|Alkaline earth metal|Ancient
21|Sc|Scandium|44.95591|211|Solid|Transition metal|1879
22|Ti|Titanium|47.867|187|Solid|Transition metal|1791
23|V|Vanadium|50.9415|179|Solid|Transition metal|1801
24|Cr|Chromium|51.996|189|Solid|Transition metal|1797
25|Mn|Manganese|54.93804|197|Solid|Transition metal|1774
26|Fe|Iron|55.84|194|Solid|Transition metal|Ancient
27|Co|Cobalt|58.93319|192|Solid|Transition metal|1735
28|Ni|Nickel|58.693|163|Solid|Transition metal|1751
29|Cu|Copper|63.55|140|Solid|Transition metal|Ancient
30|Zn|Zinc|65.4|139|Solid|Transition metal|1746
31|Ga|Gallium|69.723|187|Solid|Post-transition metal|1875
32|Ge|Germanium|72.63|211|Solid|Metalloid|1886
33|As|Arsenic|74.92159|185|Solid|Metalloid|Ancient
34|Se|Selenium|78.97|190|Solid|Nonmetal|1817
35|Br|Bromine|79.90|183|Liquid|Halogen|1826
36|Kr|Krypton|83.80|202|Gas|Noble gas|1898
37|Rb|Rubidium|85.468|303|Solid|Alkali metal|1861
38|Sr|Strontium|87.62|249|Solid|Alkaline earth metal|1790
39|Y|Yttrium|88.90584|219|Solid|Transition metal|1794
40|Zr|Zirconium|91.22|186|Solid|Transition metal|1789
41|Nb|Niobium|92.90637|207|Solid|Transition metal|1801
42|Mo|Molybdenum|95.95|209|Solid|Transition metal|1778
43|Tc|Technetium|96.90636|209|Solid|Transition metal|1937
44|Ru|Ruthenium|101.1|207|Solid|Transition metal|1827
45|Rh|Rhodium|102.9055|195|Solid|Transition metal|1803
46|Pd|Palladium|106.42|202|Solid|Transition metal|1803
47|Ag|Silver|107.868|172|Solid|Transition metal|Ancient
48|Cd|Cadmium|112.41|158|Solid|Transition metal|1817
49|In|Indium|114.818|193|Solid|Post-transition metal|1863
50|Sn|Tin|118.71|217|Solid|Post-transition metal|Ancient
51|Sb|Antimony|121.760|206|Solid|Metalloid|Ancient
52|Te|Tellurium|127.6|206|Solid|Metalloid|1782
53|I|Iodine|126.9045|198|Solid|Halogen|1811
54|Xe|Xenon|131.29|216|Gas|Noble gas|1898
55|Cs|Cesium|132.9054520|343|Solid|Alkali metal|1860
56|Ba|Barium|137.33|268|Solid|Alkaline earth metal|1808
57|La|Lanthanum|138.9055|240|Solid|Lanthanide|1839
58|Ce|Cerium|140.116|235|Solid|Lanthanide|1803
59|Pr|Praseodymium|140.90766|239|Solid|Lanthanide|1885
60|Nd|Neodymium|144.24|229|Solid|Lanthanide|1885
61|Pm|Promethium|144.91276|236|Solid|Lanthanide|1945
62|Sm|Samarium|150.4|229|Solid|Lanthanide|1879
63|Eu|Europium|151.964|233|Solid|Lanthanide|1901
64|Gd|Gadolinium|157.25|237|Solid|Lanthanide|1880
65|Tb|Terbium|158.92535|221|Solid|Lanthanide|1843
66|Dy|Dysprosium|162.500|229|Solid|Lanthanide|1886
67|Ho|Holmium|164.93033|216|Solid|Lanthanide|1878
68|Er|Erbium|167.26|235|Solid|Lanthanide|1843
69|Tm|Thulium|168.93422|227|Solid|Lanthanide|1879
70|Yb|Ytterbium|173.05|242|Solid|Lanthanide|1878
71|Lu|Lutetium|174.9667|221|Solid|Lanthanide|1907
72|Hf|Hafnium|178.49|212|Solid|Transition metal|1923
73|Ta|Tantalum|180.9479|217|Solid|Transition metal|1802
74|W|Tungsten|183.84|210|Solid|Transition metal|1783
75|Re|Rhenium|186.207|217|Solid|Transition metal|1925
76|Os|Osmium|190.2|216|Solid|Transition metal|1803
77|Ir|Iridium|192.22|202|Solid|Transition metal|1803
78|Pt|Platinum|195.08|209|Solid|Transition metal|1735
79|Au|Gold|196.96657|166|Solid|Transition metal|Ancient
80|Hg|Mercury|200.59|209|Liquid|Transition metal|Ancient
81|Tl|Thallium|204.383|196|Solid|Post-transition metal|1861
82|Pb|Lead|207|202|Solid|Post-transition metal|Ancient
83|Bi|Bismuth|208.98040|207|Solid|Post-transition metal|1753
84|Po|Polonium|208.98243|197|Solid|Metalloid|1898
85|At|Astatine|209.98715|202|Solid|Halogen|1940
86|Rn|Radon|222.01758|220|Gas|Noble gas|1900
87|Fr|Francium|223.01973|348|Solid|Alkali metal|1939
88|Ra|Radium|226.02541|283|Solid|Alkaline earth metal|1898
89|Ac|Actinium|227.02775|260|Solid|Actinide|1899
90|Th|Thorium|232.038|237|Solid|Actinide|1828
91|Pa|Protactinium|231.03588|243|Solid|Actinide|1913
92|U|Uranium|238.0289|240|Solid|Actinide|1789
93|Np|Neptunium|237.048172|221|Solid|Actinide|1940
94|Pu|Plutonium|244.06420|243|Solid|Actinide|1940
95|Am|Americium|243.061380|244|Solid|Actinide|1944
96|Cm|Curium|247.07035|245|Solid|Actinide|1944
97|Bk|Berkelium|247.07031|244|Solid|Actinide|1949
98|Cf|Californium|251.07959|245|Solid|Actinide|1950
99|Es|Einsteinium|252.0830|245|Solid|Actinide|1952
100|Fm|Fermium|257.09511||Solid|Actinide|1952
101|Md|Mendelevium|258.09843||Solid|Actinide|1955
102|No|Nobelium|259.10100||Solid|Actinide|1957
103|Lr|Lawrencium|266.120||Solid|Actinide|1961
104|Rf|Rutherfordium|267.122||Solid|Transition metal|1964
105|Db|Dubnium|268.126||Solid|Transition metal|1967
106|Sg|Seaborgium|269.128||Solid|Transition metal|1974
107|Bh|Bohrium|270.133||Solid|Transition metal|1976
108|Hs|Hassium|269.1336||Solid|Transition metal|1984
109|Mt|Meitnerium|277.154||Solid|Transition metal|1982
110|Ds|Darmstadtium|282.166||Expected to be a Solid|Transition metal|1994
111|Rg|Roentgenium|282.169||Expected to be a Solid|Transition metal|1994
112|Cn|Copernicium|286.179||Expected to be a Solid|Transition metal|1996
113|Nh|Nihonium|286.182||Expected to be a Solid|Post-transition metal|2004
114|Fl|Flerovium|290.192||Expected to be a Solid|Post-transition metal|1998
115|Mc|Moscovium|290.196||Expected to be a Solid|Post-transition metal|2003
116|Lv|Livermorium|293.205||Expected to be a Solid|Post-transition metal|2000
117|Ts|Tennessine|294.211||Expected to be a Solid|Halogen|2010
118|Og|Oganesson|295.216||Expected to be a Gas|Noble gas|2006
"""
AMU_KG = 1.66053906660e-27
DATA_YEAR = 2026          # turns discovery years into years ago

# Where each element's atoms come from: the main sources first, after Johnson (2019), "Populating the periodic
# table: Nucleosynthesis of the elements", Science 363, 474 - simplified to the leading one to three sources.
# Each source has the moment its first atoms appeared (first of their kind).
NUCLEOSYNTHESIS = {
    "big_bang": ("The Big Bang", None,
                 "Nuclei formed in the first few minutes; atoms once the universe cooled enough to hold electrons."),
    "cosmic_rays": ("Cosmic rays splitting heavier nuclei", (("after_yr", 3e8), "low"),
                    "Made when cosmic rays from supernova remnants shatter carbon, nitrogen and oxygen."),
    "massive_stars": ("Exploding massive stars", (("after_yr", 2e8), "medium"),
                      "Forged in massive stars and spread by their supernovae, the first ~200 million years after the Big Bang."),
    "low_mass_stars": ("Dying low-mass stars", (("after_yr", 4e8), "low"),
                       "Made by slow neutron capture (the s-process) in red giants and shed as they die."),
    "white_dwarfs": ("Exploding white dwarfs", (("after_yr", 1e9), "low"),
                     "Made in thermonuclear (type Ia) supernovae, which need a white dwarf and a partner."),
    "neutron_star_mergers": ("Merging neutron stars", (("after_yr", 3e8), "low"),
                             "Made by rapid neutron capture (the r-process) in neutron-star mergers and perhaps rare supernovae."),
    "decay": ("Decay of uranium and thorium", (("after_yr", 3e8), "low"),
              "Every isotope is short-lived; it exists in nature only as it is continually made by uranium and thorium decaying."),
    "laboratory": ("Made in laboratories", None, "Not found in nature; made one atom at a time in accelerators or reactors."),
}
BIG_BANG_ATOMS = {   # neutral atoms: helium first, then hydrogen and lithium at recombination
    "He": ("after_yr", 1e5), "H": ("after_yr", 3.8e5), "Li": ("after_yr", 3.8e5),
}
_SOURCES = {"BB": "big_bang", "CR": "cosmic_rays", "MS": "massive_stars", "LM": "low_mass_stars", "WD": "white_dwarfs",
            "NS": "neutron_star_mergers", "DC": "decay", "LAB": "laboratory"}
ELEMENT_ORIGINS = """
H BB; He BB; Li BB CR LM; Be CR; B CR; C LM MS; N LM MS; O MS; F MS LM; Ne MS; Na MS; Mg MS; Al MS; Si MS WD; P MS;
S MS WD; Cl MS; Ar MS WD; K MS; Ca MS WD; Sc MS; Ti MS WD; V WD MS; Cr WD MS; Mn WD MS; Fe WD MS; Co MS WD; Ni WD MS;
Cu MS; Zn MS; Ga MS LM; Ge MS LM; As MS NS; Se NS MS; Br NS MS; Kr MS LM; Rb LM NS; Sr LM; Y LM; Zr LM; Nb LM; Mo LM NS;
Tc LM; Ru NS LM; Rh NS; Pd NS LM; Ag NS; Cd LM NS; In LM NS; Sn LM; Sb NS LM; Te NS; I NS; Xe NS; Cs NS; Ba LM; La LM;
Ce LM; Pr LM NS; Nd LM NS; Pm DC; Sm NS LM; Eu NS; Gd NS; Tb NS; Dy NS; Ho NS; Er NS; Tm NS; Yb NS LM; Lu NS; Hf LM NS;
Ta NS LM; W LM NS; Re NS; Os NS; Ir NS; Pt NS; Au NS; Hg LM NS; Tl LM; Pb LM; Bi LM; Po DC; At DC; Rn DC; Fr DC; Ra DC;
Ac DC; Th NS; Pa DC; U NS; Np DC; Pu NS
"""
ELEMENT_NOTES = {
    "Tc": "No stable isotope (the longest-lived lasts ~4 million years). Red giants show it in their spectra, made "
          "there by the s-process; on Earth it was the first element made artificially (1937).",
    "Pm": "No stable isotope; traces come from uranium splitting spontaneously in ores.",
    "Np": "Traces form in uranium ores when uranium captures neutrons; first made in a lab in 1940.",
    "Pu": "Plutonium-244 (half-life 80 million years) is an r-process product, and traces of it survive in nature; "
          "first made in a lab in 1940.",
    "Bi": "Its only natural isotope is radioactive, but with a half-life a billion times the age of the universe.",
}
# the main-chart objects that already are these elements' atoms (shown there instead of a second dot)
ELEMENT_SAME_AS = {"O": ("objects", "oxygen_atom"), "He": ("objects", "helium_atom")}


def table_position(z):
    """Period, group (None in the f-block) and grid cell (row, column) in the usual 18-column layout, with the
    lanthanides and actinides as two rows (9 and 10) below the main table."""
    starts = [1, 3, 11, 19, 37, 55, 87, 119]
    period = next(i for i in range(7) if starts[i] <= z < starts[i + 1]) + 1
    i = z - starts[period - 1]
    if period == 1:
        group = 1 if z == 1 else 18
    elif period <= 3:
        group = i + 1 if i < 2 else i + 11
    elif period <= 5:
        group = i + 1
    elif i < 2:
        group = i + 1
    elif i < 17:
        return {"period": period, "group": None, "row": period + 3, "column": i + 1}
    else:
        group = i - 13
    return {"period": period, "group": group, "row": period, "column": group}


def periodic_table():
    origins = {}
    for part in ELEMENT_ORIGINS.replace("\n", " ").split(";"):
        sym, *codes = part.split()
        origins[sym] = [_SOURCES[c] for c in codes]
    rows = [line.split("|") for line in PUBCHEM_ELEMENTS.strip().splitlines()]
    radius = {int(r[0]): float(r[4]) for r in rows if r[4]}
    elements = []
    for z_s, sym, name, mass_u, vdw, state, kind, discovered in rows:
        z, mass_u = int(z_s), float(mass_u)
        # no measured radius above einsteinium: borrow the element directly above (32 places back) as an estimate
        estimated = not vdw
        r_pm = radius[z - 32] if estimated else float(vdw)
        mass_kg, width_m = mass_u * AMU_KG, 2 * r_pm * 1e-12
        sources = origins.get(sym, ["laboratory"])
        year = None if discovered == "Ancient" else int(discovered)
        # first atoms: the earliest of the element's sources
        if sources == ["laboratory"]:
            when = (("ago_yr", DATA_YEAR - year), "this_object", "high", f"First made in a laboratory in {year}.")
        else:
            options = [((BIG_BANG_ATOMS[sym], "medium") if s == "big_bang" else NUCLEOSYNTHESIS[s][1], s) for s in sources]
            ((spec, conf), first) = min(options, key=lambda o: o[0][0][1])
            when = (spec, "first_of_its_kind", conf, NUCLEOSYNTHESIS[first][2])
        same = ELEMENT_SAME_AS.get(sym)
        elements.append({
            "id": name.lower(), "atomic_number": z, "symbol": sym, "name": name, "kind": kind,
            "standard_state": state.replace("Expected to be a ", "").lower(), "state_is_predicted": state.startswith("Expected"),
            "radioactive": z == 43 or z == 61 or z >= 84,
            "discovered": year if year else "ancient",
            "table": table_position(z),
            "reference": {
                "atomic_mass_u": mass_u, "mass_kg": float(f"{mass_kg:.6g}"), "log10_mass_kg": lg(mass_kg),
                "van_der_waals_radius_pm": r_pm, "width_m": float(f"{width_m:.6g}"), "log10_width_m": lg(width_m),
                "width_basis": "van_der_waals_diameter", "width_is_estimate": estimated,
                "confidence": "low" if estimated else "high",
                "notes": f"No measured radius; uses {rows[z - 33][2]}'s ({rows[z - 33][1]}), the element above it." if estimated else "",
            },
            "origin": sources,
            "origin_note": ELEMENT_NOTES.get(sym, ""),
            "same_as": {"dataset": same[0], "id": same[1]} if same else None,
            "first_appeared": appearance(when),
        })
    return {
        "source": {
            "elements": "PubChem periodic table, https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON (read 2026-10-24)",
            "origins": "Johnson, J. A. (2019). Populating the periodic table: Nucleosynthesis of the elements. "
                       "Science 363(6426), 474-478. Simplified to each element's leading sources.",
        },
        "conventions": {
            "width": "Van der Waals diameter (2x the radius): how close two atoms sit before their electron clouds "
                     "push back. The same convention as the oxygen and helium atoms on the main chart.",
            "mass": "Standard atomic weight, or the mass of the longest-lived isotope when there is no stable one.",
            "first_appeared": "When the element's first neutral atoms existed: the earliest of its sources. Times "
                              "for stellar sources are rough (the first stars formed ~100-200 million years in).",
            "same_as": "The main-chart object that already is this element's atom; show that instead of a second dot.",
        },
        "sources": [{"id": k, "label": v[0], "description": v[2]} for k, v in NUCLEOSYNTHESIS.items()],
        "elements": elements,
    }


# Where an LP point must sit by physics, rather than where it was read off the image.
LP_PARTICLE_EV = {"top_quark": 172.57e9, "higgs_boson": 125.2e9, "w_boson": 80.369e9, "neutron": 939.565e6,
                  "proton": 938.272e6, "electron": 0.51099895e6}


def lp_plotted(oid, read):
    """Position for the shared mass-width chart. Lineweaver & Patel plot radius and use r = hbar/mc for the
    Compton limit; here everything uses the main chart's conventions (full width, W = hbar/Mc)."""
    m_read = read["log10_mass_kg"]
    if oid == "hubble_radius":
        return "hubble_sphere_today", LOG_HUBBLE_W, LOG_HUBBLE_W + LOG_SCHW
    if oid == "quantum_gravity_point":
        return "planck_point", (LOG_COMPTON - LOG_SCHW) / 2, (LOG_COMPTON + LOG_SCHW) / 2
    if oid == "three_kelvin_bh":
        m = math.log10(HBAR * C**3 / (8 * math.pi * G * K_B * T_CMB))   # Hawking temperature = CMB temperature
        return "black_hole_hawking_T_cmb", m - LOG_SCHW, m
    if oid == "smallest_observable_pbh":
        return "black_hole_line_read_mass", m_read - LOG_SCHW, m_read
    if oid in LP_PARTICLE_EV:
        m = math.log10(LP_PARTICLE_EV[oid] * EV_KG)
        return "compton_line_reference_mass", LOG_COMPTON - m, m
    if oid == "neutrino":
        return "compton_line_read_mass", LOG_COMPTON - m_read, m_read
    if oid == "visible_photons":
        w = math.log10(5.5e-7)
        return "photon_line_550nm", w, LOG_PHOTON - w
    return "read_from_chart", read["log10_width_m"], m_read


def lineweaver_patel():
    objs = []
    for oid, label, name, kind, px, lpx, main_id in LP_OBJECTS:
        read = lp_values(px)
        basis, w, m = lp_plotted(oid, read)
        objs.append({"id": oid, "name": name, "printed_label": label, "marker": kind,
                     "image": {"icon": point(px, LP_IMG), "label": point(lpx, LP_IMG) if lpx else None},
                     "chart": read,
                     "plotted": {"log10_width_m": round(w, 6), "log10_mass_kg": round(m, 6), "basis": basis},
                     "main_chart_object_id": main_id,
                     "same_as": lp_same_as(oid, main_id),
                     "first_appeared": first_appeared(oid if oid in FIRST_APPEARED else main_id, 10**m)})
    tlines = []
    for tid, label, t, top, lpx in LP_TIME_LINES:
        v = lp_values(top)
        k = v["log10_mass_g"] - 3 * v["log10_radius_cm"]
        tlines.append({"id": tid, "printed_label": label, "seconds": t, "log10_seconds": r3(math.log10(t)),
                       "style": "black dashed" if tid == "now" else "white dashed",
                       "top_of_frame": point(top, LP_IMG), "label": point(lpx, LP_IMG),
                       "chart_equation": f"log10 M[g] = 3 log10 r[cm] + {k:.2f}",
                       "chart_log10_density_g_cm3": r3(k - math.log10(4 * math.pi / 3))})
    return {
        "source": {**LP_IMG, "title": "All objects",
                   "authors": "Charles H. Lineweaver; Vihan M. Patel",
                   "citation": "Lineweaver, C. H. & Patel, V. M. (2023). All objects and some questions. "
                               "American Journal of Physics 91(10), 819.",
                   "url": "https://pubs.aip.org/aapt/ajp/article/91/10/819/2911822/All-objects-and-some-questions"},
        "axes": {
            "x": LR_AX.describe(), "y": LM_AX.describe(),
            "secondary": [
                {"quantity": "log10 radius", "unit": "Mpc", "position": "top", "offset_from_cm": -24.489},
                {"quantity": "log10 mass", "unit": "solar masses", "position": "outer left", "offset_from_g": -33.299},
                {"quantity": "log10 mass", "unit": "GeV", "position": "right", "offset_from_g": 23.749},
            ],
        },
        "objects": objs,
        "lines": [
            {"id": "black_hole_line", "printed_label": "black holes",
             "equation": "log10 M[g] = log10 r[cm] + 27.83  (r = 2GM/c^2)",
             "endpoints": [point((540, 1497), LP_IMG), point((1468, 543), LP_IMG)]},
            {"id": "compton_limit", "printed_label": "Compton limit",
             "equation": "log10 M[g] = -log10 r[cm] - 37.45  (r = hbar/Mc)",
             "endpoints": [point((540, 1497), LP_IMG), point((1005, 1975), LP_IMG)]},
            {"id": "planck_mass", "printed_label": "m_P", "equation": "log10 M[g] = -4.66",
             "style": "black dashed horizontal", "y_px": 1497},
            {"id": "planck_length", "printed_label": "l_P", "equation": "log10 r[cm] = -32.79",
             "style": "white vertical", "x_px": 540},
        ],
        "time_lines": tlines,
        "time_lines_note": "Each dashed line is a constant-density line (the universe's mean density at that time); "
                           "'now' passes through the Hubble-radius dot.",
        "regions": [
            {"id": "forbidden_by_gravity", "printed_label": "forbidden by gravity", "colour": "#83a7c5",
             "text": point((800, 700), LP_IMG), "rule": "above the black-hole line"},
            {"id": "forbidden_by_quantum_uncertainty", "printed_label": "forbidden by quantum uncertainty",
             "colour": "#83a7c5", "text": point((800, 2000), LP_IMG), "rule": "below the Compton limit"},
            {"id": "sub_planckian_unknown", "printed_label": "sub-Planckian unknown", "colour": "#83a7c5",
             "text": point((490, 800), LP_IMG), "rule": "radius below the Planck length"},
            {"id": "quantum_gravity", "printed_label": "QG", "colour": "#000000",
             "text": point((480, 1497), LP_IMG), "rule": "black wedge left of the Planck point"},
            {"id": "qgp_band", "printed_label": "QGP", "text": point((950, 1380), LP_IMG),
             "rule": "lighter stripe between the EW and nuclear time lines"},
            {"id": "bbn_band", "printed_label": "BBN", "text": point((1030, 1410), LP_IMG),
             "rule": "lighter stripe near the 'atomic' time line"},
        ],
        "domination_legend": [
            {"symbol": "Ω_Λi", "meaning": "false vacuum energy of inflation", "colour": "#a5a5a5"},
            {"symbol": "Ω_r", "meaning": "radiation", "colour": "#d1dcca"},
            {"symbol": "Ω_m", "meaning": "matter", "colour": "#fbbc6c"},
            {"symbol": "Ω_Λ", "meaning": "dark energy", "colour": "#f2f3f7"},
        ],
        "domination_note": "The allowed triangle is shaded by which component dominated the universe when it had "
                           "that density: inflation (grey sliver by the Planck point), radiation (sage), matter "
                           "(orange band ending at 'now'), dark energy (pale, the future).",
        "energy_markers": [
            {"label": "E_P", "meaning": "Planck energy", "y_px": 1500, "chart_log10_GeV": r3(LM_AX.value(1500) + 23.749), "true_log10_GeV": 19.09},
            {"label": "E_GUT", "meaning": "grand unification energy", "y_px": 1562, "chart_log10_GeV": r3(LM_AX.value(1562) + 23.749), "true_log10_GeV": 16.0},
            {"label": "E_EW", "meaning": "electroweak energy", "y_px": 1757, "chart_log10_GeV": r3(LM_AX.value(1757) + 23.749), "true_log10_GeV": 2.4},
            {"label": "CMB", "meaning": "cosmic microwave background photon energy", "y_px": 1995, "chart_log10_GeV": r3(LM_AX.value(1995) + 23.749), "true_log10_GeV": -12.2},
        ],
        "abbreviations": {"GUT": "grand unified theories", "QGP": "quark-gluon plasma", "EW": "electro weak energy",
                          "BBN": "big bang nucleosynthesis", "NS": "neutron stars", "WD": "white dwarfs",
                          "BD": "brown dwarfs", "BH": "black holes", "CMB": "cosmic microwave background",
                          "SMBH": "supermassive black holes", "PBH": "primordial black holes"},
        "brackets": [
            {"printed_label": "stellar mass BH", "along": "black_hole_line",
             "ends": [point((1128, 896), LP_IMG), point((1175, 820), LP_IMG)]},
            {"printed_label": "SMBH", "along": "black_hole_line",
             "ends": [point((1288, 732), LP_IMG), point((1392, 623), LP_IMG)]},
        ],
    }


# =============================================================================
# ERRATA - places where the poster disagrees with itself or with physics
# =============================================================================
ERRATA = [
    {"id": "mass_axis_labels", "where": "Main chart, right MASS axis above 0",
     "issue": "Printed tick labels read 3, 9, 12, 15, 15, 12, 15, 18 ... 42 going up; the ticks are really 3, 6, 9, 12, 15, 18, 21 ... 48.",
     "evidence": "The solar-mass, tonne and kilotonne reference lines line up with the corrected values to within 0.02 decades.",
     "handling": "Calibration uses the corrected values; mass_axis.ticks lists printed vs true."},
    {"id": "particle_legend_swap", "where": "Fundamental particles inset legend",
     "issue": "Green is labelled LEPTON and blue HADRONS, but green dots are proton/neutron/meson (hadrons) and blue dots are electron/muon/tau/neutrinos (leptons).",
     "handling": "Each particle carries its real 'class' plus the chart colour."},
    {"id": "density_ruler_labels", "where": "Main chart, density ruler",
     "issue": "With a uniform 9 decades per tall tick, the first four labels (92, 83, 74, 65) are one too low and '-120'/'-147' sit where -114/-141 fall.",
     "handling": "density_ruler.tall_ticks gives both printed and uniform-scale values."},
    {"id": "stellar_inset_diameters", "where": "Stellar evolution inset, diameter axis",
     "issue": "Objects sit ~1 decade to the right of their real diameters (Sun at 10^7.3 km vs 1.4x10^6 km). Masses are accurate.",
     "handling": "chart.* keeps the drawn position; reference.* has the real values."},
    {"id": "width_label_10pm", "where": "Main chart, width axis",
     "issue": "'10 pm' sits on the 10^-12 m tick (1 pm).", "handling": "Recorded as printed; true value given."},
    {"id": "inch_and_light_second", "where": "Main chart, width axis dotted lines",
     "issue": "'1 inch' and '1light-second' are drawn ~0.8 decade too far right; the other distance lines are within ~0.25 decade.",
     "handling": "offset_decades on each width reference line."},
    {"id": "water_temperatures", "where": "Main chart, energy axis",
     "issue": "100 °C, 0 °C and the Bose-Einstein condensate bracket are spread out for legibility rather than at kT.",
     "handling": "chart vs true values on each energy annotation."},
    {"id": "energy_axis_offset", "where": "Main chart, energy axis",
     "issue": "The energy axis is aligned to the mass axis with a 35.4-decade shift; E = mc^2 gives 35.75, so eV/c^2 reference lines sit ~0.3 decade high on the mass axis.",
     "handling": "Mass reference lines record offset_decades."},
    {"id": "era_brackets", "where": "Main chart, time axis",
     "issue": "The BIG BANG NUCLEOSYNTHESIS bracket covers 10^-11-10^3 s and RECOMBINATION ERA covers 10^3-10^21 s; the physical events are much narrower.",
     "handling": "Each era carries reference_log10_seconds."},
    {"id": "spelling", "where": "Main chart labels",
     "issue": "'LANIKEA' should be 'Laniakea'; 'SAG A' is Sagittarius A*; 'MONOCEROTIS' presumably V616 Monocerotis.",
     "handling": "printed_label keeps the original text; name has the corrected one."},
    {"id": "neutrino_masses", "where": "Fundamental particles inset",
     "issue": "Neutrinos are plotted at old direct upper limits (up to MeV); current limits are below ~1 eV.",
     "handling": "reference.notes on each neutrino."},
    {"id": "time_marker_spacing", "where": "Main chart, time axis",
     "issue": "Time markers are only roughly on the density scale (e.g. 1 microsecond is far from the 10^20 g/L its density implies).",
     "handling": "Each marker carries both the ruler density and a Friedmann estimate."},
    {"id": "pbh_inside_horizon", "where": "Main chart, primordial black hole icon",
     "issue": "The icon is drawn ~0.5 decade above the Schwarzschild line, i.e. denser than a black hole can be.",
     "handling": "reference places it exactly on the line (width = Schwarzschild diameter)."},
    {"id": "dark_matter_boxes", "where": "Main chart, 'DARK MATTER* (areas not yet excluded)'",
     "issue": "The boxes approximate the macro-dark-matter windows of Jacobs, Starkman & Lynn (2015): 55 g-1e17 g and "
              "2e20-4e24 g for nuclear-density objects. The lower box starts at 1 g, and the boxes' left edges follow "
              "the poster's own black-hole line, which sits ~0.2-0.3 decade off the true one.",
     "handling": "main_chart.json physics.macro_dark_matter holds the published windows; the site plots them on the "
                 "nuclear-density line."},
]


# Where each erratum can be seen on the main poster (px), for an "errors" layer.
ERRATA_ANCHORS = {
    "pbh_inside_horizon": (3116, 3367), "dark_matter_boxes": (3110, 3727),
    "mass_axis_labels": (5200, 3100), "particle_legend_swap": (1960, 3300), "density_ruler_labels": (3400, 1300),
    "stellar_inset_diameters": (1230, 600), "width_label_10pm": (3125, 6535), "inch_and_light_second": (3684, 6820),
    "water_temperatures": (1650, 5710), "energy_axis_offset": (5470, 5370), "era_brackets": (4625, 640),
    "spelling": (4590, 1815), "neutrino_masses": (1834, 3912), "time_marker_spacing": (4583, 900),
}


# =============================================================================
# writers
# =============================================================================
def write_json(name, obj):
    path = OUT / name
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_csv(name, header, rows):
    path = OUT / "csv" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def physics():
    """Every constant and line offset the site needs, so nothing is rounded twice."""
    planck_density = C**5 / (HBAR * G**2)
    dens = [
        ("planck", "Planck density", planck_density, "c^5 / (hbar G^2)"),
        ("nuclear", "Nuclear density", NUCLEAR_DENSITY, "Jacobs, Starkman & Lynn (2015) characteristic value"),
        ("water", "Water", 1000.0, ""),
        ("air", "Air", 1.225, "sea level, 15 C"),
        ("cosmic_today", "Cosmic average today", RHO_CRIT, "critical density 3H0^2/(8 pi G)"),
    ]
    return {
        "conventions": "W = full width (diameter) in metres, M = mass in kg, both log10. Density lines treat an "
                       "object as a sphere of diameter W: M = rho (pi/6) W^3.",
        "constants_si": {"G": G, "c": C, "hbar": HBAR, "h": H_PLANCK, "k_B": K_B, "M_sun": M_SUN,
                         "eV_per_c2_kg": EV_KG, "T_cmb_K": T_CMB},
        "cosmology": {"model": "flat LambdaCDM, Planck 2018", "H0_km_s_Mpc": H0_KM_S_MPC, "H0_per_s": H0,
                      "Omega_m": OMEGA_M, "Omega_r": OMEGA_R, "Omega_Lambda": round(OMEGA_L, 6),
                      "critical_density_kg_m3": RHO_CRIT, "age_s": lcdm_age()},
        "lines": {
            "schwarzschild_offset": round(LOG_SCHW, 6),
            "compton_offset": round(LOG_COMPTON, 6),
            "photon_offset": round(LOG_PHOTON, 6),
            "sphere_volume_log10": round(LOG_SPHERE, 6),
            "hubble_diameter_log10_m": round(LOG_HUBBLE_W, 6),
            "particle_horizon_diameter_log10_m": round(LOG_PARTICLE_HORIZON_W, 6),
            "energy_log10_eV_per_kg": round(-math.log10(EV_KG), 6),
        },
        "horizons": [
            {"id": "hubble_radius", "name": "Hubble radius", "style": "solid",
             "log10_diameter_m": round(LOG_HUBBLE_W, 6), "radius_gly": round(C / H0 / GLY_M, 2),
             "definition": "c / H0: the distance at which cosmic expansion carries galaxies away from us at exactly the "
                           "speed of light today.",
             "description": "A sphere this size, filled at the universe's average density, is exactly its own "
                            "Schwarzschild size - which is why it sits at the triangle's top corner. It grows over "
                            "time and will level off at about 1.2x today's size as dark energy takes over."},
            {"id": "particle_horizon", "name": "Edge of the observable universe (particle horizon)", "style": "dashed",
             "log10_diameter_m": round(LOG_PARTICLE_HORIZON_W, 6),
             "radius_gly": round(PARTICLE_HORIZON_D / 2 / GLY_M, 2),
             "definition": "The farthest distance from which light emitted since the Big Bang has had time to reach "
                           "us, measured as where that source is today (comoving distance).",
             "description": "It is about 3x the Hubble radius. Light that set out from just beyond the Hubble sphere "
                            "still reached us, because the Hubble sphere grew and overtook it, and space kept "
                            "stretching while the light travelled. So galaxies between the two lines are visible "
                            "even though they recede faster than light today. Nothing beyond this line has ever "
                            "been able to send us a signal."},
        ],
        "densities": [{"id": i, "name": n, "kg_m3": v, "log10_kg_m3": round(math.log10(v), 6), "source": src}
                      for i, n, v, src in dens],
        "macro_dark_matter": {
            "density_kg_m3": NUCLEAR_DENSITY,
            "windows_kg": [[0.055, 1e14], [2e17, 4e21]],
            "hypothetical": True,
            "source": "Jacobs, Starkman & Lynn (2015), 'Macro Dark Matter', MNRAS 450, 3418 (arXiv:1410.2236): "
                      "unconstrained for nuclear-dense objects of 55 g-1e17 g and 2e20 g-4e24 g "
                      "(the lower window closes if macros destabilise ordinary matter).",
        },
    }


def main():
    OUT.mkdir(exist_ok=True)
    objects = build_main_objects()
    stellar = stellar_inset()
    particles = particles_inset()
    lp = lineweaver_patel()
    elements = periodic_table()

    main_chart = {
        "source": {**MAIN_IMG, "title": "The Triangle of Everything",
                   "note": "Illustrated poster built on the Lineweaver & Patel 'All objects' mass-size diagram."},
        "physics": physics(),
        "coordinate_systems": {
            "px": "Full-resolution source pixels, origin top-left.",
            "norm": "px divided by image width/height (0-1) - use for responsive overlays.",
            "chart": "Values implied by where something is drawn (from the axis calibrations).",
            "reference": "Standard real-world values compiled for this dataset (not read from the image).",
            "log10_density_proxy_kg_m3": "log10(mass) - 3*log10(width), the quantity the diagonal density grid tracks.",
            "position_is_schematic": "True for icons arranged beside the main sequence for legibility; their x position is not a width.",
        },
        "axes": {
            "width": W_AX.describe(),
            "mass": {**M_AX.describe(), "ticks": mass_ticks()},
            "energy": {**E_AX.describe(), "ticks": energy_ticks()},
            "density": "See cosmic_timeline.json -> density_ruler (density lines are diagonals of slope 3).",
        },
        "triangle": {k: point(v, MAIN_IMG) for k, v in TRIANGLE.items()},
        "boundaries": boundaries(),
        "regions": regions(),
        "zoom_boxes": zoom_boxes(),
        "reference_lines": {
            "mass": mass_reference_lines(),
            "width": width_reference_lines(),
            "energy": energy_annotations(),
        },
        "texts": [{"text": t, "role": role, **point(p, MAIN_IMG)} for t, role, p in TEXTS],
        "categories": CATEGORIES,
    }

    write_json("main_chart.json", main_chart)
    write_json("objects.json", {"count": len(objects), "objects": objects})
    write_json("stellar_evolution.json", stellar)
    write_json("fundamental_particles.json", particles)
    write_json("cosmic_timeline.json", timeline())
    write_json("lineweaver_patel.json", lp)
    write_json("elements.json", elements)
    write_json("errata.json", {"errata": [{**e, "anchor": point(ERRATA_ANCHORS[e["id"]], MAIN_IMG)}
                                          for e in ERRATA]})

    # --- flat CSV exports ---------------------------------------------------
    def ref(o, k):
        return o["reference"][k] if o["reference"] else None

    write_csv("objects.csv",
              ["id", "name", "printed_label", "category", "subcategory", "hypothetical", "labeled_on_chart",
               "identification", "icon_x_px", "icon_y_px", "icon_x_norm", "icon_y_norm",
               "chart_log10_mass_kg", "chart_log10_width_m", "chart_log10_energy_eV",
               "ref_mass_kg", "ref_width_m", "ref_width_basis", "ref_log10_mass_kg", "ref_log10_width_m",
               "ref_confidence", "description"],
              [[o["id"], o["name"], o["printed_label"], o["category"], o["subcategory"], o["hypothetical"],
                o["labeled_on_chart"], o["identification"], *o["image"]["icon"]["px"], *o["image"]["icon"]["norm"],
                o["chart"]["log10_mass_kg"], o["chart"]["log10_width_m"], o["chart"]["log10_energy_eV"],
                ref(o, "mass_kg"), ref(o, "width_m"), ref(o, "width_basis"), ref(o, "log10_mass_kg"),
                ref(o, "log10_width_m"), ref(o, "confidence"), o["description"]] for o in objects])
    write_csv("particles.csv",
              ["id", "name", "printed_label", "class", "chart_colour", "legend_says", "icon_x_px", "icon_y_px",
               "chart_log10_mass_eV", "chart_log10_wavelength_m", "ref_mass_eV", "ref_log10_mass_eV",
               "electric_charge", "spin", "generation", "notes"],
              [[p["id"], p["name"], p["printed_label"], p["class"], p["chart_colour"], p["legend_says"],
                *p["image"]["icon"]["px"], p["chart"]["log10_mass_eV"], p["chart"]["log10_wavelength_m"],
                p["reference"]["mass_eV"], p["reference"]["log10_mass_eV"], p["reference"]["electric_charge"],
                p["reference"]["spin"], p["reference"]["generation"], p["reference"]["notes"]]
               for p in particles["particles"]])
    write_csv("stellar_evolution.csv",
              ["id", "name", "printed_label", "category", "icon_x_px", "icon_y_px", "chart_log10_mass_msun",
               "chart_log10_diameter_km", "ref_mass_msun", "ref_diameter_km", "ref_confidence", "main_chart_object_id"],
              [[s["id"], s["name"], s["printed_label"], s["category"], *s["image"]["icon"]["px"],
                s["chart"]["log10_mass_msun"], s["chart"]["log10_diameter_km"], s["reference"]["mass_msun"],
                s["reference"]["diameter_km"], s["reference"]["confidence"], s["main_chart_object_id"]]
               for s in stellar["objects"]])
    write_csv("lineweaver_patel_objects.csv",
              ["id", "name", "printed_label", "marker", "icon_x_px", "icon_y_px", "log10_radius_cm", "log10_mass_g",
               "log10_mass_msun", "log10_width_m", "log10_mass_kg", "main_chart_object_id", "same_as"],
              [[o["id"], o["name"], o["printed_label"], o["marker"], *o["image"]["icon"]["px"],
                o["chart"]["log10_radius_cm"], o["chart"]["log10_mass_g"], o["chart"]["log10_mass_msun"],
                o["chart"]["log10_width_m"], o["chart"]["log10_mass_kg"], o["main_chart_object_id"],
                f'{o["same_as"]["dataset"]}:{o["same_as"]["id"]}' if o["same_as"] else None]
               for o in lp["objects"]])
    write_csv("elements.csv",
              ["atomic_number", "symbol", "name", "kind", "standard_state", "radioactive", "discovered",
               "period", "group", "atomic_mass_u", "mass_kg", "van_der_waals_radius_pm", "width_m", "width_is_estimate",
               "origin", "first_appeared"],
              [[e["atomic_number"], e["symbol"], e["name"], e["kind"], e["standard_state"], e["radioactive"],
                e["discovered"], e["table"]["period"], e["table"]["group"], e["reference"]["atomic_mass_u"],
                e["reference"]["mass_kg"], e["reference"]["van_der_waals_radius_pm"], e["reference"]["width_m"],
                e["reference"]["width_is_estimate"], " ".join(e["origin"]), e["first_appeared"]["label"]]
               for e in elements["elements"]])
    scale_rows = []
    for r in main_chart["reference_lines"]["mass"]:
        scale_rows.append(["mass", r["label"], r["kind"], "", r["y_px"], r["true_log10_kg"], r["chart_log10_kg"], "kg"])
    for r in main_chart["reference_lines"]["width"]:
        scale_rows.append(["width", r["label"], r["kind"], r["x_px"], "", r["true_log10_m"], r["chart_log10_m"], "m"])
    for r in main_chart["reference_lines"]["energy"]:
        scale_rows.append(["energy", r["label"], r["kind"], "", json.dumps(r["y_px"]), json.dumps(r["true_log10_eV"]),
                           json.dumps(r["chart_log10_eV"]), "eV"])
    write_csv("scale_references.csv",
              ["axis", "label", "kind", "x_px", "y_px", "true_log10", "chart_log10", "unit"], scale_rows)

    print(f"objects: {len(objects)}  stellar: {len(stellar['objects'])}  particles: {len(particles['particles'])}  "
          f"lp objects: {len(lp['objects'])}")
    for ax in (W_AX, M_AX, E_AX, D_AX, SD_AX, SM_AX, PL_AX, PM_AX, LR_AX, LM_AX):
        print(f"  {ax.name:18s} [{ax.unit:14s}] px/decade {ax.b:9.3f}  max residual {ax.residual():.3f}")


if __name__ == "__main__":
    main()
