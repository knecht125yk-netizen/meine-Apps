"""Grafische Oberfläche (PySide6) des Maschinenbau-Rechners."""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from PySide6.QtCore import QLocale, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QImage, QTextDocument
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
                               QScrollArea, QSlider, QSplitter, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from . import formeln as fm
from .darstellung import formel_png, zeichne
from .export import als_docx, als_pdf
from .profile import MASSE, PROFILE, berechne as profil_berechnen
from .rechnung import Rechnung, fmt
from .werkstoffe import WERKSTOFFE, werkstoff

# ---------------------------------------------------------------------------
# Parameter-Beschreibungen
# ---------------------------------------------------------------------------


@dataclass
class Zahl:
    key: str
    label: str
    einheit: str
    std: float
    min: float
    max: float
    nachkomma: int = 1
    log: bool = False
    sichtbar: Optional[Callable[[dict], bool]] = None


@dataclass
class Auswahl:
    key: str
    label: str
    optionen: Sequence[str]
    std: Optional[str] = None
    sichtbar: Optional[Callable[[dict], bool]] = None


@dataclass
class Profil:
    key: str = "querschnitt"
    nur: Sequence[str] = field(default_factory=lambda: list(PROFILE))
    std: str = "Rechteck"
    sichtbar: Optional[Callable[[dict], bool]] = None


@dataclass
class Material:
    key: str = "werkstoff"
    std: str = "S235JR"
    sichtbar: Optional[Callable[[dict], bool]] = None


# ---------------------------------------------------------------------------
# Eingabe-Widgets
# ---------------------------------------------------------------------------

class ZahlEingabe(QWidget):
    """Schieberegler + Zahlenfeld, synchronisiert."""
    geaendert = Signal()
    SCHRITTE = 1000

    def __init__(self, z: Zahl):
        super().__init__()
        self.z = z
        self.log = z.log and z.min > 0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self.SCHRITTE)
        self.slider.setMinimumWidth(120)
        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(z.nachkomma)
        self.spin.setRange(z.min, z.max)
        self.spin.setSingleStep(10 ** -z.nachkomma if z.nachkomma else 1)
        self.spin.setValue(z.std)
        self.spin.setMinimumWidth(110)
        self.spin.setKeyboardTracking(False)
        self.spin.setGroupSeparatorShown(True)
        einheit = QLabel(z.einheit)
        einheit.setMinimumWidth(48)
        lay.addWidget(self.slider, 3)
        lay.addWidget(self.spin, 2)
        lay.addWidget(einheit)
        self._sperre = False
        self._slider_setzen(z.std)
        self.slider.valueChanged.connect(self._von_slider)
        self.spin.valueChanged.connect(self._von_spin)

    def _zu_pos(self, v):
        z = self.z
        if self.log:
            v = max(v, z.min)
            return round(self.SCHRITTE * math.log(v / z.min) / math.log(z.max / z.min))
        return round(self.SCHRITTE * (v - z.min) / (z.max - z.min))

    def _von_pos(self, p):
        z = self.z
        if self.log:
            return z.min * (z.max / z.min) ** (p / self.SCHRITTE)
        return z.min + (z.max - z.min) * p / self.SCHRITTE

    def _slider_setzen(self, v):
        self._sperre = True
        self.slider.setValue(self._zu_pos(v))
        self._sperre = False

    def _von_slider(self, p):
        if self._sperre:
            return
        v = self._von_pos(p)
        # auf "schöne" Werte runden
        if abs(v) >= 10:
            stellen = max(0, 2 - int(math.floor(math.log10(abs(v)))))
            v = round(v, -int(math.floor(math.log10(abs(v)))) + 2) if stellen == 0 else round(v, stellen)
        self._sperre = True
        self.spin.setValue(v)
        self._sperre = False
        self.geaendert.emit()

    def _von_spin(self, v):
        if self._sperre:
            return
        self._slider_setzen(v)
        self.geaendert.emit()

    def wert(self) -> float:
        return self.spin.value()


