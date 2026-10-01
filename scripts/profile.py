#!/usr/bin/env python3
"""Read or update the Green Plate diet profile (~/.green-plate/profile.json).

  python3 profile.py show
  python3 profile.py set --name "Agastya" --diets vegan,low-fodmap --allergies sesame \
                         --dislikes okra --household 2 --cuisines indian,thai --units metric
  python3 profile.py reset

Set GREEN_PLATE_PROFILE to use a different file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gp_common import canonical_diet, load_profile, profile_path  # noqa: E402

DEFAULT = {"name": "", "diets": ["vegetarian"], "allergies": [], "dislikes": [],
           "household": 2, "cuisines": [], "units": "us", "max_minutes": None, "notes": ""}


def _list(s: str):
    return [x.strip() for x in s.split(",") if x.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("reset")
    s = sub.add_parser("set")
    s.add_argument("--name")
    s.add_argument("--diets")
    s.add_argument("--allergies")
    s.add_argument("--dislikes")
    s.add_argument("--household", type=int)
    s.add_argument("--cuisines")
    s.add_argument("--units", choices=["us", "metric"])
    s.add_argument("--max-minutes", type=int)
    s.add_argument("--notes")
    args = ap.parse_args(argv)

    path = profile_path()
    if args.cmd == "show":
        prof = load_profile()
        print(json.dumps(prof, indent=2) if prof else f"No profile yet at {path}. Create one with: profile.py set --diets ...")
        return 0
    if args.cmd == "reset":
        if path.exists():
            path.unlink()
        print(f"Removed {path}")
        return 0

    prof = load_profile() or dict(DEFAULT)
    if args.name is not None:
        prof["name"] = args.name
    if args.diets is not None:
        try:
            prof["diets"] = list(dict.fromkeys(canonical_diet(d) for d in _list(args.diets)))
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    for key in ("allergies", "dislikes", "cuisines"):
        val = getattr(args, key)
        if val is not None:
            prof[key] = _list(val)
    if args.household is not None:
        prof["household"] = args.household
    if args.units is not None:
        prof["units"] = args.units
    if args.max_minutes is not None:
        prof["max_minutes"] = args.max_minutes
    if args.notes is not None:
        prof["notes"] = args.notes

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prof, indent=2), encoding="utf-8")
    print(f"Saved profile to {path}")
    print(json.dumps(prof, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
