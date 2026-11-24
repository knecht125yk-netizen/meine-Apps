"""Oberfläche (PySide6) für Kassenbuch & Rechnungen."""
from __future__ import annotations

import datetime as dt
import glob
import os
import shutil
import sys
from typing import List, Optional

from PySide6.QtCore import QDate, QLocale, QStandardPaths, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QKeySequence, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox,
                               QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
                               QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
                               QProgressBar, QPushButton, QRadioButton, QScrollArea, QSpinBox,
                               QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import erechnung, excel_liste
from .ausgabe import MONATE, beleg_pdf, kassenbuch_csv, kassenbuch_excel, kassenbuch_pdf
from .daten import (ANGEBOT_STATUS, Beleg, Datenbank, Position, RECHNUNG_STATUS, datum_de, euro, heute,
                    parse_euro)

GRENZE_VORJAHR = 25_000_00      # § 19 UStG ab 2025: Vorjahresumsatz max. 25.000 €
GRENZE_LAUFEND = 100_000_00     # laufendes Jahr max. 100.000 €

# ---------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------


def qdate(iso: str) -> QDate:
    try:
        d = dt.date.fromisoformat(iso[:10])
        return QDate(d.year, d.month, d.day)
    except (ValueError, TypeError):
        return QDate.currentDate()


def iso(q: QDate) -> str:
    return f"{q.year():04d}-{q.month():02d}-{q.day():02d}"


def datum_edit(iso_wert: str = "") -> QDateEdit:
    d = QDateEdit(qdate(iso_wert or heute()))
    d.setCalendarPopup(True)
    d.setDisplayFormat("dd.MM.yyyy")
    return d


def item(text, rechts=False, daten=None, farbe=None) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    if rechts:
        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    if daten is not None:
        it.setData(Qt.UserRole, daten)
    if farbe:
        it.setForeground(QColor(farbe))
    return it


def tabelle(spalten: List[str], dehnen: int = 1) -> QTableWidget:
    t = QTableWidget(0, len(spalten))
    t.setHorizontalHeaderLabels(spalten)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    h = t.horizontalHeader()
    h.setSectionResizeMode(QHeaderView.ResizeToContents)
    h.setSectionResizeMode(dehnen, QHeaderView.Stretch)
    return t


def gewaehlte_id(t: QTableWidget) -> Optional[int]:
    r = t.currentRow()
    if r < 0:
        return None
    it = t.item(r, 0)
    return it.data(Qt.UserRole) if it else None


def fehler(parent, text):
    QMessageBox.warning(parent, "Hinweis", str(text))


def datei_oeffnen(pfad):
    QDesktopServices.openUrl(QUrl.fromLocalFile(pfad))


class GeldEdit(QLineEdit):
    def __init__(self, cent: int = 0):
        super().__init__(euro(cent, False))
        self.setAlignment(Qt.AlignRight)
        self.setPlaceholderText("0,00")

    def cent(self) -> int:
        return parse_euro(self.text())


# ---------------------------------------------------------------------------
# Dialoge Stammdaten
# ---------------------------------------------------------------------------

class KundenDialog(QDialog):
    FELDER = [("name", "Name / Firma *"), ("zusatz", "Ansprechpartner / Zusatz"), ("strasse", "Straße, Nr."),
              ("plz", "PLZ"), ("ort", "Ort"), ("email", "E-Mail"), ("telefon", "Telefon"),
              ("nummer", "Kundennummer (leer = automatisch)"),
              ("leitweg_id", "Leitweg-ID (nur bei Behörden)")]

    def __init__(self, db: Datenbank, kid: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.db, self.kid = db, kid
        self.setWindowTitle("Kunde bearbeiten" if kid else "Neuer Kunde")
        form = QFormLayout(self)
        self.f = {}
        k = db.kunde(kid) if kid else None
        for key, label in self.FELDER:
            w = QLineEdit(k[key] if k else "")
            form.addRow(label, w)
            self.f[key] = w
        self.notiz = QPlainTextEdit(k["notiz"] if k else "")
        self.notiz.setMaximumHeight(70)
        form.addRow("Notiz", self.notiz)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.speichern)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.resize(460, 0)

    def speichern(self):
        d = {k: w.text().strip() for k, w in self.f.items()}
        d["notiz"] = self.notiz.toPlainText()
        try:
            self.kid = self.db.kunde_speichern(d, self.kid)
        except ValueError as e:
            return fehler(self, e)
        self.accept()


class ArtikelDialog(QDialog):
    def __init__(self, db: Datenbank, aid: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.db, self.aid = db, aid
        self.setWindowTitle("Artikel / Leistung")
        a = None
        if aid:
            a = db.con.execute("SELECT * FROM artikel WHERE id=?", (aid,)).fetchone()
        form = QFormLayout(self)
        self.nummer = QLineEdit(a["nummer"] if a else "")
        self.bez = QLineEdit(a["bezeichnung"] if a else "")
        self.beschr = QLineEdit(a["beschreibung"] if a else "")
        self.einheit = QComboBox()
        self.einheit.setEditable(True)
        self.einheit.addItems(["Stk.", "Std.", "pauschal", "m", "m²", "kg", "km", "Tag"])
        self.einheit.setCurrentText(a["einheit"] if a else "Stk.")
        self.preis = GeldEdit(a["preis_cent"] if a else 0)
        form.addRow("Bezeichnung *", self.bez)
        form.addRow("Beschreibung", self.beschr)
        form.addRow("Einheit", self.einheit)
        form.addRow("Preis (€)", self.preis)
        form.addRow("Artikelnummer", self.nummer)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.speichern)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.resize(420, 0)

    def speichern(self):
        try:
            self.aid = self.db.artikel_speichern({
                "nummer": self.nummer.text().strip(), "bezeichnung": self.bez.text().strip(),
                "beschreibung": self.beschr.text().strip(), "einheit": self.einheit.currentText().strip(),
                "preis_cent": self.preis.cent()}, self.aid)
        except Exception as e:
            return fehler(self, e)
        self.accept()


# ---------------------------------------------------------------------------
# Beleg-Dialog (Angebot / Rechnung)
# ---------------------------------------------------------------------------

