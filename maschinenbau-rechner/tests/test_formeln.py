import math

import pytest

from mbrechner import formeln as f
from mbrechner.profile import berechne
from mbrechner.werkstoffe import werkstoff

S235 = werkstoff("S235JR")


def approx(x, rel=1e-6):
    return pytest.approx(x, rel=rel)


# --- Profile ---------------------------------------------------------------

def test_rechteck():
    q = berechne("Rechteck", {"b": 20, "h": 40})
    assert q.A == 800
    assert q.Iy == approx(20 * 40 ** 3 / 12)
    assert q.Wy == approx(20 * 40 ** 2 / 6)
    assert q.Iz == approx(40 * 20 ** 3 / 12)


def test_rund_und_rohr():
    q = berechne("Rund", {"d": 30})
    assert q.Iy == approx(math.pi * 30 ** 4 / 64)
    assert q.Wt == approx(math.pi * 30 ** 3 / 16)
    r = berechne("Rohr", {"D": 40, "d": 30})
    assert r.A == approx(math.pi * (40 ** 2 - 30 ** 2) / 4)
    assert r.Ip == approx(math.pi * (40 ** 4 - 30 ** 4) / 32)
    with pytest.raises(ValueError):
        berechne("Rohr", {"D": 30, "d": 40})


def test_i_profil_ipe200_naeherung():
    # IPE 200 (ohne Ausrundungsradien): Tabelle Iy = 1943 cm⁴ inkl. Radien
    q = berechne("I-Profil", {"h": 200, "b": 100, "s": 5.6, "t": 8.5})
    assert q.A == approx(2 * 100 * 8.5 + 183 * 5.6)
    assert 1.80e7 < q.Iy < 1.95e7


def test_u_profil_schwerpunkt():
    q = berechne("U-Profil", {"h": 100, "b": 50, "s": 6, "t": 8.5})
    assert 0 < q.ez < 25
    assert q.Iz > 0 and q.Iy > q.Iz


# --- Biegung ---------------------------------------------------------------

def test_einfeldtraeger_mitte_entspricht_standardformel():
    q = berechne("Rechteck", {"b": 20, "h": 40})
    F, l = 1000, 1000
    r = f.biegung(f.LASTFAELLE[0], F, l, l / 2, q, S235)
    assert r.wert("M_max") == approx(F * l / 4)
    assert r.wert("f_max") == approx(F * l ** 3 / (48 * S235.E * q.Iy))
    assert r.wert(r"\sigma_b") == approx(F * l / 4 / q.Wy)
    # Biegelinie: Maximum stimmt mit Formel überein
    assert max(r.plot["w"]) == approx(r.wert("f_max"), rel=1e-3)


def test_einfeldtraeger_ausmittig_numerisch():
    q = berechne("Rund", {"d": 30})
    r = f.biegung(f.LASTFAELLE[0], 2000, 800, 200, q, S235)
    assert max(r.plot["w"]) == approx(r.wert("f_max"), rel=1e-3)
    assert r.wert("F_A") + r.wert("F_B") == approx(2000)


def test_streckenlast_und_kragtraeger():
    q = berechne("Rechteck", {"b": 20, "h": 40})
    E, I = S235.E, q.Iy
    r = f.biegung(f.LASTFAELLE[1], 2.0, 1000, 0, q, S235)
    assert r.wert("M_max") == approx(2 * 1000 ** 2 / 8)
    assert r.wert("f_max") == approx(5 * 2 * 1000 ** 4 / (384 * E * I))
    r = f.biegung(f.LASTFAELLE[2], 500, 600, 0, q, S235)
    assert r.wert("f_max") == approx(500 * 600 ** 3 / (3 * E * I))
    assert r.plot["w"][-1] == approx(r.wert("f_max"))
    r = f.biegung(f.LASTFAELLE[3], 1.0, 600, 0, q, S235)
    assert r.wert("f_max") == approx(600 ** 4 / (8 * E * I))
    assert r.plot["w"][-1] == approx(r.wert("f_max"))


def test_biegung_nachweis():
    q = berechne("Rechteck", {"b": 20, "h": 40})
    r = f.biegung(f.LASTFAELLE[2], 500, 600, 0, q, S235, S_erf=1.5)
    sigma = 500 * 600 / q.Wy
    assert r.nachweise[0].vorhanden == approx(235 / sigma)
    assert r.nachweise[0].erfuellt == (235 / sigma >= 1.5)


# --- Knickung --------------------------------------------------------------

def test_euler_elastisch():
    q = berechne("Rund", {"d": 20})
    r = f.knickung(2, 2000, 1000, q, S235)
    i = 20 / 4
    lam = 2000 / i
    assert r.wert(r"\lambda") == approx(lam)
    assert r.wert("F_K") == approx(math.pi ** 2 * S235.E * q.I_min / 2000 ** 2)


def test_eulerfaelle_knicklaengen():
    q = berechne("Rund", {"d": 20})
    for fall, beta in [(1, 2.0), (2, 1.0), (3, 0.7), (4, 0.5)]:
        r = f.knickung(fall, 1000, 1000, q, S235)
        assert r.wert("l_k") == approx(beta * 1000)


def test_tetmajer_bereich():
    q = berechne("Rund", {"d": 40})  # i = 10
    r = f.knickung(2, 800, 1000, q, S235)  # λ = 80 < 104
    assert r.wert(r"\sigma_K") == approx(310 - 1.14 * 80)


