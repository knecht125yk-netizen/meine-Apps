import pytest

from kb.daten import (Beleg, Datenbank, Position, euro, parse_euro, zeilensumme,
                      KLEINUNTERNEHMER_HINWEIS)


@pytest.fixture
def db():
    d = Datenbank(":memory:")
    d.einstellungen_speichern({"firma_name": "Test", "kasse_anfangsbestand_cent": "10000"})
    return d


@pytest.fixture
def kunde(db):
    return db.kunde_speichern({"name": "Max Mustermann", "strasse": "Hauptstr. 1", "plz": "12345", "ort": "Berlin"})


def rechnung(db, kunde, datum="2026-03-10", pos=None):
    b = Beleg("rechnung", datum=datum, kunde_id=kunde,
              positionen=pos or [Position("Arbeitszeit", 2.5, "Std.", 4500), Position("Material", 1, "Stk.", 1999)])
    return db.beleg_speichern(b)


# --- Geld ------------------------------------------------------------------

def test_euro_format_und_parser():
    assert euro(123456) == "1.234,56 €"
    assert euro(-5) == "-0,05 €"
    assert euro(100, False) == "1,00"
    assert parse_euro("1.234,56") == 123456
    assert parse_euro("1234.5") == 123450
    assert parse_euro("12 €") == 1200
    assert parse_euro("0,005") == 1          # kaufmännisch gerundet
    assert parse_euro("") == 0


def test_zeilensumme_rundung():
    assert zeilensumme(2.5, 4500) == 11250
    assert zeilensumme(1.5, 333) == 500       # 499,5 -> 500
    assert zeilensumme(3, 1999) == 5997
    assert zeilensumme(0.333, 1000) == 333


# --- Rechnungen ---------------------------------------------------------------

def test_rechnungsbetrag(db, kunde):
    r = rechnung(db, kunde)
    assert r.summe_cent == 11250 + 1999
    geladen = db.beleg(r.id)
    assert geladen.summe_cent == 13249
    assert [p.bezeichnung for p in geladen.positionen] == ["Arbeitszeit", "Material"]
    assert db.belege("rechnung")[0]["summe_cent"] == 13249


def test_fortlaufende_nummern(db, kunde):
    n = [rechnung(db, kunde).nummer for _ in range(3)]
    assert n == ["RE-2026-0001", "RE-2026-0002", "RE-2026-0003"]
    # neues Jahr beginnt wieder bei 1
    assert rechnung(db, kunde, "2027-01-02").nummer == "RE-2027-0001"
    # Angebote haben einen eigenen Nummernkreis
    a = db.beleg_speichern(Beleg("angebot", datum="2026-05-01", kunde_id=kunde, positionen=[Position("X", 1, "Stk.", 100)]))
    assert a.nummer == "AN-2026-0001"


def test_nummer_ohne_jahresreset_und_startwert(db, kunde):
    db.einstellungen_speichern({"nummer_jaehrlich": "0", "rechnung_praefix": "R", "nummer_stellen": "5"})
    db.zaehler_setzen("rechnung", 2026, 41)
    assert db.naechste_nummer_vorschau("rechnung", "2026-01-01") == "R-00042"
    assert db.naechste_nummer_vorschau("rechnung", "2026-01-01") == "R-00042"  # Vorschau verbraucht nichts
    assert rechnung(db, kunde).nummer == "R-00042"
    assert rechnung(db, kunde, "2027-01-01").nummer == "R-00043"


def test_nummer_bleibt_beim_bearbeiten(db, kunde):
    r = rechnung(db, kunde)
    r.betreff = "Neu"
    r.positionen.append(Position("Extra", 1, "Stk.", 500))
    db.beleg_speichern(r)
    assert db.beleg(r.id).nummer == "RE-2026-0001"
    assert db.beleg(r.id).summe_cent == 13749


def test_standardtexte_und_faelligkeit(db, kunde):
    r = rechnung(db, kunde, "2026-03-10")
    assert r.faellig == "2026-03-24"
    assert r.leistungsdatum == "2026-03-10"
    assert "Max Mustermann" in r.anschrift
    assert db.einstellung("kleinunternehmer_hinweis") == KLEINUNTERNEHMER_HINWEIS
    assert "§ 19 UStG" in KLEINUNTERNEHMER_HINWEIS


def test_validierung(db, kunde):
    with pytest.raises(ValueError):
        db.beleg_speichern(Beleg("rechnung", kunde_id=kunde))
    with pytest.raises(ValueError):
        db.beleg_speichern(Beleg("rechnung", positionen=[Position("X")]))


# --- Angebot -> Rechnung ----------------------------------------------------

