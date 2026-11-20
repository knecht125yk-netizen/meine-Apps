"""Export einer Rechnung als PDF (reportlab) und Word (python-docx)."""
from __future__ import annotations

import datetime as _dt
import io

from .darstellung import diagramm_png, formel_png
from .rechnung import Rechnung, fmt

PROGRAMM = "Maschinenbau-Rechner"


def _datum():
    return _dt.datetime.now().strftime("%d.%m.%Y %H:%M")


def _bildgroesse(png: bytes):
    from PIL import Image
    with Image.open(io.BytesIO(png)) as im:
        return im.size


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def als_pdf(r: Rechnung, pfad: str, projekt: str = ""):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
                                    KeepTogether)
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font, font_b = "Helvetica", "Helvetica-Bold"
    # Unicode-Schrift (für σ, τ, ², ≥ …) – DejaVu liegt matplotlib bei
    try:
        import matplotlib
        import os
        fdir = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(fdir, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(fdir, "DejaVuSans-Bold.ttf")))
        font, font_b = "DejaVu", "DejaVu-Bold"
    except Exception:
        pass

    st = getSampleStyleSheet()
    normal = ParagraphStyle("n", parent=st["Normal"], fontName=font, fontSize=9.5, leading=12)
    klein = ParagraphStyle("k", parent=normal, fontSize=8, textColor=colors.grey)
    h1 = ParagraphStyle("h1", parent=st["Heading1"], fontName=font_b, fontSize=16, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=st["Heading2"], fontName=font_b, fontSize=12, spaceBefore=10,
                        spaceAfter=4, textColor=colors.HexColor("#1f6fb2"))

    def formelbild(latex, max_b=110 * mm, hoehe_skala=0.24):
        png = formel_png(latex, 15, 200)
        w, h = _bildgroesse(png)
        b = w * hoehe_skala * mm / 2.0
        hh = h * hoehe_skala * mm / 2.0
        if b > max_b:
            hh *= max_b / b
            b = max_b
        return Image(io.BytesIO(png), width=b, height=hh)

    elemente = [Paragraph(r.titel, h1),
                Paragraph(f"{PROGRAMM} · erstellt am {_datum()}" + (f" · {projekt}" if projekt else ""), klein),
                Spacer(1, 6)]

    elemente.append(Paragraph("1. Eingaben", h2))
    daten = [["Größe", "Symbol", "Wert"]] + [[e.name, e.symbol, e.text()] for e in r.eingaben]
    t = Table(daten, colWidths=[75 * mm, 25 * mm, 70 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), font, 9), ("FONT", (0, 0), (-1, 0), font_b, 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f1fa")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elemente.append(t)

    elemente.append(Paragraph("2. Berechnung", h2))
    for i, s in enumerate(r.schritte, 1):
        zeilen = [[Paragraph(f"<b>2.{i} {s.beschreibung}</b>", normal), ""],
                  [formelbild(s.formel), Paragraph(f"<b>{s.ergebnis_text()}</b>", normal)]]
        if s.eingesetzt:
            zeilen.append([Paragraph(s.eingesetzt, klein), ""])
        tb = Table(zeilen, colWidths=[120 * mm, 50 * mm])
        tb.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("ALIGN", (1, 1), (1, 1), "RIGHT"),
                                ("LINEBELOW", (0, -1), (-1, -1), 0.3, colors.lightgrey),
                                ("BOTTOMPADDING", (0, -1), (-1, -1), 5)]))
        elemente.append(KeepTogether(tb))

    if r.nachweise:
        elemente.append(Paragraph("3. Nachweis", h2))
        for n in r.nachweise:
            farbe = "#2e8b57" if n.erfuellt else "#c0392b"
            zeilen = [[Paragraph(f"<b>{n.beschreibung}</b>", normal), ""],
                      [formelbild(n.formel), Paragraph(f"<font color='{farbe}'><b>{n.text()}</b></font>", normal)]]
            if n.eingesetzt:
                zeilen.append([Paragraph(n.eingesetzt, klein), ""])
            tb = Table(zeilen, colWidths=[80 * mm, 90 * mm])
            tb.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(farbe))]))
            elemente.append(KeepTogether(tb))
            elemente.append(Spacer(1, 4))

    if r.hinweise:
        elemente.append(Paragraph("Hinweise", h2))
        for h in r.hinweise:
            elemente.append(Paragraph("• " + h, normal))

    png = diagramm_png(r.plot)
    if png:
        elemente.append(Paragraph("Diagramm / Skizze", h2))
        w, h = _bildgroesse(png)
        b = 165 * mm
        elemente.append(Image(io.BytesIO(png), width=b, height=b * h / w))

    def fusszeile(c, doc):
        c.saveState()
        c.setFont(font, 7.5)
        c.setFillColor(colors.grey)
        c.drawString(20 * mm, 10 * mm, f"{PROGRAMM} – {r.titel}")
        c.drawRightString(190 * mm, 10 * mm, f"Seite {doc.page}")
        c.restoreState()

    doc = SimpleDocTemplate(pfad, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm, title=r.titel, author=PROGRAMM)
    doc.build(elemente, onFirstPage=fusszeile, onLaterPages=fusszeile)


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

