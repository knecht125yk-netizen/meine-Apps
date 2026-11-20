"""Aufgabenliste: Datenmodell, Speicherung (JSON) und Schnelleingabe – ohne GUI."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Tuple

HOCH, MITTEL, NIEDRIG = 1, 2, 3
PRIO_NAMEN = {HOCH: "Hoch", MITTEL: "Mittel", NIEDRIG: "Niedrig"}
PRIO_FARBEN = {HOCH: "#e53935", MITTEL: "#fb8c00", NIEDRIG: "#43a047"}
WOCHENTAGE = {"mo": 0, "di": 1, "mi": 2, "do": 3, "fr": 4, "sa": 5, "so": 6}


@dataclass
class Aufgabe:
    titel: str
    prioritaet: int = MITTEL
    faellig: str = ""            # ISO-Datum oder leer
    erledigt: bool = False
    notiz: str = ""
    erstellt: str = field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))
    erledigt_am: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def faellig_datum(self) -> Optional[dt.date]:
        try:
            return dt.date.fromisoformat(self.faellig) if self.faellig else None
        except ValueError:
            return None

    def ueberfaellig(self, heute: Optional[dt.date] = None) -> bool:
        d = self.faellig_datum()
        return bool(d and not self.erledigt and d < (heute or dt.date.today()))


@dataclass
class Einstellungen:
    symbol_x: int = -1           # -1 = automatisch (rechts oben)
    symbol_y: int = -1
    popup_breite: int = 360
    popup_hoehe: int = 460
    erledigte_zeigen: bool = True
    autostart: bool = False
    symbol_groesse: int = 56


def faellig_text(a: Aufgabe, heute: Optional[dt.date] = None) -> str:
    d = a.faellig_datum()
    if not d:
        return ""
    heute = heute or dt.date.today()
    diff = (d - heute).days
    if diff == 0:
        return "Heute"
    if diff == 1:
        return "Morgen"
    if diff == -1:
        return "Gestern"
    if diff < 0:
        return f"seit {-diff} Tagen"
    if diff < 7:
        return ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][d.weekday()] + f", {d:%d.%m.}"
    return f"{d:%d.%m.%Y}" if d.year != heute.year else f"{d:%d.%m.}"


def schnelleingabe(text: str, heute: Optional[dt.date] = None) -> Tuple[str, int, str]:
    """Text mit Kürzeln zerlegen: ``Zahnarzt anrufen !hoch @morgen``.

    Priorität: ``!`` / ``!hoch`` / ``!!`` = hoch, ``!mittel``, ``!niedrig``.
    Datum:     ``@heute``, ``@morgen``, ``@übermorgen``, ``@fr`` (nächster Freitag), ``@24.12.`` / ``@24.12.2026``.
    Rückgabe: (Titel, Priorität, ISO-Datum oder "").
    """
    heute = heute or dt.date.today()
    prio, datum = MITTEL, ""
    rest = []
    for wort in text.split():
        w = wort.lower()
        if w in ("!", "!!", "!hoch", "!h", "!1"):
            prio = HOCH
        elif w in ("!mittel", "!m", "!2"):
            prio = MITTEL
        elif w in ("!niedrig", "!n", "!3"):
            prio = NIEDRIG
        elif w.startswith("@") and len(w) > 1:
            d = _datum_kuerzel(w[1:], heute)
            if d:
                datum = d.isoformat()
            else:
                rest.append(wort)
        else:
            rest.append(wort)
    return " ".join(rest).strip(), prio, datum


def _datum_kuerzel(k: str, heute: dt.date) -> Optional[dt.date]:
    if k == "heute":
        return heute
    if k == "morgen":
        return heute + dt.timedelta(days=1)
    if k in ("übermorgen", "uebermorgen"):
        return heute + dt.timedelta(days=2)
    if k[:2] in WOCHENTAGE and (len(k) == 2 or k.startswith(("mon", "die", "mit", "don", "fre", "sam", "son"))):
        ziel = WOCHENTAGE[k[:2]]
        tage = (ziel - heute.weekday()) % 7 or 7
        return heute + dt.timedelta(days=tage)
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.?(\d{2,4})?", k)
    if m:
        t, mo, j = int(m.group(1)), int(m.group(2)), m.group(3)
        jahr = (int(j) + 2000 if len(j) == 2 else int(j)) if j else heute.year
        try:
            d = dt.date(jahr, mo, t)
        except ValueError:
            return None
        if not j and d < heute:
            d = d.replace(year=d.year + 1)
        return d
    return None


class Liste:
    def __init__(self, pfad: str):
        self.pfad = pfad
        self.aufgaben: List[Aufgabe] = []
        self.einstellungen = Einstellungen()
        self.laden()

    # -- Datei --------------------------------------------------------------
    def laden(self):
        if not os.path.exists(self.pfad):
            return
        try:
            with open(self.pfad, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            # beschädigte Datei sichern statt zu überschreiben
            try:
                os.replace(self.pfad, self.pfad + ".defekt")
            except OSError:
                pass
            return
        felder = Aufgabe.__dataclass_fields__
        self.aufgaben = [Aufgabe(**{k: v for k, v in a.items() if k in felder}) for a in d.get("aufgaben", [])]
        e = d.get("einstellungen", {})
        self.einstellungen = Einstellungen(**{k: v for k, v in e.items() if k in Einstellungen.__dataclass_fields__})

    def speichern(self):
        os.makedirs(os.path.dirname(self.pfad) or ".", exist_ok=True)
        tmp = self.pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"aufgaben": [asdict(a) for a in self.aufgaben],
                       "einstellungen": asdict(self.einstellungen)}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.pfad)

    # -- Bearbeiten ---------------------------------------------------------
    def hinzufuegen(self, titel: str, prioritaet: Optional[int] = None, faellig: Optional[str] = None) -> Aufgabe:
        t, p, d = schnelleingabe(titel)
        if not t:
            raise ValueError("Bitte einen Text für die Aufgabe eingeben.")
        a = Aufgabe(t, prioritaet if prioritaet is not None and p == MITTEL else p,
                    faellig if faellig and not d else d)
        self.aufgaben.append(a)
        self.speichern()
        return a

    def finde(self, aid: str) -> Aufgabe:
        for a in self.aufgaben:
            if a.id == aid:
                return a
        raise KeyError(aid)

    def umschalten(self, aid: str) -> Aufgabe:
        a = self.finde(aid)
        a.erledigt = not a.erledigt
        a.erledigt_am = dt.datetime.now().isoformat(timespec="seconds") if a.erledigt else ""
        self.speichern()
        return a

    def aendern(self, aid: str, **werte) -> Aufgabe:
        a = self.finde(aid)
        for k, v in werte.items():
            if k not in Aufgabe.__dataclass_fields__ or k == "id":
                raise KeyError(k)
            setattr(a, k, v)
        if not a.titel.strip():
            raise ValueError("Der Titel darf nicht leer sein.")
        self.speichern()
        return a

    def loeschen(self, aid: str):
        self.aufgaben = [a for a in self.aufgaben if a.id != aid]
        self.speichern()

    def erledigte_entfernen(self) -> int:
        vorher = len(self.aufgaben)
        self.aufgaben = [a for a in self.aufgaben if not a.erledigt]
        self.speichern()
        return vorher - len(self.aufgaben)

    # -- Ansicht ------------------------------------------------------------
    def sortiert(self, erledigte: bool = True) -> List[Aufgabe]:
        """Offene zuerst: überfällig/fällig nach Datum, dann Priorität, dann Erstellzeit."""
        offen = [a for a in self.aufgaben if not a.erledigt]
        offen.sort(key=lambda a: (a.faellig_datum() or dt.date.max, a.prioritaet, a.erstellt))
        if not erledigte:
            return offen
        fertig = sorted((a for a in self.aufgaben if a.erledigt), key=lambda a: a.erledigt_am, reverse=True)
        return offen + fertig

    def anzahl_offen(self) -> int:
        return sum(1 for a in self.aufgaben if not a.erledigt)

    def anzahl_ueberfaellig(self, heute: Optional[dt.date] = None) -> int:
        heute = heute or dt.date.today()
        return sum(1 for a in self.aufgaben if a.ueberfaellig(heute) or
                   (not a.erledigt and a.faellig_datum() == heute))
