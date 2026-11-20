# To-Do-Widget (Windows)

Ein kleines **schwebendes Symbol**, das immer im Vordergrund bleibt. Ein Klick öffnet eine kompakte To-Do-Liste, ein Klick daneben (oder auf das Symbol) klappt sie wieder ein.

## Funktionen
- **Rundes Symbol** mit Haken, das **immer im Vordergrund** liegt und **frei verschiebbar** ist (einfach mit der Maus ziehen). Die Position wird gespeichert.
- Ein **Zähler** am Symbol zeigt die offenen Aufgaben. Er wird **rot**, wenn etwas heute fällig oder überfällig ist.
- **Klick auf das Symbol** öffnet das Popup, ein **Klick daneben** oder auf das Symbol schließt es wieder. Escape schließt es ebenfalls.
- **Popup-Größe einstellbar** über den Anfasser unten rechts. Die Größe wird gemerkt. Es ist bewusst kein Vollbild möglich (max. 900 × 1000 px).
- **Aufgaben hinzufügen:** Text eintippen und Enter drücken. Priorität (● Hoch, Mittel, Niedrig) und Fälligkeit (📅) lassen sich auswählen.
- **Schnelleingabe mit Kürzeln:** `Arzt anrufen !hoch @morgen`, `Rasen mähen !niedrig @sa`, `Geschenk @24.12.`
- **Abhaken** per Checkbox, **Doppelklick** zum Bearbeiten, **Rechtsklick** auf eine Aufgabe ändert Priorität oder Fälligkeit, **✕** löscht sie.
- **Sortierung:** Überfälliges und Fälliges zuerst, dann nach Priorität. Erledigte Aufgaben stehen unten (ausblendbar über das Menü „⋯“).
- **Optionaler Autostart** mit Windows (Menü „⋯“ oder Rechtsklick auf das Symbol).
- Startet man das Programm ein zweites Mal, öffnet sich einfach die Liste der laufenden Instanz.

## Starten
**.exe:** Auf GitHub unter **Actions** den Workflow **„Windows-Apps bauen“** öffnen und beim neuesten Lauf das Artefakt **ToDo-Widget** herunterladen. Die `ToDo-Widget.exe` an einen festen Ort legen (wegen Autostart) und starten.

**Aus dem Quellcode:**
```bash
cd todo-widget
pip install -r requirements.txt
python app.py
```
Tests: `python -m pytest`

**Beenden:** Rechtsklick auf das Symbol und dann „Beenden“ (oder Menü „⋯“ → „To-Do-Widget beenden“).

## Daten
Die Aufgaben und Einstellungen liegen als JSON unter `%APPDATA%\MeineApps\ToDo-Widget\aufgaben.json`. Gespeichert wird bei jeder Änderung sofort. Eine beschädigte Datei wird als `.defekt` gesichert und nicht überschrieben.

## Annahmen
- Startposition ist rechts oben auf dem Hauptbildschirm. Liegt eine gespeicherte Position nicht mehr auf einem Bildschirm (z. B. nach dem Abstecken eines Monitors), wird das Symbol zurückgesetzt.
- Das Popup öffnet sich links neben dem Symbol. Ist dort kein Platz, öffnet es sich rechts davon.