class BelegDialog(QDialog):
    SP = ["Bezeichnung", "Beschreibung", "Menge", "Einheit", "Einzelpreis €", "Gesamt"]

    def __init__(self, db: Datenbank, typ: str, bid: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.db, self.typ = db, typ
        self.beleg = db.beleg(bid) if bid else Beleg(typ)
        name = "Rechnung" if typ == "rechnung" else "Angebot"
        nummer = self.beleg.nummer or f"{db.naechste_nummer_vorschau(typ)} (wird beim Speichern vergeben)"
        self.setWindowTitle(f"{name} {nummer}")
        self.resize(980, 680)
        lay = QVBoxLayout(self)

        kopf = QGridLayout()
        self.kunde = QComboBox()
        self.kunde.setMinimumWidth(280)
        self._kunden_laden()
        btn_kneu = QPushButton("Neuer Kunde …")
        btn_kneu.clicked.connect(self._neuer_kunde)
        self.datum = datum_edit(self.beleg.datum)
        self.leistung = datum_edit(self.beleg.leistungsdatum or self.beleg.datum)
        self.betreff = QLineEdit(self.beleg.betreff)
        self.betreff.setPlaceholderText("z. B. Reparatur Gartentor")
        kopf.addWidget(QLabel("Kunde:"), 0, 0)
        kopf.addWidget(self.kunde, 0, 1)
        kopf.addWidget(btn_kneu, 0, 2)
        kopf.addWidget(QLabel("Datum:"), 0, 3)
        kopf.addWidget(self.datum, 0, 4)
        kopf.addWidget(QLabel("Betreff:"), 1, 0)
        kopf.addWidget(self.betreff, 1, 1, 1, 2)
        if typ == "rechnung":
            kopf.addWidget(QLabel("Leistungsdatum:"), 1, 3)
            kopf.addWidget(self.leistung, 1, 4)
        kopf.addWidget(QLabel(f"Nr.: {nummer}"), 2, 0, 1, 3)
        lay.addLayout(kopf)

        # Schnell-Hinzufügen aus Artikelstamm
        schnell = QHBoxLayout()
        self.artikel = QComboBox()
        self.artikel.setEditable(True)
        self.artikel.setInsertPolicy(QComboBox.NoInsert)
        self.artikel.lineEdit().setPlaceholderText("Artikel suchen …")
        for a in db.artikel():
            self.artikel.addItem(f"{a['bezeichnung']}  –  {euro(a['preis_cent'])} / {a['einheit']}", a["id"])
        self.artikel.setCurrentIndex(-1)
        self.menge = QDoubleSpinBox()
        self.menge.setRange(0.001, 1e6)
        self.menge.setDecimals(2)
        self.menge.setValue(1)
        b_art = QPushButton("+ Artikel")
        b_art.clicked.connect(self._artikel_hinzu)
        b_frei = QPushButton("+ Freie Position")
        b_frei.clicked.connect(lambda: self._zeile_hinzu(Position("", 1, "Stk.", 0)))
        b_weg = QPushButton("Position entfernen")
        b_weg.clicked.connect(self._zeile_weg)
        b_hoch = QPushButton("▲")
        b_hoch.setFixedWidth(34)
        b_hoch.clicked.connect(lambda: self._verschieben(-1))
        b_runter = QPushButton("▼")
        b_runter.setFixedWidth(34)
        b_runter.clicked.connect(lambda: self._verschieben(1))
        schnell.addWidget(self.artikel, 3)
        schnell.addWidget(QLabel("Menge:"))
        schnell.addWidget(self.menge)
        schnell.addWidget(b_art)
        schnell.addWidget(b_frei)
        schnell.addStretch()
        schnell.addWidget(b_hoch)
        schnell.addWidget(b_runter)
        schnell.addWidget(b_weg)
        lay.addLayout(schnell)

        self.tab = QTableWidget(0, len(self.SP))
        self.tab.setHorizontalHeaderLabels(self.SP)
        h = self.tab.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (2, 3, 4, 5):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tab.itemChanged.connect(self._neu_rechnen)
        lay.addWidget(self.tab, 1)
        for p in self.beleg.positionen:
            self._zeile_hinzu(p)

        self.summe = QLabel()
        self.summe.setAlignment(Qt.AlignRight)
        self.summe.setStyleSheet("font-size:17px; font-weight:bold;")
        lay.addWidget(self.summe)
        hinweis = QLabel(db.einstellung("kleinunternehmer_hinweis"))
        hinweis.setStyleSheet("color:#666;")
        hinweis.setAlignment(Qt.AlignRight)
        lay.addWidget(hinweis)

        texte = QHBoxLayout()
        self.einleitung = QPlainTextEdit(self.beleg.einleitung or db.einstellung(f"{typ}_einleitung"))
        self.schluss = QPlainTextEdit(self.beleg.schluss or db.einstellung(f"{typ}_schluss"))
        for w, t in ((self.einleitung, "Einleitungstext"), (self.schluss, "Schlusstext ({faellig} / {gueltig} = Datum)")):
            g = QGroupBox(t)
            gl = QVBoxLayout(g)
            w.setMaximumHeight(80)
            gl.addWidget(w)
            texte.addWidget(g)
        lay.addLayout(texte)

        bb = QDialogButtonBox()
        self.b_speichern = bb.addButton("Speichern", QDialogButtonBox.AcceptRole)
        self.b_pdf = bb.addButton("Speichern && PDF", QDialogButtonBox.ActionRole)
        bb.addButton("Abbrechen", QDialogButtonBox.RejectRole)
        self.b_speichern.clicked.connect(lambda: self.speichern(False))
        self.b_pdf.clicked.connect(lambda: self.speichern(True))
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.pdf_gewuenscht = False
        if self.beleg.kunde_id:
            i = self.kunde.findData(self.beleg.kunde_id)
            self.kunde.setCurrentIndex(i)
        self._neu_rechnen()
        if not self.beleg.positionen:
            self.artikel.setFocus()

    # -- Kunden -------------------------------------------------------------
    def _kunden_laden(self):
        self.kunde.clear()
        self.kunde.addItem("– Kunde wählen –", None)
        for k in self.db.kunden():
            self.kunde.addItem(f"{k['name']}  ({k['ort']})" if k["ort"] else k["name"], k["id"])

    def _neuer_kunde(self):
        d = KundenDialog(self.db, parent=self)
        if d.exec():
            self._kunden_laden()
            self.kunde.setCurrentIndex(self.kunde.findData(d.kid))

    # -- Positionen ---------------------------------------------------------
    def _zeile_hinzu(self, p: Position):
        self.tab.blockSignals(True)
        r = self.tab.rowCount()
        self.tab.insertRow(r)
        werte = [p.bezeichnung, p.beschreibung, f"{p.menge:g}".replace(".", ","), p.einheit,
                 euro(p.preis_cent, False), ""]
        for c, v in enumerate(werte):
            it = QTableWidgetItem(v)
            if c in (2, 4, 5):
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if c == 5:
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.tab.setItem(r, c, it)
        self.tab.blockSignals(False)
        self._neu_rechnen()
        if not p.bezeichnung:
            self.tab.setCurrentCell(r, 0)
            self.tab.editItem(self.tab.item(r, 0))

    def _artikel_hinzu(self):
        aid = self.artikel.currentData()
        if aid is None:
            # Freitext aus dem Suchfeld als neue Position übernehmen
            text = self.artikel.currentText().strip()
            if text:
                self._zeile_hinzu(Position(text, self.menge.value(), "Stk.", 0))
            return
        a = self.db.con.execute("SELECT * FROM artikel WHERE id=?", (aid,)).fetchone()
        self._zeile_hinzu(Position(a["bezeichnung"], self.menge.value(), a["einheit"], a["preis_cent"],
                                   a["beschreibung"]))
        self.artikel.setCurrentIndex(-1)
        self.menge.setValue(1)

    def _zeile_weg(self):
        r = self.tab.currentRow()
        if r >= 0:
            self.tab.removeRow(r)
            self._neu_rechnen()

    def _verschieben(self, d):
        r = self.tab.currentRow()
        z = r + d
        if r < 0 or z < 0 or z >= self.tab.rowCount():
            return
        ps = self.positionen(streng=False)
        ps[r], ps[z] = ps[z], ps[r]
        self.tab.setRowCount(0)
        for p in ps:
            self._zeile_hinzu(p)
        self.tab.setCurrentCell(z, 0)

    def positionen(self, streng=True) -> List[Position]:
        out = []
        for r in range(self.tab.rowCount()):
            t = lambda c: (self.tab.item(r, c).text() if self.tab.item(r, c) else "").strip()  # noqa: E731
            try:
                menge = float(t(2).replace(".", "").replace(",", ".") or 0) if "," in t(2) else float(t(2) or 0)
                preis = parse_euro(t(4))
            except Exception:
                if streng:
                    raise ValueError(f"Zeile {r + 1}: Menge oder Preis ist keine gültige Zahl.")
                menge, preis = 0, 0
            if streng and not t(0):
                raise ValueError(f"Zeile {r + 1}: Bitte eine Bezeichnung eingeben.")
            out.append(Position(t(0), menge, t(3), preis, t(1)))
        return out

    def _neu_rechnen(self, *_):
        ps = self.positionen(streng=False)
        self.tab.blockSignals(True)
        for r, p in enumerate(ps):
            it = self.tab.item(r, 5)
            if it:
                it.setText(euro(p.summe_cent))
        self.tab.blockSignals(False)
        self.summe.setText(f"Gesamtbetrag: {euro(sum(p.summe_cent for p in ps))}")

    # -- Speichern ----------------------------------------------------------
    def speichern(self, pdf: bool):
        b = self.beleg
        try:
            b.positionen = self.positionen()
        except ValueError as e:
            return fehler(self, e)
        kid = self.kunde.currentData()
        if kid is None:
            return fehler(self, "Bitte einen Kunden auswählen (oder „Neuer Kunde …“ anlegen).")
        neuer_kunde = kid != b.kunde_id
        b.kunde_id = kid
        if neuer_kunde or not b.anschrift:
            b.anschrift = self.db.anschrift(self.db.kunde(kid))
        alt_datum = b.datum
        b.datum = iso(self.datum.date())
        if b.datum != alt_datum:
            b.faellig = ""  # neu berechnen
        b.leistungsdatum = iso(self.leistung.date()) if self.typ == "rechnung" else ""
        b.betreff = self.betreff.text().strip()
        b.einleitung = self.einleitung.toPlainText().strip()
        b.schluss = self.schluss.toPlainText().strip()
        try:
            self.db.beleg_speichern(b)
        except ValueError as e:
            return fehler(self, e)
        self.pdf_gewuenscht = pdf
        self.accept()


# ---------------------------------------------------------------------------
# Seiten
# ---------------------------------------------------------------------------

class BelegSeite(QWidget):
    def __init__(self, haupt: "Hauptfenster", typ: str):
        super().__init__()
        self.h, self.db, self.typ = haupt, haupt.db, typ
        rechnung = typ == "rechnung"
        lay = QVBoxLayout(self)
        leiste = QHBoxLayout()
        b_neu = QPushButton("+ Neue Rechnung" if rechnung else "+ Neues Angebot")
        b_neu.setObjectName("primaer")
        b_neu.clicked.connect(self.neu)
        leiste.addWidget(b_neu)
        self.knoepfe = {}
        aktionen = [("Bearbeiten", self.bearbeiten), ("PDF", self.pdf), ("Duplizieren", self.duplizieren)]
        if rechnung:
            aktionen += [("E-Rechnung …", self.e_rechnung), ("Als bezahlt markieren", self.bezahlt),
                         ("Stornieren", self.stornieren)]
        else:
            aktionen += [("→ In Rechnung umwandeln", self.umwandeln), ("Status …", self.status),
                         ("Löschen", self.loeschen)]
        for text, fn in aktionen:
            b = QPushButton(text)
            b.clicked.connect(fn)
            leiste.addWidget(b)
            self.knoepfe[text] = b
        if not rechnung:
            self.knoepfe["→ In Rechnung umwandeln"].setObjectName("primaer")
        leiste.addStretch()
        self.jahr = QComboBox()
        self.jahr.currentIndexChanged.connect(self.laden)
        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Suchen …")
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(self.laden)
        leiste.addWidget(QLabel("Jahr:"))
        leiste.addWidget(self.jahr)
        leiste.addWidget(self.suche)
        lay.addLayout(leiste)
        sp = ["Nummer", "Kunde", "Betreff", "Datum", "Fällig" if rechnung else "Gültig bis", "Betrag", "Status"]
        self.t = tabelle(sp, 2)
        self.t.doubleClicked.connect(self.bearbeiten)
        lay.addWidget(self.t)
        self.info = QLabel()
        lay.addWidget(self.info)

    def jahre_laden(self):
        akt = self.jahr.currentData()
        self.jahr.blockSignals(True)
        self.jahr.clear()
        self.jahr.addItem("Alle", None)
        for j in self.db.jahre():
            self.jahr.addItem(str(j), j)
        i = self.jahr.findData(akt)
        self.jahr.setCurrentIndex(i if i >= 0 else 0)
        self.jahr.blockSignals(False)

    def laden(self, *_):
        belege = self.db.belege(self.typ, self.jahr.currentData(), self.suche.text().strip())
        self.t.setRowCount(0)
        heute_ = heute()
        summe = 0
        farben = {"bezahlt": "#2e7d32", "storniert": "#9e9e9e", "angenommen": "#2e7d32", "abgelehnt": "#c62828",
                  "in Rechnung umgewandelt": "#1565c0"}
        for b in belege:
            r = self.t.rowCount()
            self.t.insertRow(r)
            status = b["status"]
            farbe = farben.get(status)
            if status == "offen" and self.typ == "rechnung" and b["faellig"] and b["faellig"] < heute_:
                status, farbe = "überfällig", "#c62828"
            werte = [b["nummer"], b["kunde"] or (b["anschrift"].splitlines() or [""])[0], b["betreff"],
                     datum_de(b["datum"]), datum_de(b["faellig"]), euro(b["summe_cent"]),
                     status + (f" ({datum_de(b['bezahlt_am'])})" if b["status"] == "bezahlt" else "")]
            for c, v in enumerate(werte):
                self.t.setItem(r, c, item(v, c == 5, b["id"] if c == 0 else None, farbe if c == 6 else None))
            if b["status"] != "storniert":
                summe += b["summe_cent"]
        self.info.setText(f"{len(belege)} {'Rechnungen' if self.typ == 'rechnung' else 'Angebote'} · "
                          f"Summe (ohne Stornos): {euro(summe)}")

    def _id(self):
        bid = gewaehlte_id(self.t)
        if bid is None:
            fehler(self, "Bitte zuerst einen Eintrag in der Liste auswählen.")
        return bid

    def neu(self):
        if not self.db.kunden():
            QMessageBox.information(self, "Erster Kunde", "Es gibt noch keine Kunden. Lege im nächsten Fenster "
                                                          "über „Neuer Kunde …“ einen an.")
        self._dialog(None)

    def bearbeiten(self, *_):
        bid = self._id()
        if bid is None:
            return
        b = self.db.beleg(bid)
        if b.ist_rechnung and b.status != "offen":
            if QMessageBox.question(self, "Nicht änderbar", f"Die Rechnung ist {b.status} und kann nicht mehr "
                                    "geändert werden.\nPDF anzeigen?") == QMessageBox.Yes:
                self.pdf()
            return
        self._dialog(bid)

    def _dialog(self, bid):
        d = BelegDialog(self.db, self.typ, bid, self)
        if d.exec():
            self.h.alles_neu()
            if d.pdf_gewuenscht:
                self.pdf_erzeugen(d.beleg.id)

    def pdf(self):
        bid = self._id()
        if bid is not None:
            self.pdf_erzeugen(bid)

    def pdf_erzeugen(self, bid):
        b = self.db.beleg(bid)
        ordner = self.h.pdf_ordner()
        kunde = (b.anschrift.splitlines() or ["Kunde"])[0]
        sicher = "".join(ch for ch in kunde if ch.isalnum() or ch in " -_").strip().replace(" ", "_")[:40]
        vorschlag = os.path.join(ordner, f"{b.nummer}_{sicher}.pdf")
        pfad, _ = QFileDialog.getSaveFileName(self, "PDF speichern", vorschlag, "PDF (*.pdf)")
        if not pfad:
            return
        try:
            beleg_pdf(self.db, b, pfad)
        except PermissionError:
            return fehler(self, "Die Datei ist gesperrt – ist sie noch in einem PDF-Programm geöffnet?")
        self.h.db.einstellungen_speichern({"pdf_ordner": os.path.dirname(pfad)})
        datei_oeffnen(pfad)

    def e_rechnung(self):
        bid = self._id()
        if bid is None:
            return
        b = self.db.beleg(bid)
        d = QDialog(self)
        d.setWindowTitle(f"E-Rechnung {b.nummer}")
        lay = QVBoxLayout(d)
        info = QLabel("<b>Welches Format?</b><br><br>"
                      "<b>ZUGFeRD-PDF</b> – sieht aus wie deine normale Rechnung, enthält aber zusätzlich die "
                      "maschinenlesbaren Daten. Ideal für Firmenkunden per E-Mail.<br><br>"
                      "<b>XRechnung (XML)</b> – reine Datendatei, vor allem für Behörden/öffentliche Auftraggeber "
                      "(dort meist mit Leitweg-ID des Kunden).<br><br>"
                      "<span style='color:#666'>Hinweis: Als Kleinunternehmer (§ 19 UStG) bist du von der Pflicht, "
                      "E-Rechnungen auszustellen, ausgenommen – du kannst sie aber freiwillig senden, "
                      "z. B. wenn ein Kunde danach fragt.</span>")
        info.setWordWrap(True)
        lay.addWidget(info)
        bb = QDialogButtonBox()
        b_z = bb.addButton("ZUGFeRD-PDF", QDialogButtonBox.AcceptRole)
        b_x = bb.addButton("XRechnung (XML)", QDialogButtonBox.AcceptRole)
        bb.addButton("Abbrechen", QDialogButtonBox.RejectRole)
        wahl = {}
        b_z.clicked.connect(lambda: (wahl.setdefault("f", "zugferd"), d.accept()))
        b_x.clicked.connect(lambda: (wahl.setdefault("f", "xrechnung"), d.accept()))
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        d.resize(520, 0)
        if not d.exec() or "f" not in wahl:
            return
        xr = wahl["f"] == "xrechnung"
        fehlt = erechnung.pflichtangaben_pruefen(self.db, b, xrechnung=xr)
        if fehlt:
            return fehler(self, "Für die E-Rechnung fehlen noch Angaben:\n\n• " + "\n• ".join(fehlt))
        kunde = (b.anschrift.splitlines() or ["Kunde"])[0]
        sicher = "".join(ch for ch in kunde if ch.isalnum() or ch in " -_").strip().replace(" ", "_")[:40]
        endung, filt = (("xml", "XRechnung (*.xml)") if xr else ("pdf", "ZUGFeRD-PDF (*.pdf)"))
        vorschlag = os.path.join(self.h.pdf_ordner(), f"{b.nummer}_{sicher}{'_XRechnung' if xr else '_ZUGFeRD'}.{endung}")
        pfad, _ = QFileDialog.getSaveFileName(self, "E-Rechnung speichern", vorschlag, filt)
        if not pfad:
            return
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            (erechnung.xrechnung_speichern if xr else erechnung.zugferd_pdf)(self.db, b, pfad)
        except PermissionError:
            return fehler(self, "Die Datei ist gesperrt – ist sie noch geöffnet?")
        except Exception as ex:
            return fehler(self, f"E-Rechnung konnte nicht erstellt werden:\n{ex}")
        finally:
            QApplication.restoreOverrideCursor()
        if xr:
            QMessageBox.information(self, "XRechnung erstellt", f"Gespeichert:\n{pfad}\n\nDie XML-Datei kannst du "
                                    "per E-Mail senden oder im Portal des Auftraggebers hochladen.")
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(pfad)))
        else:
            datei_oeffnen(pfad)

    def duplizieren(self):
        bid = self._id()
        if bid is None:
            return
        n = self.db.duplizieren(bid)
        self.h.alles_neu()
        self._dialog(n.id)

    def bezahlt(self):
        bid = self._id()
        if bid is None:
            return
        b = self.db.beleg(bid)
        if b.status != "offen":
            return fehler(self, f"Die Rechnung ist bereits {b.status}.")
        d = QDialog(self)
        d.setWindowTitle(f"Zahlungseingang {b.nummer}")
        f = QFormLayout(d)
        datum = datum_edit()
        kasse = QCheckBox("Als Einnahme ins Kassenbuch buchen")
        kasse.setChecked(self.db.einstellung("bezahlt_in_kasse") == "1")
        f.addRow("Betrag:", QLabel(euro(b.summe_cent)))
        f.addRow("Bezahlt am:", datum)
        f.addRow(kasse)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        if d.exec():
            try:
                self.db.als_bezahlt(bid, iso(datum.date()), kasse.isChecked())
            except ValueError as e:
                return fehler(self, e)
            self.h.alles_neu()

    def stornieren(self):
        bid = self._id()
        if bid is None:
            return
        b = self.db.beleg(bid)
        if b.status == "storniert":
            return
        if QMessageBox.question(self, "Stornieren", f"Rechnung {b.nummer} wirklich stornieren?\n\n"
                                "Die Nummer bleibt erhalten (lückenlose Nummerierung). Eine evtl. Kassenbuchung "
                                "zu dieser Rechnung wird entfernt.") == QMessageBox.Yes:
            self.db.stornieren(bid)
            self.h.alles_neu()

    def umwandeln(self):
        bid = self._id()
        if bid is None:
            return
        try:
            r = self.db.angebot_zu_rechnung(bid)
        except ValueError as e:
            return fehler(self, e)
        self.h.alles_neu()
        self.h.tabs.setCurrentWidget(self.h.rechnungen)
        if QMessageBox.question(self, "Rechnung erstellt", f"Rechnung {r.nummer} wurde erstellt "
                                f"({euro(r.summe_cent)}).\n\nJetzt als PDF speichern?") == QMessageBox.Yes:
            self.h.rechnungen.pdf_erzeugen(r.id)

    def status(self):
        bid = self._id()
        if bid is None:
            return
        b = self.db.beleg(bid)
        s, ok = QInputDialog.getItem(self, "Status", f"Status für {b.nummer}:", ANGEBOT_STATUS[:3],
                                     max(0, ANGEBOT_STATUS.index(b.status)) if b.status in ANGEBOT_STATUS[:3] else 0,
                                     False)
        if ok:
            self.db.status_setzen(bid, s)
            self.laden()

    def loeschen(self):
        bid = self._id()
        if bid is None:
            return
        b = self.db.beleg(bid)
        if QMessageBox.question(self, "Löschen", f"Angebot {b.nummer} wirklich löschen?") == QMessageBox.Yes:
            try:
                self.db.angebot_loeschen(bid)
            except ValueError as e:
                return fehler(self, e)
            self.h.alles_neu()


