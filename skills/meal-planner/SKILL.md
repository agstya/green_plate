---
name: meal-planner
description: Plans a week (or any number of days) of vegetarian/vegan meals that respect the user's dietary restrictions, with batch-cooking, leftovers and a combined aisle-sorted shopping list, delivered as an illustrated PDF cookbook. Use when the user asks for a "meal plan", "weekly menu", "what should I cook this week", "meal prep", or a "shopping list" for their diet.
---

# Meal planner

Build a realistic week of meals that respects the user's diets, then render it as a PDF with recipes, a plan table and a shopping list.

## Steps

1. **Constraints.** Take diets, allergies, household size and time limits from the saved profile (SessionStart context) plus this request. If the following aren't stated, assume them and say so in the reply:
   - 7 days
   - breakfast, lunch and dinner
   - lunch is the previous night's leftovers
2. **Pick a small recipe set.** Use 3–5 core recipes (one breakfast and two to four dinners) and reuse them through batch cooking and leftovers. Nobody cooks 21 distinct meals. Balance:
   - **Protein at every meal:** tofu or tempeh, legumes within FODMAP limits, dairy if allowed, seeds.
   - **Colour:** at least two vegetable colours per dinner.
   - **Effort:** one "project" recipe at most; the rest under 40 minutes.
   - **Shared ingredients**, so the shopping list stays short. For example, one bunch of cilantro should feed two recipes.
3. **Write a cookbook JSON** (schema: `${CLAUDE_PLUGIN_ROOT}/skills/plant-recipes/references/recipe-schema.md`):
   - full `recipes`
   - book-level `diets`
   - a `meal_plan` with `days`, `columns` and a `prep_ahead` list (what to cook on Sunday or Wednesday)
4. **Check:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_recipe.py" plan.json`. Fix every `✗`.
5. **Preview the shopping list** (optional): `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shopping_list.py" plan.json`. Adjust quantities if something looks off, for example 3 lemons where 1 would do.
6. **Render:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_pdf.py" plan.json -o plan.pdf`. This produces the cover, contents, recipes, week table, two-column shopping list and diet guide.
7. **Deliver** the PDF with a one-line summary: how many recipes, which diets, and roughly how much cooking time per week.

## Recurring plans

If the user wants a fresh plan every week, offer to set up a scheduled task that runs this skill each weekend. Vary the cuisines from week to week, and keep a short history in the working folder so recipes don't repeat within 3 weeks.