def test_angebot_umwandeln(db, kunde):
    a = db.beleg_speichern(Beleg("angebot", datum="2026-02-01", kunde_id=kunde, betreff="Gartenarbeit",
                                 positionen=[Position("Rasen mähen", 3, "Std.", 3500)]))
    r = db.angebot_zu_rechnung(a.id, "2026-02-20")
    assert r.typ == "rechnung" and r.nummer == "RE-2026-0001"
    assert r.summe_cent == a.summe_cent == 10500
    assert r.betreff == "Gartenarbeit"
    assert r.angebot_id == a.id
    assert db.beleg(a.id).status == "in Rechnung umgewandelt"
    with pytest.raises(ValueError):
        db.angebot_zu_rechnung(a.id)
    # nach Storno wieder umwandelbar
    db.stornieren(r.id)
    assert db.beleg(a.id).status == "angenommen"
    r2 = db.angebot_zu_rechnung(a.id, "2026-02-21")
    assert r2.nummer == "RE-2026-0002"


def test_rechnung_nicht_loeschbar_aber_stornierbar(db, kunde):
    r = rechnung(db, kunde)
    with pytest.raises(ValueError):
        db.angebot_loeschen(r.id)
    db.stornieren(r.id)
    assert db.beleg(r.id).status == "storniert"


# --- Bezahlung & Kassenbuch -------------------------------------------------

def test_bezahlt_bucht_einnahme(db, kunde):
    r = rechnung(db, kunde)
    kid = db.als_bezahlt(r.id, "2026-03-15")
    assert kid
    b = db.buchungen(2026)
    assert len(b) == 1 and b[0]["betrag_cent"] == 13249 and b[0]["belegnr"] == r.nummer
    assert db.kassenbestand() == 10000 + 13249
    assert db.umsatz(2026) == 13249
    # doppelt bezahlen bucht nicht doppelt
    db.als_bezahlt(r.id, "2026-03-15")
    assert len(db.buchungen(2026)) == 1
    with pytest.raises(ValueError):
        db.beleg_speichern(db.beleg(r.id))
    # Storno entfernt die Buchung
    db.stornieren(r.id)
    assert db.buchungen(2026) == []


def test_kassenbuch_bestand_und_uebersichten(db):
    db.buchen("2026-01-05", "E", 5000, "Erlöse", "Barverkauf")
    db.buchen("2026-01-20", "A", 1250, "Büromaterial", "Papier")
    db.buchen("2026-02-03", "A", 2000, "Porto")
    db.buchen("2025-12-31", "E", 100, "Sonstige Einnahmen")
    alle = db.buchungen()
    assert [b["bestand_cent"] for b in alle] == [10100, 15100, 13850, 11850]
    jan = db.buchungen(2026, 1)
    assert len(jan) == 2 and jan[-1]["bestand_cent"] == 13850
    m = db.monatsuebersicht(2026)
    assert m[0] == {"monat": 1, "einnahmen": 5000, "ausgaben": 1250, "saldo": 3750}
    assert m[1]["ausgaben"] == 2000 and m[2]["saldo"] == 0
    k = {(x["art"], x["kategorie"]): x["summe"] for x in db.kategorieuebersicht(2026)}
    assert k[("E", "Erlöse")] == 5000 and k[("A", "Porto")] == 2000
    assert db.kassenbestand("2026-01-31") == 13850


def test_buchung_validierung(db):
    with pytest.raises(ValueError):
        db.buchen("2026-01-01", "E", 0, "Erlöse")
    with pytest.raises(ValueError):
        db.buchen("2026-01-01", "X", 100, "Erlöse")
    with pytest.raises(ValueError):
        db.buchen("01.01.2026", "E", 100, "Erlöse")
    db.buchen("2026-01-01", "A", 100, "Neue Kategorie")
    assert "Neue Kategorie" in db.kategorien("A")


def test_kunde_mit_belegen_nicht_loeschbar(db, kunde):
    rechnung(db, kunde)
    with pytest.raises(ValueError):
        db.kunde_loeschen(kunde)
    k2 = db.kunde_speichern({"name": "Weg"})
    db.kunde_loeschen(k2)
    assert all(k["name"] != "Weg" for k in db.kunden())


def test_dateidatenbank_persistiert(tmp_path):
    p = str(tmp_path / "kb.db")
    d = Datenbank(p)
    kid = d.kunde_speichern({"name": "A"})
    d.beleg_speichern(Beleg("rechnung", datum="2026-01-01", kunde_id=kid, positionen=[Position("X", 1, "Stk.", 100)]))
    d.schliessen()
    d2 = Datenbank(p)
    assert d2.belege("rechnung")[0]["nummer"] == "RE-2026-0001"