class BuchungDialog(QDialog):
    def __init__(self, db: Datenbank, kid: Optional[int] = None, art: str = "E", parent=None):
        super().__init__(parent)
        self.db, self.kid = db, kid
        b = dict(db.con.execute("SELECT * FROM kasse WHERE id=?", (kid,)).fetchone()) if kid else None
        art = b["art"] if b else art
        self.setWindowTitle("Buchung bearbeiten" if kid else ("Neue Einnahme" if art == "E" else "Neue Ausgabe"))
        f = QFormLayout(self)
        artbox = QHBoxLayout()
        self.r_e = QRadioButton("Einnahme")
        self.r_a = QRadioButton("Ausgabe")
        (self.r_e if art == "E" else self.r_a).setChecked(True)
        g = QButtonGroup(self)
        g.addButton(self.r_e)
        g.addButton(self.r_a)
        artbox.addWidget(self.r_e)
        artbox.addWidget(self.r_a)
        artbox.addStretch()
        self.datum = datum_edit(b["datum"] if b else "")
        self.betrag = GeldEdit(b["betrag_cent"] if b else 0)
        self.betrag.selectAll()
        self.kategorie = QComboBox()
        self.kategorie.setEditable(True)
        self.beschr = QLineEdit(b["beschreibung"] if b else "")
        self.belegnr = QLineEdit(b["belegnr"] if b else "")
        f.addRow("Art", artbox)
        f.addRow("Datum", self.datum)
        f.addRow("Betrag (€)", self.betrag)
        f.addRow("Kategorie", self.kategorie)
        f.addRow("Beschreibung", self.beschr)
        f.addRow("Beleg-Nr.", self.belegnr)
        self.r_e.toggled.connect(self._kategorien)
        self._kategorien()
        if b:
            self.kategorie.setCurrentText(b["kategorie"])
            if b["rechnung_id"]:
                f.addRow(QLabel("<i>Automatisch aus Rechnung gebucht.</i>"))
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.speichern)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        self.betrag.setFocus()
        self.resize(420, 0)

    def _kategorien(self, *_):
        akt = self.kategorie.currentText()
        self.kategorie.clear()
        self.kategorie.addItems(self.db.kategorien("E" if self.r_e.isChecked() else "A"))
        if akt and self.kategorie.findText(akt) >= 0:
            self.kategorie.setCurrentText(akt)

    def speichern(self):
        try:
            self.kid = self.db.buchen(iso(self.datum.date()), "E" if self.r_e.isChecked() else "A",
                                      self.betrag.cent(), self.kategorie.currentText().strip(),
                                      self.beschr.text().strip(), self.belegnr.text().strip(), kid=self.kid)
        except Exception as e:
            return fehler(self, e)
        self.accept()


