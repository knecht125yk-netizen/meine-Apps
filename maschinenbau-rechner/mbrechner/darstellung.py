"""Formeldarstellung (Mathtext → PNG) und Diagramme/Skizzen mit Matplotlib.

Wird von der GUI und vom PDF-/Word-Export gemeinsam genutzt.
"""
from __future__ import annotations

import io
import math
from functools import lru_cache

import matplotlib

matplotlib.use("Agg", force=False)
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib import mathtext  # noqa: E402
from matplotlib.patches import Polygon, Rectangle, Circle, FancyArrowPatch  # noqa: E402

BLAU = "#1f6fb2"
ROT = "#c0392b"
GRUEN = "#2e8b57"
GRAU = "#7f8c8d"


@lru_cache(maxsize=512)
def formel_png(latex: str, groesse: int = 15, dpi: int = 130, farbe: str = "black") -> bytes:
    """Formel (Mathtext, ohne $) als PNG rendern."""
    buf = io.BytesIO()
    latex = latex.replace(r"\frac", r"\dfrac")  # Brüche in voller Größe
    try:
        mathtext.math_to_image(f"${latex}$", buf, prop=FontProperties(size=groesse), dpi=dpi,
                               format="png", color=farbe)
    except Exception:  # Fallback: Formel als Klartext
        buf = io.BytesIO()
        fig = Figure(figsize=(6, 0.4), dpi=dpi)
        fig.text(0, 0.3, latex, fontsize=groesse * 0.7)
        fig.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    return buf.getvalue()


