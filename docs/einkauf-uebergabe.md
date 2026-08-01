# Übergabe: Änderungen an der Einkaufslisten-Seite (`einkauf.php`)

**Kontext für dich (den übernehmenden Agenten):**
Dies ist die Essensplan-Website (PHP, läuft auf `http://192.168.1.4:8091`, dazu
gehören u. a. `einkauf.php` und `api.php`). Sie erzeugt aus ausgewählten
Rezepten eine Einkaufsliste und schreibt sie in Tandoor bzw. Home Assistant.
Die Home-Assistant-Integration (`FragForward/ha-tandoor`) verlinkt nur auf
`einkauf.php` — dort ist **nichts** zu ändern, alle Punkte unten betreffen
ausschließlich diese PHP-Seite.

Bitte zuerst `einkauf.php` (und das zugehörige JS/CSS sowie die
Speicher-Endpunkte in `api.php`) lesen und die vorhandenen Namenskonventionen
übernehmen. Keine Framework-Einführung, keine Umbauten über das Angeforderte
hinaus.

---

## 1. Rezept-Auswahl: „haben wir zuhause" → „heute nicht einkaufen"

**Ist:** Beim Auswählen eines Rezepts gibt man an, dass man *alles dafür
zuhause hat*.

**Soll:** Die Angabe ist stattdessen **„Heute nicht einkaufen"** — also eine
reine Einkaufs-Entscheidung für diesen Durchlauf, keine Vorratsaussage.

- Beschriftung und Tooltip/Hilfetext entsprechend ändern.
- Semantik: Rezept bleibt in der Liste, seine Zutaten kommen aber **nicht** auf
  die Einkaufsliste. Es darf dadurch **kein** Vorrats-/Pantry-Flag an der Zutat
  oder am Rezept dauerhaft gesetzt werden — die Entscheidung gilt nur für
  diesen Einkauf.
- Falls bisher ein persistentes „zuhause"-Flag geschrieben wurde: dieses
  Schreiben an dieser Stelle entfernen; der Status gehört in den
  Session-/Request-State des aktuellen Einkaufs.

## 2. Rezept-Zeilen kompakt mit Bild

**Soll:** Jedes Rezept in der Auswahl wird als kompakte Zeile dargestellt:

```
[ Bild ]   Rezeptname                      [ ✓ ]
```

- **links** das Rezeptbild (klein, ca. 48–60 px, quadratisch oder rund,
  `object-fit: cover`; wenn kein Bild vorhanden ist, ein neutrales Platzhalter-
  Icon — kein leerer großer Block),
- **mittig** der Rezeptname (einzeilig, bei Überlänge Ellipsis oder max. 2
  Zeilen),
- **rechts** die Auswahl-Checkbox / der Haken.
- Auf schmalen Screens darf untereinander umgebrochen werden, die Zeile soll
  aber **insgesamt klein bleiben** — keine großen Kacheln, es sollen mehrere
  Rezepte gleichzeitig sichtbar sein.
- Wichtig: Rezepte müssen **abwählbar** sein. Der Normalfall ist, dass nicht
  alles auf einmal gekauft wird — z. B. nur 2 von 6 Essen.

## 3. Abgewählte Rezepte hinter einem Button

**Soll:** Rezepte, die *nicht* eingekauft werden, verschwinden aus der
Hauptliste und liegen zusammengeklappt hinter einem Button, z. B.:

```
Nicht gekaufte anzeigen (4)
```

- Klick klappt sie auf/zu (reines Toggle im Frontend, kein Reload).
- Aus dem aufgeklappten Bereich müssen sie sich wieder aktivieren lassen, dann
  wandern sie zurück nach oben.
- Anzahl im Button-Label mitführen.

## 4. Zutaten-Dialog (Stift): Hinweistexte entfernen

Im Dialog, der beim Klick auf das **Stift-Symbol** in der Zutatenauswahl
aufgeht, sollen diese Hinweistexte **ersatzlos raus**:

1. `(wird in der Rezepte-App gespeichert)`
2. der Erklärtext zum Kommentarfeld:
   `Kommentar an den Agenten, z. B. »nenne Quark in Topfen um«` und
   `Wird beim nächsten Agenten-Lauf umgesetzt (Zusammenführen/Umbenennen)`

**Nur die Texte entfernen — die Felder selbst bleiben**, insbesondere das
Kommentarfeld. Wenn eine Beschriftung nötig ist, reicht ein kurzes
`Kommentar` als Label oder Placeholder.

## 5. „Haben wir immer zuhause": kein Seiten-Reload mehr (wichtigster Punkt)

**Ist:** Setzt man den Haken **„haben wir immer zuhause"** bei einer Zutat,
wird die ganze Seite neu geladen. Folge: ein gerade getippter Kommentar ist
weg, und auch die bisherige Rezept-/Zutatenauswahl geht verloren.

**Soll:**

- Klick auf den Haken speichert **per AJAX** (`fetch` auf den bestehenden
  Endpunkt in `api.php`, ggf. einen schlanken Endpunkt ergänzen) — **kein
  Form-Submit, kein `location.reload()`, kein Redirect**.
- Sichtbare Reaktion im DOM ist **ausschließlich**: bei dieser Zutat wird der
  Haken bei **„kaufen"** entfernt. Sonst nichts. Fertig.
- Getippter, noch nicht gespeicherter **Kommentar bleibt erhalten**.
- Die **bisherige Auswahl** (welche Rezepte / welche Zutaten gekauft werden)
  bleibt vollständig erhalten.
- Optimistisch aktualisieren, aber bei Fehlerantwort den vorherigen Zustand
  zurücksetzen und eine kurze, unaufdringliche Fehlermeldung anzeigen (keine
  `alert()`-Box, die den Dialog blockiert).
- Beim Prüfen bitte auch schauen, ob es weitere Stellen im Dialog gibt, die
  denselben Reload auslösen — diese analog auf AJAX umstellen.

---

## Abnahme-Checkliste

- [ ] Beschriftung lautet „Heute nicht einkaufen", kein dauerhaftes
      Vorrats-Flag wird dabei geschrieben
- [ ] Rezeptzeile: Bild links, Name mittig, Haken rechts, kompakt, mit
      Platzhalter bei fehlendem Bild
- [ ] Abgewählte Rezepte liegen hinter „Nicht gekaufte anzeigen (n)" und lassen
      sich reaktivieren
- [ ] Die beiden Hinweistexte im Stift-Dialog sind weg, Kommentarfeld ist noch da
- [ ] „Haben wir immer zuhause" lädt die Seite **nicht** neu; nur der
      „kaufen"-Haken der Zutat verschwindet; Kommentar und Auswahl bleiben
- [ ] Getestet mit mehreren Rezepten, davon nur 2 ausgewählt
