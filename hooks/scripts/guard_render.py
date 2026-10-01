#!/usr/bin/env python3
"""PreToolUse hook (Bash): block `render_pdf.py` when the recipes break their diets.

The renderer checks too, but stopping here gives Claude the full report before it runs
anything. `--force` in the command skips the guard (the user explicitly asked for it).
Exit code 2 + stderr = block the tool call and show the reason to Claude.
"""
import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from gp_common import check_recipe, format_report, load_diets, load_profile, recipes_in  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (payload.get("tool_input") or {}).get("command", "")
    if "render_pdf.py" not in cmd or "--force" in cmd:
        return 0
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    json_args = [t for t in tokens if t.endswith(".json")]
    rules = load_diets()
    profile = None if "--no-profile" in tokens else load_profile()
    problems = []
    for arg in json_args:
        p = Path(arg).expanduser()
        if not p.is_absolute():
            p = cwd / p
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            reports = [check_recipe(r, profile=profile, rules=rules) for r in recipes_in(doc)]
        except Exception:
            continue  # let the renderer report unreadable files itself
        bad = [r for r in reports if not r["ok"]]
        if bad:
            problems.append(f"{p.name}:\n" + format_report(bad, rules))
    if problems:
        sys.stderr.write("Green Plate blocked the PDF render: these recipes break their declared diets.\n"
                         + "\n".join(problems)
                         + "\nFix the JSON (apply the swaps) and run the render again. Only add --force if the user "
                           "explicitly accepts the deviation.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
