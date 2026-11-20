"""Festigkeitsberechnungen – reine Logik ohne GUI (testbar).

Einheitensystem: Kräfte in N, Längen in mm, Spannungen in N/mm² (= MPa),
Momente werden in N·m eingegeben und intern in N·mm umgerechnet.
"""
from __future__ import annotations

import math
from typing import Dict, List

from .profile import Querschnitt, berechne as profil_berechnen, FORMELN as PROFIL_FORMELN
from .rechnung import Rechnung, fmt
from .werkstoffe import Werkstoff

# ---------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------

def _querschnitt_eingaben(r: Rechnung, q: Querschnitt):
    r.eingabe("Querschnitt", "", q.bezeichnung())


def _werkstoff_eingaben(r: Rechnung, w: Werkstoff, mit_E=True):
    r.eingabe("Werkstoff", "", w.name)
    r.eingabe("Streckgrenze", "Re", w.Re, "N/mm²")
    if mit_E:
        r.eingabe("Elastizitätsmodul", "E", w.E, "N/mm²")


def _linspace(a, b, n=201):
    return [a + (b - a) * k / (n - 1) for k in range(n)]


# ---------------------------------------------------------------------------
# Zug / Druck
# ---------------------------------------------------------------------------

def zug_druck(F: float, l: float, q: Querschnitt, w: Werkstoff, S_erf: float = 1.5) -> Rechnung:
    """F > 0: Zug, F < 0: Druck."""
    r = Rechnung("Zug / Druck")
    r.eingabe("Kraft (Zug +, Druck −)", "F", F, "N")
    r.eingabe("Stablänge", "l", l, "mm")
    _querschnitt_eingaben(r, q)
    _werkstoff_eingaben(r, w)
    r.eingabe("erforderliche Sicherheit", "S_erf", S_erf)

    A = r.schritt("Querschnittsfläche", PROFIL_FORMELN[q.profil]["A"], "A", q.A, "mm²")
    sigma = r.schritt("Normalspannung", r"\sigma = \frac{F}{A}", r"\sigma", F / A, "N/mm²",
                      f"σ = {fmt(F)} N / {fmt(A)} mm²")
    eps = r.schritt("Dehnung", r"\varepsilon = \frac{\sigma}{E}", r"\varepsilon", sigma / w.E, "",
                    f"ε = {fmt(sigma)} / {fmt(w.E)}")
    r.schritt("Längenänderung", r"\Delta l = \frac{F\,l}{E\,A}", r"\Delta l", F * l / (w.E * A), "mm",
              f"Δl = {fmt(F)} · {fmt(l)} / ({fmt(w.E)} · {fmt(A)})")
    S = w.Re / abs(sigma) if sigma else float("inf")
    r.nachweis("Sicherheit gegen Fließen", S, S_erf, r"S_F = \frac{R_e}{|\sigma|}",
               f"S = {fmt(w.Re)} / {fmt(abs(sigma))}")
    if F < 0:
        r.hinweise.append("Druckbelastung: Bei schlanken Stäben zusätzlich den Knicknachweis führen.")
    r.plot = {"typ": "stab", "F": F, "l": l, "dl": F * l / (w.E * A)}
    return r


# ---------------------------------------------------------------------------
# Biegung
# ---------------------------------------------------------------------------

LASTFAELLE = [
    "Einfeldträger – Einzellast",
    "Einfeldträger – Streckenlast",
    "Kragträger – Einzellast am Ende",
    "Kragträger – Streckenlast",
]