def diagramm_png(plot: dict, breite=7.0, hoehe=4.2, dpi=150) -> bytes | None:
    if not plot:
        return None
    fig = Figure(figsize=(breite, hoehe), dpi=dpi)
    zeichne(plot, fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Zeichenfunktionen
# ---------------------------------------------------------------------------

def zeichne(plot: dict, fig: Figure):
    fig.clear()
    if not plot:
        return
    typ = plot.get("typ")
    fn = {
        "biegung": _biegung, "knickung": _knickung, "torsion": _torsion,
        "querschnitt": _querschnitt, "stab": _stab, "pressung": _pressung,
        "mohr": _mohr, "balken": _balken, "passfeder": _passfeder,
    }.get(typ)
    if fn:
        fn(plot, fig)
    try:
        fig.tight_layout()
    except Exception:
        pass


def _biegung(p, fig):
    l, a, lf = p["l"], p["a"], p["lastfall"]
    ax0 = fig.add_subplot(3, 1, 1)
    ax1 = fig.add_subplot(3, 1, 2, sharex=ax0)
    ax2 = fig.add_subplot(3, 1, 3, sharex=ax0)
    # Systemskizze
    ax0.set_title("System", fontsize=9, loc="left")
    ax0.plot([0, l], [0, 0], color="black", lw=4)
    krag = lf.startswith("Krag")
    if krag:
        ax0.add_patch(Rectangle((-0.03 * l, -0.6), 0.03 * l, 1.2, color=GRAU, hatch="///", fill=False))
    else:
        for x in (0, l):
            ax0.add_patch(Polygon([[x, 0], [x - 0.02 * l, -0.5], [x + 0.02 * l, -0.5]], color=GRAU))
    if "Einzellast" in lf:
        xF = l if krag else a
        ax0.annotate("", xy=(xF, 0.05), xytext=(xF, 1.0),
                     arrowprops=dict(arrowstyle="-|>", color=ROT, lw=2))
        ax0.text(xF, 1.05, "F", color=ROT, ha="center", fontsize=9)
    else:
        for k in range(11):
            x = l * k / 10
            ax0.annotate("", xy=(x, 0.05), xytext=(x, 0.6),
                         arrowprops=dict(arrowstyle="-|>", color=ROT, lw=1))
        ax0.plot([0, l], [0.6, 0.6], color=ROT, lw=1)
        ax0.text(l / 2, 0.7, "q", color=ROT, ha="center", fontsize=9)
    ax0.set_ylim(-0.8, 1.4)
    ax0.axis("off")
    # Momentenverlauf
    x, M = p["x"], [m / 1000 for m in p["M"]]
    ax1.fill_between(x, M, color=BLAU, alpha=0.25)
    ax1.plot(x, M, color=BLAU)
    ax1.set_ylabel("M in N·m", fontsize=8)
    ax1.invert_yaxis()
    ax1.grid(alpha=0.3)
    ax1.set_title("Biegemomentenverlauf", fontsize=9, loc="left")
    # Biegelinie
    w = [-v for v in p["w"]]
    ax2.plot(x, w, color=ROT, lw=2)
    ax2.axhline(0, color="black", lw=0.8)
    i = max(range(len(w)), key=lambda k: abs(w[k]))
    ax2.plot(x[i], w[i], "o", color=ROT)
    ax2.annotate(f"f = {abs(w[i]):.3g} mm", (x[i], w[i]), textcoords="offset points",
                 xytext=(5, -12), fontsize=8)
    ax2.set_ylabel("w in mm", fontsize=8)
    ax2.set_xlabel("x in mm", fontsize=8)
    ax2.grid(alpha=0.3)
    ax2.set_title("Biegelinie", fontsize=9, loc="left")
    for ax in (ax1, ax2):
        ax.tick_params(labelsize=7)


def _knickung(p, fig):
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(p["lams"], p["linie"], color=BLAU, lw=2, label="Knickspannungslinie")
    ax.plot(p["lams"], p["euler"], color=GRAU, lw=1, ls="--", label="Euler-Hyperbel")
    ax.axvline(p["lam0"], color=GRUEN, ls=":", label=f"λ0 = {p['lam0']:.0f}")
    ax.axhline(p["Re"], color=GRAU, lw=0.8, ls="-.", label="Re")
    ax.plot(p["lam"], p["sK"], "o", color=ROT, ms=8, label=f"Stab: λ = {p['lam']:.1f}")
    ax.set_ylim(0, p["Re"] * 1.4)
    ax.set_xlabel("Schlankheitsgrad λ")
    ax.set_ylabel("σ_K in N/mm²")
    ax.set_title("Knickspannungsdiagramm", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    # kleine Skizze des Eulerfalls
    ins = fig.add_axes([0.80, 0.42, 0.14, 0.3])
    _eulerfall_skizze(ins, p["fall"])


def _eulerfall_skizze(ax, fall):
    ax.axis("off")
    ax.set_xlim(-1, 1)
    ax.set_ylim(-0.3, 2.4)
    import numpy as np
    y = np.linspace(0, 2, 50)
    if fall == 1:
        x = 0.5 * (1 - np.cos(np.pi * y / 4))
    elif fall == 2:
        x = 0.4 * np.sin(np.pi * y / 2)
    elif fall == 3:
        x = 0.35 * np.sin(np.pi * y / 2) * (1 - y / 2.6)
    else:
        x = 0.3 * (1 - np.cos(np.pi * y))
    ax.plot(x, y, color=BLAU, lw=2)
    ax.plot([0, 0], [0, 2], color=GRAU, lw=0.8, ls="--")
    ax.add_patch(Rectangle((-0.4, -0.15), 0.8, 0.15, color=GRAU))
    if fall == 4:
        ax.add_patch(Rectangle((-0.4, 2), 0.8, 0.15, color=GRAU))
    elif fall in (2, 3):
        ax.plot([0], [2], "o", color=GRAU)
    ax.annotate("", xy=(x[-1], 2.0), xytext=(x[-1], 2.4), arrowprops=dict(arrowstyle="-|>", color=ROT))
    ax.set_title(f"Fall {fall}", fontsize=8)


def _querschnitt(p, fig):
    ax = fig.add_subplot(1, 1, 1)
    umriss = p["umriss"]
    if umriss:
        aussen = umriss[0]
        ax.add_patch(Polygon(aussen, closed=True, facecolor=BLAU, alpha=0.35, edgecolor=BLAU, lw=2))
        for innen in umriss[1:]:
            ax.add_patch(Polygon(innen, closed=True, facecolor="white", edgecolor=BLAU, lw=2))
        xs = [pt[0] for poly in umriss for pt in poly]
        ys = [pt[1] for poly in umriss for pt in poly]
        r = max(max(map(abs, xs)), max(map(abs, ys))) * 1.25
        ax.set_xlim(-r, r)
        ax.set_ylim(-r, r)
        ax.axhline(0, color=ROT, lw=0.8, ls="-.")
        ax.axvline(0, color=ROT, lw=0.8, ls="-.")
        ax.text(r * 0.92, r * 0.03, "y", color=ROT)
        ax.text(r * 0.03, r * 0.9, "z", color=ROT)
    ax.set_aspect("equal")
    ax.set_title(p.get("titel", ""), fontsize=9)
    ax.tick_params(labelsize=7)


def _stab(p, fig):
    ax = fig.add_subplot(1, 1, 1)
    l = p["l"]
    ax.add_patch(Rectangle((0, -0.2), l, 0.4, facecolor=BLAU, alpha=0.4, edgecolor=BLAU))
    ax.add_patch(Rectangle((-0.04 * l, -0.6), 0.04 * l, 1.2, color=GRAU))
    zug = p["F"] >= 0
    start, ende = (l, l * 1.2) if zug else (l * 1.2, l)
    ax.annotate("", xy=(ende, 0), xytext=(start, 0), arrowprops=dict(arrowstyle="-|>", color=ROT, lw=2))
    ax.text(l * 1.1, 0.3, f"F = {abs(p['F']):.4g} N ({'Zug' if zug else 'Druck'})", ha="center", fontsize=9)
    ax.text(l / 2, -0.5, f"l = {l:.4g} mm,  Δl = {p['dl']:.3g} mm", ha="center", fontsize=9)
    ax.set_xlim(-0.1 * l, 1.3 * l)
    ax.set_ylim(-1, 1)
    ax.axis("off")


def _pressung(p, fig):
    ax = fig.add_subplot(1, 1, 1)
    farben = [ROT if p["p"] > p["p_zul"] else GRUEN, GRAU]
    ax.barh(["p vorhanden", "p zulässig"], [p["p"], p["p_zul"]], color=farben)
    ax.set_xlabel("N/mm²")
    ax.set_title("Flächenpressung", fontsize=10)
    ax.grid(alpha=0.3, axis="x")


def _mohr(p, fig):
    ax = fig.add_subplot(1, 1, 1)
    m, R = p["m"], p["R"]
    ax.add_patch(Circle((m, 0), R, fill=False, color=BLAU, lw=2))
    ax.plot([p["sx"], p["sy"]], [p["tau"], -p["tau"]], "o-", color=ROT)
    ax.plot([m - R, m + R], [0, 0], "s", color=GRUEN)
    ax.text(m + R, 0, "  σ1", va="bottom", color=GRUEN)
    ax.text(m - R, 0, "σ2  ", va="bottom", ha="right", color=GRUEN)
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(0, color="black", lw=0.8)
    lim = abs(m) + R + 1
    ax.set_xlim(min(-1, m - R) - 0.1 * lim, max(1, m + R) + 0.1 * lim)
    ax.set_ylim(-R * 1.3 - 1, R * 1.3 + 1)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("σ in N/mm²")
    ax.set_ylabel("τ in N/mm²")
    ax.set_title("Mohrscher Spannungskreis", fontsize=10)
    ax.grid(alpha=0.3)


def _balken(p, fig):
    ax = fig.add_subplot(1, 1, 1)
    namen = list(p["werte"].keys())
    werte = list(p["werte"].values())
    g = p.get("grenze")
    farben = []
    for n, v in zip(namen, werte):
        if g is not None and ("zul" in n or "grenz" in n):
            farben.append(GRAU)
        elif g is not None and v > g:
            farben.append(ROT)
        else:
            farben.append(BLAU)
    ax.bar(namen, werte, color=farben)
    if g is not None:
        ax.axhline(g, color=GRUEN, ls="--", lw=1.2)
    for i, v in enumerate(werte):
        ax.text(i, v, f"{v:.4g}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel(p.get("einheit", ""))
    ax.set_title(p.get("titel", ""), fontsize=10)
    ax.grid(alpha=0.3, axis="y")


def _torsion(p, fig):
    ax = fig.add_subplot(1, 2, 1)
    D, d = p["D"], p["d"] or 0
    ax.add_patch(Circle((0, 0), D / 2, facecolor=BLAU, alpha=0.35, edgecolor=BLAU, lw=2))
    if d:
        ax.add_patch(Circle((0, 0), d / 2, facecolor="white", edgecolor=BLAU, lw=2))
    ax.add_patch(FancyArrowPatch((D * 0.35, -D * 0.35), (D * 0.35, D * 0.35),
                                 connectionstyle="arc3,rad=0.6", arrowstyle="-|>", mutation_scale=15,
                                 color=ROT, lw=2))
    ax.text(D * 0.62, 0, "Mt", color=ROT)
    ax.set_xlim(-D * 0.8, D * 0.8)
    ax.set_ylim(-D * 0.8, D * 0.8)
    ax.set_aspect("equal")
    ax.set_title("Querschnitt", fontsize=9)
    ax.tick_params(labelsize=7)
    ax2 = fig.add_subplot(1, 2, 2)
    r = [D / 2 * k / 50 for k in range(51)]
    t = [p["tau"] * x / (D / 2) if x >= d / 2 else 0 for x in r]
    ax2.plot(r, t, color=ROT, lw=2)
    ax2.fill_between(r, t, color=ROT, alpha=0.2)
    ax2.set_xlabel("Radius r in mm")
    ax2.set_ylabel("τ in N/mm²")
    ax2.set_title("Schubspannungsverteilung", fontsize=9)
    ax2.grid(alpha=0.3)


def _passfeder(p, fig):
    ax = fig.add_subplot(1, 1, 1)
    d, b, h, t1 = p["d"], p["b"], p["h"], p["t1"]
    R = d / 2
    ax.add_patch(Circle((0, 0), R * 1.6, facecolor="#dfe6e9", edgecolor=GRAU, lw=1.5))  # Nabe
    ax.add_patch(Circle((0, 0), R, facecolor=BLAU, alpha=0.4, edgecolor=BLAU, lw=2))   # Welle
    ax.add_patch(Rectangle((-b / 2, R - t1), b, h, facecolor="#f39c12", edgecolor="black", lw=1.2))
    ax.text(0, R - t1 + h + R * 0.1, f"Passfeder {b:g}×{h:g}", ha="center", fontsize=9)
    ax.text(0, 0, f"Ø{d:g}", ha="center", va="center", fontsize=9)
    lim = R * 1.8
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Wellen-Naben-Verbindung", fontsize=10)