class EingangsDialog(QDialog):
    """Zeigt eine empfangene E-Rechnung lesbar an und bucht sie auf Wunsch als Ausgabe."""

    def __init__(self, db: Datenbank, r, pfad: str, daten: bytes, parent=None):
        super().__init__(parent)
        self.db, self.r, self.pfad, self.daten = db, r, pfad, daten
        self.setWindowTitle(f"E-Rechnung {r.nummer} von {r.verkaeufer}")
        self.resize(760, 600)
        lay = QVBoxLayout(self)
        kopf = QLabel(
            f"<h2 style='margin:0'>{r.verkaeufer}</h2><span style='color:#666'>{r.verkaeufer_adresse}</span><br><br>"
            f"<b>Rechnung:</b> {r.nummer} &nbsp; <b>Datum:</b> {datum_de(r.datum)} &nbsp; "
            f"<b>Fällig:</b> {datum_de(r.faellig) or '–'}<br><b>An:</b> {r.kaeufer} &nbsp; <b>Format:</b> {r.format}"
            + (f"<br><b>IBAN:</b> {r.iban}" if r.iban else ""))
        kopf.setTextFormat(Qt.RichText)
        kopf.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(kopf)
        t = tabelle(["Bezeichnung", "Menge", "Einheit", "Einzelpreis", "Summe"], 0)
        for p in r.positionen:
            z = t.rowCount()
            t.insertRow(z)
            for c, v in enumerate([p["bezeichnung"], p["menge"].replace(".", ","), erechnung.einheit_text(p["einheit"]),
                                   euro(parse_euro(p["preis"])) if p["preis"] else "",
                                   euro(parse_euro(p["summe"])) if p["summe"] else ""]):
                t.setItem(z, c, item(v, c >= 1 and c != 2))
        lay.addWidget(t, 1)
        summen = QLabel(f"Netto: {euro(r.netto_cent)} · USt: {euro(r.steuer_cent)} · "
                        f"<b style='font-size:16px'>Zu zahlen: {euro(r.zahlbetrag_cent)}</b>")
        summen.setAlignment(Qt.AlignRight)
        lay.addWidget(summen)
        hinweis = QLabel("Als Kleinunternehmer kannst du keine Vorsteuer abziehen – gebucht wird der Bruttobetrag. "
                         "Die Originaldatei wird beim Buchen im Datenordner unter „Eingangsrechnungen“ archiviert.")
        hinweis.setWordWrap(True)
        hinweis.setStyleSheet("color:#666;")
        lay.addWidget(hinweis)
        zeile = QHBoxLayout()
        self.kat = QComboBox()
        self.kat.setEditable(True)
        self.kat.addItems(db.kategorien("A"))
        self.kat.setCurrentText("Material" if "Material" in db.kategorien("A") else self.kat.itemText(0))
        self.datum = datum_edit(r.datum or heute())
        zeile.addWidget(QLabel("Kategorie:"))
        zeile.addWidget(self.kat, 1)
        zeile.addWidget(QLabel("Buchungsdatum (Zahlung):"))
        zeile.addWidget(self.datum)
        lay.addLayout(zeile)
        bb = QDialogButtonBox()
        b_buchen = bb.addButton("Als Ausgabe ins Kassenbuch buchen", QDialogButtonBox.AcceptRole)
        bb.addButton("Schließen", QDialogButtonBox.RejectRole)
        b_buchen.clicked.connect(self.buchen)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        if r.zahlbetrag_cent <= 0:
            b_buchen.setEnabled(False)

    def buchen(self):
        r = self.r
        try:
            ordner = os.path.join(os.path.dirname(self.db.pfad) if self.db.pfad != ":memory:" else
                                  os.path.expanduser("~"), "Eingangsrechnungen")
            os.makedirs(ordner, exist_ok=True)
            name = "".join(ch for ch in f"{r.datum}_{r.verkaeufer}_{r.nummer}" if ch.isalnum() or ch in "-_.")[:90]
            ziel = os.path.join(ordner, name + os.path.splitext(self.pfad)[1].lower())
            with open(ziel, "wb") as f:
                f.write(self.daten)
            self.db.buchen(iso(self.datum.date()), "A", r.zahlbetrag_cent, self.kat.currentText().strip(),
                           f"{r.verkaeufer}"[:120], r.nummer)
        except Exception as ex:
            return fehler(self, ex)
        self.accept()


