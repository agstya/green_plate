#!/usr/bin/env python3
"""Render recipe JSON into an illustrated "Green Plate" PDF cookbook.

  python3 render_pdf.py cookbook.json -o my-cookbook.pdf
  python3 render_pdf.py recipe.json -o dinner.pdf --paper white     # printer-friendly
  python3 render_pdf.py cookbook.json --force                        # render even if diet check fails

Input: a single recipe, a list of recipes, or a cookbook object
  {"title", "subtitle", "for", "diets": [...], "recipes": [...], "meal_plan": {...}, "notes": "..."}
See skills/plant-recipes/references/recipe-schema.md for every field.

Before drawing anything the recipes are run through the diet checker; violations abort
the render (exit 1) unless --force is given, in which case they are printed as warnings.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from reportlab.lib.colors import HexColor, Color, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, FrameBreak, KeepTogether,
                                    NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)
except ImportError:  # pragma: no cover
    sys.stderr.write("render_pdf.py needs ReportLab:  pip install reportlab\n")
    sys.exit(3)

import illustrations as ill  # noqa: E402
import shopping_list  # noqa: E402
from gp_common import (PLUGIN_ROOT, check_recipe, expand_diets, format_report, ingredient_text,  # noqa: E402
                       load_diets, load_profile, recipes_in)

# ---------------------------------------------------------------- theme
FOREST = HexColor("#2F4A3A")
INK = HexColor("#33322E")
MUTED = HexColor("#77736A")
SAGE = HexColor("#A8BFA0")
SAGE_LIGHT = HexColor("#E6EEDF")
SAGE_PANEL = HexColor("#EDF2E6")
OLIVE = HexColor("#6E9A5B")
CARROT = HexColor("#E8913A")
TOMATO = HexColor("#D9624A")
MUSTARD = HexColor("#E7B94C")
CREAM = HexColor("#F8F5EC")
PAPER = CREAM

FONT_DIR = PLUGIN_ROOT / "assets" / "fonts"
SERIF, SERIF_B, SERIF_SB, SERIF_I = "Helvetica", "Helvetica-Bold", "Helvetica-Bold", "Helvetica-Oblique"
SANS, SANS_M, SANS_B, SANS_L = "Helvetica", "Helvetica", "Helvetica-Bold", "Helvetica"


def register_fonts():
    global SERIF, SERIF_B, SERIF_SB, SERIF_I, SANS, SANS_M, SANS_B, SANS_L
    files = {
        "PlateSerif": "PlateSerif-Regular.ttf", "PlateSerif-Bold": "PlateSerif-Bold.ttf",
        "PlateSerif-SemiBold": "PlateSerif-SemiBold.ttf", "PlateSerif-Italic": "PlateSerif-Italic.ttf",
        "Poppins": "Poppins-Regular.ttf", "Poppins-Medium": "Poppins-Medium.ttf",
        "Poppins-Bold": "Poppins-Bold.ttf", "Poppins-Light": "Poppins-Light.ttf",
    }
    try:
        for name, fn in files.items():
            pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / fn)))
    except Exception as exc:  # fall back to core fonts
        sys.stderr.write(f"note: bundled fonts unavailable ({exc}); using Helvetica\n")
        return
    pdfmetrics.registerFontFamily("PlateSerif", normal="PlateSerif", bold="PlateSerif-Bold",
                                  italic="PlateSerif-Italic", boldItalic="PlateSerif-Bold")
    pdfmetrics.registerFontFamily("Poppins", normal="Poppins", bold="Poppins-Bold",
                                  italic="Poppins-Light", boldItalic="Poppins-Bold")
    SERIF, SERIF_B, SERIF_SB, SERIF_I = "PlateSerif", "PlateSerif-Bold", "PlateSerif-SemiBold", "PlateSerif-Italic"
    SANS, SANS_M, SANS_B, SANS_L = "Poppins", "Poppins-Medium", "Poppins-Bold", "Poppins-Light"


# ---------------------------------------------------------------- text helpers
_FRAC = {"⅓": "1/3", "⅔": "2/3", "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8", "⅕": "1/5"}


def clean(text: Any) -> str:
    s = str(text if text is not None else "")
    for k, v in _FRAC.items():
        s = s.replace(k, v)
    return s


def rich(text: Any) -> str:
    """Escape for Paragraph markup and support **bold** and *italic*."""
    s = escape(clean(text))
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", s)
    return s


def styles() -> Dict[str, ParagraphStyle]:
    S = {}
    S["title"] = ParagraphStyle("title", fontName=SERIF_B, fontSize=27, leading=31, textColor=FOREST)
    S["desc"] = ParagraphStyle("desc", fontName=SERIF_I, fontSize=10.5, leading=15, textColor=MUTED)
    S["h2"] = ParagraphStyle("h2", fontName=SERIF_B, fontSize=15, leading=19, textColor=FOREST, spaceAfter=2)
    S["h1"] = ParagraphStyle("h1", fontName=SERIF_B, fontSize=30, leading=34, textColor=FOREST, spaceAfter=4)
    S["kicker"] = ParagraphStyle("kicker", fontName=SANS_M, fontSize=7.5, leading=10, textColor=OLIVE)
    S["small"] = ParagraphStyle("small", fontName=SANS, fontSize=7.8, leading=10.5, textColor=MUTED)
    S["group"] = ParagraphStyle("group", fontName=SANS_B, fontSize=7.5, leading=10, textColor=OLIVE,
                                spaceBefore=7, spaceAfter=2)
    S["ing"] = ParagraphStyle("ing", fontName=SANS, fontSize=8.8, leading=12, textColor=INK, leftIndent=9,
                              firstLineIndent=0, spaceAfter=3.2, bulletIndent=0, bulletFontSize=8)
    S["step"] = ParagraphStyle("step", fontName=SERIF, fontSize=10.3, leading=15, textColor=INK)
    S["body"] = ParagraphStyle("body", fontName=SERIF, fontSize=10, leading=14.5, textColor=INK)
    S["box"] = ParagraphStyle("box", fontName=SANS, fontSize=8.4, leading=11.6, textColor=INK, spaceAfter=3)
    S["boxh"] = ParagraphStyle("boxh", fontName=SANS_B, fontSize=7.8, leading=10, textColor=FOREST, spaceAfter=4)
    S["cell"] = ParagraphStyle("cell", fontName=SANS, fontSize=8.4, leading=11, textColor=INK)
    S["cellh"] = ParagraphStyle("cellh", fontName=SANS_B, fontSize=8, leading=10, textColor=white)
    S["check"] = ParagraphStyle("check", fontName=SANS, fontSize=8.8, leading=11.5, textColor=INK)
    S["toc"] = ParagraphStyle("toc", fontName=SERIF_SB, fontSize=13, leading=16, textColor=FOREST)
    S["tocd"] = ParagraphStyle("tocd", fontName=SANS, fontSize=8, leading=10.5, textColor=MUTED)
    return S


# ---------------------------------------------------------------- drawing helpers

def pill(c, x, y, text, fill, color=white, font=None, size=7.2, pad=6, h=15, stroke=None):
    font = font or SANS_M
    w = pdfmetrics.stringWidth(text, font, size) + 2 * pad
    c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, h / 2, stroke=1 if stroke is not None else 0, fill=1)
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x + pad, y + (h - size) / 2 + 1.2, text)
    return w


def page_bg(c, doc):
    c.setFillColor(PAPER)
    c.rect(0, 0, doc.pagesize[0], doc.pagesize[1], stroke=0, fill=1)


def footer(c, doc):
    W = doc.pagesize[0]
    c.setFillColor(MUTED)
    c.setFont(SANS, 7.5)
    c.drawRightString(W - doc.leftMargin, 26, str(c.getPageNumber()))
    c.drawString(doc.leftMargin + 14, 26, getattr(doc, "book_title", "Green Plate"))
    ill.place(c, "leaf", doc.leftMargin + 5, 29, 10, -40)
    c.setStrokeColor(SAGE)
    c.setLineWidth(0.5)
    c.line(doc.leftMargin, 40, W - doc.leftMargin, 40)


def diet_badges(c, x, y, diets, rules, max_x, size=7.2):
    cx = x
    for d in diets:
        r = rules[d]
        label = r["label"]
        w = pdfmetrics.stringWidth(label, SANS_M, size) + 12
        if cx + w > max_x:
            cx = x
            y -= 19
        pill(c, cx, y, label, HexColor(r.get("color", "#6E9A5B")), size=size)
        cx += w + 5
    return y


def clipped_image(c, path, cx, cy, r):
    try:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(str(path))
        iw, ih = img.getSize()
    except Exception:
        return False
    scale = max(2 * r / iw, 2 * r / ih)
    w, h = iw * scale, ih * scale
    c.saveState()
    c.setFillColor(Color(0.18, 0.29, 0.23, alpha=0.12))
    c.circle(cx + r * 0.05, cy - r * 0.07, r * 1.02, stroke=0, fill=1)
    p = c.beginPath()
    p.circle(cx, cy, r)
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(img, cx - w / 2, cy - h / 2, w, h)
    c.restoreState()
    c.setStrokeColor(white)
    c.setLineWidth(4)
    c.circle(cx, cy, r, stroke=1, fill=0)
    return True


# ---------------------------------------------------------------- flowables

class Step(Flowable):
    def __init__(self, n, text, style, accent=OLIVE):
        super().__init__()
        self.n, self.para, self.accent = n, Paragraph(rich(text), style), accent
        self.gap = 26

    def wrap(self, aw, ah):
        self.aw = aw
        _, h = self.para.wrap(aw - self.gap, ah)
        self.h = max(h, 18) + 9
        return aw, self.h

    def split(self, aw, ah):
        return []

    def draw(self):
        c = self.canv
        top = self.h - 9
        c.setFillColor(self.accent)
        c.circle(9, top - 8, 9, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont(SANS_B, 8.5)
        c.drawCentredString(9, top - 11, str(self.n))
        self.para.drawOn(c, self.gap, top - self.para.height)


class CheckItem(Flowable):
    def __init__(self, text, style):
        super().__init__()
        self.para = Paragraph(text, style)

    def wrap(self, aw, ah):
        _, h = self.para.wrap(aw - 16, ah)
        self.h = h + 4
        return aw, self.h

    def draw(self):
        c = self.canv
        c.setStrokeColor(SAGE)
        c.setLineWidth(0.9)
        c.roundRect(0, self.h - 13.5, 9, 9, 2, stroke=1, fill=0)
        self.para.drawOn(c, 16, self.h - 4 - self.para.height)


class Marker(Flowable):
    """Zero-size flowable that records the page it lands on (for the contents page)."""

    def __init__(self, key, registry):
        super().__init__()
        self.key, self.registry = key, registry

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        self.registry[self.key] = self.canv.getPageNumber()


class SectionTitle(Flowable):
    def __init__(self, kicker, title, icon="sprig"):
        super().__init__()
        self.kicker, self.title, self.icon = kicker, title, icon

    def wrap(self, aw, ah):
        self.aw = aw
        return aw, 62

    def draw(self):
        c = self.canv
        ill.place(c, self.icon, 14, 30, 34, -15)
        c.setFillColor(OLIVE)
        c.setFont(SANS_M, 7.5)
        c.drawString(40, 44, self.kicker.upper())
        c.setFillColor(FOREST)
        c.setFont(SERIF_B, 25)
        c.drawString(40, 18, self.title)
        c.setStrokeColor(SAGE)
        c.setLineWidth(0.6)
        c.line(0, 4, self.aw, 4)


def boxed(flowables, bg=SAGE_PANEL, width=None, pad=10):
    t = Table([[flowables]], colWidths=[width] if width else None)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), pad), ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad - 2), ("BOTTOMPADDING", (0, 0), (-1, -1), pad - 3),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    return t


# ---------------------------------------------------------------- builder

class Book:
    def __init__(self, doc_json: Any, paper: str = "cream", size=letter, profile=None, rules=None):
        self.raw = doc_json
        self.rules = rules or load_diets()
        self.profile = profile
        self.recipes = recipes_in(doc_json)
        self.meta = doc_json if isinstance(doc_json, dict) and "recipes" in doc_json else {}
        self.size = size
        self.W, self.H = size
        self.M = 48
        self.S = styles()
        global PAPER
        PAPER = CREAM if paper == "cream" else white
        self.pages: Dict[str, int] = {}
        self.has_cover = bool(self.meta) or len(self.recipes) > 1
        self.title = clean(self.meta.get("title") or (self.recipes[0].get("title") if len(self.recipes) == 1 else "Green Plate"))

    # ---- per-recipe layout -------------------------------------------------
    def recipe_diets(self, r):
        return expand_diets(r.get("diets", []) or [], self.rules) if r.get("diets") else []

    def header_parts(self, r, i):
        hero_d = 180
        text_w = self.W - 2 * self.M - hero_d - 26
        title = Paragraph(rich(r.get("title", "Untitled")), self.S["title"])
        _, th = title.wrap(text_w, 400)
        desc = None
        dh = 0
        if r.get("description"):
            desc = Paragraph(rich(r["description"]), self.S["desc"])
            _, dh = desc.wrap(text_w, 400)
        chips_h = 22
        n_diets = len(self.recipe_diets(r))
        badge_rows = 0 if not n_diets else 1 + (n_diets > 4)
        left_h = 16 + th + (8 + dh if desc else 0) + 12 + chips_h + badge_rows * 19 + 4
        height = max(left_h, hero_d + 6)
        return {"title": title, "th": th, "desc": desc, "dh": dh, "text_w": text_w, "hero_d": hero_d, "height": height}

    def draw_header(self, c, doc, r, i, hp):
        page_bg(c, doc)
        W, H, M = self.W, self.H, self.M
        top = H - M
        # soft sage blob behind hero
        hero_r = hp["hero_d"] / 2 - 4
        hcx, hcy = W - M - hero_r - 4, top - hero_r - 6
        c.setFillColor(SAGE_LIGHT)
        c.circle(hcx + 18, hcy + 12, hero_r + 26, stroke=0, fill=1)
        ill.place(c, "sprig", hcx - hero_r - 4, hcy - hero_r + 18, 46, 35)
        ill.place(c, "leaf", hcx + hero_r + 2, hcy + hero_r - 6, 26, -30)
        img = r.get("image")
        drawn = False
        if img:
            p = Path(img)
            if not p.is_absolute() and getattr(self, "base_dir", None):
                p = self.base_dir / p
            drawn = clipped_image(c, p, hcx, hcy, hero_r)
        if not drawn:
            names = [ingredient_text(x) for x in self._ings(r)]
            icons = r.get("illustration") or ill.icons_for(names)
            ill.bowl(c, hcx, hcy, hero_r, icons, base=r.get("bowl", self._bowl_base(names)), seed=i + 3)
        # kicker
        kicker = f"RECIPE {i + 1:02d}"
        if r.get("cuisine"):
            kicker += f"  ·  {clean(r['cuisine']).upper()}"
        if r.get("course"):
            kicker += f"  ·  {clean(r['course']).upper()}"
        c.setFillColor(OLIVE)
        c.setFont(SANS_M, 7.5)
        c.drawString(M, top - 8, kicker)
        y = top - 16
        hp["title"].drawOn(c, M, y - hp["th"])
        y -= hp["th"]
        if hp["desc"]:
            y -= 6
            hp["desc"].drawOn(c, M, y - hp["dh"])
            y -= hp["dh"]
        # meta chips
        y -= 26
        x = M
        meta = []
        if r.get("serves"):
            meta.append(f"Serves {clean(r['serves'])}")
        if r.get("prep_min") is not None:
            meta.append(f"Prep {clean(r['prep_min'])} min")
        if r.get("cook_min") is not None:
            meta.append(f"Cook {clean(r['cook_min'])} min")
        if r.get("difficulty"):
            meta.append(clean(r["difficulty"]).capitalize())
        for m in meta:
            x += pill(c, x, y, m, white, color=FOREST, size=7.4, stroke=SAGE, h=16) + 5
        diets = self.recipe_diets(r)
        if diets:
            y -= 21
            diet_badges(c, M, y, diets, self.rules, M + hp["text_w"] + 10)
        footer(c, doc)

    def draw_cont(self, c, doc, r):
        page_bg(c, doc)
        c.setFillColor(OLIVE)
        c.setFont(SANS_M, 7.5)
        c.drawString(self.M, self.H - self.M - 6, "CONTINUED")
        c.setFillColor(FOREST)
        c.setFont(SERIF_B, 14)
        c.drawString(self.M + 64, self.H - self.M - 7, clean(r.get("title", "")))
        c.setStrokeColor(SAGE)
        c.setLineWidth(0.5)
        c.line(self.M, self.H - self.M - 16, self.W - self.M, self.H - self.M - 16)
        footer(c, doc)

    @staticmethod
    def _height(flowables, width):
        from reportlab.pdfgen.canvas import Canvas
        dummy = Canvas(io.BytesIO())
        total = 0.0
        for f in flowables:
            if isinstance(f, KeepTogether):  # its wrap() reports a sentinel height; measure the parts
                total += Book._height(f._content, width)
                continue
            _, h = f.wrapOn(dummy, width, 10_000)
            total += h + f.getSpaceBefore() + f.getSpaceAfter()
        return total

    def draw_panel(self, c, x, y, w, h):
        c.setFillColor(SAGE_PANEL)
        c.roundRect(x, y, w, h, 12, stroke=0, fill=1)

    @staticmethod
    def _ings(r):
        for ing in r.get("ingredients", []) or []:
            if isinstance(ing, dict) and "items" in ing:
                for sub in ing["items"]:
                    yield sub
            else:
                yield ing

    @staticmethod
    def _bowl_base(names):
        txt = " ".join(names).lower()
        if re.search(r"curry|turmeric|dal|lentil|pumpkin|sweet potato|coconut milk", txt):
            return "warm"
        if re.search(r"tomato|beet|red pepper|harissa", txt):
            return "red"
        if re.search(r"oats|porridge|yogurt|banana", txt):
            return "cream"
        return "green"

    # ---- flowables for one recipe -----------------------------------------
    def ingredient_flowables(self, r):
        S = self.S
        out = [Paragraph("Ingredients", S["h2"])]
        if r.get("serves"):
            out.append(Paragraph(f"for {escape(clean(r['serves']))} servings", S["small"]))
        out.append(Spacer(1, 4))
        groups: List[tuple] = []
        for ing in r.get("ingredients", []) or []:
            if isinstance(ing, dict) and "items" in ing:
                groups.append((ing.get("group") or ing.get("name") or "", ing["items"]))
            else:
                g = ing.get("group", "") if isinstance(ing, dict) else ""
                if groups and groups[-1][0] == g:
                    groups[-1][1].append(ing)
                else:
                    groups.append((g, [ing]))
        for gname, items in groups:
            if gname:
                out.append(Paragraph(escape(clean(gname)).upper(), S["group"]))
            for ing in items:
                if isinstance(ing, str):
                    txt = rich(ing)
                else:
                    qty = clean(ing.get("qty", "") or "")
                    txt = (f"<font name='{SANS_M}' color='#2F4A3A'>{escape(qty)}</font> " if qty else "") + rich(ingredient_text(ing))
                    if ing.get("note"):
                        txt += f" <font color='#77736A'>, {rich(ing['note'])}</font>"
                    if ing.get("optional"):
                        txt += " <font color='#6E9A5B' size='7'>(optional)</font>"
                out.append(Paragraph(txt, S["ing"], bulletText="•"))
        return out

    def method_flowables(self, r):
        S = self.S
        out = [Paragraph("Method", S["h2"]), Spacer(1, 6)]
        for n, step in enumerate(r.get("steps", []) or [], 1):
            out.append(Step(n, step, S["step"]))
        extras = []
        swaps = r.get("swaps") or []
        if swaps:
            items = [Paragraph("DIET SWAPS USED", S["boxh"])]
            for sw in swaps:
                if isinstance(sw, dict):
                    t = f"<b>{rich(sw.get('from', ''))}</b>  »  <b>{rich(sw.get('to', ''))}</b>"
                    if sw.get("why"):
                        t += f"<br/><font color='#77736A'>{rich(sw['why'])}</font>"
                else:
                    t = rich(sw)
                items.append(Paragraph(t, S["box"]))
            extras.append(boxed(items, bg=HexColor("#FBEBD9")))
        for e in extras:
            out.append(Spacer(1, 10))
            out.append(KeepTogether([e]))
        return out

    def side_flowables(self, r):
        """Nutrition, portion notes and cook's notes: they live under the ingredients in the side panel."""
        S = self.S
        blocks = []
        nut = r.get("nutrition") or {}
        if nut:
            blocks.append([Spacer(1, 10), self.nutrition_table(nut)])
        out = []
        rep = check_recipe(r, profile=self.profile, rules=self.rules)
        notes = [w for w in rep["warnings"] if w.get("diet") in self.rules]
        if notes:
            seen, lines = set(), []
            for w in notes:
                key = (w["diet"], w["note"])
                if key in seen:
                    continue
                seen.add(key)
                lines.append(Paragraph(f"<b>{rich(w['ingredient'])}</b> ({escape(self.rules[w['diet']]['label'])}): {rich(w['note'])}",
                                       S["box"]))
            blocks.append([Spacer(1, 10),
                           KeepTogether([boxed([Paragraph("PORTION NOTES", S["boxh"])] + lines, bg=HexColor("#FFF6D9"), pad=8)])])
        tips = r.get("tips") or []
        if tips:
            blocks.append([Spacer(1, 10), KeepTogether([Paragraph("COOK'S NOTES", S["group"])] +
                                                       [Paragraph(rich(t), S["ing"], bulletText="•") for t in tips])])
        return blocks

    def nutrition_table(self, nut):
        labels = [("calories", "Calories", " kcal"), ("protein_g", "Protein", " g"), ("carbs_g", "Carbs", " g"),
                  ("fat_g", "Fat", " g"), ("fiber_g", "Fibre", " g")]
        lab = ParagraphStyle("nl", fontName=SANS, fontSize=7.8, leading=10, textColor=MUTED)
        val = ParagraphStyle("nv", fontName=SANS_M, fontSize=8.4, leading=10, textColor=FOREST, alignment=2)
        rows = [[Paragraph(label, lab), Paragraph(f"{escape(clean(nut[key]))}{unit}", val)]
                for key, label, unit in labels if nut.get(key) is not None]
        if not rows:
            return Spacer(1, 0)
        t = Table(rows, colWidths=[92, 70], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), white), ("ROUNDEDCORNERS", [7, 7, 7, 7]),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, SAGE_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        head = Paragraph("NUTRITION PER SERVING (APPROX.)", self.S["group"])
        return KeepTogether([head, t])

    # ---- special pages ----------------------------------------------------
    def draw_cover(self, c, doc):
        W, H = self.W, self.H
        page_bg(c, doc)
        panel_h = H * 0.56
        c.setFillColor(ill.FOREST)
        c.rect(0, H - panel_h, W, panel_h, stroke=0, fill=1)
        # wavy bottom edge
        p = c.beginPath()
        y0 = H - panel_h
        p.moveTo(0, y0 + 8)
        for k in range(6):
            x1 = W * k / 6
            p.curveTo(x1 + W / 24, y0 - 14, x1 + W / 8, y0 + 22, x1 + W / 6, y0 + 4)
        p.lineTo(W, y0 - 30)
        p.lineTo(0, y0 - 30)
        p.close()
        c.setFillColor(PAPER)
        c.drawPath(p, stroke=0, fill=1)
        cx, cy, br = W / 2, H - panel_h * 0.47, 112
        ill.scatter(c, 0, y0 + 18, W, panel_h - 18, seed=11, density=1.05, size=(24, 40),
                    avoid=(cx - br - 30, cy - br - 30, cx + br + 30, cy + br + 30))
        names = [ingredient_text(x) for r in self.recipes for x in self._ings(r)]
        ill.bowl(c, cx, cy, br, ill.icons_for(names, limit=6), base=self._bowl_base(names), seed=5)
        # titles
        y = H - panel_h - 70
        c.setFillColor(OLIVE)
        c.setFont(SANS_M, 8.5)
        kick = clean(self.meta.get("kicker") or "A GREEN PLATE COOKBOOK").upper()
        c.drawCentredString(W / 2, y + 26, " ".join(kick))
        t = Paragraph(rich(self.title), ParagraphStyle("ct", fontName=SERIF_B, fontSize=38, leading=42,
                                                       textColor=FOREST, alignment=TA_CENTER))
        _, th = t.wrap(W - 140, 200)
        t.drawOn(c, 70, y - th + 10)
        y = y - th + 2
        if self.meta.get("subtitle"):
            st = Paragraph(rich(self.meta["subtitle"]), ParagraphStyle("cs", fontName=SERIF_I, fontSize=13, leading=18,
                                                                       textColor=MUTED, alignment=TA_CENTER))
            _, sh = st.wrap(W - 160, 100)
            st.drawOn(c, 80, y - sh - 4)
            y -= sh + 8
        # diet badges centred
        diets = self.book_diets()
        if diets:
            widths = [pdfmetrics.stringWidth(self.rules[d]["label"], SANS_M, 8) + 14 for d in diets]
            total = sum(widths) + 6 * (len(widths) - 1)
            x = (W - total) / 2
            for d, w in zip(diets, widths):
                pill(c, x, y - 30, self.rules[d]["label"], HexColor(self.rules[d]["color"]), size=8, pad=7, h=18)
                x += w + 6
            y -= 30
        c.setFillColor(MUTED)
        c.setFont(SANS, 8.5)
        who = self.meta.get("for") or (self.profile or {}).get("name")
        line = f"{len(self.recipes)} recipes"
        if who:
            line = f"Made for {clean(who)}  ·  " + line
        line += "  ·  " + _dt.date.today().strftime("%B %Y")
        c.drawCentredString(W / 2, 62, line)
        ill.place(c, "leaf", W / 2 - 60, 90, 16, -60)
        ill.place(c, "leaf", W / 2 + 60, 90, 16, 60)
        c.setStrokeColor(SAGE)
        c.setLineWidth(0.6)
        c.line(W / 2 - 48, 90, W / 2 + 48, 90)

    def book_diets(self):
        if self.meta.get("diets"):
            return expand_diets(self.meta["diets"], self.rules)
        sets = [set(self.recipe_diets(r)) for r in self.recipes if r.get("diets")]
        if not sets:
            return []
        common = set.intersection(*sets)
        order = list(self.rules)
        return sorted(common, key=order.index)

    def contents(self):
        S = self.S
        out = [SectionTitle("Inside", "Contents", "sprig"), Spacer(1, 14)]
        rows = []
        for i, r in enumerate(self.recipes):
            t = r.get("prep_min", 0) or 0
            t = (t if isinstance(t, (int, float)) else 0) + (r.get("cook_min", 0) if isinstance(r.get("cook_min", 0), (int, float)) else 0)
            sub = []
            if r.get("course"):
                sub.append(clean(r["course"]))
            if r.get("cuisine"):
                sub.append(clean(r["cuisine"]))
            if t:
                sub.append(f"{int(t)} min")
            short = " ".join(self.rules[d]["short"] for d in self.recipe_diets(r))
            rows.append([
                Paragraph(f"<font name='{SANS_B}' color='#6E9A5B'>{i + 1:02d}</font>", S["cell"]),
                [Paragraph(rich(r.get("title", "")), S["toc"]),
                 Paragraph(escape(" · ".join(sub)) + (f"   <font color='#6E9A5B'>{escape(short)}</font>" if short else ""), S["tocd"])],
                Paragraph(f"<font name='{SERIF_SB}' size='13' color='#2F4A3A'>{self.pages.get(f'r{i}', '')}</font>",
                          ParagraphStyle("pg", alignment=2)),
            ])
        extras = []
        if self.meta.get("meal_plan"):
            extras.append(("Weekly meal plan", "mealplan"))
        if self.want_shopping:
            extras.append(("Shopping list", "shopping"))
        extras.append(("Diet guide & notes", "notes"))
        for label, key in extras:
            rows.append(["", Paragraph(label, S["toc"]),
                         Paragraph(f"<font name='{SERIF_SB}' size='13' color='#2F4A3A'>{self.pages.get(key, '')}</font>",
                                   ParagraphStyle("pg", alignment=2))])
        tw = self.W - 2 * self.M
        t = Table(rows, colWidths=[34, tw - 84, 50])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, SAGE_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
        ]))
        out.append(t)
        diets = self.book_diets()
        if diets:
            out += [Spacer(1, 18), Paragraph("Every recipe in this book is: " + ", ".join(
                f"<font name='{SANS_B}' color='{self.rules[d]['color']}'>{escape(self.rules[d]['label'])}</font>" for d in diets),
                self.S["body"])]
        if self.meta.get("intro"):
            out += [Spacer(1, 10), Paragraph(rich(self.meta["intro"]), self.S["desc"])]
        return out

    def meal_plan(self):
        mp = self.meta.get("meal_plan") or {}
        days = mp.get("days") or []
        if not days:
            return []
        S = self.S
        cols = mp.get("columns") or [k for k in ("breakfast", "lunch", "dinner", "snack") if any(d.get(k) for d in days)]
        head = [Paragraph("DAY", S["cellh"])] + [Paragraph(cname.upper(), S["cellh"]) for cname in cols]
        rows = [head]
        for d in days:
            rows.append([Paragraph(f"<font name='{SERIF_B}' size='11' color='#2F4A3A'>{escape(clean(d.get('day', '')))}</font>", S["cell"])]
                        + [Paragraph(rich(d.get(k, "") or "—"), S["cell"]) for k in cols])
        tw = self.W - 2 * self.M
        first = 62
        t = Table(rows, colWidths=[first] + [(tw - first) / len(cols)] * len(cols), repeatRows=1)
        st = [("BACKGROUND", (0, 0), (-1, 0), ill.FOREST), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
              ("ROUNDEDCORNERS", [8, 8, 8, 8]), ("LINEBELOW", (0, 1), (-1, -2), 0.4, SAGE_LIGHT)]
        for i in range(1, len(rows)):
            st.append(("BACKGROUND", (0, i), (-1, i), white if i % 2 else SAGE_PANEL))
        t.setStyle(TableStyle(st))
        out = [SectionTitle("Plan", mp.get("title", "Your week on a plate"), "carrot"), Spacer(1, 12)]
        if mp.get("intro"):
            out += [Paragraph(rich(mp["intro"]), S["desc"]), Spacer(1, 10)]
        out.append(t)
        if mp.get("prep_ahead"):
            out += [Spacer(1, 14), boxed([Paragraph("PREP AHEAD", S["boxh"])] +
                                         [Paragraph("• " + rich(p), S["box"]) for p in mp["prep_ahead"]])]
        return out

    def shopping(self):
        S = self.S
        grouped = shopping_list.build(self.recipes)
        icons = {"Produce": "carrot", "Protein & Dairy": "tofu", "Grains & Pasta": "grains", "Beans & Legumes": "chickpea",
                 "Nuts & Seeds": "pea", "Spices": "chili", "Pantry": "lemon", "Other": "leaf"}
        out = []
        for aisle, items in grouped.items():
            block = [AisleHead(aisle, icons.get(aisle, "leaf"))]
            for it in items:
                q = f" <font color='#77736A'>— {escape(clean(it['qty']))}</font>" if it["qty"] else ""
                block.append(CheckItem(rich(it["item"]) + q, S["check"]))
            block.append(Spacer(1, 8))
            out.append(KeepTogether(block[:4]))
            out.extend(block[4:])
        return out

    def draw_shop_header(self, c, doc):
        page_bg(c, doc)
        M, H, W = self.M, self.H, self.W
        ill.place(c, "tomato", M + 14, H - M - 32, 32, -10)
        c.setFillColor(OLIVE)
        c.setFont(SANS_M, 7.5)
        c.drawString(M + 40, H - M - 18, "MARKET")
        c.setFillColor(FOREST)
        c.setFont(SERIF_B, 25)
        c.drawString(M + 40, H - M - 44, "Shopping list")
        c.setFillColor(MUTED)
        c.setFont(SANS, 7.8)
        c.drawRightString(W - M, H - M - 44, "Combined across every recipe  ·  salt, pepper & water assumed")
        c.setStrokeColor(SAGE)
        c.setLineWidth(0.6)
        c.line(M, H - M - 58, W - M, H - M - 58)
        footer(c, doc)

    def notes(self):
        S = self.S
        out = [SectionTitle("Good to know", "Diet guide & notes", "spinach"), Spacer(1, 10)]
        diets = []
        for r in self.recipes:
            for d in self.recipe_diets(r):
                if d not in diets:
                    diets.append(d)
        for d in diets or list(self.rules):
            rule = self.rules[d]
            out.append(DietRow(rule, S))
            out.append(Spacer(1, 6))
        prof = self.profile or {}
        if prof.get("allergies") or prof.get("dislikes"):
            bits = []
            if prof.get("allergies"):
                bits.append("<b>Allergies avoided:</b> " + escape(", ".join(prof["allergies"])))
            if prof.get("dislikes"):
                bits.append("<b>Dislikes avoided:</b> " + escape(", ".join(prof["dislikes"])))
            out += [Spacer(1, 6), boxed([Paragraph("FROM YOUR PROFILE", S["boxh"])] + [Paragraph(b, S["box"]) for b in bits])]
        if self.meta.get("notes"):
            out += [Spacer(1, 10), Paragraph(rich(self.meta["notes"]), S["body"])]
        out += [Spacer(1, 16), Paragraph(
            "Recipes were checked against the Green Plate ingredient rules before printing. Rules are a cooking aid, "
            "not medical advice: always read labels for hidden allergens, and if you follow a low-FODMAP diet for IBS, "
            "work with a dietitian and confirm serving sizes in the Monash University FODMAP app.", S["small"])]
        return out

    # ---- assemble ----------------------------------------------------------
    def build(self, out_path: str, want_shopping: Optional[bool] = None):
        self.want_shopping = (len(self.recipes) > 1) if want_shopping is None else want_shopping
        # pass 1 collects page numbers, pass 2 prints them in the contents
        for _ in range(2):
            buf = io.BytesIO()
            self._build_once(buf)
        Path(out_path).write_bytes(buf.getvalue())

    def _build_once(self, fh):
        W, H, M = self.W, self.H, self.M
        doc = BaseDocTemplate(fh, pagesize=self.size, leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=54,
                              title=self.title, author="Green Plate", subject="Plant-based recipes")
        doc.book_title = self.title
        bottom = 54
        full = Frame(M, bottom, W - 2 * M, H - M - bottom, id="full", leftPadding=0, rightPadding=0)
        templates = [
            PageTemplate("cover", [Frame(M, bottom, W - 2 * M, H - M - bottom, id="c")], onPage=self.draw_cover),
            PageTemplate("plain", [full], onPage=lambda c, d: (page_bg(c, d), footer(c, d))),
        ]
        col_w = (W - 2 * M - 28) / 2
        shop_top = H - M - 70
        templates.append(PageTemplate("shop", [
            Frame(M, bottom, col_w, shop_top - bottom, id="s1", leftPadding=0, rightPadding=0),
            Frame(M + col_w + 28, bottom, col_w, shop_top - bottom, id="s2", leftPadding=0, rightPadding=0)],
            onPage=self.draw_shop_header))
        story: List[Any] = []
        if self.has_cover:
            story += [Spacer(1, 1), NextPageTemplate("plain"), PageBreak()] + self.contents()
        left_w = 186
        gap = 22
        for i, r in enumerate(self.recipes):
            hp = self.header_parts(r, i)
            ftop = H - M - hp["height"] - 18
            fh_ = ftop - bottom
            lf = Frame(M + 12, bottom, left_w - 24, fh_ - 12, id=f"l{i}", leftPadding=0, rightPadding=0, topPadding=12)
            rf = Frame(M + left_w + gap, bottom, W - 2 * M - left_w - gap, fh_, id=f"rt{i}", leftPadding=0, rightPadding=0)

            def on_recipe(c, d, r=r, i=i, hp=hp, ftop=ftop):
                self.draw_header(c, d, r, i, hp)
                self.draw_panel(c, M, bottom + 4, left_w, ftop - bottom - 4)

            cont_top = H - M - 26
            cf = Frame(M, bottom, W - 2 * M, cont_top - bottom, id=f"cf{i}", leftPadding=0, rightPadding=0)
            templates.append(PageTemplate(f"r{i}", [lf, rf], onPage=on_recipe))
            templates.append(PageTemplate(f"c{i}", [cf], onPage=lambda c, d, r=r: self.draw_cont(c, d, r)))
            if story:
                story += [NextPageTemplate(f"r{i}"), PageBreak()]
            else:  # very first page
                templates.insert(0, templates.pop())   # c{i}
                templates.insert(0, templates.pop())   # r{i} becomes the first template
            story += [NextPageTemplate(f"c{i}"), Marker(f"r{i}", self.pages)]
            ing = self.ingredient_flowables(r)
            avail = fh_ - 12 - 12 - 6
            used = self._height(ing, left_w - 24)
            in_panel, overflow = [], []
            for block in self.side_flowables(r):  # fill the panel greedily, keep order
                h = self._height(block, left_w - 24)
                if not overflow and used + h <= avail:
                    in_panel += block
                    used += h
                else:
                    overflow += block
            story += ing + in_panel + [FrameBreak()] + self.method_flowables(r) + overflow
        tail = []
        if self.meta.get("meal_plan"):
            tail += [NextPageTemplate("plain"), PageBreak(), Marker("mealplan", self.pages)] + self.meal_plan()
        if self.want_shopping:
            tail += [NextPageTemplate("shop"), PageBreak(), Marker("shopping", self.pages)] + self.shopping()
        if self.has_cover:
            tail += [NextPageTemplate("plain"), PageBreak(), Marker("notes", self.pages)] + self.notes()
        story += tail
        doc.addPageTemplates(templates)
        doc.build(story)


