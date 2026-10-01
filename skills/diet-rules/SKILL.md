---
name: diet-rules
description: Reference knowledge for vegetarian, vegan, low-FODMAP, gluten-free, nut-free, Jain and sattvic eating — what each excludes, hidden sources, portion limits and the best swaps, including how to combine several diets at once. Use when the user asks "is X vegan / low-FODMAP / Jain?", "what can I use instead of garlic/onion/soy sauce/paneer?", how two diets interact, or when adapting a recipe to a diet.
---

# Diet rules

Answer questions about the supported diets accurately and practically, and use these rules whenever you write or adapt a recipe.

## Sources of truth

1. `${CLAUDE_PLUGIN_ROOT}/scripts/diets.json` holds the machine rules the checker enforces. Read it when you need the exact term lists.
2. `references/diet-cheatsheet.md` is the human-readable guide: exclusions, hidden sources, portion limits, swaps, and how diets combine.

## Quick answers

To check any ingredient against every diet (or a chosen few):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_recipe.py" --ingredient "<name>" [--diets jain,low-fodmap]
```

Reply in plain language: whether it fits, why or why not, and the best swap. If the answer depends on the product or the portion (oats, asafoetida, miso, stock cubes, chickpeas, lentils, avocado), say so.

## Combining diets: key conflicts to anticipate

- **Vegan + low-FODMAP:** most legumes are high in GOS. Lean on firm tofu, tempeh, canned and rinsed lentils or chickpeas in small serves, quinoa, peanuts, and pumpkin seeds. Protein needs deliberate planning.
- **Jain + low-FODMAP:** a natural fit. Both drop onion and garlic, and asafoetida covers the flavour (use a gluten-free one if needed).
- **Jain + vegan:** paneer, ghee and yogurt are out. Use firm tofu, coconut yogurt and oil.
- **Gluten-free + Indian cooking:** most asafoetida is cut with wheat flour. Specify a gluten-free brand.
- **Nut-free + vegan creaminess:** replace cashew cream with sunflower or melon seeds, silken tofu (not if low-FODMAP), oat cream (only certified GF oats if gluten-free), or coconut milk.
- **Sattvic:** like Jain on onion, garlic and mushrooms, but root vegetables are allowed. Avoid vinegar, alcohol, caffeine and heavy chili.

## Accuracy guardrails

- Low-FODMAP thresholds come from Monash University research and change as they retest foods. Give the approximate serve and point to the Monash FODMAP app for the current number.
- Do not claim that anything is safe for coeliac disease or a severe allergy without "check the label / certification".
- Jain practice varies by family. Some eat dry ginger, some avoid all fungi and fermented foods, and some don't eat after sunset. State the conservative default and invite the user to adjust it.
