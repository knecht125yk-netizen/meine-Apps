"""Datenhaltung (SQLite) und Geschäftslogik für Kassenbuch & Rechnungen.

Beträge werden durchgehend als ganze Cent (int) gespeichert, um Rundungsfehler
zu vermeiden. Mengen dürfen Dezimalzahlen sein (z. B. 1,5 Stunden).
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

KLEINUNTERNEHMER_HINWEIS = "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet (Kleinunternehmerregelung)."

STANDARD_EINSTELLUNGEN = {
    "firma_name": "Mein Kleingewerbe",
    "inhaber": "",
    "strasse": "",
    "plz": "",
    "ort": "",
    "telefon": "",
    "email": "",
    "web": "",
    "steuernummer": "",
    "ust_idnr": "",
    "bank": "",
    "iban": "",
    "bic": "",
    "zahlungsziel_tage": "14",
    "angebot_gueltig_tage": "30",
    "rechnung_praefix": "RE",
    "angebot_praefix": "AN",
    "nummer_stellen": "4",
    "nummer_jaehrlich": "1",          # 1 = Zähler beginnt jedes Jahr neu
    "kleinunternehmer_hinweis": KLEINUNTERNEHMER_HINWEIS,
    "rechnung_einleitung": "vielen Dank für Ihren Auftrag. Ich berechne Ihnen folgende Leistungen:",
    "rechnung_schluss": "Bitte überweisen Sie den Rechnungsbetrag bis zum {faellig} unter Angabe der "
                        "Rechnungsnummer auf das unten genannte Konto.\n\nMit freundlichen Grüßen",
    "angebot_einleitung": "vielen Dank für Ihre Anfrage. Gerne biete ich Ihnen Folgendes an:",
    "angebot_schluss": "Dieses Angebot ist gültig bis zum {gueltig}. Ich freue mich auf Ihren Auftrag.\n\n"
                       "Mit freundlichen Grüßen",
    "kasse_anfangsbestand_cent": "0",
    "kasse_anfangsdatum": "",
    "bezahlt_in_kasse": "1",           # bezahlte Rechnung automatisch als Einnahme buchen
}

EINNAHME_KATEGORIEN = ["Erlöse", "Sonstige Einnahmen", "Privateinlage"]
AUSGABE_KATEGORIEN = ["Wareneinkauf", "Material", "Fremdleistungen", "Büromaterial", "Porto",
                      "Telefon / Internet", "Software / Lizenzen", "Fahrtkosten", "Werbung",
                      "Versicherungen", "Gebühren", "Miete", "Werkzeug / Geräte", "Fortbildung",
                      "Privatentnahme", "Sonstige Ausgaben"]

ANGEBOT_STATUS = ["offen", "angenommen", "abgelehnt", "in Rechnung umgewandelt"]
RECHNUNG_STATUS = ["offen", "bezahlt", "storniert"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS einstellungen (schluessel TEXT PRIMARY KEY, wert TEXT);
CREATE TABLE IF NOT EXISTS logo (id INTEGER PRIMARY KEY CHECK (id = 1), daten BLOB);
CREATE TABLE IF NOT EXISTS kunden (
    id INTEGER PRIMARY KEY, nummer TEXT, name TEXT NOT NULL, zusatz TEXT DEFAULT '',
    strasse TEXT DEFAULT '', plz TEXT DEFAULT '', ort TEXT DEFAULT '', email TEXT DEFAULT '',
    telefon TEXT DEFAULT '', notiz TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS artikel (
    id INTEGER PRIMARY KEY, nummer TEXT DEFAULT '', bezeichnung TEXT NOT NULL,
    beschreibung TEXT DEFAULT '', einheit TEXT DEFAULT 'Stk.', preis_cent INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS zaehler (typ TEXT, jahr INTEGER, letzter INTEGER, PRIMARY KEY (typ, jahr));
CREATE TABLE IF NOT EXISTS belege (
    id INTEGER PRIMARY KEY, typ TEXT NOT NULL CHECK (typ IN ('angebot','rechnung')),
    nummer TEXT NOT NULL UNIQUE, datum TEXT NOT NULL, leistungsdatum TEXT DEFAULT '',
    kunde_id INTEGER REFERENCES kunden(id), anschrift TEXT DEFAULT '', betreff TEXT DEFAULT '',
    einleitung TEXT DEFAULT '', schluss TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'offen',
    faellig TEXT DEFAULT '', bezahlt_am TEXT DEFAULT '', angebot_id INTEGER REFERENCES belege(id),
    erstellt TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS positionen (
    id INTEGER PRIMARY KEY, beleg_id INTEGER NOT NULL REFERENCES belege(id) ON DELETE CASCADE,
    pos INTEGER NOT NULL, bezeichnung TEXT NOT NULL, beschreibung TEXT DEFAULT '',
    menge REAL NOT NULL DEFAULT 1, einheit TEXT DEFAULT 'Stk.', preis_cent INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS kasse (
    id INTEGER PRIMARY KEY, datum TEXT NOT NULL, art TEXT NOT NULL CHECK (art IN ('E','A')),
    betrag_cent INTEGER NOT NULL CHECK (betrag_cent > 0), kategorie TEXT NOT NULL,
    beschreibung TEXT DEFAULT '', belegnr TEXT DEFAULT '', rechnung_id INTEGER REFERENCES belege(id),
    erstellt TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS kategorien (name TEXT NOT NULL, art TEXT NOT NULL, PRIMARY KEY (name, art));
"""


