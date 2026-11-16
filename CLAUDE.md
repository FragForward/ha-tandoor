# ha-tandoor

## Produkt

- **Für wen und wozu:** Inoffizielle Home-Assistant-Integration für [Tandoor Recipes](https://github.com/TandoorRecipes/recipes): Einkaufsliste und Essensplan aus Tandoor in Home Assistant. Öffentliches Repo (MIT), Installation über HACS als Custom Repository.
- **Gehört dazu:**
  - Einkaufsliste als `todo`-Entität (lesen, anlegen, abhaken, umbenennen, löschen; Änderungen gehen zurück an Tandoor).
  - Essensplan als `calendar`, dazu Sensoren (heute, morgen, offene Einkaufseinträge).
  - Zwei mitgelieferte Lovelace-Karten in einer JS-Datei: `tandoor-mealplan-card` und `tandoor-kochliste-card`, jeweils mit Editor.
  - Optional die **Kochliste** der Essensplan-Website (Begleit-API, nicht Teil von Tandoor): Sensor, Dienste `tandoor.kochliste_*`, Wünsche und Vorlagen, Bewertung.
  - Optional der Bring-Rückkanal (`bring_sync.py`): beobachtet eine Bring-`todo`-Entität und stellt Rezepte auf „kochbar“, sobald alle gesendeten Zutaten abgehakt sind.
- **Gehört nicht dazu:** Tandoor selbst, die Essensplan-Website (eigenes System, hier nur ihr API-Client), Node-RED-Flows und der Tandoor-Connector (nur als Anleitung in `docs/` beschrieben).
- **Kunde:** keiner, eigenes Projekt; `docs/kunde.md` gibt es nicht.

## Starten / Testen / Prüfen

Ausprobiert am 16.11.2026 im Worktree (Python 3.10.11, Node 24.13.1). Im Repo gibt es **keine Tests, keinen Linter und keine CI**; geprüft wird nur die Syntax, alles Weitere in einer laufenden Home-Assistant-Instanz.

| Was | Befehl / Ort |
|---|---|
| Lokal starten | keiner; die Integration läuft nur in Home Assistant. `homeassistant` ist auf diesem PC nicht installiert, ein lokaler Start ist **ungeprüft** |
| Alle Tests | keine vorhanden (kein `tests/`, kein pytest installiert) |
| Syntax Python | `python -m compileall -q custom_components/tandoor` (legt `__pycache__` an, steht in `.gitignore`) |
| Syntax Karte (JS) | `node --check custom_components/tandoor/frontend/tandoor-mealplan-card.js` |
| JSON gültig | `python -m json.tool custom_components/tandoor/manifest.json` (ebenso `hacs.json`, `strings.json`, `translations/de.json`, `translations/en.json`) |
| YAML gültig | `python -c "import yaml;yaml.safe_load(open('custom_components/tandoor/services.yaml',encoding='utf-8'))"` |
| Statische Prüfung / Lint | keine eingerichtet (`ruff` nicht installiert); hassfest und HACS-Validierung **ungeprüft** |
| Build | keiner; die Karte ist eine einzelne, von Hand gepflegte JS-Datei ohne Bundler |
| CI | keine (`.github/` fehlt) |
| Testsystem | keines im Repo beschrieben |
| Live | Auslieferung über GitHub-Release mit Tag `vX.Y.Z` (zuletzt `v0.5.20`), HACS holt das Release; danach Home Assistant neu starten. Prüfung in der eigenen Instanz: Gerät „Tandoor Recipes“ mit allen Entitäten, Karten laden in der neuen Version. Ablauf aus Historie und README abgeleitet, hier **nicht ausprobiert** |

## Stack

- **Python** für Home Assistant ab 2025.6.0 (`hacs.json`); keine zusätzlichen Abhängigkeiten (`requirements` in `manifest.json` ist leer), HTTP über die aiohttp-Sitzung von Home Assistant.
- **Home-Assistant-Bausteine:** Config Flow und Options Flow, `DataUpdateCoordinator` (Einkaufsliste 60 s, Essensplan 5 min, Kochliste 60 s; `const.py`), Plattformen `calendar`, `sensor`, `todo`, eigene Dienste und WebSocket-Befehle.
- **Frontend:** reines JavaScript (Custom Elements), kein Framework, kein Build-Schritt.
- **Gegenstellen:** Tandoor 2.x über die REST-API mit Token; Essensplan-Website über `api.php` ohne Anmeldung.

## Struktur

| Ordner / Datei | Inhalt |
|---|---|
| `custom_components/tandoor/__init__.py` | Setup des Eintrags, Auslieferung der Karte und Pflege der Lovelace-Ressource |
| `custom_components/tandoor/api.py` | `TandoorClient` (Tandoor-API) und `EssensplanClient` (Kochliste), Fehlerklassen, Datenklassen |
| `custom_components/tandoor/coordinator.py` | drei Koordinatoren: Einkaufsliste, Essensplan, Kochliste |
| `custom_components/tandoor/calendar.py`, `sensor.py`, `todo.py`, `entity.py` | Entitäten |
| `custom_components/tandoor/services.py`, `services.yaml` | Dienste `tandoor.kochliste_*` und ihre Beschreibung |
| `custom_components/tandoor/websocket.py` | WebSocket-Befehle für die Karten (Rezept, Bewertung, Zutaten, Suche, Wünsche) |
| `custom_components/tandoor/bring_sync.py` | Bring-Rückkanal der Kochliste |
| `custom_components/tandoor/config_flow.py` | Einrichtung (URL, Token) und Optionen (Essensplan-URL, Bring-Entität) |
| `custom_components/tandoor/frontend/tandoor-mealplan-card.js` | beide Karten samt Editoren |
| `custom_components/tandoor/strings.json`, `translations/` | Texte englisch und deutsch |
| `custom_components/tandoor/brand/`, `images/` | Logos und Bilder für README und HACS |
| `docs/` | Anleitungen für Anwender (englisch) |

## Ablauf

Ablauf je Änderung: globaler Skill `feature-ablauf`.

- **Spezifikationen:** noch keine; `docs/spec/<bereich>.md` entsteht beim ersten Anfassen eines Bereichs.
- **Oberfläche:** `docs/design.md` gibt es noch nicht; vor der ersten Änderung an einer Karte aus dem Bestand anlegen (Vorlage `templates/claude/design.md` im Master-Repo).
- **Auslieferung:** je Version ein PR auf `main`, danach Tag und GitHub-Release `vX.Y.Z`. Die Versionsnummer steht an vier Stellen und wird gemeinsam erhöht: `manifest.json` (`version`), `const.py` (`FRONTEND_VERSION`) und die beiden Kopfkommentare in der Kartendatei.
- **Wer gibt frei:** der User; Kunden gibt es nicht.

## Stand

| Bereich | Status | Spezifikation |
|---|---|---|
| Einkaufsliste (`todo`, Sensor) | fertig | fehlt |
| Essensplan (`calendar`, Sensoren, Karte) | fertig | fehlt |
| Kochliste (Sensor, Dienste, Karte, Wünsche) | fertig | fehlt |
| Bring-Rückkanal | fertig | fehlt |

## Konventionen

- **Sprache:** README und `docs/` sind englisch (öffentliches Repo), ebenso Docstrings und Bezeichner der Integration. Commits und PRs deutsch. Neue Namen im Code englisch; bestehende deutsche Namen bleiben (Dienste `kochliste_gekocht`, Felder `sterne`, `kommentar`, Methoden in `EssensplanClient`), sie folgen der API der Essensplan-Website.
- **Texte:** jeder neue Text in `strings.json`, `translations/en.json` (inhaltsgleich mit `strings.json`) und `translations/de.json`; jeder neue Dienst zusätzlich in `services.yaml`.
- **Fehler der Gegenstellen** laufen über die Klassen in `api.py` (`TandoorConnectionError`, `TandoorAuthenticationError`, `EssensplanError`).

## Was nie passieren darf

- Zugangsdaten ins Repo: das Repo ist öffentlich. Das Tandoor-Token lebt nur im Config-Entry von Home Assistant.
- Ein Ausfall der Essensplan-Website darf das Setup der Integration nicht scheitern lassen; die Kochliste ist optional (leere URL schaltet sie ab) und erholt sich selbst.
- Die Pflege der Lovelace-Ressource darf das Setup nie abbrechen (Fehler werden dort bewusst abgefangen).
- Die Karte ausliefern, ohne `FRONTEND_VERSION` zu erhöhen: die Ressourcen-Adresse trägt die Version (`?v=`), sonst behalten Browser und Fully Kiosk die alte Datei.

## Fallen, kurz

- **Kartendatei über der Größengrenze:** `tandoor-mealplan-card.js` hat 1433 Zeilen (globale Regel: ab 700 teilen). Nie ganz lesen, erst nach der Klasse suchen (`TandoorMealplanCard` ab Zeile 1, `TandoorKochlisteCard` ab Zeile 541). Teilen wäre ein eigener PR und braucht einen Weg, die Teile zu einer ausgelieferten Datei zu fügen; den gibt es hier noch nicht.
- **Vorgabe der Essensplan-URL** in `const.py` zeigt auf eine private Adresse im Heimnetz; fremde Installationen müssen sie in den Optionen ändern oder leeren.
- **Bring-Rückkanal** ordnet über den Artikelnamen zu (ohne Groß-/Kleinschreibung); wird ein Artikel in Bring umbenannt, bleibt das Rezept im Einkaufszustand, bis es von Hand umgestellt wird.
- **Tandoor-Connector** hält seine Einstellungen im Speicher: nach Ändern oder Löschen den Tandoor-Container neu starten ([docs/connector.md](docs/connector.md)).
- **Rezeptbilder** lädt der Browser direkt von Tandoor; die Tandoor-Adresse muss vom Anzeigegerät aus erreichbar sein.
- **Alte Branches** `worktree-v05xx` auf dem Server sind gemergte Versionsstände, keine offene Arbeit. Nicht in `main` enthalten sind (Stand 16.11.2026) nur `worktree-tandoor-card-robustness` und `claude/shopping-list-recipe-ui-2aeko9`.

## Weiterführend

| Datei | Wann lesen |
|---|---|
| [README.md](README.md) | Funktionen, Einrichtung, Kartenoptionen, Dienste der Kochliste |
| [docs/nodered-bring-sync.md](docs/nodered-bring-sync.md) | Einkaufsliste per Node-RED nach Bring übertragen (empfohlener Weg) |
| [docs/connector.md](docs/connector.md) | Tandoor-Connector als Alternative, mit seinen Einschränkungen |