def biegung(lastfall: str, last: float, l: float, a: float, q: Querschnitt, w: Werkstoff,
            S_erf: float = 1.5) -> Rechnung:
    """Biegung um die y-Achse.

    lastfall: Eintrag aus LASTFAELLE
    last:     Einzellast F in N bzw. Streckenlast q in N/mm (= kN/m)
    l:        Stützweite bzw. Kraglänge in mm
    a:        Lastangriffspunkt vom linken Auflager (nur Einfeldträger – Einzellast)
    """
    if lastfall not in LASTFAELLE:
        raise ValueError(f"Unbekannter Lastfall: {lastfall}")
    if l <= 0:
        raise ValueError("Länge muss größer als 0 sein.")
    r = Rechnung(f"Biegung – {lastfall}")
    E, I, W = w.E, q.Iy, q.Wy
    einzel = "Einzellast" in lastfall
    if einzel:
        r.eingabe("Einzellast", "F", last, "N")
    else:
        r.eingabe("Streckenlast", "q", last, "N/mm")
    r.eingabe("Länge", "l", l, "mm")
    if lastfall == LASTFAELLE[0]:
        a = min(max(a, 0.0), l)
        r.eingabe("Lastabstand vom linken Lager", "a", a, "mm")
    _querschnitt_eingaben(r, q)
    _werkstoff_eingaben(r, w)
    r.eingabe("erforderliche Sicherheit", "S_erf", S_erf)

    r.schritt("Flächenträgheitsmoment", PROFIL_FORMELN[q.profil]["Iy"], "I_y", I, "mm⁴")
    r.schritt("Widerstandsmoment", PROFIL_FORMELN[q.profil]["Wy"], "W_y", W, "mm³")

    xs = _linspace(0, l)
    F = qq = last
    if lastfall == LASTFAELLE[0]:
        b = l - a
        FA = F * b / l
        FB = F * a / l
        r.schritt("Auflagerkraft links", r"F_A = \frac{F\,b}{l}", "F_A", FA, "N",
                  f"F_A = {fmt(F)} · {fmt(b)} / {fmt(l)}")
        r.schritt("Auflagerkraft rechts", r"F_B = \frac{F\,a}{l}", "F_B", FB, "N")
        M = r.schritt("max. Biegemoment (unter der Last)", r"M_{max} = \frac{F\,a\,b}{l}", "M_max",
                      F * a * b / l, "N·mm", f"M = {fmt(F)} · {fmt(a)} · {fmt(b)} / {fmt(l)}")

        def wx(x):
            if x <= a:
                return F * b * x * (l ** 2 - b ** 2 - x ** 2) / (6 * E * I * l)
            return F * a * (l - x) * (l ** 2 - a ** 2 - (l - x) ** 2) / (6 * E * I * l)

        Ms = [FA * x if x <= a else FA * x - F * (x - a) for x in xs]
        g = max(a, b)
        k = min(a, b)
        fmax = F * k * (l ** 2 - k ** 2) ** 1.5 / (9 * math.sqrt(3) * E * I * l)
        r.schritt("Durchbiegung unter der Last", r"f_F = \frac{F\,a^2\,b^2}{3\,E\,I\,l}", "f_F",
                  F * a ** 2 * b ** 2 / (3 * E * I * l), "mm")
        r.schritt("max. Durchbiegung", r"f_{max} = \frac{F\,k\,(l^2-k^2)^{3/2}}{9\sqrt{3}\,E\,I\,l}"
                  r",\ k=\min(a,b)", "f_max", fmax, "mm",
                  f"k = {fmt(k)} mm (größerer Abschnitt {fmt(g)} mm)")
    elif lastfall == LASTFAELLE[1]:
        FA = qq * l / 2
        r.schritt("Auflagerkräfte", r"F_A = F_B = \frac{q\,l}{2}", "F_A", FA, "N")
        M = r.schritt("max. Biegemoment (Feldmitte)", r"M_{max} = \frac{q\,l^2}{8}", "M_max",
                      qq * l ** 2 / 8, "N·mm", f"M = {fmt(qq)} · {fmt(l)}² / 8")

        def wx(x):
            return qq * x * (l ** 3 - 2 * l * x ** 2 + x ** 3) / (24 * E * I)

        Ms = [FA * x - qq * x ** 2 / 2 for x in xs]
        r.schritt("max. Durchbiegung", r"f_{max} = \frac{5\,q\,l^4}{384\,E\,I}", "f_max",
                  5 * qq * l ** 4 / (384 * E * I), "mm",
                  f"f = 5 · {fmt(qq)} · {fmt(l)}⁴ / (384 · {fmt(E)} · {fmt(I)})")
    elif lastfall == LASTFAELLE[2]:
        r.schritt("Einspannkraft", r"F_A = F", "F_A", F, "N")
        M = r.schritt("max. Biegemoment (Einspannung)", r"M_{max} = F\,l", "M_max", F * l, "N·mm",
                      f"M = {fmt(F)} · {fmt(l)}")

        def wx(x):  # x ab Einspannung
            return F * x ** 2 * (3 * l - x) / (6 * E * I)

        Ms = [-F * (l - x) for x in xs]
        r.schritt("max. Durchbiegung (freies Ende)", r"f_{max} = \frac{F\,l^3}{3\,E\,I}", "f_max",
                  F * l ** 3 / (3 * E * I), "mm",
                  f"f = {fmt(F)} · {fmt(l)}³ / (3 · {fmt(E)} · {fmt(I)})")
    else:
        r.schritt("Einspannkraft", r"F_A = q\,l", "F_A", qq * l, "N")
        M = r.schritt("max. Biegemoment (Einspannung)", r"M_{max} = \frac{q\,l^2}{2}", "M_max",
                      qq * l ** 2 / 2, "N·mm", f"M = {fmt(qq)} · {fmt(l)}² / 2")

        def wx(x):
            return qq * x ** 2 * (6 * l ** 2 - 4 * l * x + x ** 2) / (24 * E * I)

        Ms = [-qq * (l - x) ** 2 / 2 for x in xs]
        r.schritt("max. Durchbiegung (freies Ende)", r"f_{max} = \frac{q\,l^4}{8\,E\,I}", "f_max",
                  qq * l ** 4 / (8 * E * I), "mm",
                  f"f = {fmt(qq)} · {fmt(l)}⁴ / (8 · {fmt(E)} · {fmt(I)})")

    sigma = r.schritt("max. Biegespannung", r"\sigma_b = \frac{M_{max}}{W_y}", r"\sigma_b",
                      abs(M) / W, "N/mm²", f"σ_b = {fmt(abs(M))} N·mm / {fmt(W)} mm³")
    S = w.Re / sigma if sigma else float("inf")
    r.nachweis("Sicherheit gegen Fließen", S, S_erf, r"S_F = \frac{R_e}{\sigma_b}",
               f"S = {fmt(w.Re)} / {fmt(sigma)}")
    f = r.wert("f_max")
    r.hinweise.append(f"Durchbiegungsverhältnis f/l = 1/{fmt(l / f) if f else '∞'} "
                      "(übliche Grenzen: Maschinenbau 1/1000 … 1/3000, Stahlbau 1/300).")
    r.plot = {"typ": "biegung", "lastfall": lastfall, "l": l, "a": a, "x": xs,
              "w": [wx(x) for x in xs], "M": Ms}
    return r


# ---------------------------------------------------------------------------
# Knickung
# ---------------------------------------------------------------------------