# ---------------------------------------------------------------------------
# Geld
# ---------------------------------------------------------------------------

def euro(cent: int, mit_zeichen: bool = True) -> str:
    """1234567 -> '12.345,67 €'"""
    neg = cent < 0
    cent = abs(int(cent))
    s = f"{cent // 100:,}".replace(",", ".") + f",{cent % 100:02d}"
    return ("-" if neg else "") + s + (" €" if mit_zeichen else "")


def parse_euro(text: str) -> int:
    """'1.234,5' / '1234.50' / '12 €' -> Cent."""
    t = str(text).strip().replace("€", "").replace(" ", "")
    if not t:
        return 0
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    d = Decimal(t)
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def zeilensumme(menge: float, preis_cent: int) -> int:
    d = Decimal(str(menge)) * Decimal(int(preis_cent))
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def datum_de(iso: str) -> str:
    if not iso:
        return ""
    try:
        return dt.date.fromisoformat(iso[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return iso


def heute() -> str:
    return dt.date.today().isoformat()


# ---------------------------------------------------------------------------
# Datenklassen
# ---------------------------------------------------------------------------

@dataclass
class Position:
    bezeichnung: str
    menge: float = 1.0
    einheit: str = "Stk."
    preis_cent: int = 0
    beschreibung: str = ""

    @property
    def summe_cent(self) -> int:
        return zeilensumme(self.menge, self.preis_cent)


@dataclass
class Beleg:
    typ: str
    nummer: str = ""
    datum: str = field(default_factory=heute)
    leistungsdatum: str = ""
    kunde_id: Optional[int] = None
    anschrift: str = ""
    betreff: str = ""
    einleitung: str = ""
    schluss: str = ""
    status: str = "offen"
    faellig: str = ""
    bezahlt_am: str = ""
    angebot_id: Optional[int] = None
    positionen: List[Position] = field(default_factory=list)
    id: Optional[int] = None

    @property
    def summe_cent(self) -> int:
        return sum(p.summe_cent for p in self.positionen)

    @property
    def ist_rechnung(self) -> bool:
        return self.typ == "rechnung"


# ---------------------------------------------------------------------------
# Datenbank
# ---------------------------------------------------------------------------

class Datenbank:
    def __init__(self, pfad: str = ":memory:"):
        self.pfad = pfad
        self.con = sqlite3.connect(pfad)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.executescript(SCHEMA)
        self._standardwerte()

    def schliessen(self):
        self.con.close()

    def _standardwerte(self):
        with self.con:
            for k, v in STANDARD_EINSTELLUNGEN.items():
                self.con.execute("INSERT OR IGNORE INTO einstellungen VALUES (?, ?)", (k, v))
            if not self.con.execute("SELECT 1 FROM kategorien LIMIT 1").fetchone():
                self.con.executemany("INSERT INTO kategorien VALUES (?, 'E')", [(k,) for k in EINNAHME_KATEGORIEN])
                self.con.executemany("INSERT INTO kategorien VALUES (?, 'A')", [(k,) for k in AUSGABE_KATEGORIEN])

    # -- Einstellungen ------------------------------------------------------
    def einstellung(self, k: str) -> str:
        r = self.con.execute("SELECT wert FROM einstellungen WHERE schluessel=?", (k,)).fetchone()
        return r[0] if r else STANDARD_EINSTELLUNGEN.get(k, "")

    def einstellungen(self) -> Dict[str, str]:
        d = dict(STANDARD_EINSTELLUNGEN)
        d.update({r[0]: r[1] for r in self.con.execute("SELECT schluessel, wert FROM einstellungen")})
        return d

    def einstellungen_speichern(self, werte: Dict[str, str]):
        with self.con:
            for k, v in werte.items():
                self.con.execute("INSERT OR REPLACE INTO einstellungen VALUES (?, ?)", (k, str(v)))

    def logo(self) -> Optional[bytes]:
        r = self.con.execute("SELECT daten FROM logo WHERE id=1").fetchone()
        return r[0] if r else None

    def logo_speichern(self, daten: Optional[bytes]):
        with self.con:
            if daten:
                self.con.execute("INSERT OR REPLACE INTO logo VALUES (1, ?)", (daten,))
            else:
                self.con.execute("DELETE FROM logo")

    # -- Kategorien ---------------------------------------------------------
    def kategorien(self, art: str) -> List[str]:
        return [r[0] for r in self.con.execute("SELECT name FROM kategorien WHERE art=? ORDER BY rowid", (art,))]

    def kategorie_hinzufuegen(self, name: str, art: str):
        with self.con:
            self.con.execute("INSERT OR IGNORE INTO kategorien VALUES (?, ?)", (name.strip(), art))

    # -- Kunden -------------------------------------------------------------
    def kunden(self, suche: str = "") -> List[sqlite3.Row]:
        s = f"%{suche}%"
        return self.con.execute(
            "SELECT * FROM kunden WHERE name LIKE ? OR zusatz LIKE ? OR ort LIKE ? OR nummer LIKE ? "
            "ORDER BY name COLLATE NOCASE", (s, s, s, s)).fetchall()

    def kunde(self, kid: int) -> Optional[sqlite3.Row]:
        return self.con.execute("SELECT * FROM kunden WHERE id=?", (kid,)).fetchone()

    def kunde_speichern(self, daten: dict, kid: Optional[int] = None) -> int:
        felder = ["nummer", "name", "zusatz", "strasse", "plz", "ort", "email", "telefon", "notiz"]
        if not daten.get("name", "").strip():
            raise ValueError("Der Kundenname darf nicht leer sein.")
        werte = [daten.get(f, "") or "" for f in felder]
        with self.con:
            if kid:
                self.con.execute(f"UPDATE kunden SET {', '.join(f + '=?' for f in felder)} WHERE id=?",
                                 werte + [kid])
                return kid
            if not werte[0]:
                n = self.con.execute("SELECT COUNT(*) FROM kunden").fetchone()[0] + 1
                werte[0] = f"K{n:04d}"
            cur = self.con.execute(f"INSERT INTO kunden ({', '.join(felder)}) VALUES ({', '.join('?' * len(felder))})",
                                   werte)
            return cur.lastrowid

    def kunde_loeschen(self, kid: int):
        if self.con.execute("SELECT 1 FROM belege WHERE kunde_id=? LIMIT 1", (kid,)).fetchone():
            raise ValueError("Kunde wird in Angeboten/Rechnungen verwendet und kann nicht gelöscht werden.")
        with self.con:
            self.con.execute("DELETE FROM kunden WHERE id=?", (kid,))

    @staticmethod
    def anschrift(k) -> str:
        zeilen = [k["name"], k["zusatz"], k["strasse"], f"{k['plz']} {k['ort']}".strip()]
        return "\n".join(z for z in zeilen if z)

    # -- Artikel ------------------------------------------------------------
    def artikel(self, suche: str = "") -> List[sqlite3.Row]:
        s = f"%{suche}%"
        return self.con.execute("SELECT * FROM artikel WHERE bezeichnung LIKE ? OR nummer LIKE ? "
                                "ORDER BY bezeichnung COLLATE NOCASE", (s, s)).fetchall()

    def artikel_speichern(self, daten: dict, aid: Optional[int] = None) -> int:
        felder = ["nummer", "bezeichnung", "beschreibung", "einheit", "preis_cent"]
        if not str(daten.get("bezeichnung", "")).strip():
            raise ValueError("Die Bezeichnung darf nicht leer sein.")
        werte = [daten.get(f, "") for f in felder]
        werte[4] = int(daten.get("preis_cent", 0) or 0)
        with self.con:
            if aid:
                self.con.execute(f"UPDATE artikel SET {', '.join(f + '=?' for f in felder)} WHERE id=?",
                                 werte + [aid])
                return aid
            return self.con.execute(f"INSERT INTO artikel ({', '.join(felder)}) VALUES (?,?,?,?,?)", werte).lastrowid

    def artikel_loeschen(self, aid: int):
        with self.con:
            self.con.execute("DELETE FROM artikel WHERE id=?", (aid,))

    # -- Nummernkreise ------------------------------------------------------
    def _naechste_nummer(self, typ: str, datum: str) -> str:
        """Fortlaufende Nummer vergeben (innerhalb einer laufenden Transaktion aufrufen)."""
        e = self.einstellungen()
        jaehrlich = e["nummer_jaehrlich"] == "1"
        jahr = int(datum[:4]) if jaehrlich else 0
        r = self.con.execute("SELECT letzter FROM zaehler WHERE typ=? AND jahr=?", (typ, jahr)).fetchone()
        n = (r[0] if r else 0) + 1
        self.con.execute("INSERT OR REPLACE INTO zaehler VALUES (?, ?, ?)", (typ, jahr, n))
        praefix = e["rechnung_praefix" if typ == "rechnung" else "angebot_praefix"]
        stellen = int(e["nummer_stellen"] or 4)
        teile = [praefix] if praefix else []
        if jaehrlich:
            teile.append(datum[:4])
        teile.append(f"{n:0{stellen}d}")
        nummer = "-".join(teile)
        # Sicherheitsnetz gegen Dubletten (z. B. nach manueller Zählerkorrektur)
        while self.con.execute("SELECT 1 FROM belege WHERE nummer=?", (nummer,)).fetchone():
            n += 1
            self.con.execute("INSERT OR REPLACE INTO zaehler VALUES (?, ?, ?)", (typ, jahr, n))
            teile[-1] = f"{n:0{stellen}d}"
            nummer = "-".join(teile)
        return nummer

    def naechste_nummer_vorschau(self, typ: str, datum: Optional[str] = None) -> str:
        datum = datum or heute()
        sp = "vorschau"
        self.con.execute(f"SAVEPOINT {sp}")
        try:
            return self._naechste_nummer(typ, datum)
        finally:
            self.con.execute(f"ROLLBACK TO {sp}")
            self.con.execute(f"RELEASE {sp}")

    def zaehler_setzen(self, typ: str, jahr: int, letzter: int):
        """Startnummer festlegen (z. B. beim Umstieg von einem anderen Programm)."""
        if self.einstellung("nummer_jaehrlich") != "1":
            jahr = 0
        with self.con:
            self.con.execute("INSERT OR REPLACE INTO zaehler VALUES (?, ?, ?)", (typ, jahr, int(letzter)))

    def zaehler(self, typ: str, jahr: int) -> int:
        if self.einstellung("nummer_jaehrlich") != "1":
            jahr = 0
        r = self.con.execute("SELECT letzter FROM zaehler WHERE typ=? AND jahr=?", (typ, jahr)).fetchone()
        return r[0] if r else 0

    # -- Belege -------------------------------------------------------------
    def beleg_speichern(self, b: Beleg) -> Beleg:
        if not b.positionen:
            raise ValueError("Bitte mindestens eine Position erfassen.")
        if b.kunde_id is None and not b.anschrift.strip():
            raise ValueError("Bitte einen Kunden auswählen.")
        if b.kunde_id and not b.anschrift.strip():
            b.anschrift = self.anschrift(self.kunde(b.kunde_id))
        e = self.einstellungen()
        if not b.faellig:
            tage = int(e["zahlungsziel_tage" if b.ist_rechnung else "angebot_gueltig_tage"] or 14)
            b.faellig = (dt.date.fromisoformat(b.datum) + dt.timedelta(days=tage)).isoformat()
        if not b.einleitung:
            b.einleitung = e["rechnung_einleitung" if b.ist_rechnung else "angebot_einleitung"]
        if not b.schluss:
            b.schluss = e["rechnung_schluss" if b.ist_rechnung else "angebot_schluss"]
        if b.ist_rechnung and not b.leistungsdatum:
            b.leistungsdatum = b.datum
        felder = ["typ", "nummer", "datum", "leistungsdatum", "kunde_id", "anschrift", "betreff",
                  "einleitung", "schluss", "status", "faellig", "bezahlt_am", "angebot_id"]
        with self.con:
            if b.id is None:
                b.nummer = self._naechste_nummer(b.typ, b.datum)
                werte = [getattr(b, f) for f in felder]
                b.id = self.con.execute(f"INSERT INTO belege ({', '.join(felder)}) VALUES "
                                        f"({', '.join('?' * len(felder))})", werte).lastrowid
            else:
                alt = self.beleg(b.id)
                if alt.ist_rechnung and alt.status != "offen":
                    raise ValueError("Bezahlte oder stornierte Rechnungen können nicht mehr geändert werden.")
                b.nummer = alt.nummer  # Nummer bleibt fest
                self.con.execute(f"UPDATE belege SET {', '.join(f + '=?' for f in felder)} WHERE id=?",
                                 [getattr(b, f) for f in felder] + [b.id])
                self.con.execute("DELETE FROM positionen WHERE beleg_id=?", (b.id,))
            for i, p in enumerate(b.positionen, 1):
                self.con.execute("INSERT INTO positionen (beleg_id, pos, bezeichnung, beschreibung, menge, "
                                 "einheit, preis_cent) VALUES (?,?,?,?,?,?,?)",
                                 (b.id, i, p.bezeichnung, p.beschreibung, float(p.menge), p.einheit,
                                  int(p.preis_cent)))
        return b

    def beleg(self, bid: int) -> Beleg:
        r = self.con.execute("SELECT * FROM belege WHERE id=?", (bid,)).fetchone()
        if not r:
            raise KeyError(bid)
        b = Beleg(**{k: r[k] for k in r.keys() if k in Beleg.__dataclass_fields__})
        b.positionen = [Position(p["bezeichnung"], p["menge"], p["einheit"], p["preis_cent"], p["beschreibung"])
                        for p in self.con.execute("SELECT * FROM positionen WHERE beleg_id=? ORDER BY pos", (bid,))]
        return b

    def belege(self, typ: str, jahr: Optional[int] = None, suche: str = "") -> List[dict]:
        sql = ("SELECT b.*, COALESCE(k.name, '') AS kunde, "
               "COALESCE((SELECT SUM(CAST(ROUND(menge * preis_cent) AS INTEGER)) FROM positionen p "
               "WHERE p.beleg_id=b.id), 0) AS summe_cent "
               "FROM belege b LEFT JOIN kunden k ON k.id=b.kunde_id WHERE b.typ=?")
        par: list = [typ]
        if jahr:
            sql += " AND substr(b.datum,1,4)=?"
            par.append(str(jahr))
        if suche:
            sql += " AND (b.nummer LIKE ? OR k.name LIKE ? OR b.betreff LIKE ?)"
            par += [f"%{suche}%"] * 3
        sql += " ORDER BY b.datum DESC, b.id DESC"
        out = []
        for r in self.con.execute(sql, par):
            d = dict(r)
            # exakte Summe (Rundung pro Position wie auf dem Beleg)
            d["summe_cent"] = self.beleg(d["id"]).summe_cent
            out.append(d)
        return out

    def angebot_loeschen(self, bid: int):
        b = self.beleg(bid)
        if b.ist_rechnung:
            raise ValueError("Rechnungen werden nicht gelöscht, sondern storniert (lückenlose Nummern).")
        with self.con:
            self.con.execute("UPDATE belege SET angebot_id=NULL WHERE angebot_id=?", (bid,))
            self.con.execute("DELETE FROM belege WHERE id=?", (bid,))

    def status_setzen(self, bid: int, status: str):
        b = self.beleg(bid)
        erlaubt = RECHNUNG_STATUS if b.ist_rechnung else ANGEBOT_STATUS
        if status not in erlaubt:
            raise ValueError(f"Ungültiger Status: {status}")
        with self.con:
            self.con.execute("UPDATE belege SET status=? WHERE id=?", (status, bid))

    def angebot_zu_rechnung(self, angebot_id: int, datum: Optional[str] = None) -> Beleg:
        """Erstellt aus einem Angebot eine neue Rechnung (mit neuer Rechnungsnummer)."""
        a = self.beleg(angebot_id)
        if a.ist_rechnung:
            raise ValueError("Das ist bereits eine Rechnung.")
        vorhanden = self.con.execute("SELECT nummer FROM belege WHERE angebot_id=? AND typ='rechnung' "
                                     "AND status!='storniert'", (angebot_id,)).fetchone()
        if vorhanden:
            raise ValueError(f"Zu diesem Angebot existiert bereits die Rechnung {vorhanden[0]}.")
        r = Beleg("rechnung", datum=datum or heute(), kunde_id=a.kunde_id, anschrift=a.anschrift,
                  betreff=a.betreff, angebot_id=a.id,
                  positionen=[Position(p.bezeichnung, p.menge, p.einheit, p.preis_cent, p.beschreibung)
                              for p in a.positionen])
        self.beleg_speichern(r)
        self.status_setzen(a.id, "in Rechnung umgewandelt")
        return r

    def duplizieren(self, bid: int, typ: Optional[str] = None) -> Beleg:
        a = self.beleg(bid)
        n = Beleg(typ or a.typ, datum=heute(), kunde_id=a.kunde_id, anschrift=a.anschrift, betreff=a.betreff,
                  positionen=[Position(p.bezeichnung, p.menge, p.einheit, p.preis_cent, p.beschreibung)
                              for p in a.positionen])
        return self.beleg_speichern(n)

    def als_bezahlt(self, bid: int, datum: Optional[str] = None, in_kasse: Optional[bool] = None) -> Optional[int]:
        """Rechnung als bezahlt markieren; optional automatisch im Kassenbuch als Einnahme buchen."""
        b = self.beleg(bid)
        if not b.ist_rechnung:
            raise ValueError("Nur Rechnungen können bezahlt werden.")
        if b.status == "storniert":
            raise ValueError("Die Rechnung ist storniert.")
        datum = datum or heute()
        if in_kasse is None:
            in_kasse = self.einstellung("bezahlt_in_kasse") == "1"
        kid = None
        with self.con:
            self.con.execute("UPDATE belege SET status='bezahlt', bezahlt_am=? WHERE id=?", (datum, bid))
        if in_kasse and b.summe_cent > 0 and not self.con.execute(
                "SELECT 1 FROM kasse WHERE rechnung_id=?", (bid,)).fetchone():
            kunde = b.anschrift.splitlines()[0] if b.anschrift else ""
            kid = self.buchen(datum, "E", b.summe_cent, "Erlöse", f"Zahlung {kunde}".strip(), b.nummer,
                              rechnung_id=bid)
        return kid

    def stornieren(self, bid: int):
        b = self.beleg(bid)
        if not b.ist_rechnung:
            raise ValueError("Nur Rechnungen können storniert werden.")
        with self.con:
            self.con.execute("UPDATE belege SET status='storniert' WHERE id=?", (bid,))
            self.con.execute("DELETE FROM kasse WHERE rechnung_id=?", (bid,))
            if b.angebot_id:
                self.con.execute("UPDATE belege SET status='angenommen' WHERE id=? AND "
                                 "status='in Rechnung umgewandelt'", (b.angebot_id,))

    # -- Kassenbuch ---------------------------------------------------------
    def buchen(self, datum: str, art: str, betrag_cent: int, kategorie: str, beschreibung: str = "",
               belegnr: str = "", rechnung_id: Optional[int] = None, kid: Optional[int] = None) -> int:
        if art not in ("E", "A"):
            raise ValueError("Art muss 'E' (Einnahme) oder 'A' (Ausgabe) sein.")
        if int(betrag_cent) <= 0:
            raise ValueError("Der Betrag muss größer als 0 sein.")
        dt.date.fromisoformat(datum)
        if not kategorie:
            raise ValueError("Bitte eine Kategorie wählen.")
        self.kategorie_hinzufuegen(kategorie, art)
        with self.con:
            if kid:
                self.con.execute("UPDATE kasse SET datum=?, art=?, betrag_cent=?, kategorie=?, beschreibung=?, "
                                 "belegnr=? WHERE id=?",
                                 (datum, art, int(betrag_cent), kategorie, beschreibung, belegnr, kid))
                return kid
            return self.con.execute("INSERT INTO kasse (datum, art, betrag_cent, kategorie, beschreibung, belegnr, "
                                    "rechnung_id) VALUES (?,?,?,?,?,?,?)",
                                    (datum, art, int(betrag_cent), kategorie, beschreibung, belegnr,
                                     rechnung_id)).lastrowid

    def buchung_loeschen(self, kid: int):
        with self.con:
            self.con.execute("DELETE FROM kasse WHERE id=?", (kid,))

    def buchungen(self, jahr: Optional[int] = None, monat: Optional[int] = None) -> List[dict]:
        """Buchungen chronologisch inkl. laufendem Kassenbestand."""
        alle = [dict(r) for r in self.con.execute("SELECT * FROM kasse ORDER BY datum, id")]
        bestand = int(self.einstellung("kasse_anfangsbestand_cent") or 0)
        out = []
        for b in alle:
            bestand += b["betrag_cent"] if b["art"] == "E" else -b["betrag_cent"]
            b["bestand_cent"] = bestand
            j, m = int(b["datum"][:4]), int(b["datum"][5:7])
            if (jahr is None or j == jahr) and (monat is None or m == monat):
                out.append(b)
        return out

    def kassenbestand(self, bis: Optional[str] = None) -> int:
        bestand = int(self.einstellung("kasse_anfangsbestand_cent") or 0)
        sql = "SELECT art, SUM(betrag_cent) FROM kasse"
        par = []
        if bis:
            sql += " WHERE datum <= ?"
            par.append(bis)
        for art, summe in self.con.execute(sql + " GROUP BY art", par):
            bestand += summe if art == "E" else -summe
        return bestand

    def monatsuebersicht(self, jahr: int) -> List[dict]:
        out = []
        for m in range(1, 13):
            e = a = 0
            for art, summe in self.con.execute(
                    "SELECT art, SUM(betrag_cent) FROM kasse WHERE substr(datum,1,7)=? GROUP BY art",
                    (f"{jahr:04d}-{m:02d}",)):
                if art == "E":
                    e = summe
                else:
                    a = summe
            out.append({"monat": m, "einnahmen": e, "ausgaben": a, "saldo": e - a})
        return out

    def kategorieuebersicht(self, jahr: int, monat: Optional[int] = None) -> List[dict]:
        muster = f"{jahr:04d}-{monat:02d}%" if monat else f"{jahr:04d}-%"
        return [dict(r) for r in self.con.execute(
            "SELECT art, kategorie, SUM(betrag_cent) AS summe, COUNT(*) AS anzahl FROM kasse "
            "WHERE datum LIKE ? GROUP BY art, kategorie ORDER BY art DESC, summe DESC", (muster,))]

    def jahre(self) -> List[int]:
        js = {int(r[0]) for r in self.con.execute(
            "SELECT DISTINCT substr(datum,1,4) FROM kasse UNION SELECT DISTINCT substr(datum,1,4) FROM belege")}
        js.add(dt.date.today().year)
        return sorted(js, reverse=True)

    # -- Kennzahlen ---------------------------------------------------------
    def umsatz(self, jahr: int) -> int:
        """Umsatz nach Zufluss: bezahlte Rechnungen (nach Zahldatum) des Jahres."""
        s = 0
        for r in self.con.execute("SELECT id FROM belege WHERE typ='rechnung' AND status='bezahlt' "
                                  "AND substr(bezahlt_am,1,4)=?", (str(jahr),)):
            s += self.beleg(r[0]).summe_cent
        return s

    def offene_rechnungen(self) -> List[dict]:
        return [b for b in self.belege("rechnung") if b["status"] == "offen"]
