"""Tray-Anwendung der Programmsperre (PySide6)."""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

import psutil
from PySide6.QtCore import QLocale, QPointF, QRectF, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QSpinBox,
                               QSystemTrayIcon, QVBoxLayout, QWidget)

from . import system
from .kern import Konfiguration, Sperre, normalisieren, pin_gueltig

INSTANZ = "MeineApps-Programmsperre"


def konfig_pfad() -> str:
    basis = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.path.expanduser("~/.programmsperre")
    return os.path.join(basis, "einstellungen.json")


def schloss_icon(farbe="#1f4e79", offen=False) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(farbe), 7)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    bogen = QPainterPath()
    x = 18 if not offen else 30
    bogen.moveTo(x, 30)
    bogen.lineTo(x, 20)
    bogen.arcTo(QRectF(x, 6, 28, 28), 180, -180)
    bogen.lineTo(x + 28, 30 if not offen else 22)
    p.drawPath(bogen)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(farbe))
    p.drawRoundedRect(QRectF(10, 28, 44, 32), 6, 6)
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(32, 42), 5, 5)
    p.drawRect(QRectF(30, 44, 4, 9))
    p.end()
    return QIcon(pm)


def zeit(sek: int) -> str:
    m, s = divmod(int(sek), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d} h" if h else f"{m}:{s:02d} min"


# ---------------------------------------------------------------------------
# Dialoge
# ---------------------------------------------------------------------------

class PinEingabe(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setEchoMode(QLineEdit.Password)
        self.setMaxLength(12)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("font-size:22px; letter-spacing:6px; padding:6px;")
        self.setPlaceholderText("PIN")


class PinAbfrage(QDialog):
    """Allgemeine PIN-Abfrage (für Einstellungen, Beenden, Pause)."""

    def __init__(self, sperre: Sperre, zweck: str, parent=None):
        super().__init__(parent)
        self.sperre = sperre
        self.setWindowTitle("Programmsperre – PIN")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"<b>{zweck}</b><br>Bitte PIN eingeben:"))
        self.pin = PinEingabe()
        lay.addWidget(self.pin)
        self.info = QLabel()
        self.info.setStyleSheet("color:#c62828;")
        lay.addWidget(self.info)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.pruefen)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.ok = bb.button(QDialogButtonBox.Ok)
        self.timer = QTimer(self, interval=500, timeout=self._warten)
        self.timer.start()
        self._warten()

    def _warten(self):
        w = self.sperre.wartezeit()
        self.ok.setEnabled(w == 0)
        if w:
            self.info.setText(f"Zu viele Fehlversuche – bitte {w} s warten.")

    def pruefen(self):
        if self.sperre.pin_pruefen(self.pin.text()):
            self.accept()
            return
        self.pin.clear()
        if not self.sperre.wartezeit():
            self.info.setText(f"Falsche PIN. Noch {self.sperre.restversuche()} Versuch(e).")
        self._warten()


def pin_bestaetigt(sperre: Sperre, zweck: str, parent=None) -> bool:
    d = PinAbfrage(sperre, zweck, parent)
    d.raise_()
    d.activateWindow()
    return d.exec() == QDialog.Accepted


class NeuePinDialog(QDialog):
    def __init__(self, titel="PIN festlegen", parent=None):
        super().__init__(parent)
        self.setWindowTitle(titel)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        f = QFormLayout(self)
        f.addRow(QLabel("Die PIN (4–12 Ziffern) wird zum Freigeben gesperrter Programme\n"
                        "und für die Einstellungen benötigt. Gut merken!"))
        self.a = PinEingabe()
        self.b = PinEingabe()
        f.addRow("Neue PIN:", self.a)
        f.addRow("Wiederholen:", self.b)
        self.info = QLabel()
        self.info.setStyleSheet("color:#c62828;")
        f.addRow(self.info)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.pruefen)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def pruefen(self):
        fehler = pin_gueltig(self.a.text())
        if fehler:
            self.info.setText(fehler)
        elif self.a.text() != self.b.text():
            self.info.setText("Die beiden Eingaben stimmen nicht überein.")
        else:
            self.accept()


