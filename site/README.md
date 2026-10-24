# Triangle of Everything: website prototype

A static, no-build prototype drawn entirely from the datasets in `../data`. It uses no images: every chart, line, region and label comes from the JSON or from physics equations.

The triangle's walls, density and time lines and dark-matter windows all use the exact constants in `main_chart.json → physics`. The data layer places black holes and particles with those same numbers, so anything that belongs on a line stays on it at any zoom (tested at 150×). Lines and regions are clipped to the visible area before rendering, which keeps SVG coordinates small and precise.

## Run it

Serve the **project root** (not `site/`), because the page loads `../data/*.json`:

```bash
python3 -m http.server 8642
```

Then open <http://localhost:8642/site/>. Opening `index.html` straight from disk won't work, because browsers block `fetch` on `file://` pages. D3 7.8.5 loads from cdnjs, so the first load needs an internet connection.

## Layout

The **Triangle** is the home view, and the cosmic-time bar is always along its bottom. The page opens on today, paused. **Stars**, **Particles**, **Elements** and **Timeline** are reached from the triangle instead of from tabs:
- the **Open Stars ›** and **Open Particles ›** zoom boxes on the chart. The Stars box covers only the stars, stellar remnants, brown dwarfs and stellar black holes, not the planets that the Stars view also lists. The elements have no box; any element's **Show in Elements** opens the periodic table.
- the **Timeline ›** button at the right end of the time bar
- an item's details ("Show in Stars", "Show on the timeline" …), search results and deep links

A **‹ Triangle** button at the top left of those views goes back. The brand link resets everything to the triangle, today, at the home zoom.

## Views

- **Triangle.** Log width against log mass at equal scale. The triangle edges come from their equations: the Schwarzschild radius, the Compton limit and the Hubble radius. Toggleable layers, all on when the page opens:
  - density lines
  - time since the Big Bang (the universe's mean density at each moment; each line meets the black-hole edge at that moment's Hubble sphere)
  - black-hole classes
  - the light spectrum
  - the dark-matter windows (the published macro-dark-matter ranges on the nuclear-density line)
  - the zoom boxes
  - reference scales (1 kg, 1 lb, 1 nm, 1 AU, 1 light-year …)
  - an energy and temperature axis
  - Lineweaver & Patel extras: the four points from their chart that nothing else here covers (a flea, the neutrino, visible light and a black hole with a 3 K Hawking temperature). Their other points are the same things the triangle already shows, so each one is folded into that item instead of drawn twice. Its reading appears in the item's details under "On Lineweaver & Patel's chart", and old `#lp:…` links lead to it.

  The Hubble radius (solid) and the observable universe's edge (dashed particle horizon, about 3.2× wider) are both clickable. Each opens an explanation of what it is and why the two differ.
- **Stars.** Diameter against mass (in solar masses), with the black-hole region, the main-sequence band, the TOV and Chandrasekhar limits, the water-density line, and evolution arrows between objects.
- **Particles.** A mass ladder by family (quarks, leptons, bosons, hadrons). Neutrinos show as upper limits, the photon sits in a massless row, and decays and combinations are drawn as arcs that light up for the selected particle.
- **Elements.** The periodic table, coloured by where each element's atoms are made (the Big Bang, exploding massive stars, merging neutron stars, laboratories …), with a stripe along the bottom of each cell for every source. Turning off its one layer colours it by kind (alkali metal, noble gas …) instead. All 118 atoms are also dots on the triangle, by van der Waals diameter and atomic mass; zoomed in, they show the periodic pattern, with the alkali metals the widest of each period. Oxygen and helium are the poster's own atom dots, so they aren't drawn twice, and they're drawn at the same small size as the other atoms. In cosmic time, hydrogen, helium and lithium atoms appear at recombination, the elements forged in stars from ~200 million years on, and the lab-made elements in the last 82 years.
- **Timeline.** A log-time axis that compares the poster's era brackets with when things actually happened, shows every marked moment, and has a second axis for the universe's mean density.

