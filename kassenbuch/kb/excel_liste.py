"""Excel-Liste, die vom Kassenbuch automatisch gepflegt wird.

Nach jeder Änderung schreibt die App die komplette Arbeitsmappe neu: Kassenbuch (alle Jahre),
Übersicht mit Monatssummen (als Excel-Formeln), Kategorien, Rechnungen, Angebote, Kunden, Artikel.
Die App ist die „Quelle der Wahrheit“ – Änderungen direkt in Excel werden beim nächsten
Aktualisieren überschrieben (deshalb steht ein Hinweis in jedem Blatt).
"""
from __future__ import annotations

import datetime as dt
import os
import tempfile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from .daten import Datenbank

GELD = '#,##0.00 "€";[Red]-#,##0.00 "€"'
DATUM = "DD.MM.YYYY"
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]
HINWEIS = "Automatisch vom Kassenbuch erstellt – bitte Änderungen in der App vornehmen (hier wird überschrieben)."


def _d(iso):
    try:
        return dt.date.fromisoformat(iso[:10]) if iso else None
    except ValueError:
        return None


def _blatt(wb, titel, ueberschrift, kopf, zeilen, breiten, formate=None, tabelle=None):
    ws = wb.create_sheet(titel)
    ws["A1"] = ueberschrift
    ws["A1"].font = Font(bold=True, size=14, color="1F4E79")
    ws["A2"] = HINWEIS
    ws["A2"].font = Font(italic=True, size=9, color="808080")
    ws.append(kopf)
    for z in zeilen:
        ws.append(z)
    letzte = max(4, ws.max_row)
    for i, b in enumerate(breiten, 1):
        ws.column_dimensions[get_column_letter(i)].width = b
    for spalte, fmt in (formate or {}).items():
        for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=spalte, max_col=spalte):
            for c in row:
                c.number_format = fmt
    if zeilen:
        t = Table(displayName=tabelle or titel.replace(" ", ""), ref=f"A3:{get_column_letter(len(kopf))}{letzte}")
        t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(t)
    else:
        for c in ws[3]:
            c.font = Font(bold=True)
    ws.freeze_panes = "A4"
    return ws


