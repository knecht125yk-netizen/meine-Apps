"""Kernlogik der Programmsperre – ohne GUI und ohne Prozesszugriff (testbar).

* PIN wird nur als PBKDF2-SHA256-Hash mit Salt gespeichert.
* Freigaben gelten pro Programm (Prozessname, z. B. ``chrome.exe``) bis zu einem Zeitpunkt.
* Nach mehreren falschen PIN-Eingaben wird die Eingabe für eine wachsende Zeit gesperrt.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

ITERATIONEN = 200_000
MAX_FEHLVERSUCHE = 5
WARTEZEIT_S = 60  # verdoppelt sich bei jeder weiteren Sperre

# Prozesse, die niemals gesperrt werden dürfen (sonst kann Windows/der Nutzer hängen)
GESCHUETZT = {
    "explorer.exe", "csrss.exe", "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe", "smss.exe",
    "wininit.exe", "dwm.exe", "taskmgr.exe", "system", "registry", "fontdrvhost.exe", "sihost.exe",
    "ctfmon.exe", "searchhost.exe", "startmenuexperiencehost.exe", "shellexperiencehost.exe",
    "runtimebroker.exe", "conhost.exe", "programmsperre.exe", "python.exe", "pythonw.exe",
}


def normalisieren(name: str) -> str:
    """Prozessnamen vergleichbar machen: nur Dateiname, klein geschrieben."""
    return name.strip().strip('"').replace("\\", "/").rsplit("/", 1)[-1].lower()


def pin_hash(pin: str, salt: Optional[bytes] = None, iterationen: Optional[int] = None):
    salt = salt or secrets.token_bytes(16)
    iterationen = iterationen or ITERATIONEN
    h = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterationen)
    return salt.hex(), h.hex()


def pin_gueltig(pin: str) -> Optional[str]:
    """Gibt eine Fehlermeldung zurück oder None, wenn die PIN akzeptabel ist."""
    if not pin.isdigit():
        return "Die PIN darf nur aus Ziffern bestehen."
    if not 4 <= len(pin) <= 12:
        return "Die PIN muss 4 bis 12 Ziffern lang sein."
    if len(set(pin)) == 1:
        return "Bitte keine PIN aus lauter gleichen Ziffern verwenden."
    return None


@dataclass
class Programm:
    name: str                 # Prozessname, z. B. "chrome.exe"
    anzeige: str = ""         # Anzeigename, z. B. "Google Chrome"
    pfad: str = ""            # optional: Pfad zur EXE (nur zur Info)

    def __post_init__(self):
        self.name = normalisieren(self.name)
        if not self.anzeige:
            self.anzeige = os.path.splitext(self.name)[0].capitalize()


@dataclass
class Konfiguration:
    pin_salt: str = ""
    pin_hash: str = ""
    iterationen: int = ITERATIONEN
    programme: List[Programm] = field(default_factory=list)
    freigabe_minuten: int = 30
    nach_ablauf_sperren: bool = True    # laufendes Programm nach Ablauf erneut anhalten
    warnung_minuten: int = 2            # Vorwarnung vor Ablauf
    autostart: bool = True

    @classmethod
    def laden(cls, pfad: str) -> "Konfiguration":
        if not os.path.exists(pfad):
            return cls()
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        progs = [Programm(**p) for p in d.pop("programme", [])]
        bekannt = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(programme=progs, **bekannt)

    def speichern(self, pfad: str):
        os.makedirs(os.path.dirname(pfad) or ".", exist_ok=True)
        tmp = pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        os.replace(tmp, pfad)


class Sperre:
    """Zustand der Sperre (Freigaben, Fehlversuche, Pause)."""

    def __init__(self, konfig: Konfiguration, uhr=time.time):
        self.k = konfig
        self.uhr = uhr
        self.freigaben: Dict[str, float] = {}
        self.gewarnt: set = set()
        self.fehlversuche = 0
        self.sperrstufe = 0
        self.eingabe_gesperrt_bis = 0.0
        self.pausiert_bis = 0.0

    # -- PIN ----------------------------------------------------------------
    @property
    def pin_gesetzt(self) -> bool:
        return bool(self.k.pin_hash)

    def pin_setzen(self, neue_pin: str):
        fehler = pin_gueltig(neue_pin)
        if fehler:
            raise ValueError(fehler)
        self.k.iterationen = ITERATIONEN
        self.k.pin_salt, self.k.pin_hash = pin_hash(neue_pin, None, ITERATIONEN)

    def wartezeit(self) -> int:
        """Sekunden, bis wieder eine PIN eingegeben werden darf (0 = sofort)."""
        return max(0, int(round(self.eingabe_gesperrt_bis - self.uhr())))

    def pin_pruefen(self, pin: str) -> bool:
        if not self.pin_gesetzt:
            return False
        if self.wartezeit() > 0:
            return False
        _, h = pin_hash(pin, bytes.fromhex(self.k.pin_salt), self.k.iterationen)
        if hmac.compare_digest(h, self.k.pin_hash):
            self.fehlversuche = 0
            self.sperrstufe = 0
            return True
        self.fehlversuche += 1
        if self.fehlversuche >= MAX_FEHLVERSUCHE:
            self.eingabe_gesperrt_bis = self.uhr() + WARTEZEIT_S * (2 ** self.sperrstufe)
            self.sperrstufe += 1
            self.fehlversuche = 0
        return False

    def restversuche(self) -> int:
        return MAX_FEHLVERSUCHE - self.fehlversuche

    # -- Programme ----------------------------------------------------------
    def namen(self) -> set:
        return {p.name for p in self.k.programme}

    def programm_hinzufuegen(self, name: str, anzeige: str = "", pfad: str = "") -> Programm:
        p = Programm(name, anzeige, pfad)
        if p.name in GESCHUETZT:
            raise ValueError(f"{p.name} ist ein Systemprogramm und kann nicht gesperrt werden.")
        if not p.name.endswith(".exe") and "." not in p.name:
            p.name += ".exe"
        if p.name in self.namen():
            raise ValueError(f"{p.name} ist bereits in der Liste.")
        self.k.programme.append(p)
        return p

    def programm_entfernen(self, name: str):
        name = normalisieren(name)
        self.k.programme = [p for p in self.k.programme if p.name != name]
        self.freigaben.pop(name, None)

    def anzeige(self, name: str) -> str:
        name = normalisieren(name)
        for p in self.k.programme:
            if p.name == name:
                return p.anzeige
        return name

    # -- Freigaben & Pause --------------------------------------------------
    def ist_freigegeben(self, name: str) -> bool:
        return self.freigaben.get(normalisieren(name), 0) > self.uhr()

    def ist_pausiert(self) -> bool:
        return self.pausiert_bis > self.uhr()

    def ist_gesperrt(self, name: str) -> bool:
        name = normalisieren(name)
        return name in self.namen() and not self.ist_freigegeben(name) and not self.ist_pausiert()

    def freigeben(self, name: str, minuten: Optional[int] = None):
        minuten = self.k.freigabe_minuten if minuten is None else minuten
        name = normalisieren(name)
        self.freigaben[name] = self.uhr() + minuten * 60
        self.gewarnt.discard(name)

    def sperren(self, name: str):
        self.freigaben.pop(normalisieren(name), None)

    def restzeit(self, name: str) -> int:
        return max(0, int(self.freigaben.get(normalisieren(name), 0) - self.uhr()))

    def pausieren(self, minuten: int):
        self.pausiert_bis = self.uhr() + minuten * 60

    def pause_beenden(self):
        self.pausiert_bis = 0.0

    def abgelaufen(self) -> List[str]:
        """Freigaben, die soeben abgelaufen sind (werden dabei entfernt)."""
        jetzt = self.uhr()
        weg = [n for n, t in self.freigaben.items() if t <= jetzt]
        for n in weg:
            del self.freigaben[n]
            self.gewarnt.discard(n)
        return weg

    def bald_ablaufend(self) -> List[str]:
        """Freigaben, die innerhalb der Warnzeit ablaufen und noch nicht gewarnt wurden."""
        grenze = self.k.warnung_minuten * 60
        out = []
        for n, t in self.freigaben.items():
            if n not in self.gewarnt and 0 < t - self.uhr() <= grenze:
                self.gewarnt.add(n)
                out.append(n)
        return out
