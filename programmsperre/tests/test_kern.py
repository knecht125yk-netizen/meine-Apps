import json

import pytest

from sperre import kern
from sperre.kern import Konfiguration, Sperre, pin_gueltig


class Uhr:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


@pytest.fixture(autouse=True)
def schnell(monkeypatch):
    monkeypatch.setattr(kern, "ITERATIONEN", 1000)


@pytest.fixture
def s():
    uhr = Uhr()
    sp = Sperre(Konfiguration(), uhr)
    sp.pin_setzen("4711")
    sp.programm_hinzufuegen("C:\\Spiele\\Minecraft.EXE", "Minecraft")
    sp.programm_hinzufuegen("chrome")
    return sp


def test_pin_regeln():
    assert pin_gueltig("12a4")
    assert pin_gueltig("123")
    assert pin_gueltig("1111")
    assert pin_gueltig("4711") is None


def test_pin_wird_nur_als_hash_gespeichert(s, tmp_path):
    p = tmp_path / "c.json"
    s.k.speichern(str(p))
    text = p.read_text()
    assert "4711" not in text
    d = json.loads(text)
    assert len(d["pin_hash"]) == 64 and len(d["pin_salt"]) == 32


def test_pin_pruefen(s):
    assert s.pin_pruefen("4711")
    assert not s.pin_pruefen("1234")
    assert s.restversuche() == 4


def test_fehlversuche_sperren_eingabe(s):
    for _ in range(5):
        assert not s.pin_pruefen("0000")
    assert s.wartezeit() == 60
    assert not s.pin_pruefen("4711")      # auch richtige PIN während der Wartezeit abgelehnt
    s.uhr.t += 61
    assert s.pin_pruefen("4711")
    for _ in range(5):
        s.pin_pruefen("0000")
    assert s.wartezeit() == 60            # nach Erfolg zurückgesetzt


def test_wartezeit_verdoppelt_sich(s):
    for _ in range(5):
        s.pin_pruefen("0000")
    s.uhr.t += 61
    for _ in range(5):
        s.pin_pruefen("0000")
    assert s.wartezeit() == 120


def test_programmnamen_normalisiert(s):
    assert s.namen() == {"minecraft.exe", "chrome.exe"}
    assert s.ist_gesperrt("MINECRAFT.exe")
    assert not s.ist_gesperrt("notepad.exe")
    with pytest.raises(ValueError):
        s.programm_hinzufuegen("chrome.exe")
    with pytest.raises(ValueError):
        s.programm_hinzufuegen("explorer.exe")


def test_freigabe_mit_ablauf(s):
    s.k.freigabe_minuten = 30
    s.freigeben("chrome.exe")
    assert not s.ist_gesperrt("chrome.exe")
    assert s.ist_gesperrt("minecraft.exe")
    assert 1790 <= s.restzeit("chrome.exe") <= 1800
    s.uhr.t += 28 * 60 + 1
    assert s.bald_ablaufend() == ["chrome.exe"]
    assert s.bald_ablaufend() == []       # nur einmal warnen
    s.uhr.t += 2 * 60
    assert s.abgelaufen() == ["chrome.exe"]
    assert s.ist_gesperrt("chrome.exe")


def test_pause(s):
    s.pausieren(10)
    assert not s.ist_gesperrt("chrome.exe")
    s.uhr.t += 601
    assert s.ist_gesperrt("chrome.exe")


def test_konfiguration_laden_speichern(s, tmp_path):
    p = str(tmp_path / "sub" / "c.json")
    s.k.freigabe_minuten = 45
    s.k.speichern(p)
    k2 = Konfiguration.laden(p)
    assert k2.freigabe_minuten == 45
    assert [x.name for x in k2.programme] == ["minecraft.exe", "chrome.exe"]
    s2 = Sperre(k2)
    assert s2.pin_pruefen("4711")


def test_entfernen(s):
    s.freigeben("chrome.exe")
    s.programm_entfernen("Chrome.exe")
    assert "chrome.exe" not in s.namen()
    assert not s.ist_gesperrt("chrome.exe")
