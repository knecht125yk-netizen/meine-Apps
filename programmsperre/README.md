# Programmsperre (Windows)

Sperrt **einzelne Programme** wie Spiele, Browser oder Steam, **nicht den ganzen PC**. Ein gesperrtes Programm wird sofort nach dem Start angehalten, und es erscheint ein PIN-Dialog. Mit der richtigen PIN ist das Programm für eine einstellbare Zeit freigegeben.

## So funktioniert es
- Die App läuft als **Schloss-Symbol im Infobereich** (unten rechts in der Taskleiste) und startet auf Wunsch **automatisch mit Windows**.
- Sie prüft zweimal pro Sekunde die laufenden Prozesse. Startet ein gesperrtes Programm, wird es **eingefroren** (angehalten) und ein PIN-Dialog erscheint:
  - **Richtige PIN** gibt das Programm für die gewählte Dauer frei (15 Min. bis 4 Std., Standardwert einstellbar), und es läuft sofort weiter.
  - **„Programm beenden“**, Escape oder das Schließen des Dialogs beendet das Programm.
  - Lässt sich ein Programm nicht anhalten (fehlende Rechte), wird es sofort beendet.
- Ein paar Minuten vor Ablauf der Freigabe kommt eine **Vorwarnung**. Nach Ablauf wird das Programm wieder angehalten und die PIN erneut verlangt. Alternativ einstellbar: Das Programm läuft weiter, und erst ein Neustart braucht wieder die PIN.
- Nach 5 falschen PINs ist die Eingabe 60 s gesperrt. Jede weitere Sperre dauert doppelt so lang.
- **Geschützt per PIN:** die Einstellungen (Programmliste, Freigabedauer, PIN ändern, Autostart), das Pausieren der Sperre und das **Beenden** der Programmsperre.
- Die PIN wird nur als **Hash gespeichert** (PBKDF2-SHA256, 200.000 Iterationen, zufälliges Salt) und nie im Klartext.

## Einrichtung
1. Programm starten (siehe unten) und beim ersten Start eine **PIN (4 bis 12 Ziffern)** festlegen.
2. Im Einstellungsfenster Programme hinzufügen. Dafür gibt es drei Wege:
   - **„Aus laufenden Programmen …“**: das Programm vorher starten, dann aus der Liste wählen (der einfachste Weg).
   - **„EXE-Datei wählen …“**, z. B. `C:\Program Files\Google\Chrome\Application\chrome.exe`.
   - **„Name eingeben …“**, z. B. `chrome.exe`, `msedge.exe`, `firefox.exe`, `steam.exe`, `Minecraft.exe`.
3. Speichern. Danach findest du alles über **Rechtsklick auf das Schloss-Symbol**.

## Starten
**.exe:** Auf GitHub unter **Actions** den Workflow **„Windows-Apps bauen“** öffnen und beim neuesten Lauf das Artefakt **Programmsperre** herunterladen. Die `Programmsperre.exe` an einen festen Ort kopieren (z. B. `C:\Programme\Programmsperre\`), weil der Autostart auf diesen Pfad zeigt, und dann starten.

**Aus dem Quellcode:**
```bash
cd programmsperre
pip install -r requirements.txt
python app.py
```
Tests: `python -m pytest`

Die Einstellungen liegen unter `%APPDATA%\MeineApps\Programmsperre\einstellungen.json`. Der Autostart-Eintrag steht unter `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.

## Annahmen und Grenzen
- Programme werden über den **Prozessnamen** erkannt (z. B. `chrome.exe`). Eine umbenannte Kopie der EXE wird nicht erkannt.
- Die App läuft mit normalen Benutzerrechten. Wer Administratorrechte hat, kann sie über den Task-Manager beenden. Für Kinder empfiehlt sich deshalb ein **Standard-Benutzerkonto ohne Adminrechte**.
- Systemprogramme (Explorer, Task-Manager, svchost …) lassen sich absichtlich nicht sperren, damit sich Windows nicht „aufhängt“.
- Zwischen dem Programmstart und dem Anhalten können bis zu etwa 0,5 s vergehen. In dieser Zeit kann kurz ein Fenster aufblitzen.
- Wenn die Sperre die PIN für einen Browser verlangt, werden alle Prozesse dieses Browsers gemeinsam angehalten und freigegeben.
- PIN vergessen? Programmsperre über den Task-Manager beenden und die Datei `einstellungen.json` löschen. Danach kann eine neue PIN festgelegt werden (dafür braucht man Zugriff auf das Benutzerkonto).