EULERFAELLE = {
    1: ("Fall 1: unten eingespannt, oben frei", 2.0),
    2: ("Fall 2: beidseitig gelenkig", 1.0),
    3: ("Fall 3: eingespannt – gelenkig", 0.7),
    4: ("Fall 4: beidseitig eingespannt", 0.5),
}


def knickung(eulerfall: int, l: float, F: float, q: Querschnitt, w: Werkstoff,
             S_erf: float = 3.0) -> Rechnung:
    """Knicknachweis nach Euler (elastisch) bzw. Tetmajer / Johnson (unelastisch)."""
    name, beta = EULERFAELLE[eulerfall]
    r = Rechnung(f"Knickung – Euler {name}")
    r.eingabe("Druckkraft", "F", F, "N")
    r.eingabe("Stablänge", "l", l, "mm")
    r.eingabe("Eulerfall", "", name)
    _querschnitt_eingaben(r, q)
    _werkstoff_eingaben(r, w)
    r.eingabe("erforderliche Sicherheit", "S_erf", S_erf)

    lk = r.schritt("Knicklänge", r"l_k = \beta \cdot l", "l_k", beta * l, "mm",
                   f"l_k = {fmt(beta)} · {fmt(l)}")
    A = r.schritt("Querschnittsfläche", PROFIL_FORMELN[q.profil]["A"], "A", q.A, "mm²")
    Imin = r.schritt("kleinstes Flächenträgheitsmoment", r"I_{min} = \min(I_y, I_z)", "I_min",
                     q.I_min, "mm⁴")
    i = r.schritt("Trägheitsradius", r"i = \sqrt{\frac{I_{min}}{A}}", "i", math.sqrt(Imin / A), "mm",
                  f"i = √({fmt(Imin)} / {fmt(A)})")
    lam = r.schritt("Schlankheitsgrad", r"\lambda = \frac{l_k}{i}", r"\lambda", lk / i, "",
                    f"λ = {fmt(lk)} / {fmt(i)}")

    if w.tetmajer:
        ta, tb, lam0 = w.tetmajer
        r.schritt("Grenzschlankheit (Tetmajer-Tabelle)", r"\lambda_0", r"\lambda_0", lam0, "")
    else:
        lam0 = math.pi * math.sqrt(2 * w.E / w.Re)
        r.schritt("Grenzschlankheit (Johnson)", r"\lambda_0 = \pi \sqrt{\frac{2\,E}{R_e}}",
                  r"\lambda_0", lam0, "")

    if lam >= lam0:
        bereich = "elastisch (Euler)"
        sK = r.schritt("Knickspannung nach Euler", r"\sigma_K = \frac{\pi^2\,E}{\lambda^2}",
                       r"\sigma_K", math.pi ** 2 * w.E / lam ** 2, "N/mm²",
                       f"σ_K = π² · {fmt(w.E)} / {fmt(lam)}²")
    elif w.tetmajer:
        bereich = "unelastisch (Tetmajer)"
        sK = ta - tb * lam
        sK = r.schritt("Knickspannung nach Tetmajer", rf"\sigma_K = {fmt(ta)} - {fmt(tb)}\,\lambda",
                       r"\sigma_K", sK, "N/mm²", f"σ_K = {fmt(ta)} − {fmt(tb)} · {fmt(lam)}")
    else:
        bereich = "unelastisch (Johnson-Parabel)"
        sK = r.schritt("Knickspannung nach Johnson",
                       r"\sigma_K = R_e - \frac{R_e^2}{4\pi^2 E}\,\lambda^2", r"\sigma_K",
                       w.Re - w.Re ** 2 / (4 * math.pi ** 2 * w.E) * lam ** 2, "N/mm²")
    if sK > w.Re:
        sK = r.schritt("Begrenzung auf Quetschgrenze", r"\sigma_K = R_e", r"\sigma_{K,eff}", w.Re,
                       "N/mm²", "kurzer Stab: Fließen maßgebend")
        bereich += ", begrenzt durch Fließen"
    FK = r.schritt("Knickkraft", r"F_K = \sigma_K \cdot A", "F_K", sK * A, "N",
                   f"F_K = {fmt(sK)} · {fmt(A)}")
    r.schritt("vorhandene Druckspannung", r"\sigma_d = \frac{F}{A}", r"\sigma_d", F / A, "N/mm²")
    S = FK / F if F else float("inf")
    r.nachweis("Sicherheit gegen Knicken", S, S_erf, r"S_K = \frac{F_K}{F}",
               f"S = {fmt(FK)} / {fmt(F)}")
    r.hinweise.append(f"Bereich: {bereich}. Euler gilt nur für λ ≥ λ0 = {fmt(lam0)}.")
    # Knickspannungslinie für Diagramm
    lams = _linspace(1, max(250, lam * 1.3), 300)
    linie = []
    for L in lams:
        if L >= lam0:
            s = math.pi ** 2 * w.E / L ** 2
        elif w.tetmajer:
            s = ta - tb * L
        else:
            s = w.Re - w.Re ** 2 / (4 * math.pi ** 2 * w.E) * L ** 2
        linie.append(min(s, w.Re))
    r.plot = {"typ": "knickung", "lam": lam, "sK": sK, "lam0": lam0, "lams": lams, "linie": linie,
              "euler": [math.pi ** 2 * w.E / L ** 2 for L in lams], "Re": w.Re, "fall": eulerfall}
    return r


# ---------------------------------------------------------------------------
# Torsion
# ---------------------------------------------------------------------------

