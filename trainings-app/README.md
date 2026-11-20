# Trainings-App (Web-App / PWA)

Läuft im Browser auf dem **PC und auf dem iPhone**, lässt sich wie eine App installieren und funktioniert **offline**. Der Fortschritt wird lokal auf dem Gerät gespeichert.

## Inhalte

### 🧮 Kopfrechnen
- Grundrechenarten **+ − × ÷** und **Mix**, 5 **Schwierigkeitsstufen** (Leicht bis Profi)
- Modi: **10 Aufgaben**, **60-Sekunden-Zeitmodus**, **Endlos**
- Eigene Zifferntastatur (am PC geht auch die normale Tastatur mit Enter). Punkte für Tempo, Bonus ab 5 richtigen Antworten in Folge.
- **Statistik:** Trefferquote je Rechenart, richtige Aufgaben der letzten 7 Tage als Diagramm, Bestwerte je Modus, Rechenart und Stufe

### 🇬🇧 Englisch (Babbel-Stil, eigene Inhalte)
- **12 Lektionen** von A1 bis B1 (Begrüßung, Zahlen und Uhrzeit, Familie, Essen, Einkaufen, Reisen, Arbeit, Wohnen, Freizeit, Gesundheit, Wetter, Gefühle und Meinungen) mit **144 Vokabeln** samt Beispielsätzen
- Übungstypen: **Multiple Choice** (EN→DE, DE→EN, Grammatik), **Lückentexte**, **Satzbau** (Wörter antippen), **Tippen** (mit Tippfehler-Toleranz)
- Falsch beantwortete Aufgaben kommen am Ende der Lektion noch einmal dran.
- **Karteikarten mit Wiederholungssystem:** Leitner-System mit 6 Fächern und Intervallen von 1, 3, 7, 16 und 35 Tagen. Die Bewertung erfolgt über „Nochmal / Schwer / Gut / Leicht“. Abfragerichtung umschaltbar.
- **Aussprache 🔊** über die Sprachausgabe des Geräts (britisch oder amerikanisch)

### 💬 Kommunikation
- **Smalltalk:** Gesprächseinstiege in 5 Kategorien mit Zufallsgenerator, goldene Regeln und Sätze zum Vertiefen
- **Fragetechniken:** 9 Techniken (offen, geschlossen, Alternativ-, Präzisierungs-, Spiegel-, hypothetische, Skalierungs-, zirkuläre und Suggestivfragen) mit Beispielen und **Quiz**
- **Aktives Zuhören:** Techniken, Stolpersteine und eine **Übung** (beste Reaktion auswählen)
- **6 Übungsszenarien** mit Entscheidungen, Feedback und Modell: Feedback geben (SBI), Konflikt lösen, Gehalt verhandeln (Harvard-Konzept), Kritik annehmen, Nein sagen, Smalltalk auf einem Event
- Ein **Tipp des Tages**

### ⭐ Motivation
XP und Level, Tagesziel mit Fortschrittsring, **Serie** (Tage in Folge), 14 **Erfolge**, Konfetti und Töne (abschaltbar), heller und dunkler Modus.

## Starten / Installieren

**Lokal am PC:** Doppelklick auf `index.html` funktioniert für einen schnellen Test, ist aber ohne Offline-Modus. Besser ist ein lokaler Webserver:
```bash
cd trainings-app
python -m http.server 8000
```
Danach `http://localhost:8000` öffnen.

**Online über GitHub Pages:**
Der Workflow `.github/workflows/pages.yml` testet die App und veröffentlicht den Ordner `trainings-app/` automatisch, sobald Änderungen im Standard-Branch (`main`) landen. Bitte einmalig in den Repository-Einstellungen unter **Settings → Pages → Source: „GitHub Actions“** auswählen.
> ⚠️ GitHub Pages ist für **private** Repositories nur mit einem kostenpflichtigen Plan (z. B. GitHub Pro) verfügbar. Alternativen: das Repository öffentlich machen, nur die Trainings-App in ein eigenes öffentliches Repo kopieren, oder den Ordner per Drag-and-drop bei Netlify Drop bzw. Cloudflare Pages hochladen (kostenlos).

**Auf dem iPhone installieren:** Die Pages-Adresse in **Safari** öffnen, auf **Teilen** tippen und dann **„Zum Home-Bildschirm“** wählen. Danach startet die App im Vollbild und funktioniert offline.
**Am PC (Chrome/Edge):** In der Adressleiste auf das Install-Symbol klicken und dann **„Installieren“** wählen.

## Daten
Der gesamte Fortschritt liegt im `localStorage` des Browsers. Unter **Profil → Exportieren/Importieren** lässt er sich als JSON-Datei sichern oder auf ein anderes Gerät übertragen. Hinweis: iOS kann Daten von Web-Apps, die mehrere Wochen nicht genutzt wurden, löschen. Ab und zu exportieren lohnt sich also.

## Technik und Tests
- Reines HTML, CSS und JavaScript ohne Abhängigkeiten oder Build-Schritt. Der Service Worker (`sw.js`) speichert alle Dateien für den Offline-Betrieb.
- Die Logik (Aufgabengenerator, Leitner-System, Antwortprüfung, XP, Serie) steckt in `js/logik.js`, die Inhalte in `js/inhalt-*.js`.
- Tests: `node --test tests/*.test.js` (Node 18+). Sie prüfen u. a., dass alle Rechenaufgaben ganzzahlig und nicht negativ sind, wie die Karteikarten-Fächer funktionieren und dass alle Lektionen und Szenarien vollständig sind.

## Annahmen
- Die Lerninhalte sind eigens für diese App geschrieben und keine Kopie von Babbel o. Ä.
- Neue Wörter kommen nach einer Lektion automatisch in den Karteikasten.
- Die Serie zählt, sobald an einem Tag XP gesammelt wurden. Ein ausgelassener Tag setzt sie zurück.
