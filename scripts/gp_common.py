"""Shared helpers for the Green Plate plugin: diet rules, profile, recipe checking.

Pure standard library so the hooks run anywhere Python 3.8+ exists.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPTS_DIR.parent
DIETS_FILE = SCRIPTS_DIR / "diets.json"

DIET_ALIASES = {
    "veg": "vegetarian", "vegetarian": "vegetarian", "lacto-vegetarian": "vegetarian",
    "vegan": "vegan", "plant-based": "vegan",
    "low-fodmap": "low-fodmap", "lowfodmap": "low-fodmap", "low fodmap": "low-fodmap", "fodmap": "low-fodmap", "lf": "low-fodmap",
    "gluten-free": "gluten-free", "glutenfree": "gluten-free", "gluten free": "gluten-free", "gf": "gluten-free", "coeliac": "gluten-free", "celiac": "gluten-free",
    "nut-free": "nut-free", "nutfree": "nut-free", "nut free": "nut-free", "nf": "nut-free",
    "jain": "jain",
    "sattvic": "sattvic", "satvik": "sattvic", "satvic": "sattvic",
}


# --------------------------------------------------------------------------- data

def load_diets() -> Dict[str, Any]:
    with open(DIETS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def canonical_diet(name: str) -> str:
    key = str(name).strip().lower().replace("_", "-")
    if key in DIET_ALIASES:
        return DIET_ALIASES[key]
    raise ValueError(f"Unknown diet '{name}'. Known: {', '.join(sorted(set(DIET_ALIASES.values())))}")


def expand_diets(diets: Iterable[str], rules: Dict[str, Any]) -> List[str]:
    """Canonicalise diet names and add implied diets (vegan -> vegetarian)."""
    out: List[str] = []
    stack = [canonical_diet(d) for d in diets]
    while stack:
        d = stack.pop(0)
        if d in out:
            continue
        out.append(d)
        stack.extend(rules[d].get("includes", []))
    return out


def profile_path() -> Path:
    env = os.environ.get("GREEN_PLATE_PROFILE")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".green-plate" / "profile.json"


def load_profile() -> Optional[Dict[str, Any]]:
    p = profile_path()
    if not p.is_file():
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


# --------------------------------------------------------------------------- matching

_PUNCT = re.compile(r"[^\w\s'\-]+")


def normalise(text: str) -> str:
    text = str(text).lower().replace("’", "'")
    text = _PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_re(term: str) -> re.Pattern:
    return re.compile(r"(?<![\w])" + re.escape(normalise(term)) + r"(?![\w])")


_RE_CACHE: Dict[str, re.Pattern] = {}


def _has(text: str, term: str) -> bool:
    pat = _RE_CACHE.get(term)
    if pat is None:
        pat = _RE_CACHE[term] = _word_re(term)
    return bool(pat.search(text))


def _strip(text: str, phrase: str) -> str:
    pat = _RE_CACHE.get("strip::" + phrase)
    if pat is None:
        pat = _RE_CACHE["strip::" + phrase] = _word_re(phrase)
    return pat.sub(" ", text)


def ingredient_text(ing: Any) -> str:
    if isinstance(ing, str):
        return ing
    if isinstance(ing, dict):
        return str(ing.get("item") or ing.get("name") or "")
    return str(ing)


def check_ingredient(name: str, diet: str, rule: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    text = normalise(name)
    original = text
    result: Dict[str, List[Dict[str, str]]] = {"avoid": [], "limit": []}
    if any(_has(text, n) for n in rule.get("neutralizers", [])):
        return result
    # longest phrases first so 'sunflower seed butter' beats 'seed butter'
    for phrase in sorted(rule.get("safe_phrases", []), key=len, reverse=True):
        text = _strip(text, phrase)
    for group in rule.get("avoid", []):
        hits = [t for t in group["terms"] if _has(text, t)]
        if hits:
            result["avoid"].append({"term": max(hits, key=len), "reason": group["reason"], "swap": group.get("swap", "")})
    # portion limits look at the full name (safe phrases only exempt an ingredient from 'avoid')
    for group in rule.get("limit", []):
        if any(_has(original, u) for u in group.get("unless", [])):
            continue
        hits = [t for t in group["terms"] if _has(original, t)]
        if hits:
            result["limit"].append({"term": max(hits, key=len), "note": group["note"]})
    return result


def iter_ingredients(recipe: Dict[str, Any]):
    for ing in recipe.get("ingredients", []) or []:
        if isinstance(ing, dict) and "items" in ing:  # grouped form
            for sub in ing["items"]:
                yield sub
        else:
            yield ing


def schema_problems(recipe: Dict[str, Any]) -> List[str]:
    probs = []
    if not isinstance(recipe, dict):
        return ["recipe must be a JSON object"]
    if not recipe.get("title"):
        probs.append("missing 'title'")
    ings = list(iter_ingredients(recipe))
    if not ings:
        probs.append("missing or empty 'ingredients'")
    for i, ing in enumerate(ings):
        if isinstance(ing, dict) and not (ing.get("item") or ing.get("name")):
            probs.append(f"ingredient #{i + 1} has no 'item'")
    steps = recipe.get("steps")
    if not steps or not isinstance(steps, list):
        probs.append("missing or empty 'steps' list")
    serves = recipe.get("serves")
    if serves is not None and not isinstance(serves, (int, float, str)):
        probs.append("'serves' should be a number")
    return probs


def check_recipe(recipe: Dict[str, Any], extra_diets: Iterable[str] = (), profile: Optional[Dict[str, Any]] = None,
                 rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a report: {title, diets, violations, warnings, schema, ok}."""
    rules = rules or load_diets()
    declared = list(recipe.get("diets", []) or []) + list(extra_diets)
    if profile:
        declared += profile.get("diets", []) or []
    diets = expand_diets(declared, rules) if declared else []

    allergy_terms = [a for a in (profile or {}).get("allergies", []) or [] if a]
    dislike_terms = [a for a in (profile or {}).get("dislikes", []) or [] if a]

    violations, warnings = [], []
    for ing in iter_ingredients(recipe):
        name = ingredient_text(ing)
        ok_for = set()
        if isinstance(ing, dict):
            ok_for = {canonical_diet(d) for d in ing.get("ok_for", []) or []}
        for diet in diets:
            res = check_ingredient(name, diet, rules[diet])
            for v in res["avoid"]:
                entry = {"ingredient": name, "diet": diet, **v}
                if diet in ok_for:
                    warnings.append({**entry, "note": f"Marked ok_for {diet} by author — double-check: {v['reason']}."})
                else:
                    violations.append(entry)
            for w in res["limit"]:
                warnings.append({"ingredient": name, "diet": diet, **w})
        text = normalise(name)
        for a in allergy_terms:
            if _has(text, a):
                violations.append({"ingredient": name, "diet": "allergy", "term": a,
                                   "reason": f"listed as an allergy in your profile", "swap": "remove or replace"})
        for d in dislike_terms:
            if _has(text, d):
                warnings.append({"ingredient": name, "diet": "preference", "term": d,
                                 "note": "You marked this as a dislike in your profile."})

    schema = schema_problems(recipe)
    return {
        "title": recipe.get("title", "(untitled)"),
        "diets": diets,
        "violations": violations,
        "warnings": warnings,
        "schema": schema,
        "ok": not violations and not schema,
    }


