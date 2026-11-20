import io

import pytest
from matplotlib import mathtext
from matplotlib.font_manager import FontProperties

from mbrechner import formeln as f
from mbrechner.export import als_docx, als_pdf
from mbrechner.profile import berechne
from mbrechner.werkstoffe import werkstoff

S235 = werkstoff("S235JR")


def alle_rechnungen():
    q = berechne("Rechteck", {"b": 20, "h": 40})
    rund = berechne("Rund", {"d": 30})
    rs = [f.biegung(lf, 1000 if "Einzel" in lf else 2, 1000, 300, q, S235) for lf in f.LASTFAELLE]
    rs += [f.knickung(k, 1000, 5000, rund, S235) for k in (1, 2, 3, 4)]
    rs += [f.knickung(2, 300, 5000, rund, werkstoff("EN AW-6082 T6"))]
    rs += [f.zug_druck(-1000, 500, q, S235), f.torsion(100, 500, rund, S235),
           f.schub(f.SCHUBARTEN[0], 1000, rund, S235, 2), f.schub(f.SCHUBARTEN[1], 1000, q, S235),
           f.schub(f.SCHUBARTEN[1], 1000, berechne("I-Profil", {"h": 200, "b": 100, "s": 5.6, "t": 8.5}), S235),
           f.flaechenpressung(f.PRESSUNGSARTEN[0], 1000, 10, 20, 100),
           f.flaechenpressung(f.PRESSUNGSARTEN[1], 1000, 10, 20, 100),
           f.vergleichsspannung(100, 20, 30, S235), f.schraube("M10", "8.8", 1000, 2000, 2),
           f.welle(5, 1000, 30, 30, S235), f.passfeder(40, 200, 50),
           f.sicherheitsnachweis(100, f.GRENZEN[1], S235, 2)]
    rs += [f.querschnittswerte(p, berechne(p, {"b": 20, "h": 40, "d": 20, "D": 40, "s": 5, "t": 8}).masse)
           for p in ("Rechteck", "Rund", "Rohr", "I-Profil", "U-Profil")]
    return rs


def test_alle_formeln_sind_gueltiges_mathtext():
    for r in alle_rechnungen():
        formeln = [s.formel for s in r.schritte] + [n.formel for n in r.nachweise]
        for latex in formeln:
            mathtext.math_to_image(f"${latex}$", io.BytesIO(), prop=FontProperties(size=12), format="png")


@pytest.mark.parametrize("idx", [0, 4, 9, 13, 16])
def test_export_pdf_und_docx(tmp_path, idx):
    r = alle_rechnungen()[idx]
    als_pdf(r, str(tmp_path / "r.pdf"))
    als_docx(r, str(tmp_path / "r.docx"))
    assert (tmp_path / "r.pdf").read_bytes()[:4] == b"%PDF"
    assert (tmp_path / "r.docx").stat().st_size > 5000
