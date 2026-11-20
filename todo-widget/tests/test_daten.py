import datetime as dt

import pytest

from todo.daten import HOCH, MITTEL, NIEDRIG, Aufgabe, Liste, faellig_text, schnelleingabe

HEUTE = dt.date(2026, 11, 20)  # Freitag


def test_schnelleingabe():
    assert schnelleingabe("Zahnarzt anrufen !hoch @morgen", HEUTE) == ("Zahnarzt anrufen", HOCH, "2026-11-21")
    assert schnelleingabe("Müll !", HEUTE) == ("Müll", HOCH, "")
    assert schnelleingabe("Rasen @mo !niedrig", HEUTE) == ("Rasen", NIEDRIG, "2026-11-23")
    assert schnelleingabe("Wochenbericht @fr", HEUTE)[2] == "2026-11-27"   # nächster, nicht heutiger Freitag
    assert schnelleingabe("Geschenk @24.12.", HEUTE)[2] == "2026-12-24"
    assert schnelleingabe("Steuer @31.5.", HEUTE)[2] == "2027-05-31"       # vergangenes Datum -> nächstes Jahr
    assert schnelleingabe("Termin @3.2.27", HEUTE)[2] == "2027-02-03"
    assert schnelleingabe("Mail an @peter", HEUTE) == ("Mail an @peter", MITTEL, "")
    assert schnelleingabe("Kaputt @31.2.", HEUTE) == ("Kaputt @31.2.", MITTEL, "")


def test_faellig_text():
    a = Aufgabe("x", faellig="2026-11-20")
    assert faellig_text(a, HEUTE) == "Heute"
    a.faellig = "2026-11-21"
    assert faellig_text(a, HEUTE) == "Morgen"
    a.faellig = "2026-11-17"
    assert faellig_text(a, HEUTE) == "seit 3 Tagen"
    a.faellig = "2026-11-24"
    assert faellig_text(a, HEUTE) == "Di, 24.11."
    a.faellig = "2027-01-15"
    assert faellig_text(a, HEUTE) == "15.01.2027"
    a.faellig = ""
    assert faellig_text(a, HEUTE) == ""


@pytest.fixture
def liste(tmp_path):
    return Liste(str(tmp_path / "a" / "todo.json"))


def test_hinzufuegen_speichern_laden(liste):
    a = liste.hinzufuegen("Einkaufen !hoch")
    liste.hinzufuegen("Lesen", NIEDRIG, "2030-01-01")
    liste.einstellungen.symbol_x = 100
    liste.speichern()
    l2 = Liste(liste.pfad)
    assert [x.titel for x in l2.aufgaben] == ["Einkaufen", "Lesen"]
    assert l2.aufgaben[0].prioritaet == HOCH and l2.aufgaben[0].id == a.id
    assert l2.aufgaben[1].faellig == "2030-01-01" and l2.aufgaben[1].prioritaet == NIEDRIG
    assert l2.einstellungen.symbol_x == 100
    with pytest.raises(ValueError):
        liste.hinzufuegen("   !hoch")


def test_umschalten_loeschen(liste):
    a = liste.hinzufuegen("A")
    b = liste.hinzufuegen("B")
    liste.umschalten(a.id)
    assert a.erledigt and a.erledigt_am
    assert liste.anzahl_offen() == 1
    liste.umschalten(a.id)
    assert not a.erledigt and a.erledigt_am == ""
    liste.umschalten(b.id)
    assert liste.erledigte_entfernen() == 1
    assert [x.titel for x in liste.aufgaben] == ["A"]
    liste.loeschen(a.id)
    assert liste.aufgaben == []


def test_sortierung(liste):
    liste.aufgaben = [
        Aufgabe("ohne Datum niedrig", NIEDRIG, erstellt="1"),
        Aufgabe("ohne Datum hoch", HOCH, erstellt="2"),
        Aufgabe("später", MITTEL, "2030-01-01", erstellt="3"),
        Aufgabe("überfällig", NIEDRIG, "2020-01-01", erstellt="4"),
        Aufgabe("erledigt", HOCH, "2019-01-01", erledigt=True, erledigt_am="2026", erstellt="5"),
    ]
    assert [a.titel for a in liste.sortiert()] == ["überfällig", "später", "ohne Datum hoch",
                                                   "ohne Datum niedrig", "erledigt"]
    assert "erledigt" not in [a.titel for a in liste.sortiert(erledigte=False)]
    assert liste.anzahl_ueberfaellig() == 1


def test_aendern(liste):
    a = liste.hinzufuegen("Alt")
    liste.aendern(a.id, titel="Neu", prioritaet=HOCH, faellig="2026-12-01")
    assert Liste(liste.pfad).aufgaben[0].titel == "Neu"
    with pytest.raises(ValueError):
        liste.aendern(a.id, titel=" ")
    with pytest.raises(KeyError):
        liste.aendern(a.id, unsinn=1)


def test_defekte_datei_wird_gesichert(tmp_path):
    p = tmp_path / "todo.json"
    p.write_text("{kaputt")
    l = Liste(str(p))
    assert l.aufgaben == []
    assert (tmp_path / "todo.json.defekt").exists()
