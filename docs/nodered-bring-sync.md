# Shopping list → Bring! (or any other list) with Node-RED

This guide moves every Tandoor shopping list entry into another Home Assistant todo
list (e.g. a **Bring!** list from the core Bring integration) — with the **amount as
the item description** ("Onion" with description "2 pcs") — and then **deletes the
entry from Tandoor**. Result: the Tandoor list stays empty, your target list is the
single source of truth.

> ⚠️ **AI disclaimer:** this flow was generated with an AI assistant and has not been
> further audited by hand. It only talks to your own Home Assistant instance
> (no external services, no credentials inside the flow), but review it before use.

## Requirements

- This integration installed (provides the `todo.…_shopping_list` entity, polled every 60 s)
- The integration option **Amount and unit in the description** turned on
  (Settings → Devices & services → Tandoor Recipes → Configure). The Tandoor list then
  already looks like a Bring! list (title `Onion`, description `2 pcs`), so the flow just
  copies title and description — no parsing, no unit list.
- Node-RED with [node-red-contrib-home-assistant-websocket](https://github.com/zachowj/node-red-contrib-home-assistant-websocket)
- A target todo entity, e.g. from the core [Bring! integration](https://www.home-assistant.io/integrations/bring/)

## How it works

1. **Trigger:** fires when the state (= number of open items) of the Tandoor todo entity **increases**. A gate blocks decreasing changes, so the flow cannot re-trigger itself while deleting.
2. **Fetch:** reads all open items via `todo.get_items`.
3. **Prepare:** one message per open item — title as name, description (amount and unit) as description.
4. **Delete first:** removes the entry from Tandoor by uid. Deleting acts as a claim — if two flow runs race, the loser errors out and never reaches the target list, so duplicates are impossible.
5. **Add:** creates the item on the target list, amount as description. Identical names within one batch are only added once.

> **First run:** the flow transfers **all** currently open entries of the Tandoor list.

> **Upgrading from an older version of this flow** (the one with the *parse* node and the
> `UNITS` list): it reads the amount from the title. If you turn the option on, the amount
> is no longer in the title and the old flow would drop it — so turn the option on **and**
> re-import this flow at the same time. If you keep the option off, your old flow keeps
> working unchanged.

## Import

Copy the JSON below (Node-RED → menu → Import), then:

- select your Home Assistant server in the trigger/action nodes,
- adjust the **source** entity (`todo.tandoor_shopping_list` — the shopping list entity of this integration; the id depends on your HA language, e.g. `todo.tandoor_einkaufsliste` on German systems),
- adjust the **target** entity in the last node (e.g. your Bring! list).

```json
[
  {"id":"ttrg1","type":"server-state-changed","z":"","name":"Tandoor list changed","server":"","version":6,"outputs":1,"exposeAsEntityConfig":"","entities":{"entity":["todo.tandoor_shopping_list"],"substring":[],"regex":[]},"outputInitially":false,"stateType":"str","ifState":"","ifStateType":"str","ifStateOperator":"is","outputOnlyOnStateChange":true,"for":"0","forType":"num","forUnits":"minutes","ignorePrevStateNull":false,"ignorePrevStateUnknown":true,"ignorePrevStateUnavailable":true,"ignoreCurrentStateUnknown":true,"ignoreCurrentStateUnavailable":true,"outputProperties":[{"property":"payload","propertyType":"msg","value":"","valueType":"entityState"},{"property":"data","propertyType":"msg","value":"","valueType":"eventData"}],"x":120,"y":100,"wires":[["tgate1"]]},
  {"id":"tgate1","type":"function","z":"","name":"only on new item","func":"const d = msg.data || {};\nconst ev = d.event || d;\nconst oldC = Number(ev.old_state ? ev.old_state.state : NaN);\nconst newC = Number(ev.new_state ? ev.new_state.state : NaN);\n// block unless the open-item count clearly increased\nif (!Number.isFinite(oldC) || !Number.isFinite(newC) || newC <= oldC) {\n    return null;\n}\nreturn msg;","outputs":1,"timeout":0,"noerr":0,"initialize":"","finalize":"","libs":[],"x":330,"y":100,"wires":[["tget1"]]},
  {"id":"tget1","type":"api-call-service","z":"","name":"fetch items","server":"","version":7,"debugenabled":false,"action":"todo.get_items","floorId":[],"areaId":[],"deviceId":[],"entityId":["todo.tandoor_shopping_list"],"labelId":[],"data":"{\"status\":\"needs_action\"}","dataType":"json","mergeContext":"","mustacheAltTags":false,"outputProperties":[{"property":"payload","propertyType":"msg","value":"","valueType":"results"}],"queue":"none","blockInputOverrides":false,"domain":"todo","service":"get_items","x":530,"y":100,"wires":[["tfn1"]]},
  {"id":"tfn1","type":"function","z":"","name":"one msg per item","func":"const lists = msg.payload || {};\nconst key = Object.keys(lists)[0];\nconst items = (lists[key] && lists[key].items) || [];\nconst seen = new Set();\nconst msgs = [];\nfor (const i of items) {\n    if (i.status !== 'needs_action') continue;\n    // title = food, description = amount and unit (integration option)\n    const name = (i.summary || '').trim();\n    const desc = (i.description || '').trim();\n    const k = name.toLowerCase();\n    msgs.push({ payload: name, description: desc, uid: i.uid, first: !seen.has(k) });\n    seen.add(k);\n}\nreturn [msgs];","outputs":1,"timeout":0,"noerr":0,"initialize":"","finalize":"","libs":[],"x":760,"y":100,"wires":[["tdel1"]]},
  {"id":"tdel1","type":"api-call-service","z":"","name":"delete from Tandoor","server":"","version":7,"debugenabled":false,"action":"todo.remove_item","floorId":[],"areaId":[],"deviceId":[],"entityId":["todo.tandoor_shopping_list"],"labelId":[],"data":"{\"item\": uid}","dataType":"jsonata","mergeContext":"","mustacheAltTags":false,"outputProperties":[],"queue":"none","blockInputOverrides":false,"domain":"todo","service":"remove_item","x":990,"y":100,"wires":[["tflt1"]]},
  {"id":"tflt1","type":"switch","z":"","name":"only 1st per name","property":"first","propertyType":"msg","rules":[{"t":"true"}],"checkall":"true","repair":false,"outputs":1,"x":1200,"y":100,"wires":[["tadd1"]]},
  {"id":"tadd1","type":"api-call-service","z":"","name":"add to target list","server":"","version":7,"debugenabled":false,"action":"todo.add_item","floorId":[],"areaId":[],"deviceId":[],"entityId":["todo.shopping_list"],"labelId":[],"data":"description = \"\" ? {\"item\": payload} : {\"item\": payload, \"description\": description}","dataType":"jsonata","mergeContext":"","mustacheAltTags":false,"outputProperties":[],"queue":"none","blockInputOverrides":false,"domain":"todo","service":"add_item","x":1400,"y":100,"wires":[[]]}
]
```

## Alternative: Tandoor's built-in Connector

Tandoor can also push entries itself — see [connector.md](connector.md). The connector is
simpler (no Node-RED) but one-way only, puts the amount in the item **title**
(`Onion (2)`), adds a "From TandoorRecipes" signature to the description and never
clears the Tandoor list. Pick **one** mechanism per target list.
