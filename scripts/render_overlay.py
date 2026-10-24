#!/usr/bin/env python3
"""Draw every hotspot from ./data back onto the source images to check positions.

Needs Pillow:  pip install pillow
Writes data/qa/*.png (downscaled overlays) - open them and check each marker sits on its icon.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
QA = DATA / "qa"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def draw_marks(img, marks, scale, crop=None):
    """marks: list of (px, text, colour). crop: (x0, y0, x1, y1) in source px."""
    if crop:
        img = img.crop(crop)
        ox, oy = crop[0], crop[1]
    else:
        ox = oy = 0
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    for (x, y), text, colour in marks:
        sx, sy = (x - ox) * scale, (y - oy) * scale
        if not (0 <= sx <= img.width and 0 <= sy <= img.height):
            continue
        r = 7
        d.ellipse((sx - r, sy - r, sx + r, sy + r), outline=colour, width=3)
        d.text((sx + r + 2, sy - r), text, fill=colour)
    return img


def main():
    QA.mkdir(parents=True, exist_ok=True)
    src = ROOT / load("main_chart.json")["source"]["file"]
    big = Image.open(src).convert("RGB")

    objects = load("objects.json")["objects"]
    obj_marks = [(o["image"]["icon"]["px"], o["id"], "#00ff66") for o in objects]
    obj_marks += [(o["image"]["label"]["px"], "L", "#ffff00") for o in objects if o["image"]["label"]]
    draw_marks(big, obj_marks, 0.55, crop=(2000, 1400, 5400, 5700)).save(QA / "main_objects.png")

    stellar = load("stellar_evolution.json")
    st_marks = [(p, s["id"], "#00ff66") for s in stellar["objects"] for p in s["image"]["all_icons_px"]]
    st_marks += [(p["px"], t["id"], "#ff66ff") for t in stellar["transitions"] for p in t["polyline"]]
    draw_marks(big, st_marks, 0.8, crop=(550, 550, 2600, 1950)).save(QA / "stellar_inset.png")

    particles = load("fundamental_particles.json")
    pa_marks = [(p["image"]["icon"]["px"], p["id"], "#00ff66") for p in particles["particles"]]
    draw_marks(big, pa_marks, 0.8, crop=(550, 2600, 2100, 4000)).save(QA / "particles_inset.png")

    main_chart = load("main_chart.json")
    ax_marks = [((r["x_px"], 6700), r["label"], "#00ffff") for r in main_chart["reference_lines"]["width"]]
    ax_marks += [((5420, r["y_px"]), r["label"], "#00ffff") for r in main_chart["reference_lines"]["mass"]]
    ax_marks += [(b["point"]["px"], b["id"], "#ff3333") for b in main_chart["boundaries"] if "point" in b]
    ax_marks += [(p["px"], b["id"], "#ff9900") for b in main_chart["boundaries"] for p in b.get("polyline", [])]
    for r in main_chart["regions"]:
        for p in r.get("polygon", []):
            ax_marks.append((p["px"], r["id"], "#ff66ff"))
    draw_marks(big, ax_marks, 0.25).save(QA / "main_axes_regions.png")

    lp = load("lineweaver_patel.json")
    lp_img = Image.open(ROOT / lp["source"]["file"]).convert("RGB")
    lp_marks = [(o["image"]["icon"]["px"], o["id"], "#d00000") for o in lp["objects"]]
    draw_marks(lp_img, lp_marks, 1.0, crop=(400, 300, 1900, 2300)).save(QA / "lineweaver_patel.png")
    print("wrote", ", ".join(sorted(p.name for p in QA.glob("*.png"))), file=sys.stderr)


if __name__ == "__main__":
    main()
