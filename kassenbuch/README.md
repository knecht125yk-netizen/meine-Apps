# Kassenbuch & Rechnungen (Windows)

Einfache Buchhaltung für ein Kleingewerbe nach der **Kleinunternehmerregelung (§ 19 UStG)**. Es wird keine Umsatzsteuer ausgewiesen, und der Pflichthinweis steht automatisch auf jedem Angebot und jeder Rechnung.

## Funktionen
- **Firmendaten und Logo** werden einmal unter *Einstellungen* hinterlegt und erscheinen auf allen PDFs (Briefkopf, Fußzeile mit Bank und Steuernummer).
- **Kundenstamm** mit automatischen Kundennummern (K0001 …) und **Artikel- bzw. Leistungsstamm** mit Einheiten (Std., Stk., pauschal …).
- **Angebote mit wenig Aufwand:** Kunde wählen, Artikel suchen, Menge eingeben, „+ Artikel“ klicken. Texte, Datum und Gültigkeit werden automatisch vorbelegt.
- **Per Klick ein Angebot in eine Rechnung umwandeln** (Button „→ In Rechnung umwandeln“). Positionen und Betreff werden übernommen, und das Angebot wird als „in Rechnung umgewandelt“ markiert.
- **Fortlaufende Rechnungsnummern** wie `RE-2026-0001`. Präfix, Stellenzahl und Jahresreset sind einstellbar, eine Startnummer lässt sich für den Umstieg festlegen. Rechnungen werden nie gelöscht, sondern **storniert**, damit die Nummern lückenlos bleiben. Bezahlte Rechnungen sind schreibgeschützt.
- **Zahlungseingang:** „Als bezahlt markieren“ bucht den Betrag automatisch als Einnahme ins Kassenbuch (abschaltbar).
- **Kassenbuch** mit Einnahmen und Ausgaben, Kategorien (eigene Kategorien sind möglich), laufendem Kassenbestand und Anfangsbestand.
- **Monats- und Jahresübersicht** sowie eine Auswertung nach Kategorien.
- **Export:** Angebote und Rechnungen als **PDF** (DIN-5008-Layout mit Adressfenster), das Kassenbuch als **CSV** (Excel-kompatibel, Semikolon), **Excel (.xlsx**, mit Monats- und Kategorienblatt) und **PDF**.
- **Startseite** mit Umsatz, offenen und überfälligen Rechnungen, Kassenbestand und einer **Ampel für die Kleinunternehmergrenze** (seit 2025: Vorjahr ≤ 25.000 €, laufendes Jahr ≤ 100.000 €).
- **Datensicherung:** Täglich wird automatisch gesichert (die letzten 14 Tage werden behalten). Zusätzlich gibt es den Button „Datensicherung erstellen …“.

## Starten
**.exe:** Auf GitHub unter **Actions** den Workflow **„Windows-Apps bauen“** öffnen und beim neuesten Lauf das Artefakt **Kassenbuch** herunterladen. Dann entpacken und `Kassenbuch.exe` starten.

**Aus dem Quellcode:**
```bash
cd kassenbuch
pip install -r requirements.txt
python app.py
```
Tests: `python -m pytest`

Beim ersten Start öffnet sich die Seite *Einstellungen*. Trag dort deine Firmendaten (mindestens Name, Anschrift und Steuernummer) ein, wähl optional ein Logo und klick auf **Speichern**.

## Wo liegen die Daten?
Die SQLite-Datei `kassenbuch.db` liegt unter `%APPDATA%\MeineApps\Kassenbuch\` (über *Einstellungen → Datenordner öffnen* erreichbar). Die automatischen Sicherungen liegen im Unterordner `Sicherungen`.

## Annahmen und Hinweise
- Beträge werden intern in Cent gespeichert. Jede Position wird kaufmännisch auf den Cent gerundet und dann summiert.
- Als „Umsatz“ für die Kleinunternehmergrenze zählen **bezahlte** Rechnungen, und zwar im Jahr des Zahlungseingangs (Zuflussprinzip).
- Die Nummernkreise für Rechnungen und Angebote sind getrennt. Ändert man eine Rechnung, solange sie noch offen ist, bleibt ihre Nummer erhalten.
- Die Rechnungen enthalten die Pflichtangaben nach § 14 UStG für Kleinunternehmer: Name und Anschrift beider Seiten, Steuernummer, Datum, fortlaufende Nummer, Leistung, Menge, Leistungsdatum, Betrag und den § 19-Hinweis.
- Kleinunternehmer dürfen weiterhin PDF-Rechnungen schreiben. Eine E-Rechnung (XRechnung/ZUGFeRD) ist nicht enthalten.
- Das Kassenbuch dient der übersichtlichen Aufzeichnung. Für eine streng GoBD-konforme, unveränderbare Kassenführung (z. B. bei Bargeschäften mit Registrierkasse) ist eine zertifizierte Lösung nötig. Im Zweifel bitte Steuerberater fragen.
