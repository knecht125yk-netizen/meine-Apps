"""Zugriff auf Prozesse und Windows-Autostart."""
from __future__ import annotations

import os
import sys
from typing import Dict, Iterable, List, Tuple

import psutil

from .kern import GESCHUETZT, normalisieren

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Programmsperre"


# ---------------------------------------------------------------------------
# Prozesse
# ---------------------------------------------------------------------------

def finde(namen: Iterable[str]) -> Dict[str, List[psutil.Process]]:
    """Laufende Prozesse zu den gegebenen (normalisierten) Namen."""
    gesucht = set(namen)
    treffer: Dict[str, List[psutil.Process]] = {}
    if not gesucht:
        return treffer
    eigene = os.getpid()
    for p in psutil.process_iter(["name"]):
        try:
            n = (p.info.get("name") or "").lower()
            if n in gesucht and p.pid != eigene:
                treffer.setdefault(n, []).append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return treffer


def anhalten(prozesse: Iterable[psutil.Process]) -> Tuple[List[psutil.Process], List[psutil.Process]]:
    """Prozesse einfrieren. Gelingt das nicht, wird beendet. Rückgabe: (angehalten, beendet)."""
    angehalten, beendet = [], []
    for p in prozesse:
        try:
            p.suspend()
            angehalten.append(p)
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            try:
                p.kill()
                beendet.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return angehalten, beendet


def fortsetzen(prozesse: Iterable[psutil.Process]):
    for p in prozesse:
        try:
            p.resume()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def beenden(prozesse: Iterable[psutil.Process]):
    prozesse = list(prozesse)
    for p in prozesse:
        try:
            p.resume()  # eingefrorene Prozesse reagieren sonst evtl. nicht
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        try:
            p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    psutil.wait_procs(prozesse, timeout=2)


def laufende_programme() -> List[Tuple[str, str]]:
    """(Name, Pfad) aller laufenden Programme des Benutzers – ohne Systemprozesse."""
    gesehen = {}
    for p in psutil.process_iter(["name", "exe"]):
        try:
            n = (p.info.get("name") or "")
            exe = p.info.get("exe") or ""
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if not n or not exe:
            continue
        low = normalisieren(n)
        if low in GESCHUETZT or "\\windows\\system32" in exe.lower() or low in gesehen:
            continue
        gesehen[low] = exe
    return sorted(gesehen.items(), key=lambda x: x[0])


# ---------------------------------------------------------------------------
# Autostart (HKCU\...\Run)
# ---------------------------------------------------------------------------

def startbefehl() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --autostart'
    pyw = sys.executable.replace("python.exe", "pythonw.exe")
    skript = os.path.abspath(sys.argv[0])
    return f'"{pyw}" "{skript}" --autostart'


def autostart_setzen(an: bool) -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if an:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, startbefehl())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def autostart_aktiv() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False
