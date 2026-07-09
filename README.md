<p align="center">
  <img src="images/icon@2x.png" alt="Tandoor Recipes" width="160">
</p>

# Tandoor Recipes for Home Assistant

Unofficial Home Assistant integration for [Tandoor Recipes](https://github.com/TandoorRecipes/recipes) — bringing your shopping list and meal plan into Home Assistant, similar to what the core Mealie integration offers.

## Features

| Entity | Type | Description |
|---|---|---|
| Shopping list | `todo` | The Tandoor shopping list as a native to-do entity. Add, check off, rename and delete items — changes sync back to Tandoor. Leading amounts are parsed (`2 Onions` → amount 2, food *Onions*). |
| Meal plan | `calendar` | Your Tandoor meal plan as a calendar with all-day events (`Dinner: Goulash`). |
| Meal plan today | `sensor` | Names of today's planned meals. Carries a `days` attribute with the full next 7 days (name, meal type, servings, image, recipe URL, working/waiting time) — ideal for dashboard cards. |
| Meal plan tomorrow | `sensor` | Names of tomorrow's planned meals. |
| Open shopping items | `sensor` | Number of unchecked shopping list entries. |

Polling intervals: shopping list every 60 s, meal plan every 5 min.

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu (top right) → **Custom repositories**
2. Repository: `https://github.com/FragForward/ha-tandoor` — Type: **Integration** → **Add**
3. Search for **Tandoor Recipes** in HACS, open it and click **Download**
4. Restart Home Assistant (Settings → System → Restart)

### Manual

Copy the `custom_components/tandoor/` folder into your Home Assistant `config/custom_components/` directory and restart Home Assistant.

## Setup

1. **Create an API token in Tandoor:** click your user avatar (top right) → **Settings** → tab **API** → **New token**, scope `read write`. Copy the token (`tda_...`).
2. In Home Assistant go to **Settings → Devices & Services → Add Integration** and search for **Tandoor Recipes**.
3. Enter:
   - **URL** — the base URL of your Tandoor instance as you open it in the browser, e.g. `http://192.168.1.4:9926` (no trailing slash needed)
   - **API token** — the token from step 1
4. Click **OK** — the integration validates the connection and creates the device with all entities.

## Lovelace card

The integration ships a dashboard card that renders the meal plan with recipe images, meal type chips, working/waiting times and servings — clickable through to the recipe in Tandoor.

<img src="images/card.png" alt="Tandoor mealplan card" width="420">

The card has a full visual editor (entity picker, days to show, max meals per day, display toggles) and appears in the dashboard card picker.

**No manual installation needed** — the card is served and registered automatically by the integration. Just add it to any dashboard:

```yaml
type: custom:tandoor-mealplan-card
entity: sensor.tandoor_meal_plan_today   # your "Meal plan today" sensor
days_to_show: 2
```

Options: `title`, `days_to_show` (1–7), `show_image`, `show_times`, `clickable`, `hide_empty_days`.

Note: the recipe images are loaded directly from your Tandoor instance, so the browser needs to be able to reach the Tandoor URL.

## Tips

- **Shopping list to Bring!/other apps:** Tandoor's built-in *Connectors* (Tandoor → Space settings → Connectors) can push shopping list entries straight into any Home Assistant todo entity — e.g. a Bring! list from the core Bring integration.
- Foods flagged *ignore shopping* in Tandoor (salt, water, …) never reach the shopping list, and Tandoor's food alias automations keep naming consistent.

## Disclaimer

This is a third-party integration, not affiliated with the Tandoor project. Tested against Tandoor 2.x.

## License

[MIT](LICENSE)
