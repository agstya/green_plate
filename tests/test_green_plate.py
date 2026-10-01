"""Tests for the Green Plate plugin: diet rules, shopping list, hooks and PDF rendering.

Run:  python3 -m pytest -q
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["GREEN_PLATE_PROFILE"] = str(ROOT / "tests" / "_no_profile.json")

from gp_common import check_ingredient, check_recipe, expand_diets, load_diets  # noqa: E402
import shopping_list  # noqa: E402

RULES = load_diets()


def avoid(name, diet):
    return bool(check_ingredient(name, diet, RULES[diet])["avoid"])


def limit(name, diet):
    return bool(check_ingredient(name, diet, RULES[diet])["limit"])


# ---------------------------------------------------------------- rules
@pytest.mark.parametrize("name,diet", [
    ("garlic", "low-fodmap"), ("2 cloves garlic, minced", "low-fodmap"), ("red onion", "low-fodmap"),
    ("honey", "vegan"), ("paneer", "vegan"), ("ghee", "vegan"), ("eggs", "vegan"),
    ("soy sauce", "gluten-free"), ("all-purpose flour", "gluten-free"), ("semolina", "gluten-free"),
    ("cashews", "nut-free"), ("peanut butter", "nut-free"), ("basil pesto", "nut-free"),
    ("potato", "jain"), ("fresh ginger", "jain"), ("ginger-garlic paste", "jain"), ("mushrooms", "sattvic"),
    ("fish sauce", "vegetarian"), ("parmesan", "vegetarian"), ("gelatin", "vegetarian"),
])
def test_avoid(name, diet):
    assert avoid(name, diet)


@pytest.mark.parametrize("name,diet", [
    ("garlic-infused oil", "low-fodmap"), ("spring onion, green parts only", "low-fodmap"),
    ("firm tofu", "low-fodmap"), ("almond milk", "low-fodmap"),
    ("peanut butter", "vegan"), ("coconut milk", "vegan"), ("vegan butter", "vegan"), ("eggplant", "vegan"),
    ("butternut squash", "vegan"), ("cream of tartar", "vegan"),
    ("tamari (gluten-free)", "gluten-free"), ("rice flour", "gluten-free"), ("buckwheat", "gluten-free"),
    ("flat rice noodles", "gluten-free"), ("gluten-free pasta", "gluten-free"),
    ("coconut", "nut-free"), ("nutmeg", "nut-free"), ("butternut squash", "nut-free"),
    ("dry ginger powder", "jain"), ("turmeric powder", "jain"), ("tomatoes", "jain"),
    ("carrot", "sattvic"), ("vegetable stock", "vegetarian"),
])
def test_allowed(name, diet):
    assert not avoid(name, diet)


def test_portion_limits():
    assert limit("canned lentils, drained", "low-fodmap")
    assert limit("chickpeas", "low-fodmap")
    assert limit("coconut milk", "low-fodmap")
    assert not limit("almond milk", "low-fodmap")
    assert limit("rolled oats", "gluten-free")


def test_vegan_implies_vegetarian():
    assert expand_diets(["vegan"], RULES) == ["vegan", "vegetarian"]
    assert "vegetarian" in expand_diets(["jain"], RULES)


def test_unknown_diet():
    with pytest.raises(ValueError):
        expand_diets(["paleo"], RULES)


def test_profile_allergy_is_violation():
    recipe = {"title": "t", "diets": ["vegan"], "ingredients": [{"item": "sesame oil"}], "steps": ["cook"]}
    rep = check_recipe(recipe, profile={"allergies": ["sesame"], "dislikes": []})
    assert not rep["ok"] and rep["violations"][0]["diet"] == "allergy"


def test_ok_for_override_downgrades_to_warning():
    recipe = {"title": "t", "diets": ["gluten-free"], "steps": ["x"],
              "ingredients": [{"item": "soba noodles", "ok_for": ["gluten-free"], "note": "100% buckwheat"}]}
    rep = check_recipe(recipe)
    assert rep["ok"] and rep["warnings"]


def test_schema_problems():
    rep = check_recipe({"title": "", "ingredients": [], "steps": []})
    assert not rep["ok"] and len(rep["schema"]) >= 3


@pytest.mark.parametrize("example", sorted((ROOT / "examples").glob("*.json")))
def test_examples_pass(example):
    out = subprocess.run([sys.executable, str(SCRIPTS / "check_recipe.py"), str(example)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


# ---------------------------------------------------------------- shopping list
def test_shopping_list_merges_quantities():
    recipes = [
        {"title": "a", "ingredients": [{"item": "basmati rice", "qty": "1 cup"}, {"item": "lime", "qty": "1"}]},
        {"title": "b", "ingredients": [{"item": "Basmati rice", "qty": "1/2 cup"}, {"item": "salt"}]},
    ]
    grouped = shopping_list.build(recipes)
    rice = [i for i in grouped["Grains & Pasta"] if "rice" in i["item"].lower()][0]
    assert rice["qty"] == "1 1/2 cup"
    assert all(i["item"] != "salt" for items in grouped.values() for i in items)


# ---------------------------------------------------------------- hooks
def run_hook(script, payload):
    return subprocess.run([sys.executable, str(ROOT / "hooks" / "scripts" / script)], input=json.dumps(payload),
                          capture_output=True, text=True)


def test_post_write_hook_blocks_bad_recipe(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"title": "Garlic Pasta", "diets": ["low-fodmap", "vegan"], "steps": ["cook"],
                               "ingredients": [{"item": "garlic"}, {"item": "parmesan"}]}))
    out = run_hook("validate_recipe_write.py", {"tool_name": "Write", "tool_input": {"file_path": str(bad)}})
    res = json.loads(out.stdout)
    assert res["decision"] == "block" and "garlic" in res["reason"]


def test_post_write_hook_ignores_other_json(tmp_path):
    f = tmp_path / "package.json"
    f.write_text('{"name": "x"}')
    out = run_hook("validate_recipe_write.py", {"tool_name": "Write", "tool_input": {"file_path": str(f)}})
    assert out.returncode == 0 and out.stdout.strip() == ""


def test_guard_blocks_render(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"title": "x", "diets": ["jain"], "ingredients": [{"item": "potato"}], "steps": ["s"]}))
    cmd = f"python3 scripts/render_pdf.py {bad} -o out.pdf"
    out = run_hook("guard_render.py", {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(tmp_path)})
    assert out.returncode == 2 and "potato" in out.stderr
    out = run_hook("guard_render.py", {"tool_name": "Bash", "tool_input": {"command": cmd + " --force"}})
    assert out.returncode == 0


def test_session_start_hook_outputs_context():
    out = run_hook("session_start.py", {"hook_event_name": "SessionStart"})
    ctx = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Green Plate" in ctx


# ---------------------------------------------------------------- rendering
def test_render_pdf(tmp_path):
    pytest.importorskip("reportlab")
    out = tmp_path / "book.pdf"
    res = subprocess.run([sys.executable, str(SCRIPTS / "render_pdf.py"), str(ROOT / "examples" / "calm-belly-week.json"),
                          "-o", str(out)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    data = out.read_bytes()
    assert data.startswith(b"%PDF") and len(data) > 20_000


def test_render_refuses_bad_recipe(tmp_path):
    pytest.importorskip("reportlab")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"title": "x", "diets": ["vegan"], "ingredients": [{"item": "honey"}], "steps": ["s"]}))
    res = subprocess.run([sys.executable, str(SCRIPTS / "render_pdf.py"), str(bad)], capture_output=True, text=True)
    assert res.returncode == 1 and "honey" in res.stderr
