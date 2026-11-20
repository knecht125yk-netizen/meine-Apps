# Meine Apps

Sammlung kleiner Programme. Jede App liegt in einem eigenen Ordner und hat dort eine eigene README mit Anleitung und den getroffenen Annahmen.

| App | Plattform | Kurzbeschreibung |
|---|---|---|
| [Maschinenbau-Rechner](maschinenbau-rechner/) | Windows (.exe) | Biegung, Knickung, Zug/Druck, Torsion, Schub, Flächenpressung, von Mises, Schrauben, Wellen, Passfedern, Profile, Werkstoffe. Formeln werden angezeigt, Export als PDF und Word |
| [Kassenbuch & Rechnungen](kassenbuch/) | Windows (.exe) | Kleinunternehmer (§ 19 UStG): Kunden, Artikel, Angebote → Rechnungen, fortlaufende Nummern, Kassenbuch, Export als PDF, CSV und Excel |
| [Programmsperre](programmsperre/) | Windows (.exe) | Sperrt ausgewählte Programme per PIN (nicht den PC), läuft im Infobereich, Autostart |
| [To-Do-Widget](todo-widget/) | Windows (.exe) | Schwebendes Symbol mit ausklappbarer To-Do-Liste (Priorität, Fälligkeit) |
| [Trainings-App](trainings-app/) | Web-App / PWA (PC + iPhone, offline) | Kopfrechnen, Englisch (Lektionen und Karteikarten), Kommunikationstraining |

## Windows-Programme herunterladen (.exe)
Die EXE-Dateien baut GitHub automatisch, ohne dass am eigenen PC etwas installiert werden muss:
1. Im Repository den Tab **Actions** öffnen.
2. Links den Workflow **„Windows-Apps bauen“** wählen.
3. Den neuesten Lauf mit grünem Haken öffnen und unten bei **Artifacts** die gewünschte App herunterladen (ZIP mit `.exe` und README).
4. Entpacken und starten. Falls Windows SmartScreen warnt: „Weitere Informationen“ und dann „Trotzdem ausführen“, weil die EXE nicht signiert ist.

Der Workflow (`.github/workflows/windows-build.yml`) führt vor dem Bauen die Tests jeder App aus.

## Trainings-App online stellen
Siehe [trainings-app/README.md](trainings-app/README.md). Der Workflow `pages.yml` veröffentlicht die App über GitHub Pages.

## Entwickeln
Für alle Windows-Apps: Python 3.11+ und `pip install -r requirements.txt` im jeweiligen Ordner, danach `python app.py`. Tests mit `python -m pytest`.
