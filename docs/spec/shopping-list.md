# Spec: Shopping list (`todo` entity)

## Who and why

Home Assistant users who want to see and edit the Tandoor shopping list in HA, and who
want to forward it to other list apps (e.g. Bring!) via an automation or Node-RED.

## Criteria

Default format (option "amount in description" off) — existing behaviour:

- **K1** Every open or recently checked Tandoor shopping entry appears as one to-do item;
  checked entries are `completed`, open ones `needs_action`.
- **K2** Option off: the summary is `amount unit food` with empty parts left out
  (`2 kg Mehl`, `3 Eier`, `Salz`), never with a leading or double space. No description.
- **K3** Option off, create: a summary with a leading number (`2 Onions`, `1,5 Milch`)
  becomes amount `2` / `1.5` and food `Onions` / `Milch`; without a leading number the
  whole text is the food and the amount is 0. An empty summary is rejected.
- **K4** Option off, update: checking or unchecking sends only the new status. A changed
  summary is parsed as in K3 and sent as food and amount; an unchanged summary sends
  neither.

Option "amount in description" on (new, 19.11.2026, issue #23 / PR #25):

- **K5** The option lives in the integration options (default off). Changing it reloads the
  entry, so the format switches without restarting Home Assistant.
- **K6** Option on: the summary is the food name only; the description is `amount unit`
  (`2 kg`, `3`, `1.5 Esslöffel`). With neither amount nor unit there is no description.
- **K7** Option on: the entity offers setting a description, so `todo.add_item` and
  `todo.update_item` accept the `description` field. Option off: not offered (as before).
- **K8** Option on, create: the summary is the food. The description is read as a leading
  number, optionally followed by a unit up to the first comma or the end
  (`2 kg` → 2 / kg, `2` → 2 / no unit, `1,5 l` → 1.5 / l, `2 kg, organic` → 2 / kg).
  A missing description, or one that does not start with a number, gives amount 0 and no
  unit. The summary is not parsed for a leading number.
- **K9** Option on, update: checking or unchecking an item whose description was not
  changed sends only the new status; amount, unit and food in Tandoor stay unchanged.
- **K10** Option on, update: a changed description is read as in K8 and sends the new amount
  and unit; a cleared description sets the amount to 0 and removes the unit. A changed
  summary is sent as the new food name; an unchanged summary is not sent.

## Edge cases

- Description with only spaces counts as empty.
- Units longer than ten characters (`Packung(en)`) are kept in full.
- Amounts are shown without trailing zeros (`2`, not `2.0`).

## Out of scope

- A templatable description (suggested in #23).
- The sync to Bring! itself (Node-RED guide in `docs/nodered-bring-sync.md`).

## Open questions

- Removing the unit via `PATCH unit: null` is not yet verified against a live Tandoor.

## Decisions

- 19.11.2026, user: PR #25 is taken over and fixed; the new format is an option so existing
  setups keep working. The Node-RED guide uses the description when present, so the
  parsing there is no longer needed with the option on.