def als_docx(r: Rechnung, pfad: str, projekt: str = ""):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    stil = doc.styles["Normal"]
    stil.font.name = "Calibri"
    stil.font.size = Pt(10)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2)

    doc.add_heading(r.titel, level=1)
    p = doc.add_paragraph(f"{PROGRAMM} · erstellt am {_datum()}" + (f" · {projekt}" if projekt else ""))
    p.runs[0].font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    p.runs[0].font.size = Pt(8)

    doc.add_heading("1. Eingaben", level=2)
    t = doc.add_table(rows=1, cols=3)
    t.style = "Light Grid Accent 1"
    for zelle, text in zip(t.rows[0].cells, ["Größe", "Symbol", "Wert"]):
        zelle.text = text
    for e in r.eingaben:
        z = t.add_row().cells
        z[0].text, z[1].text, z[2].text = e.name, e.symbol, e.text()

    def formel(par, latex):
        png = formel_png(latex, 15, 200)
        w, h = _bildgroesse(png)
        hoehe = Cm(h / 200 * 2.54 * 0.9)
        breite = Cm(w / 200 * 2.54 * 0.9)
        if breite > Cm(13):
            hoehe = int(hoehe * Cm(13) / breite)
            breite = Cm(13)
        par.add_run().add_picture(io.BytesIO(png), width=breite, height=hoehe)

    doc.add_heading("2. Berechnung", level=2)
    for i, s in enumerate(r.schritte, 1):
        p = doc.add_paragraph()
        p.add_run(f"2.{i} {s.beschreibung}").bold = True
        p = doc.add_paragraph()
        formel(p, s.formel)
        run = p.add_run(f"    =  {s.ergebnis_text()}")
        run.bold = True
        if s.eingesetzt:
            p = doc.add_paragraph(s.eingesetzt)
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.color.rgb = RGBColor(0x60, 0x60, 0x60)

    if r.nachweise:
        doc.add_heading("3. Nachweis", level=2)
        for n in r.nachweise:
            p = doc.add_paragraph()
            p.add_run(n.beschreibung).bold = True
            p = doc.add_paragraph()
            formel(p, n.formel)
            run = p.add_run("    " + n.text())
            run.bold = True
            run.font.color.rgb = RGBColor(0x2e, 0x8b, 0x57) if n.erfuellt else RGBColor(0xc0, 0x39, 0x2b)
            if n.eingesetzt:
                doc.add_paragraph(n.eingesetzt).runs[0].font.size = Pt(8)

    if r.hinweise:
        doc.add_heading("Hinweise", level=2)
        for h in r.hinweise:
            doc.add_paragraph(h, style="List Bullet")

    png = diagramm_png(r.plot)
    if png:
        doc.add_heading("Diagramm / Skizze", level=2)
        doc.add_picture(io.BytesIO(png), width=Cm(16))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.save(pfad)


def text_zusammenfassung(r: Rechnung) -> str:
    """Kurze Klartext-Zusammenfassung (z. B. für die Zwischenablage)."""
    zeilen = [r.titel, ""]
    zeilen += [f"{e.name} {e.symbol}: {e.text()}" for e in r.eingaben]
    zeilen.append("")
    zeilen += [f"{s.beschreibung}: {s.symbol.strip(chr(92))} = {s.ergebnis_text()}" for s in r.schritte]
    zeilen += [f"{n.beschreibung}: {n.text()}" for n in r.nachweise]
    return "\n".join(zeilen)


__all__ = ["als_pdf", "als_docx", "text_zusammenfassung", "fmt"]