def torsion(Mt: float, l: float, q: Querschnitt, w: Werkstoff, S_erf: float = 1.5) -> Rechnung:
    """Torsion von Kreis- und Kreisringquerschnitten. Mt in N·m."""
    if q.profil not in ("Rund", "Rohr"):
        raise ValueError("Torsion ist nur für Rund- und Rohrquerschnitte hinterlegt.")
    r = Rechnung("Torsion")
    r.eingabe("Torsionsmoment", "M_t", Mt, "N·m")
    r.eingabe("Länge", "l", l, "mm")
    _querschnitt_eingaben(r, q)
    _werkstoff_eingaben(r, w)
    r.eingabe("Querkontraktionszahl", "ν", w.nu)
    r.eingabe("erforderliche Sicherheit", "S_erf", S_erf)
    Mt_Nmm = Mt * 1000
    Wt = r.schritt("Torsionswiderstandsmoment", PROFIL_FORMELN[q.profil]["Wt"], "W_t", q.Wt, "mm³")
    Ip = r.schritt("polares Flächenträgheitsmoment", PROFIL_FORMELN[q.profil]["Ip"], "I_p", q.Ip, "mm⁴")
    G = r.schritt("Schubmodul", r"G = \frac{E}{2\,(1+\nu)}", "G", w.G, "N/mm²")
    tau = r.schritt("Torsionsspannung", r"\tau_t = \frac{M_t}{W_t}", r"\tau_t", Mt_Nmm / Wt, "N/mm²",
                    f"τ = {fmt(Mt_Nmm)} N·mm / {fmt(Wt)} mm³")
    phi = r.schritt("Verdrehwinkel", r"\varphi = \frac{M_t\,l}{G\,I_p}", r"\varphi",
                    Mt_Nmm * l / (G * Ip), "rad")
    r.schritt("Verdrehwinkel in Grad", r"\varphi° = \varphi \cdot \frac{180}{\pi}", r"\varphi°",
              math.degrees(phi), "°")
    tF = r.schritt("Schubfließgrenze (GEH)", r"\tau_F = \frac{R_e}{\sqrt{3}}", r"\tau_F",
                   w.Re / math.sqrt(3), "N/mm²")
    S = tF / abs(tau) if tau else float("inf")
    r.nachweis("Sicherheit gegen Fließen", S, S_erf, r"S_F = \frac{\tau_F}{\tau_t}",
               f"S = {fmt(tF)} / {fmt(abs(tau))}")
    D = q.masse.get("D", q.masse.get("d"))
    r.plot = {"typ": "torsion", "D": D, "d": q.masse.get("d") if q.profil == "Rohr" else 0, "tau": tau}
    return r


# ---------------------------------------------------------------------------
# Schub / Abscheren
# ---------------------------------------------------------------------------

SCHUBARTEN = ["Abscheren (Bolzen, Niet, Stift)", "Querkraftschub im Biegeträger"]


def schub(art: str, F: float, q: Querschnitt, w: Werkstoff, n: int = 1, S_erf: float = 1.5) -> Rechnung:
    r = Rechnung(f"Schub – {art}")
    r.eingabe("Querkraft", "F", F, "N")
    _querschnitt_eingaben(r, q)
    _werkstoff_eingaben(r, w, mit_E=False)
    r.eingabe("erforderliche Sicherheit", "S_erf", S_erf)
    A = r.schritt("Querschnittsfläche", PROFIL_FORMELN[q.profil]["A"], "A", q.A, "mm²")
    if art == SCHUBARTEN[0]:
        r.eingabe("Anzahl Scherflächen", "n", n)
        tau = r.schritt("Abscherspannung", r"\tau_a = \frac{F}{n \cdot A}", r"\tau", F / (n * A),
                        "N/mm²", f"τ = {fmt(F)} / ({n} · {fmt(A)})")
    else:
        if q.profil in ("I-Profil", "U-Profil"):
            As = (q.masse["h"] - 2 * q.masse["t"]) * q.masse["s"]
            r.schritt("Stegfläche", r"A_{Steg} = (h - 2t)\,s", "A_Steg", As, "mm²")
            tau = r.schritt("Schubspannung im Steg (Näherung)", r"\tau_{max} \approx \frac{F}{A_{Steg}}",
                            r"\tau", F / As, "N/mm²")
        else:
            kappa, txt = {"Rechteck": (1.5, r"\frac{3}{2}"), "Rund": (4 / 3, r"\frac{4}{3}"),
                          "Rohr": (2.0, "2")}[q.profil]
            r.schritt("mittlere Schubspannung", r"\tau_m = \frac{F}{A}", r"\tau_m", F / A, "N/mm²")
            tau = r.schritt("max. Schubspannung (Schwerachse)", rf"\tau_{{max}} = {txt} \cdot \frac{{F}}{{A}}",
                            r"\tau", kappa * F / A, "N/mm²")
    tF = r.schritt("Schubfließgrenze (GEH)", r"\tau_F = \frac{R_e}{\sqrt{3}}", r"\tau_F",
                   w.Re / math.sqrt(3), "N/mm²")
    S = tF / abs(tau) if tau else float("inf")
    r.nachweis("Sicherheit gegen Fließen", S, S_erf, r"S = \frac{\tau_F}{\tau}",
               f"S = {fmt(tF)} / {fmt(abs(tau))}")
    r.plot = {"typ": "querschnitt", "umriss": q.umriss, "titel": q.bezeichnung()}
    return r


# ---------------------------------------------------------------------------
# Flächenpressung
# ---------------------------------------------------------------------------

