---
name: diet-profile
description: Saves, shows or updates the user's Green Plate diet profile — diets (vegan, low-FODMAP, gluten-free, nut-free, Jain, sattvic), allergies, dislikes, household size, favourite cuisines, units and time limit — so every future recipe respects it automatically. Use when the user says "I'm vegan", "remember I can't eat X", "set up my diet", "update my profile", "what restrictions do you have for me?" or "forget my diet settings".
---

# Diet profile

The profile is a small JSON file at `~/.green-plate/profile.json`; the `GREEN_PLATE_PROFILE` environment variable overrides the location. Three things use it:

- The SessionStart hook loads it into every session.
- `check_recipe.py` treats its **allergies** as hard violations and its **dislikes** as warnings.
- `render_pdf.py` uses it for the "Made for …" line on the cover and the diet-guide page.

## Commands

```bash
P="${CLAUDE_PLUGIN_ROOT}/scripts/profile.py"
python3 "$P" show
python3 "$P" set --name "Agastya" --diets vegan,low-fodmap,gluten-free \
                 --allergies sesame --dislikes okra,eggplant \
                 --household 2 --cuisines indian,thai,mediterranean --units us --max-minutes 40
python3 "$P" reset
```

Each `set` flag replaces only that field; fields you leave out are kept. Lists are comma-separated.

## How to run the conversation

1. If the user hasn't given details, ask in one round (use AskUserQuestion when it's available):
   - **Diets:** offer all seven; several can be selected.
   - **Allergies or intolerances:** free text.
   - **Household size and usual time per meal.**
2. Save the answers with the command above, then confirm in one sentence what was stored.
3. Allergy terms are matched as whole words against ingredient names, so store simple nouns: "sesame", "soy", "mustard", "celery".
4. For a medical diet such as low-FODMAP for IBS or gluten-free for coeliac disease, add one gentle line: the plugin is a cooking aid, and a dietitian should guide the diet.