def recipes_in(doc: Any) -> List[Dict[str, Any]]:
    """A file may hold one recipe, a list of recipes, or a cookbook {recipes:[...]}."""
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict) and isinstance(doc.get("recipes"), list):
        book_diets = doc.get("diets", []) or []
        out = []
        for r in doc["recipes"]:
            r = dict(r)
            r["diets"] = list(dict.fromkeys(list(r.get("diets", []) or []) + list(book_diets)))
            out.append(r)
        return out
    return [doc]


def format_report(reports: List[Dict[str, Any]], rules: Optional[Dict[str, Any]] = None) -> str:
    rules = rules or load_diets()
    lines = []
    for rep in reports:
        labels = ", ".join(rules[d]["label"] for d in rep["diets"]) or "no diets declared"
        status = "PASS" if rep["ok"] else "FAIL"
        lines.append(f"[{status}] {rep['title']}  —  {labels}")
        for s in rep["schema"]:
            lines.append(f"    ✗ schema: {s}")
        for v in rep["violations"]:
            dl = rules.get(v["diet"], {}).get("label", v["diet"])
            lines.append(f"    ✗ {v['ingredient']!r} breaks {dl}: {v['reason']} (matched '{v['term']}'). Try: {v['swap']}")
        for w in rep["warnings"]:
            dl = rules.get(w["diet"], {}).get("label", w["diet"])
            lines.append(f"    ! {w['ingredient']!r} ({dl}): {w['note']}")
    return "\n".join(lines)
