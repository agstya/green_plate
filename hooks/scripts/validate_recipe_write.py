#!/usr/bin/env python3
"""PostToolUse hook (Write|Edit|MultiEdit): re-check recipe JSON right after it is saved.

Only acts on .json files that look like Green Plate recipes (they contain "ingredients"
or a "recipes" list). If a recipe breaks one of its declared diets — or the user's
allergies — the hook returns {"decision": "block", "reason": ...} so Claude sees the
problems and fixes the file before going further. Everything else passes silently.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from gp_common import check_recipe, format_report, load_diets, load_profile, recipes_in  # noqa: E402


def looks_like_recipes(doc) -> bool:
    if isinstance(doc, dict):
        return "ingredients" in doc or isinstance(doc.get("recipes"), list)
    if isinstance(doc, list):
        return bool(doc) and all(isinstance(x, dict) and "ingredients" in x for x in doc)
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path.endswith(".json"):
        return 0
    p = Path(path)
    if not p.is_absolute() and payload.get("cwd"):
        p = Path(payload["cwd"]) / p
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if not looks_like_recipes(doc):
        return 0
    rules = load_diets()
    try:
        reports = [check_recipe(r, profile=load_profile(), rules=rules) for r in recipes_in(doc)]
    except ValueError as exc:  # e.g. unknown diet name
        print(json.dumps({"decision": "block", "reason": f"Green Plate: {exc}"}))
        return 0
    if all(r["ok"] for r in reports):
        return 0
    reason = ("Green Plate diet check failed for " + p.name + ". Fix these ingredients (use the suggested swaps), "
              "then save again:\n" + format_report([r for r in reports if not r["ok"]], rules))
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
