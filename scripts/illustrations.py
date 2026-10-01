"""Vector vegetable illustrations drawn directly with ReportLab.

Every function draws a shape centred on (0, 0) at a nominal size `s` (roughly its
height in points). Callers translate / rotate the canvas first, or use `place()`.
No image files needed, so PDFs stay small and crisp at any zoom.
"""
from __future__ import annotations

import math
import random
import re
from typing import Callable, Dict, List

from reportlab.lib.colors import HexColor, Color

# ---------------------------------------------------------------- palette
FOREST = HexColor("#2F4A3A")
LEAF = HexColor("#6E9A5B")
LEAF_DARK = HexColor("#4E7A45")
LEAF_LIGHT = HexColor("#A9C79A")
SAGE = HexColor("#A8BFA0")
SAGE_LIGHT = HexColor("#E3EBDD")
CREAM = HexColor("#F7F4EC")
TOMATO = HexColor("#D9624A")
TOMATO_LIGHT = HexColor("#EE8C74")
CARROT = HexColor("#E8913A")
CARROT_DARK = HexColor("#C9742A")
MUSTARD = HexColor("#E7B94C")
LEMON_PALE = HexColor("#F6E3A1")
AUBERGINE = HexColor("#6B3E6E")
AVO_DARK = HexColor("#3F5E2E")
AVO_FLESH = HexColor("#CFE09A")
PIT = HexColor("#8A5A3B")
CHICKPEA = HexColor("#E2C48E")
CHICKPEA_DARK = HexColor("#C9A66B")
TOFU = HexColor("#FBF3DC")
TOFU_EDGE = HexColor("#E7D9B4")
WHITE = HexColor("#FFFFFF")


def _alpha(col: Color, a: float) -> Color:
    return Color(col.red, col.green, col.blue, alpha=a)


# ---------------------------------------------------------------- primitives

def leaf(c, s, color=LEAF, vein=LEAF_LIGHT, width=0.42):
    w = s * width
    p = c.beginPath()
    p.moveTo(0, -s / 2)
    p.curveTo(w, -s * 0.2, w, s * 0.2, 0, s / 2)
    p.curveTo(-w, s * 0.2, -w, -s * 0.2, 0, -s / 2)
    p.close()
    c.setFillColor(color)
    c.drawPath(p, stroke=0, fill=1)
    c.setStrokeColor(vein)
    c.setLineWidth(max(0.5, s * 0.03))
    c.setLineCap(1)
    c.line(0, -s * 0.48, 0, s * 0.38)
    for t in (-0.2, 0.0, 0.2):
        c.line(0, s * t, s * 0.16, s * (t + 0.12))
        c.line(0, s * t, -s * 0.16, s * (t + 0.12))


def sprig(c, s, color=LEAF_DARK):
    c.setStrokeColor(color)
    c.setLineWidth(max(0.6, s * 0.035))
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(0, -s / 2)
    p.curveTo(s * 0.08, -s * 0.1, -s * 0.06, s * 0.2, 0, s / 2)
    c.drawPath(p, stroke=1, fill=0)
    for i, t in enumerate((-0.3, -0.08, 0.14, 0.34)):
        side = 1 if i % 2 == 0 else -1
        c.saveState()
        c.translate(0, s * t)
        c.rotate(-side * 50)
        c.translate(0, s * 0.11)
        leaf(c, s * 0.26, color=LEAF if i % 2 else LEAF_DARK, vein=LEAF_LIGHT, width=0.5)
        c.restoreState()
    c.saveState()
    c.translate(0, s * 0.5)
    leaf(c, s * 0.24, color=LEAF, vein=LEAF_LIGHT, width=0.5)
    c.restoreState()


def tomato(c, s):
    r = s / 2
    c.setFillColor(TOMATO)
    c.ellipse(-r, -r * 0.92, r, r * 0.92, stroke=0, fill=1)
    c.setFillColor(_alpha(WHITE, 0.35))
    c.ellipse(-r * 0.55, r * 0.15, -r * 0.15, r * 0.5, stroke=0, fill=1)
    c.setFillColor(LEAF_DARK)
    for k in range(5):
        c.saveState()
        c.translate(0, r * 0.62)
        c.rotate(k * 72)
        c.translate(0, r * 0.2)
        leaf(c, r * 0.42, color=LEAF_DARK, vein=LEAF_DARK, width=0.35)
        c.restoreState()
    c.setStrokeColor(LEAF_DARK)
    c.setLineWidth(max(0.8, s * 0.05))
    c.line(0, r * 0.62, r * 0.08, r * 0.95)


