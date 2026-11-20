"""Schwebendes To-Do-Symbol mit ausklappbarer Aufgabenliste (PySide6)."""
from __future__ import annotations

import datetime as dt
import os
import sys
import time
from typing import Optional

from PySide6.QtCore import QDate, QLocale, QPoint, QRect, QSize, QStandardPaths, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QCalendarWidget, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
                               QSizeGrip, QToolButton, QVBoxLayout, QWidget, QWidgetAction)

from .daten import HOCH, MITTEL, NIEDRIG, PRIO_FARBEN, PRIO_NAMEN, Aufgabe, Liste, faellig_text

INSTANZ = "MeineApps-ToDo-Widget"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AKZENT = "#3949ab"


def datenpfad() -> str:
    basis = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.path.expanduser("~/.todo-widget")
    return os.path.join(basis, "aufgaben.json")


# ---------------------------------------------------------------------------
# Autostart
# ---------------------------------------------------------------------------

def autostart_setzen(an: bool) -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    if getattr(sys, "frozen", False):
        befehl = f'"{sys.executable}"'
    else:
        befehl = f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{os.path.abspath(sys.argv[0])}"'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if an:
                winreg.SetValueEx(k, "ToDo-Widget", 0, winreg.REG_SZ, befehl)
            else:
                try:
                    winreg.DeleteValue(k, "ToDo-Widget")
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def app_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(AKZENT))
    p.setPen(Qt.NoPen)
    p.drawEllipse(2, 2, 60, 60)
    p.setPen(QPen(QColor("white"), 7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    pfad = QPainterPath()
    pfad.moveTo(18, 33)
    pfad.lineTo(28, 43)
    pfad.lineTo(46, 22)
    p.drawPath(pfad)
    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------------------
# Schwebendes Symbol
# ---------------------------------------------------------------------------

class Symbol(QWidget):
    geklickt = Signal()
    verschoben = Signal(QPoint)

    def __init__(self, groesse: int = 56):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.groesse = groesse
        self.setFixedSize(groesse + 8, groesse + 8)
        self.offen = 0
        self.dringend = 0
        self._druck: Optional[QPoint] = None
        self._start: Optional[QPoint] = None
        self._gezogen = False
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("To-Do – klicken zum Öffnen, ziehen zum Verschieben, Rechtsklick für Menü")

    def zaehler(self, offen: int, dringend: int):
        self.offen, self.dringend = offen, dringend
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = self.groesse
        # Schatten
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawEllipse(5, 6, g, g)
        p.setBrush(QColor(AKZENT))
        p.drawEllipse(3, 3, g, g)
        # Haken
        p.setPen(QPen(QColor("white"), max(4, g // 10), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        s = g / 64
        pfad = QPainterPath()
        pfad.moveTo(3 + 18 * s, 3 + 33 * s)
        pfad.lineTo(3 + 28 * s, 3 + 43 * s)
        pfad.lineTo(3 + 46 * s, 3 + 22 * s)
        p.drawPath(pfad)
        # Zähler-Badge
        if self.offen:
            text = str(self.offen) if self.offen < 100 else "99+"
            f = QFont()
            f.setBold(True)
            f.setPixelSize(max(10, g // 5))
            p.setFont(f)
            b = max(20, g // 2.6)
            r = QRect(int(g + 6 - b), 0, int(b), int(b))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#e53935" if self.dringend else "#ffffff"))
            p.drawEllipse(r)
            p.setPen(QColor("white" if self.dringend else AKZENT))
            p.drawText(r, Qt.AlignCenter, text)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._druck = e.globalPosition().toPoint()
            self._start = self.pos()
            self._gezogen = False

    def mouseMoveEvent(self, e):
        if self._druck is None:
            return
        d = e.globalPosition().toPoint() - self._druck
        if d.manhattanLength() > 5:
            self._gezogen = True
        if self._gezogen:
            self.move(self._start + d)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._druck is None:
            return
        self._druck = None
        if self._gezogen:
            self.verschoben.emit(self.pos())
        else:
            self.geklickt.emit()


# ---------------------------------------------------------------------------
# Eine Zeile der Liste
# ---------------------------------------------------------------------------

class Zeile(QWidget):
    def __init__(self, popup: "Popup", a: Aufgabe):
        super().__init__()
        self.popup, self.a = popup, a
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 3, 4, 3)
        lay.setSpacing(6)
        self.check = QCheckBox()
        self.check.setChecked(a.erledigt)
        self.check.toggled.connect(lambda _: popup.umschalten(a.id))
        punkt = QLabel("●")
        punkt.setStyleSheet(f"color:{PRIO_FARBEN[a.prioritaet]}; font-size:12px;")
        punkt.setToolTip(f"Priorität: {PRIO_NAMEN[a.prioritaet]}")
        self.titel = QLabel(a.titel)
        self.titel.setWordWrap(True)
        stil = "font-size:13px;"
        if a.erledigt:
            stil += "color:#9e9e9e; text-decoration: line-through;"
        self.titel.setStyleSheet(stil)
        lay.addWidget(self.check)
        lay.addWidget(punkt)
        lay.addWidget(self.titel, 1)
        ft = faellig_text(a)
        if ft:
            f = QLabel(ft)
            heute = a.faellig_datum() == dt.date.today()
            farbe = "#9e9e9e" if a.erledigt else "#e53935" if a.ueberfaellig() else "#fb8c00" if heute else "#5c6bc0"
            f.setStyleSheet(f"color:{farbe}; font-size:11px; font-weight:bold;")
            lay.addWidget(f)
        x = QToolButton()
        x.setText("✕")
        x.setAutoRaise(True)
        x.setToolTip("Löschen")
        x.setStyleSheet("QToolButton{color:#bbb;} QToolButton:hover{color:#e53935;}")
        x.clicked.connect(lambda: popup.loeschen(a.id))
        lay.addWidget(x)

    def mouseDoubleClickEvent(self, _):
        self.popup.bearbeiten(self.a.id)

    def contextMenuEvent(self, e):
        self.popup.kontextmenue(self.a.id, e.globalPos())


# ---------------------------------------------------------------------------
# Popup mit der Liste
# ---------------------------------------------------------------------------

class Popup(QFrame):
    zu = Signal()
    geaendert = Signal()

    def __init__(self, liste: Liste):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint)
        self.liste = liste
        self.setObjectName("popup")
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        e = liste.einstellungen
        self.resize(e.popup_breite, e.popup_hoehe)
        self.setMinimumSize(280, 260)
        self.setMaximumSize(900, 1000)   # bewusst kein Vollbild
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 4)
        kopf = QHBoxLayout()
        self.ueberschrift = QLabel()
        self.ueberschrift.setStyleSheet("font-size:16px; font-weight:bold; color:%s;" % AKZENT)
        kopf.addWidget(self.ueberschrift, 1)
        menue_btn = QToolButton()
        menue_btn.setText("⋯")
        menue_btn.setStyleSheet("font-size:18px;")
        menue_btn.setAutoRaise(True)
        menue_btn.setPopupMode(QToolButton.InstantPopup)
        self.menue = QMenu(menue_btn)
        self.menue.aboutToShow.connect(self._menue_bauen)
        menue_btn.setMenu(self.menue)
        kopf.addWidget(menue_btn)
        lay.addLayout(kopf)

        eingabe = QHBoxLayout()
        self.neu = QLineEdit()
        self.neu.setPlaceholderText("Neue Aufgabe … + Enter")
        self.neu.setToolTip("Kürzel: !hoch, !niedrig, @heute, @morgen, @fr, @24.12.\n"
                            "Beispiel: Arzt anrufen !hoch @morgen")
        self.neu.returnPressed.connect(self.hinzufuegen)
        self.prio = QComboBox()
        for i, p in enumerate((HOCH, MITTEL, NIEDRIG)):
            self.prio.addItem(f"● {PRIO_NAMEN[p]}", p)
            self.prio.setItemData(i, QColor(PRIO_FARBEN[p]), Qt.ForegroundRole)
        self.prio.setCurrentIndex(1)
        self.prio.setToolTip("Priorität")
        self.datum_btn = QToolButton()
        self.datum_btn.setText("📅")
        self.datum_btn.setToolTip("Fälligkeit wählen")
        self.datum_btn.setPopupMode(QToolButton.InstantPopup)
        self._datum: str = ""
        dm = QMenu(self.datum_btn)
        self.kalender = QCalendarWidget()
        self.kalender.setGridVisible(True)
        self.kalender.setFirstDayOfWeek(Qt.Monday)
        self.kalender.clicked.connect(lambda d: (self._datum_setzen(d), dm.close()))
        wa = QWidgetAction(dm)
        wa.setDefaultWidget(self.kalender)
        dm.addAction(wa)
        dm.addAction("Kein Datum", lambda: self._datum_setzen(None))
        self.datum_btn.setMenu(dm)
        plus = QPushButton("+")
        plus.setFixedWidth(34)
        plus.setObjectName("plus")
        plus.clicked.connect(self.hinzufuegen)
        eingabe.addWidget(self.neu, 1)
        eingabe.addWidget(self.prio)
        eingabe.addWidget(self.datum_btn)
        eingabe.addWidget(plus)
        lay.addLayout(eingabe)
        self.datum_info = QLabel()
        self.datum_info.setStyleSheet("color:#5c6bc0; font-size:11px;")
        self.datum_info.hide()
        lay.addWidget(self.datum_info)

        self.lw = QListWidget()
        self.lw.setSelectionMode(QListWidget.NoSelection)
        self.lw.setFocusPolicy(Qt.NoFocus)
        lay.addWidget(self.lw, 1)
        unten = QHBoxLayout()
        self.status = QLabel()
        self.status.setStyleSheet("color:#888; font-size:11px;")
        unten.addWidget(self.status, 1)
        unten.addWidget(QSizeGrip(self), 0, Qt.AlignBottom | Qt.AlignRight)
        lay.addLayout(unten)
        self.zuletzt_geschlossen = 0.0
        self.aktualisieren()

    # -- Datum --------------------------------------------------------------
    def _datum_setzen(self, d: Optional[QDate]):
        if d is None:
            self._datum = ""
            self.datum_info.hide()
        else:
            self._datum = f"{d.year():04d}-{d.month():02d}-{d.day():02d}"
            self.datum_info.setText(f"Fällig: {faellig_text(Aufgabe('x', faellig=self._datum))}  "
                                    f"({d.toString('dd.MM.yyyy')})")
            self.datum_info.show()

    # -- Aktionen -----------------------------------------------------------
    def hinzufuegen(self):
        text = self.neu.text().strip()
        if not text:
            return
        try:
            self.liste.hinzufuegen(text, self.prio.currentData(), self._datum or None)
        except ValueError:
            return
        self.neu.clear()
        self.prio.setCurrentIndex(1)
        self._datum_setzen(None)
        self.aktualisieren()

    def umschalten(self, aid):
        self.liste.umschalten(aid)
        QTimer.singleShot(150, self.aktualisieren)   # kurz sichtbar abhaken, dann umsortieren

    def loeschen(self, aid):
        self.liste.loeschen(aid)
        self.aktualisieren()

    def bearbeiten(self, aid):
        a = self.liste.finde(aid)
        for i in range(self.lw.count()):
            w = self.lw.itemWidget(self.lw.item(i))
            if isinstance(w, Zeile) and w.a.id == aid:
                ed = QLineEdit(a.titel, w)
                ed.setGeometry(w.titel.geometry())
                ed.show()
                ed.setFocus()
                ed.selectAll()

                def fertig(ed=ed):
                    t = ed.text().strip()
                    if t and t != a.titel:
                        self.liste.aendern(aid, titel=t)
                    QTimer.singleShot(0, self.aktualisieren)
                ed.editingFinished.connect(fertig)
                return

    def kontextmenue(self, aid, pos):
        a = self.liste.finde(aid)
        m = QMenu(self)
        m.addAction("Bearbeiten", lambda: self.bearbeiten(aid))
        pm = m.addMenu("Priorität")
        for p in (HOCH, MITTEL, NIEDRIG):
            act = pm.addAction(f"● {PRIO_NAMEN[p]}", lambda p=p: self._aendern(aid, prioritaet=p))
            act.setCheckable(True)
            act.setChecked(a.prioritaet == p)
        dm = m.addMenu("Fällig")
        heute = dt.date.today()
        for text, tage in (("Heute", 0), ("Morgen", 1), ("In einer Woche", 7)):
            dm.addAction(text, lambda t=tage: self._aendern(aid, faellig=(heute + dt.timedelta(days=t)).isoformat()))
        kal = QCalendarWidget()
        kal.setFirstDayOfWeek(Qt.Monday)
        if a.faellig_datum():
            d = a.faellig_datum()
            kal.setSelectedDate(QDate(d.year, d.month, d.day))
        kal.clicked.connect(lambda d: (self._aendern(aid, faellig=f"{d.year():04d}-{d.month():02d}-{d.day():02d}"),
                                       m.close()))
        wa = QWidgetAction(dm)
        wa.setDefaultWidget(kal)
        dm.addAction(wa)
        dm.addAction("Kein Datum", lambda: self._aendern(aid, faellig=""))
        m.addSeparator()
        m.addAction("Erledigt" if not a.erledigt else "Wieder offen", lambda: self.umschalten(aid))
        m.addAction("Löschen", lambda: self.loeschen(aid))
        m.exec(pos)

    def _aendern(self, aid, **w):
        self.liste.aendern(aid, **w)
        self.aktualisieren()

    def _menue_bauen(self):
        m = self.menue
        m.clear()
        e = self.liste.einstellungen
        a = m.addAction("Erledigte anzeigen")
        a.setCheckable(True)
        a.setChecked(e.erledigte_zeigen)
        a.toggled.connect(self._erledigte_zeigen)
        m.addAction("Erledigte löschen", self._erledigte_loeschen)
        m.addSeparator()
        a = m.addAction("Mit Windows starten")
        a.setCheckable(True)
        a.setChecked(e.autostart)
        a.toggled.connect(self._autostart)
        m.addAction("Fenstergröße zurücksetzen", self._groesse_zuruecksetzen)
        m.addSeparator()
        m.addAction("Hilfe zur Schnelleingabe", self._hilfe)
        m.addAction("To-Do-Widget beenden", QApplication.quit)

    def _erledigte_zeigen(self, an):
        self.liste.einstellungen.erledigte_zeigen = an
        self.liste.speichern()
        self.aktualisieren()

    def _erledigte_loeschen(self):
        n = self.liste.erledigte_entfernen()
        self.aktualisieren()
        self.status.setText(f"{n} erledigte Aufgabe(n) gelöscht.")

    def _autostart(self, an):
        self.liste.einstellungen.autostart = an
        self.liste.speichern()
        autostart_setzen(an)

    def _groesse_zuruecksetzen(self):
        self.resize(360, 460)
        self._groesse_merken()

    def _hilfe(self):
        QMessageBox.information(None, "Schnelleingabe",
                                "Im Eingabefeld kannst du Kürzel verwenden:\n\n"
                                "!hoch  oder  !   → hohe Priorität\n"
                                "!niedrig        → niedrige Priorität\n"
                                "@heute, @morgen, @übermorgen\n"
                                "@mo … @so      → nächster Wochentag\n"
                                "@24.12.        → Datum\n\n"
                                "Beispiel: Steuer abgeben !hoch @31.7.\n\n"
                                "Doppelklick auf eine Aufgabe = bearbeiten, Rechtsklick = Priorität/Datum.")

    # -- Anzeige ------------------------------------------------------------
    def aktualisieren(self):
        self.lw.clear()
        e = self.liste.einstellungen
        aufgaben = self.liste.sortiert(e.erledigte_zeigen)
        for a in aufgaben:
            it = QListWidgetItem()
            w = Zeile(self, a)
            it.setSizeHint(QSize(10, max(34, w.sizeHint().height())))
            self.lw.addItem(it)
            self.lw.setItemWidget(it, w)
        offen = self.liste.anzahl_offen()
        self.ueberschrift.setText(f"Meine Aufgaben ({offen})")
        if not aufgaben:
            it = QListWidgetItem("Alles erledigt! 🎉\nNeue Aufgabe oben eintippen und Enter drücken.")
            it.setTextAlignment(Qt.AlignCenter)
            it.setForeground(QColor("#9e9e9e"))
            it.setSizeHint(QSize(10, 80))
            self.lw.addItem(it)
        ue = self.liste.anzahl_ueberfaellig()
        self.status.setText(f"{ue} heute fällig oder überfällig" if ue else "")
        self.geaendert.emit()

    def _groesse_merken(self):
        e = self.liste.einstellungen
        e.popup_breite, e.popup_hoehe = self.width(), self.height()
        self.liste.speichern()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self.isVisible():
            self._groesse_merken()

    def hideEvent(self, ev):
        self.zuletzt_geschlossen = time.monotonic()
        self.zu.emit()
        super().hideEvent(ev)

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(ev)


# ---------------------------------------------------------------------------
# Steuerung
# ---------------------------------------------------------------------------

STIL = f"""
QFrame#popup {{ background: #fafafa; border: 1px solid #c5cae9; border-radius: 10px; }}
QListWidget {{ background: white; border: 1px solid #e0e0e0; border-radius: 6px; }}
QListWidget::item {{ border-bottom: 1px solid #f0f0f0; }}
QLineEdit {{ padding: 5px; border: 1px solid #c5cae9; border-radius: 5px; background: white; }}
QPushButton#plus {{ background: {AKZENT}; color: white; font-size: 18px; font-weight: bold; border-radius: 5px; padding: 2px; }}
QCheckBox::indicator {{ width: 17px; height: 17px; }}
"""


class Widget:
    def __init__(self, liste: Liste):
        self.liste = liste
        e = liste.einstellungen
        self.symbol = Symbol(e.symbol_groesse)
        self.popup = Popup(liste)
        self.symbol.geklickt.connect(self.umschalten)
        self.symbol.verschoben.connect(self.position_merken)
        self.symbol.setContextMenuPolicy(Qt.CustomContextMenu)
        self.symbol.customContextMenuRequested.connect(self.menue)
        self.popup.geaendert.connect(self.zaehler)
        self._platzieren()
        self.zaehler()
        self.symbol.show()
        # Mitternacht: Fälligkeiten neu bewerten
        self.timer = QTimer(interval=60_000, timeout=self.zaehler)
        self.timer.start()

    def _platzieren(self):
        e = self.liste.einstellungen
        bildschirm = QGuiApplication.primaryScreen().availableGeometry()
        if e.symbol_x < 0:
            pos = QPoint(bildschirm.right() - self.symbol.width() - 30, bildschirm.top() + 120)
        else:
            pos = QPoint(e.symbol_x, e.symbol_y)
            # liegt die gespeicherte Position noch auf einem Bildschirm?
            if not any(s.availableGeometry().contains(pos + QPoint(10, 10)) for s in QGuiApplication.screens()):
                pos = QPoint(bildschirm.right() - self.symbol.width() - 30, bildschirm.top() + 120)
        self.symbol.move(pos)

    def position_merken(self, pos: QPoint):
        e = self.liste.einstellungen
        e.symbol_x, e.symbol_y = pos.x(), pos.y()
        self.liste.speichern()

    def zaehler(self):
        self.symbol.zaehler(self.liste.anzahl_offen(), self.liste.anzahl_ueberfaellig())

    def umschalten(self):
        if self.popup.isVisible():
            self.popup.hide()
            return
        # Ein Klick auf das Symbol schließt das Popup (Qt.Popup) bereits – nicht sofort wieder öffnen
        if time.monotonic() - self.popup.zuletzt_geschlossen < 0.3:
            return
        self.oeffnen()

    def oeffnen(self):
        p = self.popup
        p.aktualisieren()
        s = self.symbol.geometry()
        screen = QGuiApplication.screenAt(s.center()) or QGuiApplication.primaryScreen()
        g = screen.availableGeometry()
        w, h = p.width(), p.height()
        # bevorzugt links neben dem Symbol, sonst rechts; vertikal am Symbol ausgerichtet
        x = s.left() - w - 6 if s.left() - w - 6 >= g.left() else s.right() + 6
        x = max(g.left(), min(x, g.right() - w))
        y = max(g.top(), min(s.top(), g.bottom() - h))
        p.move(x, y)
        p.show()
        p.raise_()
        p.activateWindow()
        p.neu.setFocus()

    def menue(self, pos):
        m = QMenu()
        m.addAction("Liste öffnen", self.oeffnen)
        a = m.addAction("Mit Windows starten")
        a.setCheckable(True)
        a.setChecked(self.liste.einstellungen.autostart)
        a.toggled.connect(self.popup._autostart)
        m.addAction("Position zurücksetzen", self._position_zuruecksetzen)
        m.addSeparator()
        m.addAction("Beenden", QApplication.quit)
        m.exec(self.symbol.mapToGlobal(pos))

    def _position_zuruecksetzen(self):
        e = self.liste.einstellungen
        e.symbol_x = e.symbol_y = -1
        self.liste.speichern()
        self._platzieren()


def _deutsch(app):
    from PySide6.QtCore import QLibraryInfo, QTranslator
    t = QTranslator(app)
    if t.load(QLocale(QLocale.German, QLocale.Germany), "qtbase", "_",
              QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(t)
        app._uebersetzer = t


def main():
    QLocale.setDefault(QLocale(QLocale.German, QLocale.Germany))
    app = QApplication(sys.argv)
    app.setApplicationName("ToDo-Widget")
    app.setOrganizationName("MeineApps")
    _deutsch(app)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet(STIL)
    app.setWindowIcon(app_icon())
    sock = QLocalSocket()
    sock.connectToServer(INSTANZ)
    if sock.waitForConnected(300):
        sock.write(b"oeffnen")
        sock.flush()
        sock.waitForBytesWritten(300)
        return
    QLocalServer.removeServer(INSTANZ)
    server = QLocalServer()
    server.listen(INSTANZ)
    w = Widget(Liste(datenpfad()))
    # zweiter Start -> Liste der laufenden Instanz öffnen
    server.newConnection.connect(lambda: (server.nextPendingConnection(), w.oeffnen()))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