class AisleHead(Flowable):
    def __init__(self, text, icon):
        super().__init__()
        self.text, self.icon = text, icon

    def wrap(self, aw, ah):
        self.aw = aw
        return aw, 26

    def draw(self):
        c = self.canv
        ill.place(c, self.icon, 9, 11, 18, -10)
        c.setFillColor(FOREST)
        c.setFont(SERIF_B, 13)
        c.drawString(26, 6, self.text)
        c.setStrokeColor(SAGE_LIGHT)
        c.setLineWidth(0.6)
        c.line(26 + pdfmetrics.stringWidth(self.text, SERIF_B, 13) + 8, 10, self.aw, 10)


class DietRow(Flowable):
    def __init__(self, rule, S):
        super().__init__()
        self.rule = rule
        self.para = Paragraph(rich(rule["description"]), S["body"])

    def wrap(self, aw, ah):
        self.aw = aw
        _, h = self.para.wrap(aw - 110, ah)
        self.h = max(h, 18) + 4
        return aw, self.h

    def draw(self):
        c = self.canv
        pill(c, 0, self.h - 18, self.rule["label"], HexColor(self.rule["color"]), size=7.6, h=16)
        self.para.drawOn(c, 110, self.h - 4 - self.para.height + 2)


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="recipe or cookbook JSON")
    ap.add_argument("-o", "--out", help="output PDF path (default: next to the JSON)")
    ap.add_argument("--paper", choices=["cream", "white"], default="cream", help="page colour (white saves ink)")
    ap.add_argument("--size", choices=["letter", "a4"], default="letter")
    ap.add_argument("--shopping-list", dest="shopping", action="store_true", default=None)
    ap.add_argument("--no-shopping-list", dest="shopping", action="store_false")
    ap.add_argument("--force", action="store_true", help="render even if the diet check fails")
    ap.add_argument("--no-profile", action="store_true", help="ignore the saved diet profile")
    args = ap.parse_args(argv)

    src = Path(args.file)
    try:
        doc = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {src}: {exc}", file=sys.stderr)
        return 2
    rules = load_diets()
    profile = None if args.no_profile else load_profile()

    reports = [check_recipe(r, profile=profile, rules=rules) for r in recipes_in(doc)]
    if not all(r["ok"] for r in reports):
        print(format_report(reports, rules), file=sys.stderr)
        if not args.force:
            print("\nDiet check failed — fix the recipes (or pass --force).", file=sys.stderr)
            return 1
        print("\n--force given: rendering anyway.", file=sys.stderr)

    register_fonts()
    out = Path(args.out) if args.out else src.with_suffix(".pdf")
    book = Book(doc, paper=args.paper, size=A4 if args.size == "a4" else letter, profile=profile, rules=rules)
    book.base_dir = src.resolve().parent
    book.build(str(out), want_shopping=args.shopping)
    print(f"Wrote {out}  ({len(book.recipes)} recipe(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
