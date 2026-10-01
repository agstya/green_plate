#!/usr/bin/env python3
"""Check recipe JSON against dietary rules.

Usage:
  python3 check_recipe.py recipes.json                 # use diets declared in the file
  python3 check_recipe.py recipes.json --diets vegan,low-fodmap
  python3 check_recipe.py recipes.json --json          # machine-readable report
  python3 check_recipe.py --ingredient "garlic" --diets low-fodmap,jain

Exit code 0 = every recipe passes, 1 = violations or schema problems, 2 = bad input.
Your saved profile (allergies, dislikes, default diets) is applied unless --no-profile.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gp_common import (check_ingredient, check_recipe, expand_diets, format_report,  # noqa: E402
                       load_diets, load_profile, recipes_in)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="recipe / cookbook JSON file")
    ap.add_argument("--diets", default="", help="comma-separated extra diets to enforce")
    ap.add_argument("--ingredient", help="check a single ingredient name instead of a file")
    ap.add_argument("--json", action="store_true", help="print JSON report")
    ap.add_argument("--no-profile", action="store_true", help="ignore ~/.green-plate/profile.json")
    args = ap.parse_args(argv)

    rules = load_diets()
    extra = [d for d in args.diets.split(",") if d.strip()]
    profile = None if args.no_profile else load_profile()

    try:
        if args.ingredient:
            diets = expand_diets(extra or (profile or {}).get("diets", []) or list(rules), rules)
            out = {d: check_ingredient(args.ingredient, d, rules[d]) for d in diets}
            if args.json:
                print(json.dumps(out, indent=2))
            else:
                for d, res in out.items():
                    if res["avoid"]:
                        for v in res["avoid"]:
                            print(f"✗ {rules[d]['label']}: avoid — {v['reason']}. Try: {v['swap']}")
                    elif res["limit"]:
                        for w in res["limit"]:
                            print(f"! {rules[d]['label']}: {w['note']}")
                    else:
                        print(f"✓ {rules[d]['label']}: ok")
            return 1 if any(r["avoid"] for r in out.values()) else 0

        if not args.file:
            ap.error("give a recipe file or --ingredient")
        doc = json.loads(Path(args.file).read_text(encoding="utf-8"))
        reports = [check_recipe(r, extra, profile, rules) for r in recipes_in(doc)]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"ok": all(r["ok"] for r in reports), "recipes": reports}, indent=2, ensure_ascii=False))
    else:
        print(format_report(reports, rules))
        n_bad = sum(not r["ok"] for r in reports)
        print(f"\n{len(reports) - n_bad}/{len(reports)} recipe(s) pass.")
    return 0 if all(r["ok"] for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