PRESSUNGSARTEN = ["Ebene Fläche (b × l)", "Bolzen / Lager (projizierte Fläche d × l)"]


def flaechenpressung(art: str, F: float, b_oder_d: float, l: float, p_zul: float) -> Rechnung:
    r = Rechnung(f"Flächenpressung – {art}")
    r.eingabe("Kraft", "F", F, "N")
    sym = "b" if art == PRESSUNGSARTEN[0] else "d"
    r.eingabe("Breite" if sym == "b" else "Durchmesser", sym, b_oder_d, "mm")
    r.eingabe("Länge", "l", l, "mm")
    r.eingabe("zulässige Flächenpressung", "p_zul", p_zul, "N/mm²")
    if sym == "b":
        A = r.schritt("Kontaktfläche", r"A = b \cdot l", "A", b_oder_d * l, "mm²")
    else:
        A = r.schritt("projizierte Fläche", r"A_{proj} = d \cdot l", "A", b_oder_d * l, "mm²")
    p = r.schritt("Flächenpressung", r"p = \frac{F}{A}", "p", F / A, "N/mm²", f"p = {fmt(F)} / {fmt(A)}")
    r.schritt("erforderliche Länge", r"l_{erf} = \frac{F}{" + sym + r" \cdot p_{zul}}", "l_erf",
              F / (b_oder_d * p_zul), "mm")
    r.nachweis("Pressungsnachweis (p ≤ p_zul)", p_zul / p if p else float("inf"), 1.0,
               r"\frac{p_{zul}}{p} \geq 1", f"{fmt(p_zul)} / {fmt(p)}")
    r.hinweise.append("Richtwerte p_zul (ruhend): Stahl/Stahl 100–150, Stahl/GG 70–90, "
                      "Stahl/Bronze 20–40, Stahl/Alu 30–60 N/mm².")
    r.plot = {"typ": "pressung", "art": sym, "p": p, "p_zul": p_zul}
    return r


# ---------------------------------------------------------------------------
# Vergleichsspannung (von Mises)
# ---------------------------------------------------------------------------

def vergleichsspannung(sx: float, sy: float, tau: float, w: Werkstoff, S_erf: float = 1.5) -> Rechnung:
    r = Rechnung("Vergleichsspannung nach von Mises (GEH)")
    r.eingabe("Normalspannung x", "σx", sx, "N/mm²")
    r.eingabe("Normalspannung y", "σy", sy, "N/mm²")
    r.eingabe("Schubspannung", "τxy", tau, "N/mm²")
    _werkstoff_eingaben(r, w, mit_E=False)
    r.eingabe("erforderliche Sicherheit", "S_erf", S_erf)
    sv = r.schritt("Vergleichsspannung",
                   r"\sigma_v = \sqrt{\sigma_x^2 + \sigma_y^2 - \sigma_x\,\sigma_y + 3\,\tau^2}",
                   r"\sigma_v", math.sqrt(sx ** 2 + sy ** 2 - sx * sy + 3 * tau ** 2), "N/mm²",
                   f"σv = √({fmt(sx)}² + {fmt(sy)}² − {fmt(sx)}·{fmt(sy)} + 3·{fmt(tau)}²)")
    m = (sx + sy) / 2
    R = math.sqrt(((sx - sy) / 2) ** 2 + tau ** 2)
    r.schritt("Hauptspannung 1", r"\sigma_1 = \frac{\sigma_x+\sigma_y}{2} + \sqrt{\left(\frac{\sigma_x-\sigma_y}{2}\right)^2 + \tau^2}",
              r"\sigma_1", m + R, "N/mm²")
    r.schritt("Hauptspannung 2", r"\sigma_2 = \frac{\sigma_x+\sigma_y}{2} - \sqrt{\left(\frac{\sigma_x-\sigma_y}{2}\right)^2 + \tau^2}",
              r"\sigma_2", m - R, "N/mm²")
    r.schritt("Hauptspannungswinkel", r"\varphi_0 = \frac{1}{2}\arctan\frac{2\tau}{\sigma_x-\sigma_y}",
              r"\varphi_0", math.degrees(0.5 * math.atan2(2 * tau, sx - sy)), "°")
    S = w.Re / sv if sv else float("inf")
    r.nachweis("Sicherheit gegen Fließen", S, S_erf, r"S_F = \frac{R_e}{\sigma_v}",
               f"S = {fmt(w.Re)} / {fmt(sv)}")
    r.plot = {"typ": "mohr", "sx": sx, "sy": sy, "tau": tau, "m": m, "R": R}
    return r


# ---------------------------------------------------------------------------
# Schrauben
# ---------------------------------------------------------------------------

# Regelgewinde ISO 262: Name -> (d, P, d2, d3, As)
GEWINDE = {
    "M3": (3, 0.5, 2.675, 2.387, 5.03),
    "M4": (4, 0.7, 3.545, 3.141, 8.78),
    "M5": (5, 0.8, 4.480, 4.019, 14.2),
    "M6": (6, 1.0, 5.350, 4.773, 20.1),
    "M8": (8, 1.25, 7.188, 6.466, 36.6),
    "M10": (10, 1.5, 9.026, 8.160, 58.0),
    "M12": (12, 1.75, 10.863, 9.853, 84.3),
    "M14": (14, 2.0, 12.701, 11.546, 115.0),
    "M16": (16, 2.0, 14.701, 13.546, 157.0),
    "M20": (20, 2.5, 18.376, 16.933, 245.0),
    "M24": (24, 3.0, 22.051, 20.319, 353.0),
    "M30": (30, 3.5, 27.727, 25.706, 561.0),
}

