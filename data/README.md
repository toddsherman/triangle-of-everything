# Triangle of Everything: datasets

Structured data transcribed from two images, ready to drive an interactive website. The images themselves are other people's work, so they aren't in this repository; put them in the project root under the names below to regenerate the QA overlays.

| Source image | What it is |
|---|---|
| `Triangle_of_Everything.png` (7300 × 7639) | The illustrated poster, called the **main chart** here. It's a log-log plot of width vs. mass bounded by the Schwarzschild radius, the Compton limit and the Hubble radius, with a stellar-evolution inset, a fundamental-particles inset, a cosmic timeline and density ruler along the top, and an energy/temperature axis on the left. |
| `b6y2fthj95ie1.png` (2121 × 3000) | Lineweaver & Patel, *All objects and some questions*, Am. J. Phys. 91, 819 (2023), the scientific plot the poster is based on. |

Regenerate everything with `python3 scripts/build_data.py`, which uses only the standard library. All readings live in that script. To correct a position or value, edit it there and rebuild. Then run `python3 scripts/check_physics.py`. It confirms that every black hole sits exactly on the Schwarzschild line and every particle exactly on the Compton line, that nothing is denser than a black hole, and that each time marker's Hubble sphere lands on the black-hole line. `python3 scripts/render_overlay.py` (needs Pillow) draws every hotspot back onto the images in `data/qa/` so you can check placement by eye.

## Files

