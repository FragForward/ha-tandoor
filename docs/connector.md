# Tandoor → Home Assistant shopping list push (Connector)

Tandoor Recipes has a **built-in Connector feature** that actively pushes shopping list
entries into a Home Assistant todo entity — within seconds, no polling.

> **Important:** Connectors are a native feature of **Tandoor itself** (available since
> Tandoor 2.x). They work completely independently of the ha-tandoor integration —
> you can use them without this integration, and this integration works without them.

## Connector vs. this integration's todo entity

| | Connector (Tandoor feature) | `todo.…_shopping_list` (this integration) |
|---|---|---|
| Direction | Tandoor **→** HA (one way) | Two way (HA edits sync back to Tandoor) |
| Latency | Seconds (push) | Up to 60 s (polling) |
| Target | **Any** HA todo entity (e.g. a Bring! list) | Own todo entity representing the Tandoor list |
| Item format | `Food (amount)` in the title | `amount unit Food` as summary |
| Delete sync | Removes items it created when they are removed in Tandoor | Deleting in HA deletes in Tandoor |

Typical setups:

- **Simple:** Connector pushes straight into a Bring!/Google Keep/local todo list. Done.
- **Full control:** Use this integration's todo entity and build your own automation
  (e.g. Node-RED: new item → copy to Bring! with the amount as description → delete from Tandoor).
- **Do not point both at the same target list** — you would get duplicates and delete races.

## Setting up the Connector (in Tandoor)

1. **Create a Home Assistant long-lived access token:**
   In HA click your user name (bottom left) → tab **Security** → *Long-lived access tokens* →
   **Create token**. Copy it — it is shown only once.

2. **Create the connector in Tandoor:**
   Open Tandoor → click your user avatar → **Space settings** → tab **Connectors** → **New connector**:

   | Field | Value |
   |---|---|
   | Name | e.g. `Bring shopping list` |
   | Type | `HomeAssistant` |
   | URL | `http://<your-ha-host>:8123/api` (note the `/api` suffix) |
   | Token | the long-lived access token from step 1 |
   | Todo entity | the target list, e.g. `todo.bring_shopping_list` |
   | On shopping list entry created | ✅ |
   | On shopping list entry deleted | ✅ (removes the item from HA again when deleted in Tandoor) |
   | Supports description field | ✅ if the target list supports descriptions (Bring! does) |

3. **Test it:** add an item to the Tandoor shopping list — it should appear in the HA
   todo list within a few seconds.

## Troubleshooting

- Nothing arrives: check the URL ends with `/api`, the token is valid, and HA is reachable
  **from the Tandoor container** (container network!).
- Duplicates: make sure only ONE mechanism (connector *or* your own automation) writes
  to the target list.
- Entries pile up in Tandoor: the connector does not clear the Tandoor list. Either check
  items off in Tandoor, or use the integration + an automation that deletes after transfer.