def carrot(c, s):
    L, w = s * 0.78, s * 0.3
    c.saveState()
    c.translate(0, -s * 0.5)
    for k, ang in enumerate((-28, 0, 28)):
        c.saveState()
        c.translate(0, L)
        c.rotate(ang)
        c.translate(0, s * 0.13)
        leaf(c, s * 0.3, color=LEAF if k != 1 else LEAF_DARK, vein=LEAF_LIGHT, width=0.32)
        c.restoreState()
    p = c.beginPath()
    p.moveTo(-w / 2, L)
    p.curveTo(-w / 2, L * 0.5, -w * 0.12, L * 0.12, 0, 0)
    p.curveTo(w * 0.12, L * 0.12, w / 2, L * 0.5, w / 2, L)
    p.curveTo(w * 0.2, L * 1.04, -w * 0.2, L * 1.04, -w / 2, L)
    p.close()
    c.setFillColor(CARROT)
    c.drawPath(p, stroke=0, fill=1)
    c.setStrokeColor(CARROT_DARK)
    c.setLineWidth(max(0.5, s * 0.025))
    c.setLineCap(1)
    for t, side in ((0.75, -1), (0.55, 1), (0.36, -1), (0.2, 1)):
        x = side * w * 0.42 * t
        c.line(x, L * t, x - side * w * 0.18, L * t - s * 0.012)
    c.restoreState()


def pea_pod(c, s):
    w = s * 0.24
    p = c.beginPath()
    p.moveTo(0, -s / 2)
    p.curveTo(w * 1.6, -s * 0.25, w * 1.6, s * 0.25, 0, s / 2)
    p.curveTo(w * 0.5, s * 0.2, w * 0.5, -s * 0.2, 0, -s / 2)
    p.close()
    c.setFillColor(LEAF_LIGHT)
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(LEAF)
    for t in (-0.3, -0.1, 0.1, 0.3):
        c.circle(w * 0.62, s * t, s * 0.085, stroke=0, fill=1)
    c.setStrokeColor(LEAF_DARK)
    c.setLineWidth(max(0.6, s * 0.03))
    c.line(0, s / 2, -s * 0.06, s * 0.6)


