---
name: plant-recipes
description: Creates vegetarian and vegan recipes that satisfy several dietary restrictions at once (low-FODMAP, gluten-free, nut-free, Jain, sattvic), checks every ingredient with a rules engine, and delivers them as an illustrated PDF cookbook. Use when the user asks for a recipe, "something to cook", "dinner ideas", a recipe adapted to their diet, a "vegan low-FODMAP" dish, "make this recipe Jain", or a recipe PDF/cookbook.
---

# Plant Recipes → illustrated PDF

Turn a recipe request into checked, diet-safe recipes and a beautiful PDF.

## Workflow

1. **Work out the constraints.**
   - Read the SessionStart context for the saved profile (diets, allergies, dislikes, household size, units, time limit). If the user has no profile and mentions restrictions, offer once to save them with the `diet-profile` skill.
   - Merge the profile with what the user asks for in this message. The request wins on conflicts, but never drop an allergy.
   - Supported diets: `vegetarian`, `vegan`, `low-fodmap`, `gluten-free`, `nut-free`, `jain`, `sattvic`. Vegan and Jain automatically include vegetarian.
   - If the diets are unclear and nothing is saved, ask one short question; otherwise default to vegetarian.

2. **Design the recipe(s) with the rules in mind.** Load `diet-rules` (or read `${CLAUDE_PLUGIN_ROOT}/skills/diet-rules/references/diet-cheatsheet.md`) when combining diets, so swaps are chosen up front:
   - low-FODMAP: garlic-infused oil instead of garlic, spring onion **green parts only**, firm tofu (not silken), canned and rinsed legumes in small portions, maple syrup instead of honey or agave.
   - gluten-free: tamari instead of soy sauce, gluten-free asafoetida, certified gluten-free oats, rice or corn noodles.
   - Jain: no onion, garlic, potato, carrot, beet, radish or fresh ginger. Use asafoetida and dry ginger powder.
   - Write ingredient names the way the checker reads them. Label safe variants explicitly, for example "tamari (gluten-free)", "spring onion, green parts only", "rolled oats (certified gluten-free)", "garlic-infused oil".
   - Make real, tested-feeling recipes: concrete quantities, times, temperatures and doneness cues. Give approximate nutrition per serving and say it is approximate.

3. **Write the JSON.** Save it to the working folder as `<slug>.json`, following `references/recipe-schema.md`. Use a single recipe object for one dish, or a cookbook object (`title`, `subtitle`, `diets`, `recipes`, optional `meal_plan`, `intro`, `for`) for several dishes. Include `swaps` explaining every substitution you made for a diet; they appear in the PDF as "Diet swaps used".

4. **Check it.**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_recipe.py" <file>.json
   ```
   - `✗` lines are violations. Fix them with the suggested swap and re-run. Never hand-wave a violation.
   - `!` lines are portion or label notes. Keep them; the PDF prints them as "Portion notes".
   - The PostToolUse hook runs this check automatically after each save and reports failures back.
   - To quickly test one ingredient: `check_recipe.py --ingredient "miso" --diets gluten-free,low-fodmap`.

5. **Render the PDF.**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_pdf.py" <file>.json -o <file>.pdf
   ```
   Options:
   - `--paper white` saves ink when printing.
   - `--size a4` uses A4 paper.
   - `--shopping-list` / `--no-shopping-list` turn the shopping list on or off. It is on by default when there are several recipes.

   If ReportLab is missing, run `pip install reportlab` (add `--break-system-packages` if pip refuses).

   The PreToolUse hook blocks a render whose recipes fail the check. Use `--force` only if the user explicitly accepts the deviation, and mention that in your reply.

6. **Deliver.** Share the PDF (and the JSON, if the user may want to edit it). Reply in one or two sentences: what's in it and which diets it meets. Mention any portion notes that matter, such as the low-FODMAP lentil serve.

## PDF design (automatic)

- **Cover:** a deep-green panel of scattered vegetable illustrations, with the title, subtitle and diet badges.
- **Contents:** recipe titles with page numbers.
- **Recipe pages:** an illustrated bowl hero made from the recipe's ingredients, meta chips, diet badges, a sage ingredients panel with nutrition and notes, and numbered method steps.
- **Extra pages:** a meal-plan table, a two-column shopping list combined across recipes, and a diet guide.
- **Photos:** to use a real photo instead of the drawn bowl, set `"image": "path/to/photo.jpg"` on a recipe. The path is relative to the JSON file.

## Safety and honesty

- Low-FODMAP depends on portion size. Point to the Monash University FODMAP app, and say a dietitian should guide the elimination phase.
- For allergies, remind the user to read labels: asafoetida, stock cubes, miso and curry pastes often hide wheat.
- Never present nutrition numbers as exact.