def arbeitsmappe(db: Datenbank) -> Workbook:
    e = db.einstellungen()
    wb = Workbook()
    wb.remove(wb.active)
    heute = dt.date.today()

    # --- Kassenbuch (alle Jahre) ---
    buchungen = db.buchungen()
    zeilen = []
    for b in buchungen:
        d = _d(b["datum"])
        zeilen.append([d, d.year, d.month, b["belegnr"], b["beschreibung"], b["kategorie"],
                       b["betrag_cent"] / 100 if b["art"] == "E" else None,
                       b["betrag_cent"] / 100 if b["art"] == "A" else None, b["bestand_cent"] / 100])
    kb = _blatt(wb, "Kassenbuch", f"Kassenbuch – {e['firma_name']}",
                ["Datum", "Jahr", "Monat", "Beleg-Nr.", "Beschreibung", "Kategorie", "Einnahme", "Ausgabe", "Bestand"],
                zeilen, [12, 7, 7, 15, 40, 22, 14, 14, 14], {1: DATUM, 7: GELD, 8: GELD, 9: GELD}, "Kassenbuch")
    n = max(4, kb.max_row)
    E, A, J, M, K = (f"Kassenbuch!$G$4:$G${n}", f"Kassenbuch!$H$4:$H${n}", f"Kassenbuch!$B$4:$B${n}",
                     f"Kassenbuch!$C$4:$C${n}", f"Kassenbuch!$F$4:$F${n}")

    # --- Übersicht mit Formeln ---
    ue = wb.create_sheet("Übersicht", 0)
    ue["A1"] = f"Übersicht – {e['firma_name']}"
    ue["A1"].font = Font(bold=True, size=16, color="1F4E79")
    ue["A2"] = f"Stand: {dt.datetime.now():%d.%m.%Y %H:%M} · {HINWEIS}"
    ue["A2"].font = Font(italic=True, size=9, color="808080")
    ue["A4"], ue["B4"] = "Jahr der Monatsübersicht:", heute.year
    ue["B4"].font = Font(bold=True, color="C00000")
    ue["C4"] = "← Jahr hier ändern, die Tabelle rechnet automatisch neu"
    ue["C4"].font = Font(italic=True, size=9, color="808080")
    ue["A6"], ue["B6"] = "Aktueller Kassenbestand", db.kassenbestand() / 100
    offen = db.offene_rechnungen()
    ue["A7"], ue["B7"] = f"Offene Rechnungen ({len(offen)})", sum(r["summe_cent"] for r in offen) / 100
    ue["A8"], ue["B8"] = f"Umsatz {heute.year} (bezahlte Rechnungen)", db.umsatz(heute.year) / 100
    for c in ("B6", "B7", "B8"):
        ue[c].number_format = GELD
        ue[c].font = Font(bold=True)
    kopf = ["Monat", "Einnahmen", "Ausgaben", "Saldo"]
    for i, k in enumerate(kopf, 1):
        z = ue.cell(10, i, k)
        z.font = Font(bold=True, color="FFFFFF")
        z.fill = PatternFill("solid", fgColor="1F4E79")
    for m in range(1, 13):
        r = 10 + m
        ue.cell(r, 1, MONATE[m - 1])
        ue.cell(r, 2, f"=SUMIFS({E},{J},$B$4,{M},{m})").number_format = GELD
        ue.cell(r, 3, f"=SUMIFS({A},{J},$B$4,{M},{m})").number_format = GELD
        ue.cell(r, 4, f"=B{r}-C{r}").number_format = GELD
    ue.cell(23, 1, "Jahr gesamt").font = Font(bold=True)
    for col in "BCD":
        c = ue[f"{col}23"]
        c.value = f"=SUM({col}11:{col}22)"
        c.number_format = GELD
        c.font = Font(bold=True)
    ue.column_dimensions["A"].width = 38
    for col in "BCD":
        ue.column_dimensions[col].width = 16

    # --- Kategorien (Formeln, Jahr aus der Übersicht) ---
    kat = wb.create_sheet("Kategorien", 1)
    kat["A1"] = "Summen je Kategorie"
    kat["A1"].font = Font(bold=True, size=14, color="1F4E79")
    kat["A2"] = "Jahr wie in der Übersicht (Zelle B4)."
    kat["A2"].font = Font(italic=True, size=9, color="808080")
    for i, k in enumerate(["Art", "Kategorie", "Summe"], 1):
        z = kat.cell(3, i, k)
        z.font = Font(bold=True, color="FFFFFF")
        z.fill = PatternFill("solid", fgColor="1F4E79")
    r = 4
    for art, spalte in (("E", E), ("A", A)):
        for name in db.kategorien(art):
            kat.cell(r, 1, "Einnahme" if art == "E" else "Ausgabe")
            kat.cell(r, 2, name)
            kat.cell(r, 3, f"=SUMIFS({spalte},{J},Übersicht!$B$4,{K},B{r})").number_format = GELD
            r += 1
    kat.column_dimensions["A"].width = 12
    kat.column_dimensions["B"].width = 26
    kat.column_dimensions["C"].width = 16

    # --- Rechnungen / Angebote ---
    for typ, titel in (("rechnung", "Rechnungen"), ("angebot", "Angebote")):
        zeilen = []
        for b in sorted(db.belege(typ), key=lambda x: (x["datum"], x["id"])):
            zeilen.append([b["nummer"], _d(b["datum"]), b["kunde"] or (b["anschrift"].splitlines() or [""])[0],
                           b["betreff"], b["summe_cent"] / 100, b["status"], _d(b["faellig"]),
                           _d(b["bezahlt_am"]) if typ == "rechnung" else None])
        _blatt(wb, titel, titel,
               ["Nummer", "Datum", "Kunde", "Betreff", "Betrag", "Status",
                "Fällig" if typ == "rechnung" else "Gültig bis", "Bezahlt am" if typ == "rechnung" else "–"],
               zeilen, [15, 12, 28, 32, 14, 22, 12, 12], {2: DATUM, 5: GELD, 7: DATUM, 8: DATUM}, titel)

    # --- Stammdaten ---
    _blatt(wb, "Kunden", "Kunden", ["Nr.", "Name", "Zusatz", "Straße", "PLZ", "Ort", "E-Mail", "Telefon"],
           [[k["nummer"], k["name"], k["zusatz"], k["strasse"], k["plz"], k["ort"], k["email"], k["telefon"]]
            for k in db.kunden()], [9, 28, 22, 26, 8, 18, 28, 16], tabelle="Kunden")
    _blatt(wb, "Artikel", "Artikel & Leistungen", ["Nr.", "Bezeichnung", "Beschreibung", "Einheit", "Preis"],
           [[a["nummer"], a["bezeichnung"], a["beschreibung"], a["einheit"], a["preis_cent"] / 100]
            for a in db.artikel()], [9, 30, 40, 10, 12], {5: GELD}, "Artikel")
    for ws in wb.worksheets:
        ws.sheet_view.zoomScale = 110
        for row in ws.iter_rows(min_row=3, max_row=3):
            for c in row:
                c.alignment = Alignment(vertical="center")
    return wb


def schreiben(db: Datenbank, pfad: str):
    """Arbeitsmappe atomar schreiben. PermissionError, wenn die Datei gerade in Excel geöffnet ist."""
    wb = arbeitsmappe(db)
    ordner = os.path.dirname(os.path.abspath(pfad))
    os.makedirs(ordner, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="~kassenbuch_", suffix=".xlsx", dir=ordner)
    os.close(fd)
    try:
        wb.save(tmp)
        os.replace(tmp, pfad)   # schlägt unter Windows fehl, solange Excel die Datei offen hat
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