class FreigabeDialog(QDialog):
    """Erscheint, wenn ein gesperrtes Programm gestartet wurde."""

    def __init__(self, app: "SperrApp", name: str):
        super().__init__(None)
        self.app, self.name = app, name
        self.prozesse: List[psutil.Process] = []
        self.entschieden = False
        self.setWindowTitle("Programm gesperrt")
        self.setWindowIcon(schloss_icon())
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        lay = QVBoxLayout(self)
        kopf = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(schloss_icon("#c62828").pixmap(56, 56))
        kopf.addWidget(ic)
        anzeige = app.sperre.anzeige(name)
        t = QLabel(f"<span style='font-size:17px'><b>„{anzeige}“ ist gesperrt.</b></span><br>"
                   "Zum Öffnen bitte die PIN eingeben.")
        kopf.addWidget(t, 1)
        lay.addLayout(kopf)
        self.pin = PinEingabe()
        lay.addWidget(self.pin)
        zeile = QHBoxLayout()
        zeile.addWidget(QLabel("Freigeben für:"))
        self.dauer = QComboBox()
        std = app.sperre.k.freigabe_minuten
        werte = sorted({15, 30, 60, 120, 240, std})
        for m in werte:
            self.dauer.addItem(f"{m} Minuten" if m < 60 else f"{m / 60:g} Stunde(n)", m)
        self.dauer.setCurrentIndex(werte.index(std))
        zeile.addWidget(self.dauer, 1)
        lay.addLayout(zeile)
        self.info = QLabel()
        self.info.setStyleSheet("color:#c62828;")
        lay.addWidget(self.info)
        knoepfe = QHBoxLayout()
        self.b_frei = QPushButton("Freigeben")
        self.b_frei.setDefault(True)
        self.b_frei.setStyleSheet("background:#1f4e79; color:white; padding:8px 16px; font-weight:bold;")
        b_ende = QPushButton("Programm beenden")
        b_ende.setStyleSheet("padding:8px 16px;")
        self.b_frei.clicked.connect(self.freigeben)
        b_ende.clicked.connect(self.ablehnen)
        knoepfe.addWidget(b_ende)
        knoepfe.addStretch()
        knoepfe.addWidget(self.b_frei)
        lay.addLayout(knoepfe)
        self.setMinimumWidth(400)
        self.timer = QTimer(self, interval=500, timeout=self._warten)
        self.timer.start()
        self._warten()

    def hinzufuegen(self, prozesse):
        bekannt = {p.pid for p in self.prozesse}
        self.prozesse += [p for p in prozesse if p.pid not in bekannt]

    def _warten(self):
        w = self.app.sperre.wartezeit()
        self.b_frei.setEnabled(w == 0)
        if w:
            self.info.setText(f"Zu viele Fehlversuche – bitte {w} s warten.")

    def freigeben(self):
        if self.app.sperre.pin_pruefen(self.pin.text()):
            self.entschieden = True
            self.app.sperre.freigeben(self.name, self.dauer.currentData())
            system.fortsetzen(self.prozesse)
            self.app.meldung(f"{self.app.sperre.anzeige(self.name)} ist für {self.dauer.currentText()} freigegeben.")
            self.accept()
            return
        self.pin.clear()
        if not self.app.sperre.wartezeit():
            self.info.setText(f"Falsche PIN. Noch {self.app.sperre.restversuche()} Versuch(e).")
        self._warten()

    def ablehnen(self):
        self.entschieden = True
        system.beenden(self.prozesse)
        self.reject()

    def closeEvent(self, e):
        if not self.entschieden:
            self.ablehnen()
        super().closeEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.ablehnen()
            return
        super().keyPressEvent(e)


