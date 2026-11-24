import os
import subprocess
import shutil

import pytest
from openpyxl import load_workbook

from kb.daten import Beleg, Datenbank, Position
from kb.excel_liste import schreiben


@pytest.fixture
def db():
    d = Datenbank(":memory:")
    d.einstellungen_speichern({"firma_name": "Test", "kasse_anfangsbestand_cent": "10000"})
    k = d.kunde_speichern({"name": "Kunde A", "ort": "Ort"})
    r = d.beleg_speichern(Beleg("rechnung", datum="2026-03-01", kunde_id=k, positionen=[Position("X", 2, "Std.", 5000)]))
    d.als_bezahlt(r.id, "2026-03-05")
    d.beleg_speichern(Beleg("angebot", datum="2026-04-01", kunde_id=k, positionen=[Position("Y", 1, "Stk.", 999)]))
    d.buchen("2026-03-10", "A", 2500, "Material", "Holz")
    d.buchen("2025-12-30", "E", 700, "Sonstige Einnahmen")
    d.artikel_speichern({"bezeichnung": "Stunde", "einheit": "Std.", "preis_cent": 5000})
    return d


def test_blaetter_und_inhalte(db, tmp_path):
    p = tmp_path / "unterordner" / "Kassenbuch.xlsx"
    schreiben(db, str(p))
    wb = load_workbook(p)
    assert wb.sheetnames == ["Übersicht", "Kategorien", "Kassenbuch", "Rechnungen", "Angebote", "Kunden", "Artikel"]
    kb = wb["Kassenbuch"]
    werte = [[c.value for c in row] for row in kb.iter_rows(min_row=4, max_row=kb.max_row)]
    assert len(werte) == 3
    assert werte[-1][8] == pytest.approx((10000 + 700 + 10000 - 2500) / 100)
    assert wb["Rechnungen"]["A4"].value == "RE-2026-0001" and wb["Rechnungen"]["E4"].value == 100
    assert wb["Übersicht"]["B13"].value.startswith("=SUMIFS(")
    assert not [f for f in os.listdir(p.parent) if f.startswith("~kassenbuch_")]  # kein Temp-Rest


def test_ueberschreiben(db, tmp_path):
    p = tmp_path / "k.xlsx"
    schreiben(db, str(p))
    db.buchen("2026-05-01", "E", 100, "Erlöse")
    schreiben(db, str(p))
    assert load_workbook(p)["Kassenbuch"].max_row == 7


@pytest.mark.skipif(not shutil.which("soffice") and not shutil.which("libreoffice"), reason="LibreOffice fehlt")
def test_formeln_rechnen(db, tmp_path):
    """Formeln mit LibreOffice neu berechnen lassen und Monatssummen prüfen."""
    p = tmp_path / "k.xlsx"
    schreiben(db, str(p))
    office = shutil.which("soffice") or shutil.which("libreoffice")
    subprocess.run([office, "--headless", "--convert-to", "xlsx", "--outdir", str(tmp_path / "out"), str(p)],
                   check=True, capture_output=True, timeout=120)
    wb = load_workbook(tmp_path / "out" / "k.xlsx", data_only=True)
    ue = wb["Übersicht"]
    assert ue["B13"].value == pytest.approx(100)   # März Einnahmen 2026
    assert ue["C13"].value == pytest.approx(25)
    assert ue["D23"].value == pytest.approx(75)
