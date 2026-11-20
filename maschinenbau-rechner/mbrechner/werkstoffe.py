"""Werkstofftabelle mit gängigen Stählen und Aluminiumlegierungen.

Werte: typische Mindestwerte für kleine Abmessungen (Nenndicke ≤ 16 mm)
nach EN 10025 / EN 10083 / EN 10088 / EN 755. Für reale Auslegungen
immer das Werkstoffdatenblatt bzw. die Norm prüfen.

Einheiten: E, G, Rm, Re in N/mm², Dichte in g/cm³.
Tetmajer: σK = a − b·λ (N/mm²), gültig für λ < λ0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Werkstoff:
    name: str
    gruppe: str
    E: float
    Rm: float
    Re: float           # Streckgrenze Re bzw. Dehngrenze Rp0,2
    nu: float = 0.30
    dichte: float = 7.85
    tetmajer: Optional[Tuple[float, float, float]] = None  # (a, b, λ0)
    bemerkung: str = ""

    @property
    def G(self) -> float:
        """Schubmodul G = E / (2(1+ν))."""
        return self.E / (2 * (1 + self.nu))


WERKSTOFFE = [
    Werkstoff("S235JR", "Baustahl", 210000, 360, 235, tetmajer=(310, 1.14, 104),
              bemerkung="allgemeiner Baustahl"),
    Werkstoff("S355J2", "Baustahl", 210000, 470, 355,
              bemerkung="höherfester Baustahl"),
    Werkstoff("E295", "Maschinenbaustahl", 210000, 470, 295, tetmajer=(335, 0.62, 89),
              bemerkung="Wellen, Bolzen (St 50)"),
    Werkstoff("E335", "Maschinenbaustahl", 210000, 570, 335, tetmajer=(335, 0.62, 89),
              bemerkung="Wellen, Zahnräder (St 60)"),
    Werkstoff("C45E (normalgeglüht)", "Vergütungsstahl", 210000, 620, 340,
              bemerkung="+N"),
    Werkstoff("C45E (vergütet)", "Vergütungsstahl", 210000, 700, 490,
              bemerkung="+QT, d ≤ 16 mm"),
    Werkstoff("42CrMo4 (vergütet)", "Vergütungsstahl", 210000, 1100, 900,
              bemerkung="+QT, d ≤ 16 mm"),
    Werkstoff("34CrNiMo6 (vergütet)", "Vergütungsstahl", 210000, 1200, 1000,
              bemerkung="+QT, d ≤ 16 mm"),
    Werkstoff("16MnCr5", "Einsatzstahl", 210000, 600, 360,
              bemerkung="Kernwerte, nicht gehärtet (orientierend)"),
    Werkstoff("X5CrNi18-10 (1.4301)", "Edelstahl", 200000, 520, 210, nu=0.30, dichte=7.90,
              bemerkung="austenitisch, Rp0,2"),
    Werkstoff("EN AW-5083 H111", "Aluminium", 71000, 275, 125, nu=0.33, dichte=2.66,
              bemerkung="Rp0,2"),
    Werkstoff("EN AW-6060 T6", "Aluminium", 70000, 190, 150, nu=0.33, dichte=2.70,
              bemerkung="Strangpressprofile, Rp0,2"),
    Werkstoff("EN AW-6082 T6", "Aluminium", 70000, 310, 260, nu=0.33, dichte=2.70,
              bemerkung="Rp0,2"),
    Werkstoff("EN AW-7075 T6", "Aluminium", 72000, 540, 470, nu=0.33, dichte=2.81,
              bemerkung="hochfest, Rp0,2"),
]

_NACH_NAME = {w.name: w for w in WERKSTOFFE}


def werkstoff(name: str) -> Werkstoff:
    return _NACH_NAME[name]


def namen():
    return [w.name for w in WERKSTOFFE]