class ProgrammAuswahl(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Laufendes Programm auswählen")
        self.resize(480, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Starte das Programm, das gesperrt werden soll, und wähle es hier aus:"))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtern …")
        lay.addWidget(self.filter)
        self.liste = QListWidget()
        for name, exe in system.laufende_programme():
            it = QListWidgetItem(f"{name}    —    {exe}")
            it.setData(Qt.UserRole, (name, exe))
            self.liste.addItem(it)
        lay.addWidget(self.liste)
        self.filter.textChanged.connect(self._filtern)
        self.liste.itemDoubleClicked.connect(self.accept)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _filtern(self, t):
        for i in range(self.liste.count()):
            it = self.liste.item(i)
            it.setHidden(t.lower() not in it.text().lower())

    def auswahl(self):
        it = self.liste.currentItem()
        return it.data(Qt.UserRole) if it else None


class EinstellungenDialog(QDialog):
    def __init__(self, app: "SperrApp"):
        super().__init__(None)
        self.app = app
        self.s = app.sperre
        self.setWindowTitle("Programmsperre – Einstellungen")
        self.setWindowIcon(schloss_icon())
        self.resize(560, 560)
        lay = QVBoxLayout(self)
        g = QGroupBox("Gesperrte Programme")
        gl = QVBoxLayout(g)
        self.liste = QListWidget()
        gl.addWidget(self.liste)
        knoepfe = QHBoxLayout()
        for text, fn in (("Aus laufenden Programmen …", self.aus_laufenden), ("EXE-Datei wählen …", self.exe_waehlen),
                         ("Name eingeben …", self.name_eingeben), ("Entfernen", self.entfernen)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            knoepfe.addWidget(b)
        gl.addLayout(knoepfe)
        lay.addWidget(g, 1)

        g2 = QGroupBox("Verhalten")
        f = QFormLayout(g2)
        self.minuten = QSpinBox()
        self.minuten.setRange(1, 24 * 60)
        self.minuten.setSuffix(" Minuten")
        self.minuten.setValue(self.s.k.freigabe_minuten)
        self.ablauf = QCheckBox("Nach Ablauf laufendes Programm anhalten und erneut PIN verlangen")
        self.ablauf.setChecked(self.s.k.nach_ablauf_sperren)
        self.warnung = QSpinBox()
        self.warnung.setRange(0, 30)
        self.warnung.setSuffix(" Minuten vorher")
        self.warnung.setValue(self.s.k.warnung_minuten)
        self.autostart = QCheckBox("Mit Windows starten")
        self.autostart.setChecked(self.s.k.autostart)
        f.addRow("Standard-Freigabedauer:", self.minuten)
        f.addRow("", self.ablauf)
        f.addRow("Warnung vor Ablauf:", self.warnung)
        f.addRow("", self.autostart)
        b_pin = QPushButton("PIN ändern …")
        b_pin.clicked.connect(self.pin_aendern)
        f.addRow("", b_pin)
        lay.addWidget(g2)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.speichern)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._liste_laden()

    def _liste_laden(self):
        self.liste.clear()
        for p in self.s.k.programme:
            it = QListWidgetItem(schloss_icon("#c62828"), f"{p.anzeige}   ({p.name})")
            it.setData(Qt.UserRole, p.name)
            self.liste.addItem(it)

    def _hinzu(self, name, anzeige="", pfad=""):
        try:
            self.s.programm_hinzufuegen(name, anzeige, pfad)
        except ValueError as e:
            QMessageBox.warning(self, "Hinweis", str(e))
        self._liste_laden()

    def aus_laufenden(self):
        d = ProgrammAuswahl(self)
        if d.exec() and d.auswahl():
            name, exe = d.auswahl()
            anzeige, ok = QInputDialog.getText(self, "Anzeigename", "Anzeigename:", text=os.path.splitext(name)[0])
            self._hinzu(name, anzeige if ok else "", exe)

    def exe_waehlen(self):
        pfad, _ = QFileDialog.getOpenFileName(self, "Programm wählen", os.environ.get("ProgramFiles", ""),
                                              "Programme (*.exe)")
        if pfad:
            name = normalisieren(pfad)
            anzeige, ok = QInputDialog.getText(self, "Anzeigename", "Anzeigename:", text=os.path.splitext(name)[0])
            self._hinzu(name, anzeige if ok else "", pfad)

    def name_eingeben(self):
        name, ok = QInputDialog.getText(self, "Programm", "Prozessname (z. B. chrome.exe, msedge.exe, steam.exe):")
        if ok and name.strip():
            self._hinzu(name.strip())

    def entfernen(self):
        it = self.liste.currentItem()
        if it:
            self.s.programm_entfernen(it.data(Qt.UserRole))
            self._liste_laden()

    def pin_aendern(self):
        d = NeuePinDialog("PIN ändern", self)
        if d.exec():
            self.s.pin_setzen(d.a.text())
            QMessageBox.information(self, "PIN", "Die PIN wurde geändert.")

    def speichern(self):
        k = self.s.k
        k.freigabe_minuten = self.minuten.value()
        k.nach_ablauf_sperren = self.ablauf.isChecked()
        k.warnung_minuten = self.warnung.value()
        k.autostart = self.autostart.isChecked()
        system.autostart_setzen(k.autostart)
        self.app.speichern()
        self.accept()

    def reject(self):
        # Änderungen an Liste/PIN verwerfen -> Konfiguration neu laden
        self.app.neu_laden()
        super().reject()


# ---------------------------------------------------------------------------
# Tray-Anwendung
# ---------------------------------------------------------------------------

class SperrApp:
    def __init__(self, app: QApplication, pfad: Optional[str] = None):
        self.qapp = app
        self.pfad = pfad or konfig_pfad()
        self.sperre = Sperre(Konfiguration.laden(self.pfad))
        self.dialoge: Dict[str, FreigabeDialog] = {}
        self.geduldet: set = set()   # PIDs, die nach Ablauf weiterlaufen dürfen
        self.tray = QSystemTrayIcon(schloss_icon())
        self.menue = QMenu()
        self.menue.aboutToShow.connect(self._menue_bauen)
        self.tray.setContextMenu(self.menue)
        self.tray.activated.connect(lambda grund: self.status_zeigen() if grund == QSystemTrayIcon.Trigger else None)
        self.tray.show()
        self.timer = QTimer(interval=500, timeout=self.pruefen)
        self.timer.start()
        self._tooltip()

    # -- Konfiguration ------------------------------------------------------
    def speichern(self):
        self.sperre.k.speichern(self.pfad)
        self._tooltip()

    def neu_laden(self):
        freigaben = self.sperre.freigaben
        pause = self.sperre.pausiert_bis
        self.sperre.k = Konfiguration.laden(self.pfad)
        self.sperre.freigaben = freigaben
        self.sperre.pausiert_bis = pause

    def erster_start(self) -> bool:
        if self.sperre.pin_gesetzt:
            return True
        QMessageBox.information(None, "Programmsperre", "Willkommen! Lege zuerst eine PIN fest. Danach wählst du "
                                "die Programme aus, die nur mit PIN geöffnet werden dürfen.")
        d = NeuePinDialog()
        if not d.exec():
            return False
        self.sperre.pin_setzen(d.a.text())
        self.sperre.k.autostart = True
        system.autostart_setzen(True)
        self.speichern()
        EinstellungenDialog(self).exec()
        return True

    # -- Überwachung --------------------------------------------------------
    def pruefen(self):
        s = self.sperre
        for name in s.bald_ablaufend():
            self.meldung(f"Die Freigabe für {s.anzeige(name)} endet in {zeit(s.restzeit(name))}.")
        for name in s.abgelaufen():
            if s.k.nach_ablauf_sperren:
                self.meldung(f"Die Freigabe für {s.anzeige(name)} ist abgelaufen.")
            else:
                # laufende Prozesse dürfen weiterlaufen, nur ein Neustart braucht wieder die PIN
                self.geduldet |= {p.pid for p in system.finde([name]).get(name, [])}
                self.meldung(f"Die Freigabe für {s.anzeige(name)} ist abgelaufen. Das Programm läuft weiter, "
                             "ein Neustart braucht wieder die PIN.")
        self.geduldet = {pid for pid in self.geduldet if psutil.pid_exists(pid)}
        gesperrt = [n for n in s.namen() if s.ist_gesperrt(n)]
        if not gesperrt:
            self._tooltip()
            return
        for name, procs in system.finde(gesperrt).items():
            procs = self._ohne_geduldete(procs)
            if not procs:
                continue
            dialog = self.dialoge.get(name)
            if dialog and dialog.isVisible():
                neu = [p for p in procs if p.pid not in {q.pid for q in dialog.prozesse}]
                if neu:
                    angehalten, _ = system.anhalten(neu)
                    dialog.hinzufuegen(angehalten)
                continue
            angehalten, beendet = system.anhalten(procs)
            if not angehalten:
                if beendet:
                    self.meldung(f"{s.anzeige(name)} wurde beendet (gesperrt).")
                continue
            d = FreigabeDialog(self, name)
            d.hinzufuegen(angehalten)
            d.finished.connect(lambda _=0, n=name: self.dialoge.pop(n, None))
            self.dialoge[name] = d
            d.show()
            d.raise_()
            d.activateWindow()
        self._tooltip()

    def _ohne_geduldete(self, procs):
        if not self.geduldet:
            return procs
        out = []
        for p in procs:
            try:
                if p.pid in self.geduldet or p.ppid() in self.geduldet:
                    self.geduldet.add(p.pid)   # Kindprozesse (z. B. neue Browser-Tabs) ebenfalls dulden
                    continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            out.append(p)
        return out

    # -- Tray ---------------------------------------------------------------
    def meldung(self, text):
        self.tray.showMessage("Programmsperre", text, schloss_icon(), 5000)

    def _tooltip(self):
        s = self.sperre
        if s.ist_pausiert():
            self.tray.setIcon(schloss_icon("#f9a825", offen=True))
            self.tray.setToolTip(f"Programmsperre pausiert ({zeit(s.pausiert_bis - s.uhr())})")
        else:
            self.tray.setIcon(schloss_icon())
            frei = [f"{s.anzeige(n)}: {zeit(s.restzeit(n))}" for n in s.freigaben if s.ist_freigegeben(n)]
            self.tray.setToolTip("Programmsperre aktiv – " + (f"{len(s.namen())} Programm(e) gesperrt"
                                                             + ("\nFreigegeben: " + ", ".join(frei) if frei else "")))

    def _menue_bauen(self):
        m = self.menue
        m.clear()
        s = self.sperre
        kopf = QAction("Sperre pausiert" if s.ist_pausiert() else f"Sperre aktiv – {len(s.namen())} Programm(e)", m)
        kopf.setEnabled(False)
        m.addAction(kopf)
        frei = [n for n in list(s.freigaben) if s.ist_freigegeben(n)]
        if frei:
            sub = m.addMenu("Freigaben")
            for n in frei:
                a = sub.addAction(f"{s.anzeige(n)} – noch {zeit(s.restzeit(n))} → jetzt sperren")
                a.triggered.connect(lambda _=False, x=n: self._sofort_sperren(x))
        m.addSeparator()
        m.addAction("Einstellungen …", self.einstellungen)
        if s.ist_pausiert():
            m.addAction("Pause beenden", self._pause_beenden)
        else:
            m.addAction("Sperre pausieren …", self.pausieren)
        m.addSeparator()
        m.addAction("Programmsperre beenden …", self.beenden)

    def status_zeigen(self):
        self._tooltip()
        self.meldung(self.tray.toolTip())

    def _sofort_sperren(self, name):
        self.sperre.sperren(name)
        self._tooltip()

    def einstellungen(self):
        if pin_bestaetigt(self.sperre, "Einstellungen öffnen"):
            EinstellungenDialog(self).exec()

    def pausieren(self):
        if not pin_bestaetigt(self.sperre, "Sperre pausieren"):
            return
        m, ok = QInputDialog.getInt(None, "Pause", "Sperre für wie viele Minuten pausieren?", 30, 1, 24 * 60)
        if ok:
            self.sperre.pausieren(m)
            self._tooltip()
            self.meldung(f"Sperre für {m} Minuten pausiert.")

    def _pause_beenden(self):
        self.sperre.pause_beenden()
        self._tooltip()

    def beenden(self):
        if pin_bestaetigt(self.sperre, "Programmsperre beenden"):
            for d in list(self.dialoge.values()):
                d.entschieden = True
                system.fortsetzen(d.prozesse)
                d.close()
            self.speichern()
            self.tray.hide()
            self.qapp.quit()


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
    app.setApplicationName("Programmsperre")
    _deutsch(app)
    app.setOrganizationName("MeineApps")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setWindowIcon(schloss_icon())
    # nur eine Instanz
    sock = QLocalSocket()
    sock.connectToServer(INSTANZ)
    if sock.waitForConnected(300):
        if "--autostart" not in sys.argv:
            QMessageBox.information(None, "Programmsperre", "Die Programmsperre läuft bereits (Schloss-Symbol "
                                    "unten rechts in der Taskleiste).")
        return
    QLocalServer.removeServer(INSTANZ)
    server = QLocalServer()
    server.listen(INSTANZ)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Programmsperre", "Kein Infobereich (System-Tray) verfügbar.")
        return
    s = SperrApp(app)
    if not s.erster_start():
        return
    if "--autostart" not in sys.argv:
        s.meldung("Programmsperre läuft im Hintergrund. Rechtsklick auf das Schloss für Einstellungen.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
