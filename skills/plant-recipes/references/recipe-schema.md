# Recipe JSON schema

A file can contain any of three shapes:

- **one recipe**: a recipe object, as below.
- **a list of recipes**: `[recipe, recipe, …]`
- **a cookbook**: the object below. Its `diets` apply to every recipe in it.

```json
{
  "title": "Calm-Belly Plant Kitchen",
  "subtitle": "Four vegan, low-FODMAP, gluten-free dinners",
  "kicker": "A Green Plate cookbook",
  "for": "Agastya",
  "diets": ["vegan", "low-fodmap", "gluten-free"],
  "intro": "One or two sentences shown on the contents page.",
  "notes": "Optional paragraph for the diet-guide page.",
  "recipes": [ ... ],
  "meal_plan": {
    "title": "A calm-belly week",
    "intro": "Cook twice, eat all week.",
    "columns": ["breakfast", "lunch", "dinner"],
    "days": [{"day": "Mon", "breakfast": "…", "lunch": "…", "dinner": "…", "snack": "…"}],
    "prep_ahead": ["Sunday: cook the curry and rice."]
  }
}
```

## Recipe

| field | type | notes |
|---|---|---|
| `title` | string | **required** |
| `description` | string | 1–2 sentences, shown in italics under the title |
| `cuisine`, `course` | string | shown in the small kicker line |
| `serves` | number | |
| `prep_min`, `cook_min` | number | |
| `difficulty` | string | e.g. easy / medium / project |
| `diets` | string[] | any of `vegetarian vegan low-fodmap gluten-free nut-free jain sattvic` (aliases like `gf`, `lowfodmap` work) |
| `ingredients` | list | **required**, see below |
| `steps` | string[] | **required**; `**bold**` and `*italic*` are supported |
| `swaps` | list of `{from, to, why}` | the substitutions you made for the diets |
| `tips` | string[] | printed as "Cook's notes" |
| `nutrition` | `{calories, protein_g, carbs_g, fat_g, fiber_g}` | approximate, per serving |
| `illustration` | string[] | optional icon override, e.g. `["tofu","tomato","spinach","lemon"]` |
| `bowl` | string | hero bowl colour: `green warm red cream golden` |
| `image` | path | real photo used in the hero circle instead of the drawing |

### Ingredients

Use flat items with an optional `group`:

```json
{"group": "Sauce", "item": "tamari (gluten-free)", "qty": "2 tbsp", "note": "or coconut aminos", "optional": false, "aisle": "Pantry"}
```

or explicit groups: `{"group": "Sauce", "items": [ {...}, {...} ]}`. Plain strings also work.

- `item`: the ingredient name. The diet checker reads this field, so name the safe variants explicitly.
- `qty`: free text. Leading numbers and fractions (`1 1/2 cups`, `400 g`, `½ tsp`) are added up across recipes in the shopping list.
- `aisle`: optional shopping-list aisle. If omitted it is guessed. Aisles: Produce, Protein & Dairy, Grains & Pasta, Beans & Legumes, Nuts & Seeds, Spices, Pantry, Other.
- `ok_for`: optional list of diets. It turns a rule match into a warning for an item you have verified, for example a certified product. Use it sparingly and explain why in `note`.

Illustration icons available: tomato, carrot, pea, lemon, lime, chili, avocado, eggplant, chickpea, tofu, pepper, zucchini, grains, spinach, sprig, leaf, berries, pumpkin.
