# Spec: Meal plan card (`tandoor-mealplan-card`)

Only the recipe links are specified so far; the rest of the card is not yet covered.

## Who and why

Dashboard users who open recipes from the meal plan, also on phones with a recipe app
such as Kitshn (iOS) that is reached through its own web address.

## Criteria

- **L1** A tile with a recipe and `recipe_popup` on opens the recipe dialog on tap (existing).
- **L2** With `recipe_popup` off and `clickable` on, a tap on a tile with a recipe opens its
  link in a new tab (existing).
- **L3** New option `link_template` (19.11.2026, issue #26), default empty. Empty: the link is
  the Tandoor recipe URL (existing behaviour).
- **L4** Set: every `{url}` is replaced by the Tandoor recipe URL, every `{url_encoded}` by the
  same URL percent-encoded, every `{id}` by the recipe id. Example:
  `https://x.kitshn.app/#{url}` → `https://x.kitshn.app/#http://tandoor.local/view/recipe/48`.
- **L5** The template is used for the tile link (L2) and for the "open" button in the recipe
  dialog.
- **L6** A resulting link that does not start with `http://` or `https://` is not opened
  (existing safety check).
- **L7** The card editor offers `link_template` as a text field.

## Edge cases

- Entries without a recipe have no link, with or without a template.
- A template without placeholders opens that fixed address.

## Out of scope

- Custom URL schemes (`kitshn://`), see L6.
- Links in the Kochliste card (it has no recipe links).

## Decisions

- 19.11.2026, user: implement `link_template` for tile and dialog button (issue #26).