def lemon_slice(c, s, rind=MUSTARD, flesh=LEMON_PALE):
    r = s / 2
    c.setFillColor(rind)
    c.circle(0, 0, r, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.circle(0, 0, r * 0.86, stroke=0, fill=1)
    c.setFillColor(flesh)
    c.circle(0, 0, r * 0.8, stroke=0, fill=1)
    c.setStrokeColor(WHITE)
    c.setLineWidth(max(0.6, s * 0.035))
    for k in range(8):
        a = math.radians(k * 45 + 10)
        c.line(0, 0, math.cos(a) * r * 0.8, math.sin(a) * r * 0.8)
    c.setFillColor(WHITE)
    c.circle(0, 0, r * 0.08, stroke=0, fill=1)


def lime_slice(c, s):
    lemon_slice(c, s, rind=LEAF, flesh=HexColor("#D6E7A6"))


def chili(c, s):
    c.setStrokeColor(TOMATO)
    c.setLineCap(1)
    c.setLineWidth(s * 0.2)
    p = c.beginPath()
    p.moveTo(-s * 0.05, s * 0.32)
    p.curveTo(s * 0.12, s * 0.05, s * 0.1, -s * 0.25, -s * 0.12, -s * 0.42)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeColor(_alpha(WHITE, 0.4))
    c.setLineWidth(s * 0.04)
    p = c.beginPath()
    p.moveTo(-s * 0.06, s * 0.25)
    p.curveTo(s * 0.04, s * 0.08, s * 0.03, -s * 0.12, -s * 0.07, -s * 0.24)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeColor(LEAF_DARK)
    c.setLineWidth(s * 0.07)
    c.line(-s * 0.05, s * 0.36, s * 0.06, s * 0.5)
    c.setFillColor(LEAF_DARK)
    c.ellipse(-s * 0.15, s * 0.3, s * 0.07, s * 0.42, stroke=0, fill=1)


def avocado(c, s):
    r = s * 0.34
    c.setFillColor(AVO_DARK)
    c.circle(0, -s * 0.12, r, stroke=0, fill=1)
    c.circle(0, s * 0.2, r * 0.7, stroke=0, fill=1)
    c.setFillColor(AVO_FLESH)
    c.circle(0, -s * 0.12, r * 0.84, stroke=0, fill=1)
    c.circle(0, s * 0.2, r * 0.56, stroke=0, fill=1)
    c.setFillColor(PIT)
    c.circle(0, -s * 0.1, r * 0.42, stroke=0, fill=1)
    c.setFillColor(_alpha(WHITE, 0.35))
    c.circle(-r * 0.15, -s * 0.03, r * 0.12, stroke=0, fill=1)


def eggplant(c, s):
    c.setFillColor(AUBERGINE)
    c.circle(0, -s * 0.15, s * 0.3, stroke=0, fill=1)
    c.circle(0, s * 0.12, s * 0.2, stroke=0, fill=1)
    c.setFillColor(_alpha(WHITE, 0.25))
    c.ellipse(-s * 0.2, -s * 0.15, -s * 0.08, s * 0.1, stroke=0, fill=1)
    c.setFillColor(LEAF_DARK)
    for ang in (-50, 0, 50):
        c.saveState()
        c.translate(0, s * 0.3)
        c.rotate(180 + ang)
        c.translate(0, s * 0.08)
        leaf(c, s * 0.2, color=LEAF_DARK, vein=LEAF_DARK, width=0.4)
        c.restoreState()
    c.setStrokeColor(LEAF_DARK)
    c.setLineWidth(s * 0.06)
    c.setLineCap(1)
    c.line(0, s * 0.32, s * 0.04, s * 0.48)


def chickpeas(c, s):
    rnd = random.Random(7)
    for (x, y) in ((-0.2, -0.12), (0.18, -0.15), (0.0, 0.16), (-0.25, 0.22), (0.26, 0.2)):
        rr = s * (0.16 + rnd.random() * 0.03)
        c.setFillColor(CHICKPEA)
        c.circle(s * x, s * y, rr, stroke=0, fill=1)
        c.setStrokeColor(CHICKPEA_DARK)
        c.setLineWidth(max(0.5, s * 0.025))
        c.arc(s * x - rr * 0.5, s * y - rr * 0.2, s * x + rr * 0.5, s * y + rr * 0.6, 200, 120)


def tofu(c, s):
    for (x, y, a) in ((-0.18, -0.14, 8), (0.16, -0.1, -10), (0.0, 0.18, 20)):
        c.saveState()
        c.translate(s * x, s * y)
        c.rotate(a)
        d = s * 0.32
        c.setFillColor(TOFU_EDGE)
        c.roundRect(-d / 2 + s * 0.025, -d / 2 - s * 0.03, d, d, s * 0.05, stroke=0, fill=1)
        c.setFillColor(TOFU)
        c.roundRect(-d / 2, -d / 2, d, d, s * 0.05, stroke=0, fill=1)
        c.restoreState()


def bell_pepper(c, s, col=MUSTARD):
    c.setFillColor(col)
    for x in (-0.16, 0.0, 0.16):
        c.ellipse(s * x - s * 0.17, -s * 0.38, s * x + s * 0.17, s * 0.28, stroke=0, fill=1)
    c.setFillColor(_alpha(WHITE, 0.3))
    c.ellipse(-s * 0.26, -s * 0.15, -s * 0.16, s * 0.15, stroke=0, fill=1)
    c.setFillColor(LEAF_DARK)
    c.ellipse(-s * 0.14, s * 0.22, s * 0.14, s * 0.33, stroke=0, fill=1)
    c.setStrokeColor(LEAF_DARK)
    c.setLineWidth(s * 0.07)
    c.setLineCap(1)
    c.line(0, s * 0.3, s * 0.06, s * 0.46)


def zucchini_slice(c, s):
    r = s / 2
    c.setFillColor(LEAF_DARK)
    c.circle(0, 0, r, stroke=0, fill=1)
    c.setFillColor(HexColor("#EAF0C8"))
    c.circle(0, 0, r * 0.86, stroke=0, fill=1)
    c.setFillColor(HexColor("#D5E2A4"))
    for k in range(6):
        a = math.radians(k * 60)
        c.circle(math.cos(a) * r * 0.4, math.sin(a) * r * 0.4, r * 0.07, stroke=0, fill=1)


def grains(c, s, col=HexColor("#FFFDF6"), edge=HexColor("#D4C196"), count=34):
    rnd = random.Random(int(s * 10))
    for _ in range(count):
        x, y = rnd.uniform(-0.38, 0.38) * s, rnd.uniform(-0.38, 0.38) * s
        if x * x + y * y > (0.4 * s) ** 2:
            continue
        c.saveState()
        c.translate(x, y)
        c.rotate(rnd.uniform(0, 180))
        c.setFillColor(edge)
        c.ellipse(-s * 0.075, -s * 0.032, s * 0.075, s * 0.032, stroke=0, fill=1)
        c.setFillColor(col)
        c.ellipse(-s * 0.068, -s * 0.024, s * 0.064, s * 0.026, stroke=0, fill=1)
        c.restoreState()


def spinach(c, s):
    for ang, col in ((-35, LEAF_DARK), (30, LEAF), (0, HexColor("#5C8A4C"))):
        c.saveState()
        c.rotate(ang)
        c.translate(0, s * 0.05)
        leaf(c, s * 0.8, color=col, vein=LEAF_LIGHT, width=0.48)
        c.restoreState()


def berries(c, s):
    for (x, y) in ((-0.18, -0.1), (0.15, -0.16), (0.02, 0.15), (0.24, 0.16), (-0.22, 0.2)):
        c.setFillColor(HexColor("#4B5A9E"))
        c.circle(s * x, s * y, s * 0.15, stroke=0, fill=1)
        c.setFillColor(_alpha(WHITE, 0.35))
        c.circle(s * x - s * 0.04, s * y + s * 0.04, s * 0.035, stroke=0, fill=1)


def pumpkin(c, s):
    c.setFillColor(CARROT)
    for x in (-0.2, 0.2, -0.08, 0.08):
        c.ellipse(s * x - s * 0.2, -s * 0.33, s * x + s * 0.2, s * 0.28, stroke=0, fill=1)
    c.setStrokeColor(CARROT_DARK)
    c.setLineWidth(max(0.5, s * 0.025))
    for x in (-0.14, 0.0, 0.14):
        c.line(s * x, -s * 0.28, s * x, s * 0.22)
    c.setStrokeColor(LEAF_DARK)
    c.setLineWidth(s * 0.08)
    c.setLineCap(1)
    c.line(0, s * 0.25, s * 0.05, s * 0.42)


ICONS: Dict[str, Callable] = {
    "tomato": tomato, "carrot": carrot, "pea": pea_pod, "lemon": lemon_slice, "lime": lime_slice,
    "chili": chili, "avocado": avocado, "eggplant": eggplant, "chickpea": chickpeas, "tofu": tofu,
    "pepper": bell_pepper, "zucchini": zucchini_slice, "grains": grains, "spinach": spinach,
    "sprig": sprig, "leaf": leaf, "berries": berries, "pumpkin": pumpkin,
}

KEYWORDS = [
    (r"cherry tomato|tomato", "tomato"), (r"carrot", "carrot"), (r"\bpeas?\b|edamame|green beans|snap", "pea"),
    (r"lemon", "lemon"), (r"\blime", "lime"), (r"chil+i|jalape", "chili"), (r"avocado", "avocado"),
    (r"eggplant|aubergine|brinjal", "eggplant"), (r"chickpea|garbanzo|chana", "chickpea"),
    (r"tofu|paneer|tempeh", "tofu"), (r"bell pepper|capsicum", "pepper"), (r"zucchini|courgette|cucumber", "zucchini"),
    (r"\brice\b|quinoa|oats|millet|poha|couscous|polenta", "grains"),
    (r"spinach|kale|chard|lettuce|bok choy|cabbage|arugula|rocket|greens", "spinach"),
    (r"basil|cilantro|coriander leaves|parsley|mint|dill|curry leaves|herbs|chives", "sprig"),
    (r"berr", "berries"), (r"pumpkin|squash|sweet potato", "pumpkin"),
]


def icons_for(ingredient_names: List[str], limit: int = 6) -> List[str]:
    found: List[str] = []
    for name in ingredient_names:
        low = name.lower()
        for pat, icon in KEYWORDS:
            if re.search(pat, low) and icon not in found:
                found.append(icon)
                break
    for filler in ("sprig", "lemon", "leaf", "spinach"):
        if len(found) >= 3:
            break
        if filler not in found:
            found.append(filler)
    return found[:limit]


def place(c, name: str, x: float, y: float, s: float, angle: float = 0):
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    ICONS[name](c, s)
    c.restoreState()


BOWL_BASES = {
    "warm": (HexColor("#F2C48D"), HexColor("#E9A866")),
    "green": (HexColor("#DCE8C8"), HexColor("#C3D7A7")),
    "red": (HexColor("#F0A58E"), HexColor("#E2826A")),
    "cream": (HexColor("#F6EBD3"), HexColor("#EAD9B5")),
    "golden": (HexColor("#F5D98B"), HexColor("#EBC566")),
}


def bowl(c, cx: float, cy: float, r: float, icons: List[str], base: str = "green", seed: int = 1):
    """Top-down bowl with ingredients arranged around a centre piece."""
    rnd = random.Random(seed)
    if "grains" in icons:
        base = "cream"
    inner, ring = BOWL_BASES.get(base, BOWL_BASES["green"])
    c.saveState()
    c.setFillColor(_alpha(FOREST, 0.12))
    c.circle(cx + r * 0.05, cy - r * 0.07, r * 1.02, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.circle(cx, cy, r, stroke=0, fill=1)
    c.setStrokeColor(SAGE_LIGHT)
    c.setLineWidth(r * 0.025)
    c.circle(cx, cy, r * 0.93, stroke=1, fill=0)
    c.setFillColor(ring)
    c.circle(cx, cy, r * 0.82, stroke=0, fill=1)
    c.setFillColor(inner)
    c.circle(cx, cy, r * 0.74, stroke=0, fill=1)
    # clip ingredients to bowl interior
    p = c.beginPath()
    p.circle(cx, cy, r * 0.82)
    c.clipPath(p, stroke=0, fill=0)
    items = list(icons) or ["sprig"]
    if "grains" in items:  # grains become the bed of the bowl
        items.remove("grains")
        for gx in range(-2, 3):
            for gy in range(-2, 3):
                place(c, "grains", cx + gx * r * 0.32, cy + gy * r * 0.32, r * 0.5, 0)
        items = items or ["sprig"]
    centre = items[0]
    ring_items = items[1:] or ["leaf"]
    n = max(len(ring_items), 4)
    start = rnd.uniform(0, 360)
    for k in range(n):
        name = ring_items[k % len(ring_items)]
        a = math.radians(start + k * 360 / n)
        rr = r * 0.48
        place(c, name, cx + math.cos(a) * rr, cy + math.sin(a) * rr, r * 0.5, rnd.uniform(-40, 40) + math.degrees(a) - 90)
    place(c, centre, cx, cy, r * 0.56, rnd.uniform(-20, 20))
    # garnish
    for _ in range(3):
        a = rnd.uniform(0, 2 * math.pi)
        place(c, "leaf", cx + math.cos(a) * r * 0.2, cy + math.sin(a) * r * 0.2, r * 0.16, rnd.uniform(0, 360))
    c.restoreState()


def scatter(c, x0, y0, w, h, seed=3, density=1.0, size=(26, 42), names=None, avoid=None):
    """Scatter icons in a rectangle on a jittered grid (used for covers/patterns)."""
    rnd = random.Random(seed)
    names = names or ["tomato", "carrot", "pea", "lemon", "chili", "avocado", "eggplant", "sprig", "leaf", "pepper",
                      "zucchini", "berries", "pumpkin", "lime"]
    step = 62 / max(density, 0.1)
    rows, cols = int(h // step) + 1, int(w // step) + 1
    k = 0
    for i in range(rows):
        for j in range(cols):
            x = x0 + (j + 0.5 + (0.5 if i % 2 else 0)) * step + rnd.uniform(-10, 10)
            y = y0 + (i + 0.5) * step + rnd.uniform(-10, 10)
            if not (x0 - 10 <= x <= x0 + w + 10 and y0 - 10 <= y <= y0 + h + 10):
                continue
            if avoid and avoid[0] <= x <= avoid[2] and avoid[1] <= y <= avoid[3]:
                continue
            name = names[(k * 5 + rnd.randrange(len(names))) % len(names)]
            k += 1
            place(c, name, x, y, rnd.uniform(*size), rnd.uniform(-45, 45))