def test_kurzer_stab_auf_re_begrenzt():
    q = berechne("Rund", {"d": 40})
    r = f.knickung(4, 100, 1000, q, S235)  # λ = 5
    assert r.wert(r"\sigma_{K,eff}") == approx(235)


def test_johnson_fuer_werkstoff_ohne_tetmajer():
    alu = werkstoff("EN AW-6082 T6")
    q = berechne("Rund", {"d": 40})
    r = f.knickung(2, 400, 1000, q, alu)  # λ = 40
    erwartet = alu.Re - alu.Re ** 2 / (4 * math.pi ** 2 * alu.E) * 40 ** 2
    assert r.wert(r"\sigma_K") == approx(erwartet)


# --- Zug, Torsion, Schub, Pressung ----------------------------------------

def test_zug():
    q = berechne("Rund", {"d": 10})
    r = f.zug_druck(10000, 1000, q, S235)
    assert r.wert(r"\sigma") == approx(10000 / q.A)
    assert r.wert(r"\Delta l") == approx(10000 * 1000 / (S235.E * q.A))


def test_torsion():
    q = berechne("Rund", {"d": 30})
    r = f.torsion(100, 500, q, S235)
    assert r.wert(r"\tau_t") == approx(100000 / (math.pi * 30 ** 3 / 16))
    G = 210000 / 2.6
    assert r.wert(r"\varphi") == approx(100000 * 500 / (G * q.Ip))
    with pytest.raises(ValueError):
        f.torsion(100, 500, berechne("Rechteck", {"b": 10, "h": 10}), S235)


def test_schub():
    q = berechne("Rund", {"d": 10})
    r = f.schub(f.SCHUBARTEN[0], 5000, q, S235, n=2)
    assert r.wert(r"\tau") == approx(5000 / (2 * q.A))
    q2 = berechne("Rechteck", {"b": 10, "h": 20})
    r = f.schub(f.SCHUBARTEN[1], 1000, q2, S235)
    assert r.wert(r"\tau") == approx(1.5 * 1000 / 200)


def test_flaechenpressung():
    r = f.flaechenpressung(f.PRESSUNGSARTEN[1], 10000, 20, 25, 100)
    assert r.wert("p") == approx(20)
    assert r.nachweise[0].erfuellt


def test_von_mises():
    r = f.vergleichsspannung(100, 0, 50, S235)
    assert r.wert(r"\sigma_v") == approx(math.sqrt(100 ** 2 + 3 * 50 ** 2))
    assert r.wert(r"\sigma_1") + r.wert(r"\sigma_2") == approx(100)
    # reiner Schub: σv = √3 τ
    r = f.vergleichsspannung(0, 0, 10, S235)
    assert r.wert(r"\sigma_v") == approx(math.sqrt(3) * 10)


# --- Schrauben, Welle, Passfeder ------------------------------------------

def test_schraube_m10_88_vorspannkraft_plausibel():
    r = f.schraube("M10", "8.8", FA=0, FQ=0)
    # Größenordnung laut VDI-2230-Tabellen: M10 8.8, μG = 0,12 → F_M ≈ 26–30 kN, M_A ≈ 50 Nm
    assert 24000 < r.wert("F_Mzul") < 31000
    assert r.wert("M_A") == pytest.approx(50, rel=0.15)


def test_schraube_klemmkraft():
    r = f.schraube("M12", "8.8", FA=4000, FQ=6000, n=2, mu_T=0.15, i=1, alpha_A=1.6)
    assert r.wert("F_Kerf") == approx(3000 / 0.15)
    assert r.wert("F_Mmax") == approx(1.6 * (20000 + 2000))


def test_welle():
    w = werkstoff("E335")
    r = f.welle(10, 1450, 50, 30, w)
    Mt = 9550 * 10 / 1450
    assert r.wert("M_t") == approx(Mt)
    tt = 16 * Mt * 1000 / (math.pi * 30 ** 3)
    sb = 32 * 50000 / (math.pi * 30 ** 3)
    assert r.wert(r"\sigma_v") == approx(math.sqrt(sb ** 2 + 3 * (0.7 * tt) ** 2))
    # Mit d_erf ergibt sich genau σv = σzul
    d_erf = r.wert("d_erf")
    r2 = f.welle(10, 1450, 50, d_erf, w)
    assert r2.wert(r"\sigma_v") == approx(w.Re / 2.0, rel=1e-6)


def test_passfeder():
    assert f.passfeder_masse(30) == (8, 7, 4.0)
    assert f.passfeder_masse(40) == (12, 8, 5.0)
    r = f.passfeder(40, 200, 50, 90)
    p = 2 * 200000 / (40 * 3 * 38)
    assert r.wert("p") == approx(p)
    with pytest.raises(ValueError):
        f.passfeder_masse(200)


def test_sicherheitsnachweis():
    r = f.sicherheitsnachweis(100, f.GRENZEN[0], S235, 1.5)
    assert r.nachweise[0].vorhanden == approx(2.35)
    assert r.alle_erfuellt
    r = f.sicherheitsnachweis(200, f.GRENZEN[0], S235, 1.5)
    assert not r.alle_erfuellt


def test_querschnittswerte_rechnung():
    r = f.querschnittswerte("Rohr", {"D": 40, "d": 30})
    assert r.wert("I_p") > 0
