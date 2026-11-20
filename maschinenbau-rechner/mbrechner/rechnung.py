"""Datenstrukturen für eine dokumentierbare Berechnung.

Jede Berechnung liefert ein ``Rechnung``-Objekt mit Eingaben, Rechenschritten
(Formel als LaTeX/Mathtext, eingesetzte Werte, Ergebnis) und einem optionalen
Sicherheitsnachweis. Daraus erzeugen GUI, PDF- und Word-Export ihre Darstellung.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


def fmt(wert: float, stellen: int = 4) -> str:
    """Zahl gut lesbar formatieren (deutsches Dezimalkomma)."""
    if wert is None:
        return "–"
    if isinstance(wert, str):
        return wert
    if wert == 0:
        return "0"
    a = abs(wert)
    if a >= 1e7 or a < 1e-3:
        mant, exp = f"{wert:.{stellen - 1}e}".split("e")
        return f"{mant.replace('.', ',')}·10^{int(exp)}"
    if a >= 1000:
        ganz = abs(wert - round(wert)) < 1e-9
        s = f"{wert:,.0f}" if (ganz or a >= 1e5) else f"{wert:,.1f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    # signifikante Stellen
    s = f"{wert:.{stellen}g}"
    if "e" in s:
        s = f"{wert:.3f}"
    return s.replace(".", ",")


@dataclass
class Eingabe:
    name: str
    symbol: str
    wert: object
    einheit: str = ""

    def text(self) -> str:
        w = fmt(self.wert) if isinstance(self.wert, (int, float)) else str(self.wert)
        return f"{w} {self.einheit}".strip()


@dataclass
class Schritt:
    beschreibung: str
    formel: str            # Mathtext/LaTeX ohne $ ... $
    symbol: str            # Ergebnissymbol (Mathtext), z. B. r"\sigma_b"
    wert: float
    einheit: str = ""
    eingesetzt: str = ""   # Klartext mit eingesetzten Zahlen

    def ergebnis_text(self) -> str:
        return f"{fmt(self.wert)} {self.einheit}".strip()


@dataclass
class Nachweis:
    beschreibung: str
    vorhanden: float       # vorhandene Sicherheit
    erforderlich: float    # erforderliche Sicherheit
    formel: str = r"S = \frac{\sigma_{grenz}}{\sigma_{vorh}}"
    eingesetzt: str = ""

    @property
    def erfuellt(self) -> bool:
        return self.vorhanden >= self.erforderlich

    @property
    def auslastung(self) -> float:
        if self.vorhanden <= 0:
            return float("inf")
        return self.erforderlich / self.vorhanden

    def text(self) -> str:
        status = "ERFÜLLT" if self.erfuellt else "NICHT ERFÜLLT"
        return (f"S = {fmt(self.vorhanden)} ≥ S_erf = {fmt(self.erforderlich)} → {status}"
                if self.erfuellt else
                f"S = {fmt(self.vorhanden)} < S_erf = {fmt(self.erforderlich)} → {status}")


@dataclass
class Rechnung:
    titel: str
    eingaben: List[Eingabe] = field(default_factory=list)
    schritte: List[Schritt] = field(default_factory=list)
    nachweise: List[Nachweis] = field(default_factory=list)
    hinweise: List[str] = field(default_factory=list)
    plot: Optional[dict] = None   # Daten für Diagramm/Skizze

    def eingabe(self, name, symbol, wert, einheit=""):
        self.eingaben.append(Eingabe(name, symbol, wert, einheit))

    def schritt(self, beschreibung, formel, symbol, wert, einheit="", eingesetzt=""):
        s = Schritt(beschreibung, formel, symbol, wert, einheit, eingesetzt)
        self.schritte.append(s)
        return wert

    def nachweis(self, beschreibung, vorhanden, erforderlich, formel=None, eingesetzt=""):
        n = Nachweis(beschreibung, vorhanden, erforderlich,
                     formel or r"S = \frac{\sigma_{grenz}}{\sigma_{vorh}}", eingesetzt)
        self.nachweise.append(n)
        return n

    def wert(self, symbol: str) -> float:
        """Ergebnis eines Schritts über sein Symbol abrufen (praktisch für Tests)."""
        for s in self.schritte:
            if s.symbol == symbol:
                return s.wert
        raise KeyError(symbol)

    @property
    def alle_erfuellt(self) -> bool:
        return all(n.erfuellt for n in self.nachweise)
