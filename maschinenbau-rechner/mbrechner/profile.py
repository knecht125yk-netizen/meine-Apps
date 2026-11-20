"""Querschnittswerte (Flächenträgheitsmomente) für Standardprofile.

Achsen: y-Achse waagerecht (Biegung um y = "hochkant"), z-Achse senkrecht.
Alle Maße in mm, Flächen in mm², Trägheitsmomente in mm⁴, Widerstandsmomente in mm³.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

PROFILE = ["Rechteck", "Rund", "Rohr", "I-Profil", "U-Profil"]

# Benötigte Maße je Profil: (Schlüssel, Bezeichnung, Standardwert, min, max)
MASSE: Dict[str, List[Tuple[str, str, float, float, float]]] = {
    "Rechteck": [("b", "Breite b", 20, 1, 500), ("h", "Höhe h", 40, 1, 1000)],
    "Rund": [("d", "Durchmesser d", 30, 1, 500)],
    "Rohr": [("D", "Außendurchmesser D", 40, 2, 1000), ("d", "Innendurchmesser d", 30, 0, 990)],
    "I-Profil": [("h", "Höhe h", 200, 10, 1000), ("b", "Flanschbreite b", 100, 5, 500),
                 ("s", "Stegdicke s", 5.6, 1, 50), ("t", "Flanschdicke t", 8.5, 1, 60)],
    "U-Profil": [("h", "Höhe h", 100, 10, 1000), ("b", "Flanschbreite b", 50, 5, 300),
                 ("s", "Stegdicke s", 6, 1, 50), ("t", "Flanschdicke t", 8.5, 1, 60)],
}

# Formeln (Mathtext) zur Anzeige
FORMELN: Dict[str, Dict[str, str]] = {
    "Rechteck": {"A": r"A = b \cdot h", "Iy": r"I_y = \frac{b\,h^3}{12}",
                 "Iz": r"I_z = \frac{h\,b^3}{12}", "Wy": r"W_y = \frac{b\,h^2}{6}"},
    "Rund": {"A": r"A = \frac{\pi\,d^2}{4}", "Iy": r"I_y = I_z = \frac{\pi\,d^4}{64}",
             "Wy": r"W_y = \frac{\pi\,d^3}{32}", "Ip": r"I_p = \frac{\pi\,d^4}{32}",
             "Wt": r"W_t = \frac{\pi\,d^3}{16}"},
    "Rohr": {"A": r"A = \frac{\pi\,(D^2-d^2)}{4}", "Iy": r"I_y = \frac{\pi\,(D^4-d^4)}{64}",
             "Wy": r"W_y = \frac{\pi\,(D^4-d^4)}{32\,D}", "Ip": r"I_p = \frac{\pi\,(D^4-d^4)}{32}",
             "Wt": r"W_t = \frac{\pi\,(D^4-d^4)}{16\,D}"},
    "I-Profil": {"A": r"A = 2\,b\,t + (h-2t)\,s",
                 "Iy": r"I_y = \frac{b\,h^3 - (b-s)\,(h-2t)^3}{12}",
                 "Iz": r"I_z = \frac{2\,t\,b^3 + (h-2t)\,s^3}{12}",
                 "Wy": r"W_y = \frac{2\,I_y}{h}"},
    "U-Profil": {"A": r"A = 2\,b\,t + (h-2t)\,s",
                 "Iy": r"I_y = \frac{b\,h^3 - (b-s)\,(h-2t)^3}{12}",
                 "Iz": r"I_z = \sum (I_{z,i} + A_i\,a_i^2)",
                 "Wy": r"W_y = \frac{2\,I_y}{h}"},
}


@dataclass
class Querschnitt:
    profil: str
    masse: Dict[str, float]
    A: float
    Iy: float
    Iz: float
    Wy: float
    Wz: float
    Ip: float = 0.0     # polares Flächenträgheitsmoment (nur Kreis/Rohr)
    Wt: float = 0.0     # Torsionswiderstandsmoment (nur Kreis/Rohr)
    ez: float = 0.0     # Schwerpunktabstand (U-Profil: vom Steg-Rücken)
    umriss: List[List[Tuple[float, float]]] = field(default_factory=list)

    @property
    def I_min(self) -> float:
        return min(self.Iy, self.Iz)

    @property
    def iy(self) -> float:
        return math.sqrt(self.Iy / self.A)

    @property
    def i_min(self) -> float:
        return math.sqrt(self.I_min / self.A)

    def bezeichnung(self) -> str:
        teile = ", ".join(f"{k}={v:g}" for k, v in self.masse.items())
        return f"{self.profil} ({teile} mm)"


def _kreis(r, n=72, mx=0.0, my=0.0):
    return [(mx + r * math.cos(2 * math.pi * k / n), my + r * math.sin(2 * math.pi * k / n))
            for k in range(n + 1)]


def berechne(profil: str, masse: Dict[str, float]) -> Querschnitt:
    """Querschnittswerte berechnen. ``masse`` enthält die Schlüssel aus ``MASSE``."""
    m = {k: float(masse[k]) for k, *_ in MASSE[profil]}
    if profil == "Rechteck":
        b, h = m["b"], m["h"]
        _pos(b, h)
        A = b * h
        Iy = b * h ** 3 / 12
        Iz = h * b ** 3 / 12
        umriss = [[(-b / 2, -h / 2), (b / 2, -h / 2), (b / 2, h / 2), (-b / 2, h / 2), (-b / 2, -h / 2)]]
        return Querschnitt(profil, m, A, Iy, Iz, Iy / (h / 2), Iz / (b / 2), umriss=umriss)
    if profil == "Rund":
        d = m["d"]
        _pos(d)
        A = math.pi * d ** 2 / 4
        I = math.pi * d ** 4 / 64
        Ip = math.pi * d ** 4 / 32
        return Querschnitt(profil, m, A, I, I, I / (d / 2), I / (d / 2), Ip=Ip, Wt=Ip / (d / 2),
                           umriss=[_kreis(d / 2)])
    if profil == "Rohr":
        D, d = m["D"], m["d"]
        _pos(D)
        if not 0 <= d < D:
            raise ValueError("Innendurchmesser d muss kleiner als D sein.")
        A = math.pi * (D ** 2 - d ** 2) / 4
        I = math.pi * (D ** 4 - d ** 4) / 64
        Ip = 2 * I
        umriss = [_kreis(D / 2)] + ([_kreis(d / 2)] if d > 0 else [])
        return Querschnitt(profil, m, A, I, I, I / (D / 2), I / (D / 2), Ip=Ip, Wt=Ip / (D / 2),
                           umriss=umriss)
    if profil in ("I-Profil", "U-Profil"):
        h, b, s, t = m["h"], m["b"], m["s"], m["t"]
        _pos(h, b, s, t)
        if 2 * t >= h:
            raise ValueError("Flanschdicke t zu groß (2t muss kleiner als h sein).")
        if s >= b:
            raise ValueError("Stegdicke s muss kleiner als b sein.")
        hs = h - 2 * t
        A = 2 * b * t + hs * s
        Iy = (b * h ** 3 - (b - s) * hs ** 3) / 12
        Wy = Iy / (h / 2)
        if profil == "I-Profil":
            Iz = (2 * t * b ** 3 + hs * s ** 3) / 12
            Wz = Iz / (b / 2)
            x1, x2 = -b / 2, b / 2
            umriss = [[(x1, -h / 2), (x2, -h / 2), (x2, -h / 2 + t), (s / 2, -h / 2 + t),
                       (s / 2, h / 2 - t), (x2, h / 2 - t), (x2, h / 2), (x1, h / 2),
                       (x1, h / 2 - t), (-s / 2, h / 2 - t), (-s / 2, -h / 2 + t),
                       (x1, -h / 2 + t), (x1, -h / 2)]]
            return Querschnitt(profil, m, A, Iy, Iz, Wy, Wz, umriss=umriss)
        # U-Profil: Schwerpunkt e vom Stegrücken aus
        e = (2 * b * t * (b / 2) + hs * s * (s / 2)) / A
        Iz = (2 * (t * b ** 3 / 12 + b * t * (b / 2 - e) ** 2)
              + hs * s ** 3 / 12 + hs * s * (s / 2 - e) ** 2)
        Wz = Iz / max(e, b - e)
        umriss = [[(0 - e, -h / 2), (b - e, -h / 2), (b - e, -h / 2 + t), (s - e, -h / 2 + t),
                   (s - e, h / 2 - t), (b - e, h / 2 - t), (b - e, h / 2), (0 - e, h / 2),
                   (0 - e, -h / 2)]]
        return Querschnitt(profil, m, A, Iy, Iz, Wy, Wz, ez=e, umriss=umriss)
    raise ValueError(f"Unbekanntes Profil: {profil}")


def _pos(*werte):
    for w in werte:
        if w <= 0:
            raise ValueError("Alle Maße müssen größer als 0 sein.")


def standardmasse(profil: str) -> Dict[str, float]:
    return {k: std for k, _, std, *_ in MASSE[profil]}