class KassenSeite(QWidget):
    def __init__(self, haupt: "Hauptfenster"):
        super().__init__()
        self.h, self.db = haupt, haupt.db
        lay = QVBoxLayout(self)
        leiste = QHBoxLayout()
        for text, art, name in (("+ Einnahme", "E", "gruen"), ("− Ausgabe", "A", "rot")):
            b = QPushButton(text)
            b.setObjectName(name)
            b.clicked.connect(lambda _=False, a=art: self.neu(a))
            leiste.addWidget(b)
        for text, fn in (("Bearbeiten", self.bearbeiten), ("Löschen", self.loeschen),
                         ("📥 E-Rechnung empfangen …", self.e_rechnung_empfangen)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            leiste.addWidget(b)
        leiste.addStretch()
        self.jahr = QComboBox()
        self.monat = QComboBox()
        self.monat.addItem("Ganzes Jahr", None)
        for i, m in enumerate(MONATE, 1):
            self.monat.addItem(m, i)
        self.jahr.currentIndexChanged.connect(self.laden)
        self.monat.currentIndexChanged.connect(self.laden)
        leiste.addWidget(QLabel("Jahr:"))
        leiste.addWidget(self.jahr)
        leiste.addWidget(self.monat)
        for text, fn in (("CSV", self.exp_csv), ("Excel", self.exp_excel), ("PDF", self.exp_pdf)):
            b = QPushButton(f"Export {text}")
            b.clicked.connect(fn)
            leiste.addWidget(b)
        lay.addLayout(leiste)

        self.innen = QTabWidget()
        lay.addWidget(self.innen, 1)
        self.t = tabelle(["Datum", "Beschreibung", "Kategorie", "Beleg-Nr.", "Einnahme", "Ausgabe", "Bestand"], 1)
        self.t.doubleClicked.connect(self.bearbeiten)
        self.innen.addTab(self.t, "Buchungen")
        ueb = QWidget()
        ul = QHBoxLayout(ueb)
        self.t_monat = tabelle(["Monat", "Einnahmen", "Ausgaben", "Saldo"], 0)
        self.t_kat = tabelle(["Art", "Kategorie", "Anzahl", "Summe"], 1)
        g1 = QGroupBox("Monatsübersicht")
        QVBoxLayout(g1).addWidget(self.t_monat)
        g2 = QGroupBox("Nach Kategorien (gewählter Zeitraum)")
        QVBoxLayout(g2).addWidget(self.t_kat)
        ul.addWidget(g1, 1)
        ul.addWidget(g2, 1)
        self.innen.addTab(ueb, "Monats- und Jahresübersicht")
        self.summen = QLabel()
        self.summen.setStyleSheet("font-size:14px; padding:6px;")
        lay.addWidget(self.summen)

    def jahre_laden(self):
        akt = self.jahr.currentData() or dt.date.today().year
        self.jahr.blockSignals(True)
        self.jahr.clear()
        for j in self.db.jahre():
            self.jahr.addItem(str(j), j)
        self.jahr.setCurrentIndex(max(0, self.jahr.findData(akt)))
        self.jahr.blockSignals(False)

    def laden(self, *_):
        jahr = self.jahr.currentData() or dt.date.today().year
        monat = self.monat.currentData()
        bs = self.db.buchungen(jahr, monat)
        self.t.setRowCount(0)
        e = a = 0
        for b in bs:
            r = self.t.rowCount()
            self.t.insertRow(r)
            ein = b["art"] == "E"
            if ein:
                e += b["betrag_cent"]
            else:
                a += b["betrag_cent"]
            werte = [datum_de(b["datum"]), b["beschreibung"], b["kategorie"], b["belegnr"],
                     euro(b["betrag_cent"]) if ein else "", "" if ein else euro(b["betrag_cent"]),
                     euro(b["bestand_cent"])]
            for c, v in enumerate(werte):
                farbe = "#2e7d32" if c == 4 else "#c62828" if c == 5 else ("#c62828" if c == 6 and b["bestand_cent"] < 0 else None)
                self.t.setItem(r, c, item(v, c >= 4, b["id"] if c == 0 else None, farbe))
        self.t.scrollToBottom()
        bestand = self.db.kassenbestand()
        zr = f"{MONATE[monat - 1]} {jahr}" if monat else str(jahr)
        self.summen.setText(f"<b>{zr}:</b> Einnahmen <span style='color:#2e7d32'><b>{euro(e)}</b></span> · "
                            f"Ausgaben <span style='color:#c62828'><b>{euro(a)}</b></span> · "
                            f"Saldo <b>{euro(e - a)}</b> &nbsp;&nbsp;|&nbsp;&nbsp; aktueller Kassenbestand: "
                            f"<b>{euro(bestand)}</b>")
        # Übersicht
        self.t_monat.setRowCount(0)
        se = sa = 0
        for z in self.db.monatsuebersicht(jahr):
            r = self.t_monat.rowCount()
            self.t_monat.insertRow(r)
            se += z["einnahmen"]
            sa += z["ausgaben"]
            for c, v in enumerate([MONATE[z["monat"] - 1], euro(z["einnahmen"]), euro(z["ausgaben"]), euro(z["saldo"])]):
                self.t_monat.setItem(r, c, item(v, c > 0, farbe="#c62828" if c == 3 and z["saldo"] < 0 else None))
        r = self.t_monat.rowCount()
        self.t_monat.insertRow(r)
        for c, v in enumerate([f"Jahr {jahr}", euro(se), euro(sa), euro(se - sa)]):
            it = item(v, c > 0)
            f = it.font()
            f.setBold(True)
            it.setFont(f)
            self.t_monat.setItem(r, c, it)
        self.t_kat.setRowCount(0)
        for z in self.db.kategorieuebersicht(jahr, monat):
            r = self.t_kat.rowCount()
            self.t_kat.insertRow(r)
            ein = z["art"] == "E"
            for c, v in enumerate(["Einnahme" if ein else "Ausgabe", z["kategorie"], z["anzahl"], euro(z["summe"])]):
                self.t_kat.setItem(r, c, item(v, c >= 2, farbe=("#2e7d32" if ein else "#c62828") if c == 0 else None))

    def neu(self, art):
        if BuchungDialog(self.db, None, art, self).exec():
            self.h.alles_neu()

    def e_rechnung_empfangen(self):
        pfad, _ = QFileDialog.getOpenFileName(self, "Empfangene E-Rechnung öffnen", self.h.pdf_ordner(),
                                              "E-Rechnung (*.xml *.pdf)")
        if not pfad:
            return
        try:
            with open(pfad, "rb") as f:
                daten = f.read()
            r = erechnung.eingang_lesen(daten)
        except Exception as ex:
            return fehler(self, ex)
        d = EingangsDialog(self.db, r, pfad, daten, self)
        if d.exec():
            self.h.alles_neu()

    def bearbeiten(self, *_):
        kid = gewaehlte_id(self.t)
        if kid is None:
            return fehler(self, "Bitte eine Buchung auswählen.")
        if BuchungDialog(self.db, kid, parent=self).exec():
            self.h.alles_neu()

    def loeschen(self):
        kid = gewaehlte_id(self.t)
        if kid is None:
            return fehler(self, "Bitte eine Buchung auswählen.")
        if QMessageBox.question(self, "Löschen", "Diese Buchung wirklich löschen?") == QMessageBox.Yes:
            self.db.buchung_loeschen(kid)
            self.h.alles_neu()

    def _export(self, endung, filt, fn):
        jahr = self.jahr.currentData() or dt.date.today().year
        monat = self.monat.currentData()
        name = f"Kassenbuch_{jahr}" + (f"_{monat:02d}" if monat else "")
        pfad, _ = QFileDialog.getSaveFileName(self, "Exportieren", os.path.join(self.h.pdf_ordner(), f"{name}.{endung}"), filt)
        if not pfad:
            return
        try:
            fn(self.db, pfad, jahr, monat)
        except PermissionError:
            return fehler(self, "Die Datei ist gesperrt – ist sie noch geöffnet?")
        datei_oeffnen(pfad)

    def exp_csv(self):
        self._export("csv", "CSV (*.csv)", kassenbuch_csv)

    def exp_excel(self):
        self._export("xlsx", "Excel (*.xlsx)", kassenbuch_excel)

    def exp_pdf(self):
        self._export("pdf", "PDF (*.pdf)", kassenbuch_pdf)


class StammSeite(QWidget):
    """Kunden- oder Artikelliste."""

    def __init__(self, haupt: "Hauptfenster", art: str):
        super().__init__()
        self.h, self.db, self.art = haupt, haupt.db, art
        lay = QVBoxLayout(self)
        leiste = QHBoxLayout()
        b = QPushButton("+ Neuer Kunde" if art == "kunden" else "+ Neuer Artikel")
        b.setObjectName("primaer")
        b.clicked.connect(self.neu)
        leiste.addWidget(b)
        for text, fn in (("Bearbeiten", self.bearbeiten), ("Löschen", self.loeschen)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            leiste.addWidget(b)
        leiste.addStretch()
        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Suchen …")
        self.suche.setClearButtonEnabled(True)
        self.suche.textChanged.connect(self.laden)
        leiste.addWidget(self.suche)
        lay.addLayout(leiste)
        sp = (["Nr.", "Name", "Zusatz", "Anschrift", "E-Mail", "Telefon"] if art == "kunden"
              else ["Nr.", "Bezeichnung", "Beschreibung", "Einheit", "Preis"])
        self.t = tabelle(sp, 1)
        self.t.doubleClicked.connect(self.bearbeiten)
        lay.addWidget(self.t)

    def laden(self, *_):
        self.t.setRowCount(0)
        if self.art == "kunden":
            for k in self.db.kunden(self.suche.text()):
                r = self.t.rowCount()
                self.t.insertRow(r)
                werte = [k["nummer"], k["name"], k["zusatz"], f"{k['strasse']}, {k['plz']} {k['ort']}".strip(", "),
                         k["email"], k["telefon"]]
                for c, v in enumerate(werte):
                    self.t.setItem(r, c, item(v, daten=k["id"] if c == 0 else None))
        else:
            for a in self.db.artikel(self.suche.text()):
                r = self.t.rowCount()
                self.t.insertRow(r)
                for c, v in enumerate([a["nummer"], a["bezeichnung"], a["beschreibung"], a["einheit"],
                                       euro(a["preis_cent"])]):
                    self.t.setItem(r, c, item(v, c == 4, a["id"] if c == 0 else None))

    def neu(self):
        d = KundenDialog(self.db, parent=self) if self.art == "kunden" else ArtikelDialog(self.db, parent=self)
        if d.exec():
            self.laden()

    def bearbeiten(self, *_):
        i = gewaehlte_id(self.t)
        if i is None:
            return fehler(self, "Bitte einen Eintrag auswählen.")
        d = KundenDialog(self.db, i, self) if self.art == "kunden" else ArtikelDialog(self.db, i, self)
        if d.exec():
            self.h.alles_neu()

    def loeschen(self):
        i = gewaehlte_id(self.t)
        if i is None:
            return fehler(self, "Bitte einen Eintrag auswählen.")
        if QMessageBox.question(self, "Löschen", "Eintrag wirklich löschen?") != QMessageBox.Yes:
            return
        try:
            (self.db.kunde_loeschen if self.art == "kunden" else self.db.artikel_loeschen)(i)
        except ValueError as e:
            return fehler(self, e)
        self.laden()


class StartSeite(QWidget):
    def __init__(self, haupt: "Hauptfenster"):
        super().__init__()
        self.h, self.db = haupt, haupt.db
        lay = QVBoxLayout(self)
        self.gruss = QLabel()
        self.gruss.setObjectName("titel")
        lay.addWidget(self.gruss)
        kacheln = QHBoxLayout()
        self.k = {}
        for key, titel in (("umsatz", "Umsatz dieses Jahr"), ("offen", "Offene Rechnungen"),
                           ("kasse", "Kassenbestand"), ("angebote", "Offene Angebote")):
            f = QFrame()
            f.setObjectName("kachel")
            fl = QVBoxLayout(f)
            t = QLabel(titel)
            t.setStyleSheet("color:#555;")
            w = QLabel()
            w.setStyleSheet("font-size:24px; font-weight:bold; color:#1f4e79;")
            fl.addWidget(t)
            fl.addWidget(w)
            self.k[key] = w
            kacheln.addWidget(f)
        lay.addLayout(kacheln)
        schnell = QHBoxLayout()
        for text, fn in (("+ Angebot", lambda: self.h.angebote.neu()), ("+ Rechnung", lambda: self.h.rechnungen.neu()),
                         ("+ Einnahme", lambda: self.h.kasse.neu("E")), ("− Ausgabe", lambda: self.h.kasse.neu("A"))):
            b = QPushButton(text)
            b.setObjectName("gross")
            b.clicked.connect(fn)
            schnell.addWidget(b)
        lay.addLayout(schnell)
        g = QGroupBox("Kleinunternehmergrenze (§ 19 UStG)")
        gl = QVBoxLayout(g)
        self.grenze_text = QLabel()
        self.grenze_text.setWordWrap(True)
        self.grenze = QProgressBar()
        self.grenze.setRange(0, 1000)
        self.grenze.setTextVisible(False)
        gl.addWidget(self.grenze_text)
        gl.addWidget(self.grenze)
        lay.addWidget(g)
        g2 = QGroupBox("Offene Rechnungen")
        g2l = QVBoxLayout(g2)
        self.t = tabelle(["Nummer", "Kunde", "Datum", "Fällig", "Betrag"], 1)
        g2l.addWidget(self.t)
        lay.addWidget(g2, 1)

    def laden(self):
        e = self.db.einstellungen()
        jahr = dt.date.today().year
        self.gruss.setText(f"Willkommen, {e['inhaber'] or e['firma_name']}")
        umsatz = self.db.umsatz(jahr)
        offen = self.db.offene_rechnungen()
        self.k["umsatz"].setText(euro(umsatz))
        self.k["offen"].setText(f"{euro(sum(b['summe_cent'] for b in offen))}  ({len(offen)})")
        self.k["kasse"].setText(euro(self.db.kassenbestand()))
        ang = [b for b in self.db.belege("angebot") if b["status"] == "offen"]
        self.k["angebote"].setText(f"{len(ang)}  ({euro(sum(b['summe_cent'] for b in ang))})")
        vorjahr = self.db.umsatz(jahr - 1)
        anteil = umsatz / GRENZE_VORJAHR
        self.grenze.setValue(min(1000, int(anteil * 1000)))
        farbe = "#2e7d32" if anteil < 0.8 else "#f9a825" if anteil < 1 else "#c62828"
        self.grenze.setStyleSheet(f"QProgressBar::chunk {{ background: {farbe}; }}")
        txt = (f"Umsatz {jahr}: <b>{euro(umsatz)}</b> von 25.000 € ({anteil * 100:.0f} %). "
               f"Vorjahr {jahr - 1}: {euro(vorjahr)}.<br>")
        if umsatz > GRENZE_LAUFEND:
            txt += "<b style='color:#c62828'>Achtung: Über 100.000 € im laufenden Jahr – die Kleinunternehmer" \
                   "regelung entfällt ab sofort. Bitte Steuerberater kontaktieren!</b>"
        elif umsatz > GRENZE_VORJAHR:
            txt += "<b style='color:#c62828'>Über 25.000 € – im nächsten Jahr gilt die Kleinunternehmer" \
                   "regelung voraussichtlich nicht mehr.</b>"
        else:
            txt += "<span style='color:#555'>Grenzen seit 2025: Vorjahr ≤ 25.000 €, laufendes Jahr ≤ 100.000 € " \
                   "(Umsatz hier = bezahlte Rechnungen).</span>"
        self.grenze_text.setText(txt)
        self.t.setRowCount(0)
        for b in offen:
            r = self.t.rowCount()
            self.t.insertRow(r)
            ueber = b["faellig"] and b["faellig"] < heute()
            for c, v in enumerate([b["nummer"], b["kunde"], datum_de(b["datum"]), datum_de(b["faellig"]),
                                   euro(b["summe_cent"])]):
                self.t.setItem(r, c, item(v, c == 4, b["id"] if c == 0 else None, "#c62828" if ueber else None))


class EinstellungenSeite(QScrollArea):
    FIRMA = [("firma_name", "Firmenname *"), ("inhaber", "Inhaber/in"), ("strasse", "Straße, Nr."), ("plz", "PLZ"),
             ("ort", "Ort"), ("telefon", "Telefon"), ("email", "E-Mail"), ("web", "Webseite"),
             ("steuernummer", "Steuernummer *"), ("ust_idnr", "USt-IdNr. (falls vorhanden)"), ("bank", "Bank"),
             ("iban", "IBAN"), ("bic", "BIC")]

    def __init__(self, haupt: "Hauptfenster"):
        super().__init__()
        self.h, self.db = haupt, haupt.db
        self.setWidgetResizable(True)
        inhalt = QWidget()
        self.setWidget(inhalt)
        lay = QVBoxLayout(inhalt)
        oben = QHBoxLayout()
        g1 = QGroupBox("Firmendaten (erscheinen auf Angeboten und Rechnungen)")
        f1 = QFormLayout(g1)
        self.w = {}
        for k, label in self.FIRMA:
            self.w[k] = QLineEdit()
            f1.addRow(label, self.w[k])
        oben.addWidget(g1, 2)
        g2 = QGroupBox("Logo")
        f2 = QVBoxLayout(g2)
        self.logo = QLabel("Kein Logo")
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setMinimumSize(240, 120)
        self.logo.setStyleSheet("border:1px dashed #aaa; background:white;")
        b1 = QPushButton("Logo wählen …")
        b1.clicked.connect(self.logo_waehlen)
        b2 = QPushButton("Logo entfernen")
        b2.clicked.connect(self.logo_entfernen)
        f2.addWidget(self.logo)
        f2.addWidget(b1)
        f2.addWidget(b2)
        f2.addStretch()
        oben.addWidget(g2, 1)
        lay.addLayout(oben)

        g3 = QGroupBox("Nummernkreise, Fristen & Kasse")
        f3 = QFormLayout(g3)
        self.w["rechnung_praefix"] = QLineEdit()
        self.w["angebot_praefix"] = QLineEdit()
        self.stellen = QSpinBox()
        self.stellen.setRange(2, 8)
        self.jaehrlich = QCheckBox("Jahreszahl in der Nummer, Zähler beginnt jedes Jahr bei 1")
        self.ziel = QSpinBox()
        self.ziel.setRange(0, 120)
        self.ziel.setSuffix(" Tage")
        self.gueltig = QSpinBox()
        self.gueltig.setRange(1, 365)
        self.gueltig.setSuffix(" Tage")
        self.anfang = GeldEdit()
        self.auto_kasse = QCheckBox("Bezahlte Rechnungen automatisch als Einnahme ins Kassenbuch buchen")
        self.vorschau = QLabel()
        b_start = QPushButton("Startnummer festlegen …")
        b_start.clicked.connect(self.startnummer)
        f3.addRow("Präfix Rechnungen", self.w["rechnung_praefix"])
        f3.addRow("Präfix Angebote", self.w["angebot_praefix"])
        f3.addRow("Stellen der laufenden Nummer", self.stellen)
        f3.addRow("", self.jaehrlich)
        f3.addRow("Nächste Nummern", self.vorschau)
        f3.addRow("", b_start)
        f3.addRow("Zahlungsziel Rechnungen", self.ziel)
        f3.addRow("Gültigkeit Angebote", self.gueltig)
        f3.addRow("Kassen-Anfangsbestand (€)", self.anfang)
        f3.addRow("", self.auto_kasse)
        lay.addWidget(g3)

        g4 = QGroupBox("Texte")
        f4 = QFormLayout(g4)
        self.texte = {}
        for k, label in (("kleinunternehmer_hinweis", "Pflichthinweis § 19 UStG"),
                         ("rechnung_einleitung", "Rechnung – Einleitung"),
                         ("rechnung_schluss", "Rechnung – Schluss ({faellig})"),
                         ("angebot_einleitung", "Angebot – Einleitung"),
                         ("angebot_schluss", "Angebot – Schluss ({gueltig})")):
            t = QPlainTextEdit()
            t.setMaximumHeight(64)
            f4.addRow(label, t)
            self.texte[k] = t
        lay.addWidget(g4)

        g5 = QGroupBox("Excel-Liste (wird automatisch aktuell gehalten)")
        f5 = QVBoxLayout(g5)
        self.excel_an = QCheckBox("Nach jeder Änderung automatisch die Excel-Datei aktualisieren")
        self.excel_pfad = QLabel()
        self.excel_pfad.setStyleSheet("color:#555;")
        self.excel_pfad.setTextInteractionFlags(Qt.TextSelectableByMouse)
        zeile = QHBoxLayout()
        for text, fn in (("Speicherort …", self.excel_ort), ("Jetzt aktualisieren", lambda: self.h.excel_schreiben(True)),
                         ("Excel öffnen", self.excel_oeffnen)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            zeile.addWidget(b)
        zeile.addStretch()
        erkl = QLabel("Blätter: Übersicht (Monatssummen mit Formeln, Jahr wählbar), Kategorien, Kassenbuch, "
                      "Rechnungen, Angebote, Kunden, Artikel. Tipp: Speicherort in OneDrive wählen, dann ist die "
                      "Liste auch auf dem Handy aktuell. Änderungen bitte in der App machen – die Excel-Datei wird "
                      "überschrieben.")
        erkl.setWordWrap(True)
        erkl.setStyleSheet("color:#666;")
        f5.addWidget(self.excel_an)
        f5.addWidget(self.excel_pfad)
        f5.addLayout(zeile)
        f5.addWidget(erkl)
        self.excel_an.toggled.connect(self._excel_an)
        lay.addWidget(g5)

        unten = QHBoxLayout()
        b_sp = QPushButton("Einstellungen speichern")
        b_sp.setObjectName("primaer")
        b_sp.clicked.connect(self.speichern)
        b_bk = QPushButton("Datensicherung erstellen …")
        b_bk.clicked.connect(self.sicherung)
        b_ord = QPushButton("Datenordner öffnen")
        b_ord.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.db.pfad))))
        unten.addWidget(b_sp)
        unten.addStretch()
        unten.addWidget(b_bk)
        unten.addWidget(b_ord)
        lay.addLayout(unten)
        self.pfad_label = QLabel()
        self.pfad_label.setStyleSheet("color:#777;")
        lay.addWidget(self.pfad_label)

    def laden(self):
        e = self.db.einstellungen()
        for k, w in self.w.items():
            w.setText(e.get(k, ""))
        self.stellen.setValue(int(e["nummer_stellen"] or 4))
        self.jaehrlich.setChecked(e["nummer_jaehrlich"] == "1")
        self.ziel.setValue(int(e["zahlungsziel_tage"] or 14))
        self.gueltig.setValue(int(e["angebot_gueltig_tage"] or 30))
        self.anfang.setText(euro(int(e["kasse_anfangsbestand_cent"] or 0), False))
        self.auto_kasse.setChecked(e["bezahlt_in_kasse"] == "1")
        self.excel_an.blockSignals(True)
        self.excel_an.setChecked(e.get("excel_aktiv", "1") == "1")
        self.excel_an.blockSignals(False)
        self.excel_pfad.setText(f"Datei: {self.h.excel_pfad()}")
        for k, t in self.texte.items():
            t.setPlainText(e[k])
        self._logo_zeigen()
        self.vorschau.setText(f"Rechnung: <b>{self.db.naechste_nummer_vorschau('rechnung')}</b> · "
                              f"Angebot: <b>{self.db.naechste_nummer_vorschau('angebot')}</b>")
        self.pfad_label.setText(f"Datenbank: {self.db.pfad}")

    def _logo_zeigen(self):
        daten = self.db.logo()
        if daten:
            pm = QPixmap()
            pm.loadFromData(daten)
            self.logo.setPixmap(pm.scaled(240, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo.setPixmap(QPixmap())
            self.logo.setText("Kein Logo")

    def logo_waehlen(self):
        pfad, _ = QFileDialog.getOpenFileName(self, "Logo wählen", "", "Bilder (*.png *.jpg *.jpeg *.gif *.bmp)")
        if pfad:
            with open(pfad, "rb") as f:
                self.db.logo_speichern(f.read())
            self._logo_zeigen()

    def logo_entfernen(self):
        self.db.logo_speichern(None)
        self._logo_zeigen()

    def speichern(self):
        werte = {k: w.text().strip() for k, w in self.w.items()}
        if not werte["firma_name"]:
            return fehler(self, "Bitte einen Firmennamen eintragen.")
        werte.update({k: t.toPlainText().strip() for k, t in self.texte.items()})
        try:
            anfang = self.anfang.cent()
        except Exception:
            return fehler(self, "Anfangsbestand ist keine gültige Zahl.")
        werte.update({"nummer_stellen": self.stellen.value(), "nummer_jaehrlich": "1" if self.jaehrlich.isChecked() else "0",
                      "zahlungsziel_tage": self.ziel.value(), "angebot_gueltig_tage": self.gueltig.value(),
                      "kasse_anfangsbestand_cent": anfang, "bezahlt_in_kasse": "1" if self.auto_kasse.isChecked() else "0"})
        self.db.einstellungen_speichern(werte)
        self.h.alles_neu()
        self.h.statusBar().showMessage("Einstellungen gespeichert.", 4000)
        if not werte["steuernummer"]:
            fehler(self, "Hinweis: Auf Rechnungen ist die Steuernummer (oder USt-IdNr.) Pflicht.")

    def _excel_an(self, an):
        self.db.einstellungen_speichern({"excel_aktiv": "1" if an else "0"})
        if an:
            self.h.excel_schreiben(True)

    def excel_ort(self):
        pfad, _ = QFileDialog.getSaveFileName(self, "Speicherort der Excel-Liste", self.h.excel_pfad(), "Excel (*.xlsx)")
        if pfad:
            if not pfad.lower().endswith(".xlsx"):
                pfad += ".xlsx"
            self.db.einstellungen_speichern({"excel_pfad": pfad})
            self.excel_pfad.setText(f"Datei: {pfad}")
            self.h.excel_schreiben(True)

    def excel_oeffnen(self):
        p = self.h.excel_pfad()
        if not os.path.exists(p):
            self.h.excel_schreiben(True)
        datei_oeffnen(p)

    def startnummer(self):
        jahr = dt.date.today().year
        typ, ok = QInputDialog.getItem(self, "Startnummer", "Nummernkreis:", ["Rechnung", "Angebot"], 0, False)
        if not ok:
            return
        t = "rechnung" if typ == "Rechnung" else "angebot"
        akt = self.db.zaehler(t, jahr)
        n, ok = QInputDialog.getInt(self, "Startnummer", f"Letzte bereits vergebene {typ}snummer (laufende Nr.):\n"
                                    "Die nächste Nummer ist dann diese + 1.", akt, 0, 10 ** 7)
        if ok:
            if n < akt and QMessageBox.question(self, "Achtung", "Die Nummer ist kleiner als die bisher vergebene. "
                                                "Dadurch können Lücken/Kollisionen entstehen. Fortfahren?") != QMessageBox.Yes:
                return
            self.db.zaehler_setzen(t, jahr, n)
            self.laden()

    def sicherung(self):
        name = f"Kassenbuch_Sicherung_{dt.datetime.now():%Y-%m-%d_%H%M}.db"
        pfad, _ = QFileDialog.getSaveFileName(self, "Datensicherung", os.path.join(os.path.expanduser("~"), name),
                                              "Datenbank (*.db)")
        if pfad:
            self.h.sichern(pfad)
            QMessageBox.information(self, "Datensicherung", f"Gesichert nach:\n{pfad}")


# ---------------------------------------------------------------------------
# Hauptfenster
# ---------------------------------------------------------------------------

STIL = """
QWidget { font-size: 13px; }
QTabWidget::pane { border: none; }
QTabBar::tab { padding: 9px 18px; font-size: 14px; }
QTabBar::tab:selected { background: #1f4e79; color: white; border-radius: 4px; }
QPushButton { padding: 6px 12px; }
QPushButton#primaer { background: #1f4e79; color: white; font-weight: bold; border-radius: 4px; }
QPushButton#gruen { background: #2e7d32; color: white; font-weight: bold; border-radius: 4px; }
QPushButton#rot { background: #c62828; color: white; font-weight: bold; border-radius: 4px; }
QPushButton#gross { padding: 14px; font-size: 15px; font-weight: bold; background: #e9eef5; border: 1px solid #c5d3e3; border-radius: 6px; }
QPushButton#gross:hover { background: #d6e2f0; }
QFrame#kachel { background: white; border: 1px solid #d6dde6; border-radius: 8px; padding: 8px; }
QLabel#titel { font-size: 22px; font-weight: bold; color: #1f4e79; padding: 6px 0; }
QGroupBox { font-weight: bold; border: 1px solid #d0d7de; border-radius: 6px; margin-top: 10px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
"""


def datenordner() -> str:
    pfad = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.path.expanduser("~/Kassenbuch")
    os.makedirs(pfad, exist_ok=True)
    return pfad


class Hauptfenster(QMainWindow):
    def __init__(self, db_pfad: Optional[str] = None):
        super().__init__()
        self.db = Datenbank(db_pfad or os.path.join(datenordner(), "kassenbuch.db"))
        self.auto_sicherung()
        self.setWindowTitle("Kassenbuch & Rechnungen")
        self.resize(1250, 800)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.start = StartSeite(self)
        self.angebote = BelegSeite(self, "angebot")
        self.rechnungen = BelegSeite(self, "rechnung")
        self.kasse = KassenSeite(self)
        self.kunden = StammSeite(self, "kunden")
        self.artikel = StammSeite(self, "artikel")
        self.einstellungen = EinstellungenSeite(self)
        for w, t in ((self.start, "Start"), (self.angebote, "Angebote"), (self.rechnungen, "Rechnungen"),
                     (self.kasse, "Kassenbuch"), (self.kunden, "Kunden"), (self.artikel, "Artikel"),
                     (self.einstellungen, "Einstellungen")):
            self.tabs.addTab(w, t)
        self.alles_neu()
        if self.db.einstellung("firma_name") == "Mein Kleingewerbe":
            self.tabs.setCurrentWidget(self.einstellungen)
            self.statusBar().showMessage("Willkommen! Bitte zuerst die Firmendaten eintragen und speichern.")

    def alles_neu(self):
        for s in (self.angebote, self.rechnungen, self.kasse):
            s.jahre_laden()
        for s in (self.start, self.angebote, self.rechnungen, self.kasse, self.kunden, self.artikel, self.einstellungen):
            s.laden()
        self.excel_planen()

    # -- Excel-Liste -------------------------------------------------------
    def excel_pfad(self) -> str:
        p = self.db.einstellung("excel_pfad")
        if p:
            return p
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) or os.path.expanduser("~")
        return os.path.join(docs, "Kassenbuch.xlsx")

    def excel_planen(self):
        if self.db.einstellung("excel_aktiv") == "0" or self.db.pfad == ":memory:":
            return
        if not hasattr(self, "_excel_timer"):
            self._excel_timer = QTimer(self, singleShot=True, interval=1500, timeout=self.excel_schreiben)
        self._excel_timer.start()

    def excel_schreiben(self, manuell=False):
        try:
            excel_liste.schreiben(self.db, self.excel_pfad())
        except PermissionError:
            # Datei ist in Excel geöffnet -> später erneut versuchen
            self.statusBar().showMessage("Excel-Liste ist gerade geöffnet – wird nach dem Schließen automatisch "
                                         "aktualisiert.")
            if not hasattr(self, "_excel_retry"):
                self._excel_retry = QTimer(self, singleShot=True, interval=20000, timeout=self.excel_schreiben)
            self._excel_retry.start()
            if manuell:
                fehler(self, "Die Excel-Datei ist gerade geöffnet. Bitte in Excel schließen – die App aktualisiert "
                             "sie dann automatisch.")
            return
        except Exception as ex:
            self.statusBar().showMessage(f"Excel-Liste konnte nicht geschrieben werden: {ex}")
            if manuell:
                fehler(self, f"Excel-Liste konnte nicht geschrieben werden:\n{ex}")
            return
        self.statusBar().showMessage(f"Excel-Liste aktualisiert ({dt.datetime.now():%H:%M:%S}).", 5000)

    def pdf_ordner(self) -> str:
        o = self.db.einstellung("pdf_ordner")
        if o and os.path.isdir(o):
            return o
        docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) or os.path.expanduser("~")
        return docs

    def sichern(self, ziel: str):
        src = self.db.con
        dst = __import__("sqlite3").connect(ziel)
        with dst:
            src.backup(dst)
        dst.close()

    def auto_sicherung(self):
        """Einmal täglich automatisch sichern, die letzten 14 Sicherungen behalten."""
        if self.db.pfad == ":memory:":
            return
        ordner = os.path.join(os.path.dirname(self.db.pfad), "Sicherungen")
        os.makedirs(ordner, exist_ok=True)
        ziel = os.path.join(ordner, f"kassenbuch_{dt.date.today():%Y-%m-%d}.db")
        if not os.path.exists(ziel):
            try:
                self.sichern(ziel)
            except Exception:
                return
        for alt in sorted(glob.glob(os.path.join(ordner, "kassenbuch_*.db")))[:-14]:
            try:
                os.remove(alt)
            except OSError:
                pass


def _deutsch(app):
    """Qt-Standardtexte (OK, Abbrechen, Speichern …) auf Deutsch."""
    from PySide6.QtCore import QLibraryInfo, QTranslator
    t = QTranslator(app)
    if t.load(QLocale(QLocale.German, QLocale.Germany), "qtbase", "_",
              QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(t)
        app._uebersetzer = t


def main():
    QLocale.setDefault(QLocale(QLocale.German, QLocale.Germany))
    app = QApplication(sys.argv)
    app.setApplicationName("Kassenbuch")
    _deutsch(app)
    app.setOrganizationName("MeineApps")
    app.setStyle("Fusion")
    app.setStyleSheet(STIL)
    w = Hauptfenster()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
