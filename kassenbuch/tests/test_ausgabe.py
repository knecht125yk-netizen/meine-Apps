import csv

import pytest

from kb.ausgabe import beleg_pdf, kassenbuch_csv, kassenbuch_excel, kassenbuch_pdf
from kb.daten import Beleg, Datenbank, Position


@pytest.fixture
def db():
    d = Datenbank(":memory:")
    d.einstellungen_speichern({"firma_name": "Muster & Söhne", "inhaber": "Erika Muster", "iban": "DE00 1234",
                               "steuernummer": "12/345/67890", "strasse": "Weg 1", "plz": "11111", "ort": "Ort"})
    k = d.kunde_speichern({"name": "Kunde Ä", "strasse": "Str. 2", "plz": "22222", "ort": "Stadt"})
    d.beleg_speichern(Beleg("rechnung", datum="2026-04-01", kunde_id=k,
                            positionen=[Position(f"Position {i}", 1.5, "Std.", 4000 + i) for i in range(30)]))
    d.buchen("2026-04-02", "E", 12345, "Erlöse", "Barverkauf", "B-1")
    d.buchen("2026-04-03", "A", 1999, "Porto", "Briefmarken")
    return d


def test_beleg_pdf_mehrseitig(db, tmp_path):
    p = tmp_path / "r.pdf"
    beleg_pdf(db, db.beleg(1), str(p))
    data = p.read_bytes()
    assert data[:4] == b"%PDF"
    assert data.count(b"/Type /Page") >= 3  # >= 2 Seiten + Pages-Objekt


def test_kassenbuch_csv(db, tmp_path):
    p = tmp_path / "k.csv"
    kassenbuch_csv(db, str(p), 2026)
    rows = list(csv.reader(open(p, encoding="utf-8-sig"), delimiter=";"))
    assert rows[0][0] == "Datum"
    assert rows[1][4] == "123,45" and rows[2][5] == "19,99" and rows[2][6] == "103,46"


def test_kassenbuch_excel_und_pdf(db, tmp_path):
    from openpyxl import load_workbook
    p = tmp_path / "k.xlsx"
    kassenbuch_excel(db, str(p), 2026)
    wb = load_workbook(p)
    assert wb.sheetnames == ["Kassenbuch", "Monatsübersicht", "Kategorien"]
    assert wb["Kassenbuch"]["E4"].value == pytest.approx(123.45)
    kassenbuch_pdf(db, str(tmp_path / "k.pdf"), 2026)
    kassenbuch_pdf(db, str(tmp_path / "k4.pdf"), 2026, 4)
    assert (tmp_path / "k4.pdf").read_bytes()[:4] == b"%PDF"