# Festigkeitsklasse -> (Rm, Rp0,2)
FESTIGKEITSKLASSEN = {
    "4.6": (400, 240), "5.6": (500, 300), "8.8": (800, 640), "10.9": (1000, 900), "12.9": (1200, 1080),
}


def schraube(gewinde: str, klasse: str, FA: float, FQ: float, n: int = 1, mu_T: float = 0.15,
             i: int = 1, alpha_A: float = 1.6, mu_G: float = 0.12, mu_K: float = 0.12,
             nu: float = 0.9) -> Rechnung:
    """Vereinfachte Schraubenauslegung (angelehnt an VDI 2230, ohne Setzen/Kraftverhältnis).

    FA: axiale Betriebskraft gesamt (N), FQ: Querkraft gesamt (N), n: Anzahl Schrauben,
    i: Anzahl Trennfugen, mu_T: Reibzahl Trennfuge, alpha_A: Anziehfaktor.
    """
    d, P, d2, d3, As = GEWINDE[gewinde]
    Rm, Rp = FESTIGKEITSKLASSEN[klasse]
    r = Rechnung(f"Schraubenverbindung {gewinde} – {klasse}")
    r.eingabe("Gewinde", "", f"{gewinde} (P = {fmt(P)} mm, As = {fmt(As)} mm²)")
    r.eingabe("Festigkeitsklasse", "", f"{klasse} (Rm = {Rm}, Rp0,2 = {Rp} N/mm²)")
    r.eingabe("axiale Betriebskraft gesamt", "F_A", FA, "N")
    r.eingabe("Querkraft gesamt", "F_Q", FQ, "N")
    r.eingabe("Anzahl Schrauben", "n", n)
    r.eingabe("Anzahl Trennfugen", "i", i)
    r.eingabe("Reibzahl Trennfuge", "μ_T", mu_T)
    r.eingabe("Anziehfaktor", "α_A", alpha_A)
    r.eingabe("Reibzahl Gewinde / Kopf", "μ_G / μ_K", f"{fmt(mu_G)} / {fmt(mu_K)}")

    FAe = r.schritt("Axialkraft je Schraube", r"F_{A,1} = \frac{F_A}{n}", "F_A1", FA / n, "N")
    FQe = r.schritt("Querkraft je Schraube", r"F_{Q,1} = \frac{F_Q}{n}", "F_Q1", FQ / n, "N")
    FK = r.schritt("erforderliche Klemmkraft (Reibschluss)", r"F_{K,erf} = \frac{F_{Q,1}}{\mu_T \cdot i}",
                   "F_Kerf", FQe / (mu_T * i), "N", f"F_K = {fmt(FQe)} / ({fmt(mu_T)} · {i})")
    FMmin = r.schritt("Mindest-Montagevorspannkraft", r"F_{M,min} = F_{K,erf} + F_{A,1}", "F_Mmin",
                      FK + FAe, "N")
    FMmax = r.schritt("maximale Montagevorspannkraft", r"F_{M,max} = \alpha_A \cdot F_{M,min}", "F_Mmax",
                      alpha_A * FMmin, "N", f"F_M,max = {fmt(alpha_A)} · {fmt(FMmin)}")
    d0 = (d2 + d3) / 2
    k = 1.5 * d2 / d0 * (P / (math.pi * d2) + 1.155 * mu_G)
    FMzul = r.schritt("zulässige Montagevorspannkraft (ν = 0,9)",
                      r"F_{M,zul} = \frac{A_s\,\nu\,R_{p0,2}}{\sqrt{1 + 3\left[\frac{3}{2}\frac{d_2}{d_0}\left(\frac{P}{\pi d_2} + 1{,}155\,\mu_G\right)\right]^2}}",
                      "F_Mzul", As * nu * Rp / math.sqrt(1 + 3 * k ** 2), "N")
    DKm = 1.3 * d
    r.schritt("Anziehdrehmoment",
              r"M_A = F_{M,zul}\,(0{,}16\,P + 0{,}58\,d_2\,\mu_G + \frac{D_{Km}}{2}\,\mu_K)",
              "M_A", FMzul * (0.16 * P + 0.58 * d2 * mu_G + DKm / 2 * mu_K) / 1000, "N·m",
              f"mit D_Km ≈ 1,3·d = {fmt(DKm)} mm")
    r.schritt("Spannung im Spannungsquerschnitt (Montage)", r"\sigma_M = \frac{F_{M,max}}{A_s}",
              r"\sigma_M", FMmax / As, "N/mm²")
    r.nachweis("Montagevorspannkraft F_M,max ≤ F_M,zul", FMzul / FMmax if FMmax else float("inf"), 1.0,
               r"\frac{F_{M,zul}}{F_{M,max}} \geq 1", f"{fmt(FMzul)} / {fmt(FMmax)}")
    r.hinweise.append("Vereinfachte Auslegung (Kraftverhältnis Φ = 0, kein Setzen, keine Temperatur). "
                      "Für kritische Verbindungen VDI 2230 vollständig anwenden.")
    r.plot = {"typ": "balken", "titel": "Vorspannkräfte", "werte": {
        "F_K,erf": FK, "F_M,min": FMmin, "F_M,max": FMmax, "F_M,zul": FMzul}, "einheit": "N",
        "grenze": FMzul}
    return r


# ---------------------------------------------------------------------------
# Wellen
# ---------------------------------------------------------------------------

