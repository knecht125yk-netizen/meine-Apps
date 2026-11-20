# Maschinenbau-Rechner (Windows)

Festigkeitsberechnungen für den Maschinenbau mit sichtbarem Rechenweg. Jede Formel wird als Formel angezeigt, Ergebnisse aktualisieren sich live, und die komplette Rechnung lässt sich als **PDF** oder **Word (.docx)** exportieren.

## Funktionen

| Bereich | Inhalt |
|---|---|
| **Biegung** | Einfeldträger und Kragträger, jeweils mit Einzel- oder Streckenlast. Auflagerkräfte, M_max, Biegespannung, Durchbiegung, **Biegelinie** und Momentenverlauf als Diagramm |
| **Knickung** | 4 Eulerfälle, Knicklänge, Trägheitsradius, **Schlankheitsgrad λ**, Euler (elastisch), **Tetmajer** bzw. Johnson-Parabel (unelastisch), Begrenzung auf Re, Knickspannungsdiagramm |
| **Zug / Druck** | Spannung, Dehnung, Längenänderung |
| **Torsion** | Voll- und Hohlwelle: τ_t, Verdrehwinkel, Schubspannungsverteilung |
| **Schub / Abscheren** | Abscheren (n Scherflächen), Querkraftschub (Rechteck, Rund, Rohr, I/U-Steg) |
| **Flächenpressung** | ebene und projizierte Fläche, erforderliche Länge |
| **Vergleichsspannung** | von Mises (GEH), Hauptspannungen, Mohrscher Kreis |
| **Schrauben** | M3 bis M30, Festigkeitsklassen 4.6 bis 12.9: Klemmkraft, Vorspannkraft, F_M,zul, Anziehdrehmoment |
| **Wellen** | Biegung und Torsion (P, n → M_t), Vergleichsspannung, Mindestdurchmesser |
| **Passfedern** | DIN 6885 Form A mit automatischer Maßwahl, Flächenpressung, erforderliche Länge |
| **Flächenträgheitsmomente** | Rechteck, Rund, Rohr, I-Profil, U-Profil (mit Querschnittsskizze) |
| **Sicherheitsnachweis** | allgemeiner Nachweis gegen Re oder Rm |
| **Werkstofftabelle** | 14 gängige Stähle und Aluminiumlegierungen mit E, G, Re/Rp0,2, Rm, ν, ρ, Tetmajer-Werten |

Jede Eingabe hat **Schieberegler und Zahlenfeld**. Bei Kräften und Längen arbeitet der Regler logarithmisch, damit man große Bereiche gut einstellen kann. Oben rechts auf jeder Seite stehen die Buttons **PDF exportieren** und **Word exportieren**. Der Export enthält Eingaben, Formeln, eingesetzte Werte, Zwischenergebnisse, den Nachweis und das Diagramm. Unten links kannst du einen Projekt- oder Bearbeiternamen für den Export eintragen.

## Starten

**Variante A: fertige .exe (empfohlen)**
1. Auf GitHub den Tab **Actions** öffnen und den Workflow **„Windows-Apps bauen“** wählen.
2. Den neuesten erfolgreichen Lauf öffnen und unten bei *Artifacts* **Maschinenbau-Rechner** herunterladen.
3. ZIP entpacken und `Maschinenbau-Rechner.exe` starten. Windows SmartScreen fragt evtl. nach; dann auf „Weitere Informationen“ und „Trotzdem ausführen“ klicken.

**Variante B: aus dem Quellcode (Python 3.11+)**
```bash
cd maschinenbau-rechner
pip install -r requirements.txt
python app.py
```

Tests: `python -m pytest`

## Annahmen und Grenzen
- Einheiten: N, mm, N/mm². Momente werden in N·m eingegeben.
- Biegung erfolgt um die y-Achse (Profil „hochkant“). Die Durchbiegung wird nach den Standardformeln für linear-elastisches Verhalten mit kleinen Verformungen berechnet.
- Werkstoffwerte sind typische Mindestwerte für Nenndicken ≤ 16 mm. Für verbindliche Auslegungen gelten die Norm bzw. das Datenblatt.
- Tetmajer-Geraden sind nur für S235 (310 − 1,14·λ) und E295/E335 (335 − 0,62·λ) hinterlegt. Für alle anderen Werkstoffe wird im unelastischen Bereich die **Johnson-Parabel** verwendet. Kurze Stäbe werden auf Re begrenzt.
- Torsion wird nur für Kreis- und Kreisringquerschnitte berechnet, weil es für Rechteck, I- und U-Profile keine einfache geschlossene Formel gibt.
- Die Schraubenberechnung ist vereinfacht nach VDI 2230 (Kraftverhältnis Φ = 0, kein Setzen, keine Temperatureinflüsse, D_Km ≈ 1,3·d) und ersetzt keinen vollständigen VDI-Nachweis.
- Wellen werden statisch nachgewiesen. Ein Dauerfestigkeitsnachweis nach DIN 743 ist nicht enthalten.
- I- und U-Profile werden parametrisch ohne Ausrundungsradien gerechnet, die Werte liegen daher leicht unter den Tabellenwerten.