class ProfilEingabe(QWidget):
    geaendert = Signal()

    def __init__(self, p: Profil):
        super().__init__()
        lay = QFormLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.addItems(list(p.nur))
        self.combo.setCurrentText(p.std)
        lay.addRow("Profil", self.combo)
        self.felder: Dict[str, Dict[str, ZahlEingabe]] = {}
        self.zeilen: Dict[str, List[QWidget]] = {}
        for name in p.nur:
            self.felder[name] = {}
            self.zeilen[name] = []
            for key, label, std, mn, mx in MASSE[name]:
                w = ZahlEingabe(Zahl(key, label, "mm", std, mn, mx, 1, log=mn > 0))
                w.geaendert.connect(self.geaendert)
                lbl = QLabel(label)
                lay.addRow(lbl, w)
                self.felder[name][key] = w
                self.zeilen[name] += [lbl, w]
        self.combo.currentTextChanged.connect(self._umschalten)
        self._umschalten()

    def _umschalten(self, *_):
        aktiv = self.combo.currentText()
        for name, ws in self.zeilen.items():
            for w in ws:
                w.setVisible(name == aktiv)
        self.geaendert.emit()

    def wert(self):
        name = self.combo.currentText()
        return profil_berechnen(name, {k: w.wert() for k, w in self.felder[name].items()})


class WerkstoffEingabe(QWidget):
    geaendert = Signal()

    def __init__(self, m: Material):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        for w in WERKSTOFFE:
            self.combo.addItem(f"{w.name}  ({w.gruppe})", w.name)
        self.combo.setCurrentIndex([w.name for w in WERKSTOFFE].index(m.std))
        self.info = QLabel()
        self.info.setStyleSheet("color:#555; font-size:11px;")
        lay.addWidget(self.combo)
        lay.addWidget(self.info)
        self.combo.currentIndexChanged.connect(self._neu)
        self._neu()

    def _neu(self, *_):
        w = self.wert()
        self.info.setText(f"E = {fmt(w.E)} N/mm² · Re = {fmt(w.Re)} N/mm² · Rm = {fmt(w.Rm)} N/mm²")
        self.geaendert.emit()

    def wert(self):
        return werkstoff(self.combo.currentData())


# ---------------------------------------------------------------------------
# Berechnungsseite
# ---------------------------------------------------------------------------