| File | Contents |
|---|---|
| `objects.json` | The 53 things plotted in the main triangle, from the observable universe down to fundamental particles, including unlabeled icons such as Saturn, the hippo and the soccer ball. |
| `main_chart.json` | Axis calibrations, the triangle's vertices and boundary lines, regions (black-hole classes, dark-matter boxes, QGP, biology/chemistry/astrophysics, photon bands), zoom boxes linking to the insets, reference lines on every axis (1 kg, 1 lb, 1 AU, 1 parsec, 1 eV, 0 °C …), every printed title, and the category list. |
| `stellar_evolution.json` | The inset with 17 objects, evolution arrows (Sun → red giant, W.R. stars → black hole …), the TOV and Chandrasekhar limits, and the water-density and degenerate-matter lines. |
| `fundamental_particles.json` | The inset with 19 particles: class, colour, charge, spin, generation, PDG masses, the chart legend (with its error), decay and "combines into" relations, and the WIMP dark-matter region. |
| `cosmic_timeline.json` | Time markers (Planck time → 1 googol seconds), eras, the density ruler (printed vs. computed values) and the named density lines (Planck, plasma, water, false/true vacuum). `history` has the universe at 701 moments from the instant all three walls meet (half the Planck time, in this chart's conventions; see `history.start`) to today (flat ΛCDM): mean density, Hubble-sphere diameter, observable-universe diameter and radiation temperature. Early temperatures count the particle species present then (a smooth Standard Model g*(T)); `wien_b_m_K` turns a temperature into the peak wavelength of the background light. |
| `lineweaver_patel.json` | The second chart: 33 objects, axes and secondary axes, boundary equations, time lines, regions, the domination legend, energy markers, abbreviations and the citation. Objects link to main-chart ids. `same_as` names the one entry elsewhere in the datasets that already stands for a point (`{dataset, id}`, e.g. `objects`/`sun`, `fundamental_particles`/`electron`, `main_chart.physics.horizons`/`hubble_radius`), so a site can show that entry instead of a second, near-identical point. It's null for the four points nothing else covers: flea, neutrino, visible-light photons and the 3 K black hole. `chart` is what was read off their image. `plotted` is where each point belongs in this dataset's conventions: points that sit on a wall by definition (black holes, particles, the Planck point, the Hubble sphere) are placed on it exactly. |
| `elements.json` | All 118 elements, not taken from the images. Mass (standard atomic weight, or the longest-lived isotope) and van der Waals radius come from PubChem's periodic table. PubChem has no radius above einsteinium, so elements 100–118 borrow the radius of the element directly above them (`width_is_estimate`). Width is the van der Waals diameter, the same convention as the oxygen and helium atoms in `objects.json`, which `same_as` links so a site shows them once. `table` gives each element's period, group and grid cell. `origin` lists where its atoms are made, main source first, simplified from Johnson (2019); `sources` describes each one. `first_appeared` is when its first neutral atoms existed: the earliest source, or the year it was first made for laboratory elements. Times for stellar sources are rough. |
| `molecules.json` | 24 molecules, curated for this project rather than read from either chart, filling the gap between atoms and viruses: from helium hydride (the first molecule in the universe) and water to proteins, a ribosome and the DNA in one human cell. Mass comes from the chemical formula (PubChem atomic masses) or a published mass. `width_basis` says what the width is, because a molecule has no single size: a gas's measured kinetic diameter, a sphere of the molecule's volume (from density), the longest dimension of its structure, or a chain's length stretched end to end. `width_is_estimate` flags guesses. Most `first_appeared` dates are rough. |
| `errata.json` | 14 places where the poster contradicts itself or physics. Read this before trusting printed labels. |
| `csv/*.csv` | Flat exports of the object, particle, stellar, element, molecule, Lineweaver-Patel and scale-reference tables for spreadsheets and quick prototyping. |
| `qa/*.png` | Verification overlays. These aren't needed by the site. |

## Coordinates and values

Every positioned thing has the same building blocks:

- **`px`** – `[x, y]` in full-resolution source pixels, with the origin at top left.
- **`norm`** – `px` divided by image width and height (0–1). Use this for hotspots on a responsive image: `left: norm[0]*100%`, `top: norm[1]*100%`.
- **`chart`** – what the image *shows*: values computed from where the icon sits on the calibrated axes.
- **`reference`** – standard real-world values compiled for this dataset. These were **not** read from the image. Each one carries `confidence` (`high` / `medium` / `low`), `representative` (true when a typical member stands in for a class, e.g. "humans" = 70 kg, 1.7 m) and `width_basis` (`diameter`, `length`, `height`, `schwarzschild_diameter`, `reduced_compton_wavelength`, …).

Main-chart axis formulas (least-squares fits to detected tick marks; residuals ≤ 0.07 decade):

```
log10 width  [m]  = (x - 3722.1) / 46.20
log10 mass   [kg] = (4009.1 - y) / 46.18
log10 energy [eV] = (5645.4 - y) / 46.17      # same vertical axis, shifted ~35.4 decades (E = mc²)
```

The exact fitted coefficients are in `main_chart.json → axes.*`. Each inset and the Lineweaver-Patel chart has its own `axes` block in the same format: `value = (px - px_at_zero) / px_per_decade`.

### Two ways to build the site

The prototype in `../site` takes the second approach and uses no images.

1. **Annotated poster.** Show the original image and place hotspots at `image.icon.norm`, with label anchors at `image.label.norm`. Use `zoom_boxes` to animate into the insets.
2. **Re-plotted chart (D3, etc.).** Plot `reference.log10_width_m` against `reference.log10_mass_kg`, and draw the boundaries from `main_chart.json → physics.lines`. Don't retype rounded numbers, or points that belong on a line will drift off it when zoomed in:
   - Schwarzschild: `log M = log W + schwarzschild_offset` (26.527217). A black hole's width is computed from its mass with this same offset.
   - Compton: `log M = −log W + compton_offset` (−42.453744). A particle's width is computed the same way.
   - Photons: `log M = −log W + photon_offset` (W = wavelength).
   - Hubble radius: `log W = hubble_diameter_log10_m` (2c/H₀, from Planck 2018 ΛCDM).
   - Edge of the observable universe: `log W = particle_horizon_diameter_log10_m`. This is the particle horizon from the same model (radius 46.2 billion ly vs. 14.45 for the Hubble radius). The observable-universe object's width is defined as exactly this. `physics.horizons` has plain-language explanations of both.
   - Density lines: `log M = 3 log W + log ρ + sphere_volume_log10` (a sphere of diameter W).
   - Time lines: the same, with ρ = `cosmic_timeline.json → markers[].density_log10_kg_m3` (full ΛCDM). Each one meets the Schwarzschild line at that moment's Hubble sphere (`hubble_diameter_log10_m`).
   - Dark matter: `physics.macro_dark_matter` holds the published windows (Jacobs, Starkman & Lynn 2015) for nuclear-density objects. Plot them along that density line.

   Objects with `reference: null` are hypothetical, so place them at their `chart` values. When `chart.position_is_schematic` is true, the icon was set beside the main sequence for legibility, and its x position is not a width.

## Field notes

- `printed_label` is the text exactly as printed, including typos like `LANIKEA`. `name` is the corrected display name.
- `identification`:
  - `printed`: the object has a label on the chart.
  - `visual`: unlabeled, but clearly recognizable (e.g. Saturn's rings).
  - `probable`: unlabeled, with a likely identity.
  - `tentative`: unlabeled, and the identity is a best guess. These are Venus, Mercury, Mars, Pluto, Ceres, the neutron star, the white dwarfs, the red dwarfs and the brown dwarf.
- `hypothetical: true` matches the chart's asterisks ("*Asterisk means still hypothetical").
- `first_appeared` (objects, stellar, particles, elements, molecules, Lineweaver & Patel points) gives when the thing existed: `seconds_after_big_bang`, `years_ago` (for recent events) and a readable `label`.
  - `basis` says whether that's this specific object, the first of its kind, or a physics estimate (primordial black holes form at t ≈ GM/c³).
  - The black-hole class bands and the light spectrum in `main_chart.json → regions` carry `first_appeared` too.
  - `confidence` and `note` say how sure the date is. Many dates are first-of-kind estimates with wide uncertainty, so check the low-confidence ones before presenting them as fact.
- `log10_density_proxy_kg_m3` is `log M − 3 log W`, the quantity the diagonal grid lines track. It's mass per width cubed, not a true mean density.
- In the particle inset, the printed legend swaps LEPTON and HADRONS. Each particle has its correct `class` plus `chart_colour`/`legend_says`, so the site can show the original colours with correct labels.
- The mass-axis labels above zero are misprinted on the poster (3, 9, 12, 15, 15, 12, 15, 18 … should be 3, 6, 9, 12, 15, 18, 21 …). The calibration uses the true values, and `axes.mass.ticks` records printed vs. true for each tick.

## Caveats

- The poster is an illustration, so most objects sit within ±1 decade of their real values. Bigger gaps are listed in `errata.json` or flagged with `position_is_schematic`.
- Positions are accurate to about ±10 px on the main chart (≈0.2 decade). Reference-line and tick positions were detected from pixel colours and are accurate to about ±2 px.
- Reference values are standard textbook/PDG figures rounded to 3–4 significant figures. Low-confidence ones (Boötes Void mass, Las Vegas Sphere mass, El Gordo size, RNA strand) are order-of-magnitude estimates. Check them before publishing anything as authoritative.