Every dot is plotted at its true value. Where the original artwork puts something elsewhere, the details panel gives the poster's value next to the real one, and the **poster errors** list collects the big mistakes.

**Cosmic time** plays the universe in about 50 seconds. Pressing ▶ from today starts at the instant all three walls meet at a single point, half the Planck time in this chart's conventions, and runs back to today. You can also scrub the slider or click a milestone. As it plays:
- The Hubble corner slides up the black-hole wall, and the observable universe's edge moves with it (the two coincide until about 50,000 years).
- A red line shows the universe's mean density at that moment.
- Each object appears when it, or the first of its kind, came into existence.
- Layers follow the same rule. Light appears at ~10⁻¹² s, stellar black holes at ~200 million years and supermassive ones at ~700 million. The primordial-black-hole band grows up the wall with the horizon mass (c³t/G). The zoom boxes appear once something inside them exists, and are cut off at the Hubble wall while the universe is smaller than they are.
- Nothing is drawn beyond the Hubble wall of that moment: no dots, bands, markers or wavelengths longer than the Hubble sphere. The exceptions are the dashed observable-universe edge, which is a boundary, and the observable universe itself, which sits on that edge today.
- A glowing marker shows where the universe's background light peaks (Wien's law, λ = b/T). It slides down the photon line from gamma rays, through near-infrared at recombination, to microwaves today, where it's labelled as the cosmic microwave background.
- The camera follows the growing triangle until you pan or zoom yourself.
- **Sound.** While time plays, a Shepard tone rises without end: seven sine waves an octave apart all glide upward, each fading in at the bottom and out at the top. Each new dot on the triangle (an object, particle, element or star, but not a time line, band or zoom box) is announced by a ring in its colour that starts just outside the chart and closes in on the spot, following it while the camera moves. While time plays, the app looks 0.6 seconds ahead, so each ring sets off early and arrives, and vanishes, the instant its dot appears. That's when the pop plays, pitched by the dot's mass: Planck-scale things ring high and galaxies low. Dragging the slider forward can't be foreseen, so there the ring starts at once and the pop waits until it arrives; dragging back is quiet. A burst of arrivals announces at most three, its lightest, middle and heaviest member, and no more than seven go off in any 0.6 seconds. The rings show even when the sound is muted. The speaker button beside ▶ mutes everything, and the page remembers that choice. It's all synthesised with Web Audio, so there are no sound files.

The slider runs on a "story" scale: log time after the Big Bang for the first half of cosmic history, then log time before today. That way the first trillionth of a second and the last few thousand years both get room. Every object's details include when it first appeared, plus a **Watch it appear** button. Selecting something that doesn't exist yet at the moment shown jumps the slider to today.

The views share one selection. Clicking anything opens its details: the poster's value against the real value, notes, and links to the same thing in other views. You can also use search (press `/`), the smallest-to-largest **scale tour** (top left), the legend filters, the list of **poster errors**, and URL deep links such as `#object:sun` or `#particle:electron`.

## Files

| File | Role |
|---|---|
| `index.html`, `styles.css` | The page and the dark theme |
| `js/data.js` | Loads the JSON and turns every dataset into one list of items (key, group, colour, views, true positions, the poster's drawn values for comparison) |
| `js/chart.js` | Shared zoomable log-log scatter: axes, points, collision-free labels, tooltips, camera fitting |
| `js/triangle.js`, `js/stars.js`, `js/particles.js` | Each view's positions and data-drawn layers |
| `js/elements.js` | The periodic table view and its colours |
| `js/timeline.js` | The timeline (log-time axis) |
| `js/cosmictime.js` | The cosmic-time clock: story-scale slider mapping, interpolation of the history table, readout labels |
| `js/sound.js` | The Shepard tone and the pops, in Web Audio |
| `js/details.js` | The details panel |
| `js/format.js` | Formats log values as numbers in friendly units |
| `js/app.js` | Wires up navigation between views, cosmic time, selection, search, the tour, layers, the legend and the errata list |