class RechenSeite(QWidget):
    def __init__(self, titel: str, beschreibung: str, params: list, rechne: Callable[[dict], Rechnung],
                 hauptfenster: "Hauptfenster"):
        super().__init__()
        self.titel = titel
        self.params = params
        self.rechne = rechne
        self.haupt = hauptfenster
        self.widgets: Dict[str, QWidget] = {}
        self.zeilen: Dict[str, List[QWidget]] = {}
        self.rechnung: Optional[Rechnung] = None

        aussen = QVBoxLayout(self)
        kopf = QHBoxLayout()
        t = QLabel(titel)
        t.setObjectName("seitentitel")
        kopf.addWidget(t)
        kopf.addStretch()
        self.btn_pdf = QPushButton("PDF exportieren")
        self.btn_docx = QPushButton("Word exportieren")
        self.btn_pdf.clicked.connect(lambda: self.exportieren("pdf"))
        self.btn_docx.clicked.connect(lambda: self.exportieren("docx"))
        kopf.addWidget(self.btn_pdf)
        kopf.addWidget(self.btn_docx)
        aussen.addLayout(kopf)
        if beschreibung:
            b = QLabel(beschreibung)
            b.setWordWrap(True)
            b.setStyleSheet("color:#555;")
            aussen.addWidget(b)

        split = QSplitter(Qt.Horizontal)
        aussen.addWidget(split, 1)

        # Eingaben
        eingabe_box = QGroupBox("Eingaben")
        form = QFormLayout(eingabe_box)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for p in params:
            if isinstance(p, Zahl):
                w = ZahlEingabe(p)
                lbl = QLabel(p.label)
            elif isinstance(p, Auswahl):
                w = QComboBox()
                w.addItems(list(p.optionen))
                if p.std:
                    w.setCurrentText(p.std)
                w.currentTextChanged.connect(self._planen)
                lbl = QLabel(p.label)
            elif isinstance(p, Profil):
                w = ProfilEingabe(p)
                lbl = QLabel("Querschnitt")
            elif isinstance(p, Material):
                w = WerkstoffEingabe(p)
                lbl = QLabel("Werkstoff")
            else:
                continue
            if hasattr(w, "geaendert"):
                w.geaendert.connect(self._planen)
            form.addRow(lbl, w)
            self.widgets[p.key] = w
            self.zeilen[p.key] = [lbl, w]
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(eingabe_box)
        scroll.setMinimumWidth(430)
        split.addWidget(scroll)

        # Ergebnisse + Diagramm
        rechts = QSplitter(Qt.Vertical)
        self.ausgabe = QTextBrowser()
        self.ausgabe.setOpenExternalLinks(False)
        rechts.addWidget(self.ausgabe)
        self.figur = Figure(figsize=(6, 4), dpi=96)
        self.canvas = FigureCanvasQTAgg(self.figur)
        self.canvas.setMinimumHeight(260)
        rechts.addWidget(self.canvas)
        rechts.setSizes([480, 360])
        split.addWidget(rechts)
        split.setSizes([460, 820])

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self.aktualisieren)
        self.aktualisieren()

    # -- Werte ---------------------------------------------------------------
    def werte(self) -> dict:
        out = {}
        for p in self.params:
            w = self.widgets[p.key]
            if isinstance(p, Auswahl):
                out[p.key] = w.currentText()
            else:
                out[p.key] = w.wert()
        return out

    def _planen(self, *_):
        self.timer.start()

    def aktualisieren(self):
        try:
            werte = self.werte()
        except ValueError as e:
            self._fehler(str(e))
            return
        for p in self.params:
            if p.sichtbar:
                an = bool(p.sichtbar(werte))
                for w in self.zeilen[p.key]:
                    w.setVisible(an)
        try:
            r = self.rechne(werte)
        except (ValueError, ZeroDivisionError) as e:
            self._fehler(str(e) or "Ungültige Eingabe")
            return
        self.rechnung = r
        self.ausgabe.setHtml(self._html(r))
        try:
            zeichne(r.plot, self.figur)
        except Exception as e:  # Diagramm darf die Rechnung nicht blockieren
            self.figur.clear()
            self.figur.text(0.5, 0.5, f"Diagramm nicht verfügbar: {e}", ha="center")
        self.canvas.draw_idle()
        self.btn_pdf.setEnabled(True)
        self.btn_docx.setEnabled(True)

    def _fehler(self, text):
        self.rechnung = None
        self.ausgabe.setHtml(f"<p style='color:#c0392b; font-size:14px'><b>Eingabe prüfen:</b> {text}</p>")
        self.figur.clear()
        self.canvas.draw_idle()
        self.btn_pdf.setEnabled(False)
        self.btn_docx.setEnabled(False)

    def _bild(self, latex, farbe="black") -> str:
        name = f"formel://{abs(hash((latex, farbe)))}"
        img = QImage.fromData(formel_png(latex, 15, 110, farbe))
        self.ausgabe.document().addResource(QTextDocument.ImageResource, QUrl(name), img)
        return f"<img src='{name}'>"

    def _html(self, r: Rechnung) -> str:
        h = ["<style>td{padding:4px 8px;} .e{font-size:15px;font-weight:bold;color:#1f6fb2;}"
             " .k{color:#777;font-size:11px;} h3{margin-top:10px;color:#1f6fb2;}</style>"]
        if r.nachweise:
            ok = r.alle_erfuellt
            farbe = "#2e8b57" if ok else "#c0392b"
            text = "Alle Nachweise erfüllt ✔" if ok else "Nachweis NICHT erfüllt ✘"
            h.append(f"<div style='background:{farbe};color:white;padding:8px;font-size:16px;'>"
                     f"<b>{text}</b></div>")
            for n in r.nachweise:
                h.append(f"<p><b>{n.beschreibung}:</b> {self._bild(n.formel)} &nbsp; "
                         f"<span style='color:{'#2e8b57' if n.erfuellt else '#c0392b'};font-size:14px'>"
                         f"<b>{n.text()}</b></span></p>")
        h.append("<h3>Rechenweg</h3><table width='100%'>")
        for i, s in enumerate(r.schritte, 1):
            h.append(f"<tr><td colspan='2'><b>{i}. {s.beschreibung}</b></td></tr>"
                     f"<tr><td>{self._bild(s.formel)}</td>"
                     f"<td align='right' class='e'>{s.ergebnis_text()}</td></tr>")
            if s.eingesetzt:
                h.append(f"<tr><td colspan='2' class='k'>{s.eingesetzt}</td></tr>")
            h.append("<tr><td colspan='2'><hr></td></tr>")
        h.append("</table>")
        if r.hinweise:
            h.append("<h3>Hinweise</h3><ul>" + "".join(f"<li>{x}</li>" for x in r.hinweise) + "</ul>")
        return "".join(h)

    # -- Export --------------------------------------------------------------
    def exportieren(self, art):
        if not self.rechnung:
            return
        name = self.rechnung.titel.replace(" – ", "_").replace(" ", "_").replace("/", "-")
        filt = "PDF (*.pdf)" if art == "pdf" else "Word (*.docx)"
        start = os.path.join(self.haupt.letzter_ordner, f"{name}.{art}")
        pfad, _ = QFileDialog.getSaveFileName(self, "Rechnung exportieren", start, filt)
        if not pfad:
            return
        if not pfad.lower().endswith("." + art):
            pfad += "." + art
        self.haupt.letzter_ordner = os.path.dirname(pfad)
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            (als_pdf if art == "pdf" else als_docx)(self.rechnung, pfad, self.haupt.projekt.text())
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Export", "Datei ist gesperrt (evtl. noch geöffnet?).")
            return
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Export fehlgeschlagen", str(e))
            return
        QApplication.restoreOverrideCursor()
        if QMessageBox.question(self, "Export", f"Gespeichert:\n{pfad}\n\nJetzt öffnen?") == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(pfad))