def welle(P_kW: float, n_min: float, Mb: float, d: float, w: Werkstoff, alpha0: float = 0.7,
          S_erf: float = 2.0) -> Rechnung:
    """Vollwelle unter Biegung und Torsion. Mb in N·m, d in mm, n in 1/min."""
    r = Rechnung("Welle – Biegung und Torsion")
    r.eingabe("Leistung", "P", P_kW, "kW")
    r.eingabe("Drehzahl", "n", n_min, "1/min")
    r.eingabe("Biegemoment", "M_b", Mb, "N·m")
    r.eingabe("Wellendurchmesser", "d", d, "mm")
    _werkstoff_eingaben(r, w, mit_E=False)
    r.eingabe("Anstrengungsverhältnis", "α0", alpha0)
    r.eingabe("erforderliche Sicherheit", "S_erf", S_erf)
    Mt = r.schritt("Torsionsmoment", r"M_t = 9550 \cdot \frac{P}{n}", "M_t", 9550 * P_kW / n_min, "N·m",
                   f"M_t = 9550 · {fmt(P_kW)} / {fmt(n_min)}")
    sb = r.schritt("Biegespannung", r"\sigma_b = \frac{32\,M_b}{\pi\,d^3}", r"\sigma_b",
                   32 * Mb * 1000 / (math.pi * d ** 3), "N/mm²")
    tt = r.schritt("Torsionsspannung", r"\tau_t = \frac{16\,M_t}{\pi\,d^3}", r"\tau_t",
                   16 * Mt * 1000 / (math.pi * d ** 3), "N/mm²")
    sv = r.schritt("Vergleichsspannung (GEH)", r"\sigma_v = \sqrt{\sigma_b^2 + 3\,(\alpha_0\,\tau_t)^2}",
                   r"\sigma_v", math.sqrt(sb ** 2 + 3 * (alpha0 * tt) ** 2), "N/mm²")
    szul = r.schritt("zulässige Spannung", r"\sigma_{zul} = \frac{R_e}{S_{erf}}", r"\sigma_zul",
                     w.Re / S_erf, "N/mm²")
    Mv = r.schritt("Vergleichsmoment", r"M_v = \sqrt{M_b^2 + 0{,}75\,(\alpha_0\,M_t)^2}", "M_v",
                   math.sqrt(Mb ** 2 + 0.75 * (alpha0 * Mt) ** 2), "N·m")
    r.schritt("erforderlicher Durchmesser", r"d_{erf} = \sqrt[3]{\frac{32\,M_v}{\pi\,\sigma_{zul}}}", "d_erf",
              (32 * Mv * 1000 / (math.pi * szul)) ** (1 / 3), "mm")
    S = w.Re / sv if sv else float("inf")
    r.nachweis("Sicherheit gegen Fließen (statisch)", S, S_erf, r"S_F = \frac{R_e}{\sigma_v}",
               f"S = {fmt(w.Re)} / {fmt(sv)}")
    r.hinweise.append("Statischer Nachweis. Für Dauerfestigkeit Kerbwirkung (Absätze, Nuten) "
                      "nach DIN 743 berücksichtigen.")
    r.plot = {"typ": "balken", "titel": "Spannungen in der Welle",
              "werte": {"σ_b": sb, "τ_t": tt, "σ_v": sv, "σ_zul": szul}, "einheit": "N/mm²",
              "grenze": szul}
    return r


# ---------------------------------------------------------------------------
# Passfedern DIN 6885 Form A
# ---------------------------------------------------------------------------

# (d_von, d_bis, b, h, t1)
PASSFEDERN = [
    (6, 8, 2, 2, 1.2), (8, 10, 3, 3, 1.8), (10, 12, 4, 4, 2.5), (12, 17, 5, 5, 3.0),
    (17, 22, 6, 6, 3.5), (22, 30, 8, 7, 4.0), (30, 38, 10, 8, 5.0), (38, 44, 12, 8, 5.0),
    (44, 50, 14, 9, 5.5), (50, 58, 16, 10, 6.0), (58, 65, 18, 11, 7.0), (65, 75, 20, 12, 7.5),
    (75, 85, 22, 14, 9.0), (85, 95, 25, 14, 9.0), (95, 110, 28, 16, 10.0), (110, 130, 32, 18, 11.0),
]


def passfeder_masse(d: float):
    for von, bis, b, h, t1 in PASSFEDERN:
        if von < d <= bis:
            return b, h, t1
    raise ValueError("Wellendurchmesser außerhalb 6 … 130 mm (DIN 6885).")


