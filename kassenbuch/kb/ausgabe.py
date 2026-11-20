"""PDF-Ausgabe von Angeboten/Rechnungen sowie Kassenbuch-Export (CSV, Excel, PDF)."""
from __future__ import annotations

import csv
import io
import os
from typing import Dict, List, Optional

from .daten import Beleg, Datenbank, datum_de, euro

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
          "Oktober", "November", "Dezember"]


def _schriften():
    """Unicode-fähige Schrift registrieren (Arial/DejaVu), Fallback Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    kandidaten = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    try:
        import reportlab
        rl = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
        kandidaten.append((os.path.join(rl, "Vera.ttf"), os.path.join(rl, "VeraBd.ttf")))
    except Exception:
        pass
    for normal, fett in kandidaten:
        if os.path.exists(normal) and os.path.exists(fett):
            try:
                pdfmetrics.registerFont(TTFont("KB", normal))
                pdfmetrics.registerFont(TTFont("KB-Bold", fett))
                pdfmetrics.registerFontFamily("KB", normal="KB", bold="KB-Bold", italic="KB", boldItalic="KB-Bold")
                return "KB", "KB-Bold"
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


def _menge(m: float) -> str:
    return (f"{m:g}").replace(".", ",")


# ---------------------------------------------------------------------------
# Angebot / Rechnung
# ---------------------------------------------------------------------------

def beleg_pdf(db: Datenbank, b: Beleg, pfad: str):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (Frame, PageTemplate, BaseDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, KeepTogether)

    font, fett = _schriften()
    e = db.einstellungen()
    logo = db.logo()
    rechnung = b.ist_rechnung
    titel = "Rechnung" if rechnung else "Angebot"
    if rechnung and b.status == "storniert":
        titel = "Rechnung (STORNIERT)"

    normal = ParagraphStyle("n", fontName=font, fontSize=10, leading=13.5)
    klein = ParagraphStyle("k", parent=normal, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#555555"))
    rechts = ParagraphStyle("r", parent=normal, alignment=2)
    tabkopf = ParagraphStyle("tk", parent=normal, fontName=fett, fontSize=9)
    tabzelle = ParagraphStyle("tz", parent=normal, fontSize=9, leading=11.5)
    tabzelle_r = ParagraphStyle("tzr", parent=tabzelle, alignment=2)
    h1 = ParagraphStyle("h1", parent=normal, fontName=fett, fontSize=15, leading=19)

    breite, hoehe = A4
    links = 25 * mm
    rand_r = 20 * mm

    absender = " · ".join(x for x in [e["firma_name"], e["strasse"], f"{e['plz']} {e['ort']}".strip()] if x)

    def kopf_fuss(c, doc):
        c.saveState()
        # Logo
        if logo:
            try:
                img = ImageReader(io.BytesIO(logo))
                iw, ih = img.getSize()
                maxb, maxh = 60 * mm, 25 * mm
                s = min(maxb / iw, maxh / ih)
                c.drawImage(img, breite - rand_r - iw * s, hoehe - 15 * mm - ih * s, iw * s, ih * s, mask="auto")
            except Exception:
                pass
        else:
            c.setFont(fett, 14)
            c.setFillColor(colors.HexColor("#1f4e79"))
            c.drawRightString(breite - rand_r, hoehe - 22 * mm, e["firma_name"])
        if doc.page == 1:
            # Absenderzeile + Anschrift (Fenster DIN 5008, Form B)
            c.setFont(font, 7)
            c.setFillColor(colors.HexColor("#555555"))
            c.drawString(links, hoehe - 50 * mm, absender[:110])
            c.setLineWidth(0.3)
            c.line(links, hoehe - 51 * mm, links + 85 * mm, hoehe - 51 * mm)
            c.setFillColor(colors.black)
            c.setFont(font, 10.5)
            y = hoehe - 57 * mm
            for zeile in (b.anschrift or "").splitlines()[:6]:
                c.drawString(links, y, zeile)
                y -= 5 * mm
            # Infoblock rechts
            info = [(f"{titel.split(' ')[0]}snummer:" if rechnung else "Angebotsnummer:", b.nummer),
                    ("Datum:", datum_de(b.datum))]
            if b.kunde_id:
                k = db.kunde(b.kunde_id)
                if k and k["nummer"]:
                    info.append(("Kundennummer:", k["nummer"]))
            if rechnung:
                info.append(("Leistungsdatum:", datum_de(b.leistungsdatum or b.datum)))
                info.append(("Zahlbar bis:", datum_de(b.faellig)))
            else:
                info.append(("Gültig bis:", datum_de(b.faellig)))
            y = hoehe - 55 * mm
            for k_, v in info:
                c.setFont(font, 9)
                c.drawString(breite - rand_r - 75 * mm, y, k_)
                c.setFont(fett, 9)
                c.drawRightString(breite - rand_r, y, v)
                y -= 5 * mm
        # Fußzeile mit Firmendaten
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.4)
        c.line(links, 27 * mm, breite - rand_r, 27 * mm)
        spalten = [
            [e["firma_name"], e["inhaber"], e["strasse"], f"{e['plz']} {e['ort']}".strip()],
            [f"Tel.: {e['telefon']}" if e["telefon"] else "", e["email"], e["web"]],
            [e["bank"], f"IBAN: {e['iban']}" if e["iban"] else "", f"BIC: {e['bic']}" if e["bic"] else ""],
            [f"Steuernr.: {e['steuernummer']}" if e["steuernummer"] else "",
             f"USt-IdNr.: {e['ust_idnr']}" if e["ust_idnr"] else ""],
        ]
        x = links
        sb = (breite - links - rand_r) / 4
        c.setFont(font, 7)
        c.setFillColor(colors.HexColor("#555555"))
        for sp in spalten:
            y = 23 * mm
            for z in [z for z in sp if z]:
                c.drawString(x, y, z[:48])
                y -= 3.3 * mm
            x += sb
        c.drawRightString(breite - rand_r, 8 * mm, f"Seite {doc.page}")
        c.restoreState()

    doc = BaseDocTemplate(pfad, pagesize=A4, title=f"{titel} {b.nummer}", author=e["firma_name"])
    erste = Frame(links, 32 * mm, breite - links - rand_r, hoehe - 32 * mm - 100 * mm, id="erste")
    folge = Frame(links, 32 * mm, breite - links - rand_r, hoehe - 32 * mm - 45 * mm, id="folge")
    doc.addPageTemplates([PageTemplate("erste", [erste], onPage=kopf_fuss, autoNextPageTemplate="folge"),
                          PageTemplate("folge", [folge], onPage=kopf_fuss)])

    def text(t: str) -> str:
        t = (t or "").replace("{faellig}", datum_de(b.faellig)).replace("{gueltig}", datum_de(b.faellig))
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return t.replace("\n", "<br/>")

    el = [Paragraph(f"{titel} {b.nummer}", h1)]
    if b.betreff:
        el.append(Paragraph(text(b.betreff), ParagraphStyle("b", parent=normal, fontName=fett)))
    el.append(Spacer(1, 6 * mm))
    el.append(Paragraph("Sehr geehrte Damen und Herren,", normal))
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph(text(b.einleitung), normal))
    el.append(Spacer(1, 5 * mm))

    daten = [[Paragraph(x, tabkopf) for x in ["Pos.", "Bezeichnung", "Menge", "Einheit"]]
             + [Paragraph("Einzelpreis", ParagraphStyle("x", parent=tabkopf, alignment=2)),
                Paragraph("Gesamt", ParagraphStyle("y", parent=tabkopf, alignment=2))]]
    for i, p in enumerate(b.positionen, 1):
        bez = text(p.bezeichnung)
        if p.beschreibung:
            bez += f"<br/><font size=8 color='#555555'>{text(p.beschreibung)}</font>"
        daten.append([Paragraph(str(i), tabzelle), Paragraph(bez, tabzelle), Paragraph(_menge(p.menge), tabzelle_r),
                      Paragraph(p.einheit or "", tabzelle), Paragraph(euro(p.preis_cent), tabzelle_r),
                      Paragraph(euro(p.summe_cent), tabzelle_r)])
    sb = breite - links - rand_r
    t = Table(daten, colWidths=[13 * mm, sb - 13 * mm - 17 * mm - 19 * mm - 25 * mm - 26 * mm, 17 * mm,
                                19 * mm, 25 * mm, 26 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef5")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#1f4e79")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(t)
    gross = ParagraphStyle("g", parent=normal, fontName=fett, fontSize=11.5, leading=14)
    summe = Table([[Paragraph("Gesamtbetrag", gross),
                    Paragraph(euro(b.summe_cent), ParagraphStyle("gr", parent=gross, alignment=2))]],
                  colWidths=[sb - 45 * mm, 45 * mm])
    summe.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
                               ("LINEBELOW", (0, 0), (-1, 0), 1.6, colors.black),
                               ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    hinweis = Paragraph(text(e["kleinunternehmer_hinweis"]), ParagraphStyle("h", parent=normal, fontSize=9))
    el.append(KeepTogether([summe, Spacer(1, 3 * mm), hinweis]))
    el.append(Spacer(1, 7 * mm))
    if rechnung and b.status == "bezahlt" and b.bezahlt_am:
        el.append(Paragraph(f"<b>Betrag dankend erhalten am {datum_de(b.bezahlt_am)}.</b>", normal))
        el.append(Spacer(1, 3 * mm))
    el.append(Paragraph(text(b.schluss), normal))
    if e["inhaber"] or e["firma_name"]:
        el.append(Spacer(1, 4 * mm))
        el.append(Paragraph(text(e["inhaber"] or e["firma_name"]), normal))
    doc.build(el)


# ---------------------------------------------------------------------------
# Kassenbuch
# ---------------------------------------------------------------------------

def _zeitraum(jahr: int, monat: Optional[int]) -> str:
    return f"{MONATE[monat - 1]} {jahr}" if monat else f"Jahr {jahr}"


def kassenbuch_csv(db: Datenbank, pfad: str, jahr: int, monat: Optional[int] = None):
    """CSV im deutschen Excel-Format (Semikolon, Dezimalkomma, UTF-8 mit BOM)."""
    with open(pfad, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Datum", "Beleg-Nr.", "Beschreibung", "Kategorie", "Einnahme", "Ausgabe", "Bestand"])
        for b in db.buchungen(jahr, monat):
            w.writerow([datum_de(b["datum"]), b["belegnr"], b["beschreibung"], b["kategorie"],
                        euro(b["betrag_cent"], False) if b["art"] == "E" else "",
                        euro(b["betrag_cent"], False) if b["art"] == "A" else "",
                        euro(b["bestand_cent"], False)])


def kassenbuch_excel(db: Datenbank, pfad: str, jahr: int, monat: Optional[int] = None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Kassenbuch"
    fett = Font(bold=True)
    kopf_fill = PatternFill("solid", fgColor="DCE6F1")
    geld = '#,##0.00 "€";[Red]-#,##0.00 "€"'
    ws.append([f"Kassenbuch {db.einstellung('firma_name')} – {_zeitraum(jahr, monat)}"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    kopf = ["Datum", "Beleg-Nr.", "Beschreibung", "Kategorie", "Einnahme", "Ausgabe", "Bestand"]
    ws.append(kopf)
    for c in ws[3]:
        c.font, c.fill = fett, kopf_fill
    import datetime as _dt
    for b in db.buchungen(jahr, monat):
        e = b["betrag_cent"] / 100 if b["art"] == "E" else None
        a = b["betrag_cent"] / 100 if b["art"] == "A" else None
        ws.append([_dt.date.fromisoformat(b["datum"]), b["belegnr"], b["beschreibung"], b["kategorie"], e, a,
                   b["bestand_cent"] / 100])
        ws.cell(ws.max_row, 1).number_format = "DD.MM.YYYY"
        for col in (5, 6, 7):
            ws.cell(ws.max_row, col).number_format = geld
    letzte = ws.max_row
    ws.append([])
    ws.append(["", "", "Summe", "", f"=SUM(E4:E{letzte})", f"=SUM(F4:F{letzte})", ""])
    for col in (5, 6):
        ws.cell(ws.max_row, col).number_format = geld
        ws.cell(ws.max_row, col).font = fett
    ws.cell(ws.max_row, 3).font = fett
    for i, b in enumerate([12, 14, 40, 22, 14, 14, 14], 1):
        ws.column_dimensions[get_column_letter(i)].width = b
    ws.freeze_panes = "A4"

    # Monatsübersicht
    m = wb.create_sheet("Monatsübersicht")
    m.append([f"Monatsübersicht {jahr}"])
    m["A1"].font = Font(bold=True, size=14)
    m.append([])
    m.append(["Monat", "Einnahmen", "Ausgaben", "Saldo"])
    for c in m[3]:
        c.font, c.fill = fett, kopf_fill
    for z in db.monatsuebersicht(jahr):
        m.append([MONATE[z["monat"] - 1], z["einnahmen"] / 100, z["ausgaben"] / 100, z["saldo"] / 100])
    m.append(["Jahr gesamt", "=SUM(B4:B15)", "=SUM(C4:C15)", "=SUM(D4:D15)"])
    for row in m.iter_rows(min_row=4, max_row=16, min_col=2, max_col=4):
        for c in row:
            c.number_format = geld
    for c in m[16]:
        c.font = fett
    for i, b in enumerate([16, 16, 16, 16], 1):
        m.column_dimensions[get_column_letter(i)].width = b

    # Kategorien
    k = wb.create_sheet("Kategorien")
    k.append([f"Kategorien – {_zeitraum(jahr, monat)}"])
    k["A1"].font = Font(bold=True, size=14)
    k.append([])
    k.append(["Art", "Kategorie", "Anzahl", "Summe"])
    for c in k[3]:
        c.font, c.fill = fett, kopf_fill
    for z in db.kategorieuebersicht(jahr, monat):
        k.append(["Einnahme" if z["art"] == "E" else "Ausgabe", z["kategorie"], z["anzahl"], z["summe"] / 100])
        k.cell(k.max_row, 4).number_format = geld
    for i, b in enumerate([12, 26, 10, 16], 1):
        k.column_dimensions[get_column_letter(i)].width = b
    wb.save(pfad)


def kassenbuch_pdf(db: Datenbank, pfad: str, jahr: int, monat: Optional[int] = None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font, fett = _schriften()
    normal = ParagraphStyle("n", fontName=font, fontSize=9, leading=11)
    h1 = ParagraphStyle("h1", fontName=fett, fontSize=15, leading=19)
    h2 = ParagraphStyle("h2", fontName=fett, fontSize=11, leading=15, spaceBefore=8, spaceAfter=4)
    buchungen = db.buchungen(jahr, monat)
    e_sum = sum(b["betrag_cent"] for b in buchungen if b["art"] == "E")
    a_sum = sum(b["betrag_cent"] for b in buchungen if b["art"] == "A")
    if buchungen:
        erste = buchungen[0]
        start = erste["bestand_cent"] - (erste["betrag_cent"] if erste["art"] == "E" else -erste["betrag_cent"])
    else:
        start = db.kassenbestand(f"{jahr:04d}-{monat or 1:02d}-00")
    el = [Paragraph(f"Kassenbuch – {_zeitraum(jahr, monat)}", h1),
          Paragraph(f"{db.einstellung('firma_name')} · Anfangsbestand: {euro(start)} · Einnahmen: {euro(e_sum)} · "
                    f"Ausgaben: {euro(a_sum)} · Endbestand: {euro(start + e_sum - a_sum)}", normal),
          Spacer(1, 5 * mm)]
    daten = [["Datum", "Beleg-Nr.", "Beschreibung", "Kategorie", "Einnahme", "Ausgabe", "Bestand"]]
    for b in buchungen:
        daten.append([datum_de(b["datum"]), b["belegnr"], Paragraph(b["beschreibung"] or "", normal),
                      b["kategorie"], euro(b["betrag_cent"]) if b["art"] == "E" else "",
                      euro(b["betrag_cent"]) if b["art"] == "A" else "", euro(b["bestand_cent"])])
    daten.append(["", "", "Summe", "", euro(e_sum), euro(a_sum), ""])
    t = Table(daten, colWidths=[22 * mm, 28 * mm, 85 * mm, 40 * mm, 28 * mm, 28 * mm, 30 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), font, 8.5), ("FONT", (0, 0), (-1, 0), fett, 8.5),
        ("FONT", (0, -1), (-1, -1), fett, 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef5")),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#cccccc")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
    ]))
    el.append(t)
    if not monat:
        el.append(Paragraph(f"Monatsübersicht {jahr}", h2))
        md = [["Monat", "Einnahmen", "Ausgaben", "Saldo"]]
        for z in db.monatsuebersicht(jahr):
            md.append([MONATE[z["monat"] - 1], euro(z["einnahmen"]), euro(z["ausgaben"]), euro(z["saldo"])])
        md.append(["Gesamt", euro(e_sum), euro(a_sum), euro(e_sum - a_sum)])
        mt = Table(md, colWidths=[40 * mm, 35 * mm, 35 * mm, 35 * mm])
        mt.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), font, 8.5), ("FONT", (0, 0), (-1, 0), fett, 8.5),
                                ("FONT", (0, -1), (-1, -1), fett, 8.5), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef5")),
                                ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black)]))
        el.append(mt)
    kat = db.kategorieuebersicht(jahr, monat)
    if kat:
        el.append(Paragraph("Nach Kategorien", h2))
        kd = [["Art", "Kategorie", "Anzahl", "Summe"]] + [
            ["Einnahme" if z["art"] == "E" else "Ausgabe", z["kategorie"], str(z["anzahl"]), euro(z["summe"])]
            for z in kat]
        kt = Table(kd, colWidths=[25 * mm, 50 * mm, 20 * mm, 35 * mm])
        kt.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), font, 8.5), ("FONT", (0, 0), (-1, 0), fett, 8.5),
                                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef5"))]))
        el.append(kt)

    def fuss(c, doc):
        c.saveState()
        c.setFont(font, 7)
        c.drawRightString(landscape(A4)[0] - 15 * mm, 8 * mm, f"Seite {doc.page}")
        c.restoreState()

    SimpleDocTemplate(pfad, pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm,
                      bottomMargin=15 * mm, title=f"Kassenbuch {_zeitraum(jahr, monat)}").build(
        el, onFirstPage=fuss, onLaterPages=fuss)
