#!/usr/bin/env python3
"""Build a combined, aisle-grouped shopping list from recipe JSON.

  python3 shopping_list.py cookbook.json            # prints markdown
  python3 shopping_list.py cookbook.json --json

Quantities with the same item + unit are added together (e.g. 1 cup + 1/2 cup rice -> 1 1/2 cup).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gp_common import ingredient_text, iter_ingredients, normalise, recipes_in  # noqa: E402

AISLES = OrderedDict([
    ("Produce", ["spinach", "kale", "lettuce", "tomato", "tomatoes", "cucumber", "zucchini", "courgette", "eggplant", "aubergine",
                 "bell pepper", "capsicum", "carrot", "potato", "sweet potato", "pumpkin", "squash", "bok choy", "cabbage",
                 "broccoli", "green beans", "peas", "corn", "lemon", "lime", "orange", "banana", "berries", "strawberries",
                 "blueberries", "kiwi", "pineapple", "avocado", "herbs", "cilantro", "coriander leaves", "parsley", "basil",
                 "mint", "dill", "chives", "ginger", "chili", "chilli", "jalapeno", "spring onion", "scallion", "leek",
                 "okra", "gourd", "radish", "beet", "celery", "fennel", "arugula", "rocket", "curry leaves", "grapes"]),
    ("Protein & Dairy", ["tofu", "tempeh", "paneer", "seitan", "yogurt", "yoghurt", "milk", "cheese", "feta", "butter", "ghee",
                         "cream", "egg", "edamame"]),
    ("Grains & Pasta", ["rice", "quinoa", "oats", "millet", "buckwheat", "pasta", "noodles", "bread", "tortilla", "polenta",
                        "couscous", "flour", "besan", "poha", "vermicelli", "wraps"]),
    ("Beans & Legumes", ["lentil", "lentils", "dal", "chickpea", "chickpeas", "beans", "moong", "toor", "urad", "masoor"]),
    ("Nuts & Seeds", ["almond", "cashew", "walnut", "peanut", "pecan", "pistachio", "seeds", "sesame", "tahini", "flax", "chia",
                      "pumpkin seeds", "sunflower seeds", "coconut flakes", "desiccated coconut"]),
    ("Spices", ["cumin", "turmeric", "coriander", "garam masala", "paprika", "chili flakes", "chilli flakes", "cinnamon",
                "cardamom", "clove", "mustard seeds", "fenugreek", "asafoetida", "hing", "pepper", "salt", "oregano",
                "thyme", "rosemary", "nutmeg", "bay leaf", "curry powder", "smoked paprika", "sumac", "za'atar", "five spice"]),
    ("Pantry", ["oil", "vinegar", "soy sauce", "tamari", "maple syrup", "sugar", "jaggery", "stock", "broth", "coconut milk",
                "tomato paste", "canned", "tinned", "passata", "miso", "mustard", "nutritional yeast", "cornstarch",
                "baking powder", "baking soda", "vanilla", "cocoa", "chocolate", "peanut butter", "sriracha", "curry paste",
                "water", "aminos", "agar"]),
])
STAPLES = {"salt", "water", "black pepper", "pepper", "salt and pepper", "salt & pepper"}

_NUM = re.compile(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(.*)$")
_UNICODE_FRAC = {"½": "1/2", "⅓": "1/3", "⅔": "2/3", "¼": "1/4", "¾": "3/4", "⅛": "1/8"}


def guess_aisle(item: str) -> str:
    text = normalise(item)
    best, best_len = "Other", 0
    for aisle, words in AISLES.items():
        for w in words:
            if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text) and len(w) > best_len:
                best, best_len = aisle, len(w)
    return best


def parse_qty(qty: Any):
    if qty is None or qty == "":
        return None, ""
    if isinstance(qty, (int, float)):
        return Fraction(qty).limit_denominator(16), ""
    s = str(qty)
    for k, v in _UNICODE_FRAC.items():
        s = s.replace(k, " " + v)
    m = _NUM.match(s)
    if not m:
        return None, s.strip()
    num_s, unit = m.group(1).strip(), m.group(2).strip()
    total = sum(Fraction(p) for p in num_s.split())
    return total, unit


def fmt_qty(val: Fraction, unit: str) -> str:
    if val is None:
        return unit
    whole, rem = divmod(val.numerator, val.denominator)
    if rem == 0:
        s = str(whole)
    else:
        frac = Fraction(rem, val.denominator).limit_denominator(8)
        s = (f"{whole} " if whole else "") + f"{frac.numerator}/{frac.denominator}"
    return f"{s} {unit}".strip()


def build(recipes: List[Dict[str, Any]]) -> "OrderedDict[str, List[Dict[str, str]]]":
    merged: Dict[tuple, Dict[str, Any]] = OrderedDict()
    for r in recipes:
        for ing in iter_ingredients(r):
            item = ingredient_text(ing).strip()
            if not item or normalise(item) in STAPLES:
                continue
            qty = ing.get("qty", "") if isinstance(ing, dict) else ""
            aisle = (ing.get("aisle") if isinstance(ing, dict) else None) or guess_aisle(item)
            val, unit = parse_qty(qty)
            key = (normalise(item), unit.lower() if val is not None else f"__{qty}")
            if key in merged and val is not None and merged[key]["val"] is not None:
                merged[key]["val"] += val
            elif key in merged:
                continue
            else:
                merged[key] = {"item": item, "val": val, "unit": unit, "aisle": aisle.title() if aisle.islower() else aisle,
                               "raw": str(qty)}
            merged[key].setdefault("recipes", set()).add(r.get("title", ""))
    order = list(AISLES) + ["Other"]
    grouped: "OrderedDict[str, List[Dict[str, str]]]" = OrderedDict()
    for entry in sorted(merged.values(), key=lambda e: (order.index(e["aisle"]) if e["aisle"] in order else 99, e["item"].lower())):
        qty_txt = fmt_qty(entry["val"], entry["unit"]) if entry["val"] is not None else entry["raw"]
        grouped.setdefault(entry["aisle"], []).append({"item": entry["item"], "qty": qty_txt,
                                                       "used_in": sorted(t for t in entry["recipes"] if t)})
    return grouped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = json.loads(Path(args.file).read_text(encoding="utf-8"))
    grouped = build(recipes_in(doc))
    if args.json:
        print(json.dumps(grouped, indent=2, ensure_ascii=False))
    else:
        for aisle, items in grouped.items():
            print(f"## {aisle}")
            for it in items:
                print(f"- [ ] {it['item']}" + (f" — {it['qty']}" if it["qty"] else ""))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