def passfeder(d: float, Mt: float, l: float, p_zul: float = 90.0, anzahl: int = 1) -> Rechnung:
    """Passfeder DIN 6885 Form A (rundstirnig). Mt in N·m, Längen in mm."""
    b, h, t1 = passfeder_masse(d)
    r = Rechnung("Passfeder DIN 6885 Form A")
    r.eingabe("Wellendurchmesser", "d", d, "mm")
    r.eingabe("Torsionsmoment", "M_t", Mt, "N·m")
    r.eingabe("Passfederlänge", "l", l, "mm")
    r.eingabe("Anzahl Passfedern", "n", anzahl)
    r.eingabe("zulässige Flächenpressung (Nabe)", "p_zul", p_zul, "N/mm²")
    r.eingabe("Passfeder b × h, Nuttiefe t1", "", f"{fmt(b)} × {fmt(h)} mm, t1 = {fmt(t1)} mm")
    if l <= b:
        raise ValueError("Passfederlänge muss größer als die Breite b sein.")
    phi = 1.0 if anzahl == 1 else 0.75
    ltr = r.schritt("tragende Länge (Form A)", r"l_{tr} = l - b", "l_tr", l - b, "mm")
    r.schritt("Traganteil", r"\varphi = 1\ (n=1),\ 0{,}75\ (n=2)", r"\varphi", phi)
    p = r.schritt("Flächenpressung an der Nabe",
                  r"p = \frac{2\,M_t}{d\,(h - t_1)\,l_{tr}\,n\,\varphi}", "p",
                  2 * Mt * 1000 / (d * (h - t1) * ltr * anzahl * phi), "N/mm²",
                  f"p = 2 · {fmt(Mt * 1000)} / ({fmt(d)} · {fmt(h - t1)} · {fmt(ltr)} · {anzahl} · {fmt(phi)})")
    r.schritt("erforderliche Passfederlänge",
              r"l_{erf} = \frac{2\,M_t}{d\,(h-t_1)\,p_{zul}\,n\,\varphi} + b", "l_erf",
              2 * Mt * 1000 / (d * (h - t1) * p_zul * anzahl * phi) + b, "mm")
    r.nachweis("Pressungsnachweis (p ≤ p_zul)", p_zul / p if p else float("inf"), 1.0,
               r"\frac{p_{zul}}{p} \geq 1", f"{fmt(p_zul)} / {fmt(p)}")
    r.hinweise.append("Richtwerte p_zul Nabe: Stahl/Stahlguss ≈ 90–150 N/mm², Grauguss ≈ 50–80 N/mm².")
    r.plot = {"typ": "passfeder", "d": d, "b": b, "h": h, "t1": t1}
    return r


# ---------------------------------------------------------------------------
# Querschnittswerte und allgemeiner Sicherheitsnachweis
# ---------------------------------------------------------------------------

def querschnittswerte(profil: str, masse: Dict[str, float]) -> Rechnung:
    q = profil_berechnen(profil, masse)
    r = Rechnung(f"Querschnittswerte – {profil}")
    for k, v in q.masse.items():
        r.eingabe(f"Maß {k}", k, v, "mm")
    f = PROFIL_FORMELN[profil]
    r.schritt("Fläche", f["A"], "A", q.A, "mm²")
    r.schritt("Flächenträgheitsmoment um y", f["Iy"], "I_y", q.Iy, "mm⁴")
    r.schritt("Flächenträgheitsmoment um z", f.get("Iz", f["Iy"]), "I_z", q.Iz, "mm⁴")
    r.schritt("Widerstandsmoment um y", f["Wy"], "W_y", q.Wy, "mm³")
    r.schritt("Widerstandsmoment um z", r"W_z = \frac{I_z}{e_{z,max}}", "W_z", q.Wz, "mm³")
    r.schritt("Trägheitsradius (min.)", r"i_{min} = \sqrt{\frac{I_{min}}{A}}", "i_min", q.i_min, "mm")
    if q.Ip:
        r.schritt("polares Flächenträgheitsmoment", f["Ip"], "I_p", q.Ip, "mm⁴")
        r.schritt("Torsionswiderstandsmoment", f["Wt"], "W_t", q.Wt, "mm³")
    if profil == "U-Profil":
        r.schritt("Schwerpunktabstand vom Steg", r"e = \frac{\sum A_i\,x_i}{A}", "e", q.ez, "mm")
    r.plot = {"typ": "querschnitt", "umriss": q.umriss, "titel": q.bezeichnung()}
    return r


GRENZEN = ["Streckgrenze Re (Fließen)", "Zugfestigkeit Rm (Bruch)"]


def sicherheitsnachweis(sigma: float, grenze: str, w: Werkstoff, S_erf: float) -> Rechnung:
    r = Rechnung("Sicherheitsnachweis")
    r.eingabe("vorhandene Spannung", "σ_vorh", sigma, "N/mm²")
    r.eingabe("Werkstoff", "", w.name)
    r.eingabe("Grenzspannung", "", grenze)
    r.eingabe("erforderliche Sicherheit", "S_erf", S_erf)
    g = w.Re if grenze == GRENZEN[0] else w.Rm
    sym = "R_e" if grenze == GRENZEN[0] else "R_m"
    r.schritt("Grenzspannung", rf"\sigma_{{grenz}} = {sym}", r"\sigma_grenz", g, "N/mm²")
    r.schritt("zulässige Spannung", r"\sigma_{zul} = \frac{\sigma_{grenz}}{S_{erf}}", r"\sigma_zul",
              g / S_erf, "N/mm²")
    r.schritt("Auslastung", r"\eta = \frac{\sigma_{vorh}}{\sigma_{zul}}", r"\eta",
              abs(sigma) / (g / S_erf) * 100, "%")
    S = g / abs(sigma) if sigma else float("inf")
    r.nachweis("Sicherheit", S, S_erf, r"S = \frac{\sigma_{grenz}}{\sigma_{vorh}}",
               f"S = {fmt(g)} / {fmt(abs(sigma))}")
    r.hinweise.append("Übliche Sicherheiten: gegen Fließen 1,2–2,0; gegen Bruch 2,0–4,0; "
                      "gegen Knicken 3–5 (Euler) bzw. 2–4 (Tetmajer).")
    r.plot = {"typ": "balken", "titel": "Spannungsvergleich",
              "werte": {"σ_vorh": abs(sigma), "σ_zul": g / S_erf, "σ_grenz": g}, "einheit": "N/mm²",
              "grenze": g / S_erf}
    return r
