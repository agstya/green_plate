#!/usr/bin/env python3
"""SessionStart hook: tell Claude about the user's saved diet profile (if any).

Prints a JSON object whose additionalContext is injected into the session. Never fails
the session: any error results in a silent exit 0.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

try:
    from gp_common import load_diets, load_profile, profile_path
except Exception:  # pragma: no cover
    sys.exit(0)


def main() -> int:
    try:
        sys.stdin.read()  # payload not needed, but drain it
    except Exception:
        pass
    try:
        prof = load_profile()
        rules = load_diets()
    except Exception:
        return 0
    if prof:
        diets = ", ".join(rules.get(d, {}).get("label", d) for d in prof.get("diets", [])) or "none set"
        bits = [f"Green Plate diet profile ({profile_path()}): diets = {diets}"]
        if prof.get("allergies"):
            bits.append("allergies = " + ", ".join(prof["allergies"]))
        if prof.get("dislikes"):
            bits.append("dislikes = " + ", ".join(prof["dislikes"]))
        if prof.get("household"):
            bits.append(f"cooks for {prof['household']}")
        if prof.get("cuisines"):
            bits.append("likes " + ", ".join(prof["cuisines"]))
        if prof.get("max_minutes"):
            bits.append(f"prefers recipes under {prof['max_minutes']} min")
        if prof.get("units"):
            bits.append(f"units = {prof['units']}")
        msg = "; ".join(bits) + ". Apply these to every recipe request unless the user says otherwise."
    else:
        msg = ("Green Plate is installed but no diet profile is saved yet. If the user asks for recipes, "
               "offer to save their diets/allergies with the diet-profile skill.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