class WerkstoffSeite(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        t = QLabel("Werkstofftabelle")
        t.setObjectName("seitentitel")
        lay.addWidget(t)
        info = QLabel("Typische Mindestwerte für Nenndicken ≤ 16 mm. Für verbindliche Auslegungen "
                      "Normen bzw. Datenblätter verwenden. G = E / (2·(1+ν)).")
        info.setWordWrap(True)
        lay.addWidget(info)
        spalten = ["Werkstoff", "Gruppe", "E [N/mm²]", "G [N/mm²]", "Re / Rp0,2 [N/mm²]",
                   "Rm [N/mm²]", "ν", "ρ [g/cm³]", "Tetmajer", "Bemerkung"]
        tab = QTableWidget(len(WERKSTOFFE), len(spalten))
        tab.setHorizontalHeaderLabels(spalten)
        for i, w in enumerate(WERKSTOFFE):
            tet = f"σK = {w.tetmajer[0]:g} − {w.tetmajer[1]:g}·λ (λ < {w.tetmajer[2]:g})" if w.tetmajer else "–"
            for j, v in enumerate([w.name, w.gruppe, fmt(w.E), fmt(round(w.G)), fmt(w.Re), fmt(w.Rm),
                                   fmt(w.nu), fmt(w.dichte), tet, w.bemerkung]):
                item = QTableWidgetItem(v)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                tab.setItem(i, j, item)
        tab.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        tab.horizontalHeader().setStretchLastSection(True)
        tab.setAlternatingRowColors(True)
        tab.setSortingEnabled(True)
        lay.addWidget(tab)


# ---------------------------------------------------------------------------
# Seitendefinitionen
# ---------------------------------------------------------------------------

def _seiten():
    LF = fm.LASTFAELLE
    euler_namen = [v[0] for v in fm.EULERFAELLE.values()]
    return [
        ("Biegung", "Biegespannung, Durchbiegung und Biegelinie für Einfeld- und Kragträger.", [
            Auswahl("lastfall", "Lastfall", LF),
            Zahl("F", "Einzellast F", "N", 1000, 1, 1e6, 0, log=True, sichtbar=lambda w: "Einzellast" in w["lastfall"]),
            Zahl("q", "Streckenlast q", "N/mm", 2, 0.01, 1000, 2, log=True, sichtbar=lambda w: "Strecken" in w["lastfall"]),
            Zahl("l", "Länge l", "mm", 1000, 10, 20000, 0, log=True),
            Zahl("a", "Lastabstand a", "mm", 500, 0, 20000, 0, sichtbar=lambda w: w["lastfall"] == LF[0]),
            Profil(), Material(), Zahl("S", "erf. Sicherheit S", "", 1.5, 1, 5, 2),
        ], lambda w: fm.biegung(w["lastfall"], w["F"] if "Einzellast" in w["lastfall"] else w["q"],
                                w["l"], w["a"], w["querschnitt"], w["werkstoff"], w["S"])),
        ("Knickung", "Euler (elastisch) und Tetmajer/Johnson (unelastisch) mit Schlankheitsgrad.", [
            Auswahl("fall", "Eulerfall", euler_namen, euler_namen[1]),
            Zahl("l", "Stablänge l", "mm", 1500, 10, 20000, 0, log=True),
            Zahl("F", "Druckkraft F", "N", 10000, 1, 5e6, 0, log=True),
            Profil(std="Rohr"), Material(), Zahl("S", "erf. Sicherheit S", "", 3.0, 1, 10, 2),
        ], lambda w: fm.knickung(euler_namen.index(w["fall"]) + 1, w["l"], w["F"], w["querschnitt"],
                                 w["werkstoff"], w["S"])),
        ("Zug / Druck", "Normalspannung, Dehnung und Längenänderung. Druck = negative Kraft.", [
            Zahl("F", "Kraft F (Zug +, Druck −)", "N", 10000, -1e6, 1e6, 0),
            Zahl("l", "Länge l", "mm", 1000, 1, 20000, 0, log=True),
            Profil(std="Rund"), Material(), Zahl("S", "erf. Sicherheit S", "", 1.5, 1, 5, 2),
        ], lambda w: fm.zug_druck(w["F"], w["l"], w["querschnitt"], w["werkstoff"], w["S"])),
        ("Torsion", "Torsionsspannung und Verdrehwinkel für Voll- und Hohlwellen.", [
            Zahl("Mt", "Torsionsmoment Mt", "N·m", 100, 0.1, 1e5, 1, log=True),
            Zahl("l", "Länge l", "mm", 500, 1, 10000, 0, log=True),
            Profil(nur=["Rund", "Rohr"], std="Rund"), Material(std="E335"),
            Zahl("S", "erf. Sicherheit S", "", 1.5, 1, 5, 2),
        ], lambda w: fm.torsion(w["Mt"], w["l"], w["querschnitt"], w["werkstoff"], w["S"])),
        ("Schub / Abscheren", "Abscherung von Bolzen/Stiften und Querkraftschub in Trägern.", [
            Auswahl("art", "Art", fm.SCHUBARTEN),
            Zahl("F", "Querkraft F", "N", 5000, 1, 1e6, 0, log=True),
            Zahl("n", "Anzahl Scherflächen n", "", 1, 1, 10, 0, sichtbar=lambda w: w["art"] == fm.SCHUBARTEN[0]),
            Profil(std="Rund"), Material(), Zahl("S", "erf. Sicherheit S", "", 1.5, 1, 5, 2),
        ], lambda w: fm.schub(w["art"], w["F"], w["querschnitt"], w["werkstoff"], int(w["n"]), w["S"])),
        ("Flächenpressung", "Pressung an ebenen Flächen und projizierten Flächen (Bolzen, Lager).", [
            Auswahl("art", "Art", fm.PRESSUNGSARTEN),
            Zahl("F", "Kraft F", "N", 10000, 1, 1e6, 0, log=True),
            Zahl("b", "Breite b / Durchmesser d", "mm", 20, 0.5, 1000, 1, log=True),
            Zahl("l", "Länge l", "mm", 30, 0.5, 2000, 1, log=True),
            Zahl("pzul", "zulässige Pressung p_zul", "N/mm²", 100, 1, 1000, 0, log=True),
        ], lambda w: fm.flaechenpressung(w["art"], w["F"], w["b"], w["l"], w["pzul"])),
        ("Vergleichsspannung", "Von-Mises-Vergleichsspannung (GEH) mit Hauptspannungen und Mohrschem Kreis.", [
            Zahl("sx", "Normalspannung σx", "N/mm²", 120, -1000, 1000, 1),
            Zahl("sy", "Normalspannung σy", "N/mm²", 0, -1000, 1000, 1),
            Zahl("tau", "Schubspannung τ", "N/mm²", 40, -600, 600, 1),
            Material(), Zahl("S", "erf. Sicherheit S", "", 1.5, 1, 5, 2),
        ], lambda w: fm.vergleichsspannung(w["sx"], w["sy"], w["tau"], w["werkstoff"], w["S"])),
        ("Schrauben", "Vorspannkraft, Klemmkraft für Reibschluss und Anziehdrehmoment (vereinfacht nach VDI 2230).", [
            Auswahl("g", "Gewinde", list(fm.GEWINDE.keys()), "M10"),
            Auswahl("k", "Festigkeitsklasse", list(fm.FESTIGKEITSKLASSEN.keys()), "8.8"),
            Zahl("FA", "axiale Betriebskraft (gesamt)", "N", 5000, 0, 1e6, 0),
            Zahl("FQ", "Querkraft (gesamt)", "N", 3000, 0, 1e6, 0),
            Zahl("n", "Anzahl Schrauben", "", 2, 1, 50, 0),
            Zahl("i", "Anzahl Trennfugen", "", 1, 1, 6, 0),
            Zahl("muT", "Reibzahl Trennfuge μT", "", 0.15, 0.05, 0.6, 2),
            Zahl("aA", "Anziehfaktor αA", "", 1.6, 1.0, 4.0, 2),
            Zahl("muG", "Reibzahl Gewinde/Kopf μG", "", 0.12, 0.06, 0.25, 2),
        ], lambda w: fm.schraube(w["g"], w["k"], w["FA"], w["FQ"], int(w["n"]), w["muT"], int(w["i"]),
                                 w["aA"], w["muG"], w["muG"])),
        ("Wellen", "Vollwelle unter Biegung und Torsion, Vergleichsspannung und Mindestdurchmesser.", [
            Zahl("P", "Leistung P", "kW", 7.5, 0.01, 5000, 2, log=True),
            Zahl("n", "Drehzahl n", "1/min", 1450, 1, 30000, 0, log=True),
            Zahl("Mb", "Biegemoment Mb", "N·m", 40, 0, 1e5, 1),
            Zahl("d", "Wellendurchmesser d", "mm", 30, 3, 500, 1, log=True),
            Material(std="E335"),
            Zahl("a0", "Anstrengungsverhältnis α0", "", 0.7, 0.5, 1.0, 2),
            Zahl("S", "erf. Sicherheit S", "", 2.0, 1, 5, 2),
        ], lambda w: fm.welle(w["P"], w["n"], w["Mb"], w["d"], w["werkstoff"], w["a0"], w["S"])),
        ("Passfedern", "Passfeder DIN 6885 Form A – Maße werden automatisch aus dem Wellendurchmesser gewählt.", [
            Zahl("d", "Wellendurchmesser d", "mm", 40, 6.1, 130, 1),
            Zahl("Mt", "Torsionsmoment Mt", "N·m", 200, 0.1, 50000, 1, log=True),
            Zahl("l", "Passfederlänge l", "mm", 50, 5, 500, 0),
            Zahl("pzul", "zulässige Pressung p_zul", "N/mm²", 90, 10, 300, 0),
            Auswahl("anz", "Anzahl Passfedern", ["1", "2"]),
        ], lambda w: fm.passfeder(w["d"], w["Mt"], w["l"], w["pzul"], int(w["anz"]))),
        ("Flächenträgheitsmomente", "Querschnittswerte für Rechteck, Rund, Rohr, I- und U-Profil.", [
            Profil(),
        ], lambda w: fm.querschnittswerte(w["querschnitt"].profil, w["querschnitt"].masse)),
        ("Sicherheitsnachweis", "Allgemeiner Nachweis: vorhandene Spannung gegen Werkstoffkennwert.", [
            Zahl("s", "vorhandene Spannung σ", "N/mm²", 120, 0.1, 2000, 1, log=True),
            Auswahl("g", "Grenzwert", fm.GRENZEN), Material(),
            Zahl("S", "erf. Sicherheit S", "", 1.5, 1, 10, 2),
        ], lambda w: fm.sicherheitsnachweis(w["s"], w["g"], w["werkstoff"], w["S"])),
    ]


# ---------------------------------------------------------------------------
# Hauptfenster
# ---------------------------------------------------------------------------

STIL = """
QWidget { font-size: 13px; }
QListWidget { font-size: 14px; background: #f4f7fb; border: none; padding-top: 6px; }
QListWidget::item { padding: 9px 12px; }
QListWidget::item:selected { background: #1f6fb2; color: white; border-radius: 4px; }
QLabel#seitentitel { font-size: 20px; font-weight: bold; color: #1f6fb2; }
QGroupBox { font-weight: bold; border: 1px solid #d0d7de; border-radius: 6px; margin-top: 10px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
QPushButton { padding: 6px 14px; background: #1f6fb2; color: white; border-radius: 4px; }
QPushButton:disabled { background: #b0bec5; }
QPushButton:hover { background: #185a91; }
QTextBrowser { background: white; border: 1px solid #d0d7de; }
"""


class Hauptfenster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maschinenbau-Rechner")
        self.resize(1400, 860)
        self.letzter_ordner = os.path.expanduser("~")
        zentral = QWidget()
        lay = QHBoxLayout(zentral)
        lay.setContentsMargins(0, 0, 0, 0)
        links = QVBoxLayout()
        self.liste = QListWidget()
        self.liste.setFixedWidth(230)
        links.addWidget(self.liste, 1)
        self.projekt = QLineEdit()
        self.projekt.setPlaceholderText("Projekt / Bearbeiter (für Export)")
        links.addWidget(self.projekt)
        lay.addLayout(links)
        trenn = QFrame()
        trenn.setFrameShape(QFrame.VLine)
        lay.addWidget(trenn)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        for titel, beschr, params, fn in _seiten():
            self.liste.addItem(QListWidgetItem(titel))
            self.stack.addWidget(RechenSeite(titel, beschr, params, fn, self))
        self.liste.addItem(QListWidgetItem("Werkstofftabelle"))
        self.stack.addWidget(WerkstoffSeite())
        self.liste.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.liste.setCurrentRow(0)
        self.setCentralWidget(zentral)
        self.statusBar().showMessage("Werte per Schieberegler oder Zahlenfeld ändern – das Ergebnis "
                                     "aktualisiert sich sofort.")


def main():
    QLocale.setDefault(QLocale(QLocale.German, QLocale.Germany))
    app = QApplication(sys.argv)
    app.setApplicationName("Maschinenbau-Rechner")
    app.setStyle("Fusion")
    app.setStyleSheet(STIL)
    f = QFont()
    f.setPointSize(10)
    app.setFont(f)
    fenster = Hauptfenster()
    fenster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
