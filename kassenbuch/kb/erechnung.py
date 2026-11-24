"""E-Rechnung nach EN 16931: XRechnung (CII-XML) und ZUGFeRD/Factur-X (PDF mit eingebettetem XML).

Kleinunternehmer (§ 19 UStG): Umsatzsteuer-Kategorie „E“ (steuerbefreit), Steuersatz 0 %,
Befreiungsgrund „Kleinunternehmer gemäß § 19 UStG“.

Außerdem: Einlesen empfangener E-Rechnungen (XRechnung CII/UBL, ZUGFeRD-PDF) zur Anzeige
und Übernahme ins Kassenbuch.
"""
from __future__ import annotations

import datetime as dt
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from lxml import etree

from .daten import Beleg, Datenbank, parse_euro

NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
PROFIL_EN16931 = "urn:cen.eu:en16931:2017"
PROFIL_XRECHNUNG = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
BEFREIUNGSGRUND = "Kleinunternehmer gemäß § 19 UStG"

# Einheiten -> UN/ECE Recommendation 20
EINHEITEN = {
    "stk": "H87", "stk.": "H87", "stück": "H87", "st.": "H87",
    "std": "HUR", "std.": "HUR", "stunde": "HUR", "stunden": "HUR", "h": "HUR",
    "pauschal": "LS", "psch.": "LS", "pausch.": "LS",
    "m": "MTR", "m²": "MTK", "qm": "MTK", "m2": "MTK", "m³": "MTQ", "kg": "KGM", "km": "KMT",
    "tag": "DAY", "tage": "DAY", "l": "LTR", "liter": "LTR", "min": "MIN", "min.": "MIN",
}


EINHEIT_TEXT = {"H87": "Stk.", "C62": "Stk.", "EA": "Stk.", "XPP": "Stk.", "HUR": "Std.", "LS": "pauschal",
                "MTR": "m", "MTK": "m²", "MTQ": "m³", "KGM": "kg", "KMT": "km", "DAY": "Tag", "LTR": "l",
                "MIN": "Min."}


def einheit_text(code: str) -> str:
    return EINHEIT_TEXT.get(code, code)


def einheit_code(e: str) -> str:
    return EINHEITEN.get((e or "").strip().lower(), "C62")  # C62 = „Einheit“


def _betrag(cent: int) -> str:
    return f"{Decimal(int(cent)) / 100:.2f}"


def _menge(m: float) -> str:
    d = Decimal(str(m)).normalize()
    return format(d, "f") if d == d.to_integral() else format(d.quantize(Decimal("0.0001")).normalize(), "f")


def _datum(iso: str) -> str:
    return iso[:10].replace("-", "")


# ---------------------------------------------------------------------------
# Prüfung der Pflichtangaben (vor dem Erzeugen, mit verständlichen Meldungen)
# ---------------------------------------------------------------------------

def pflichtangaben_pruefen(db: Datenbank, b: Beleg, xrechnung: bool = True) -> List[str]:
    """Liste fehlender Angaben (leer = alles da)."""
    e = db.einstellungen()
    k = db.kunde(b.kunde_id) if b.kunde_id else None
    fehlt = []
    if not b.ist_rechnung:
        fehlt.append("E-Rechnungen gibt es nur für Rechnungen, nicht für Angebote.")
    if b.status == "storniert":
        fehlt.append("Die Rechnung ist storniert.")
    for key, name in (("firma_name", "Firmenname"), ("strasse", "Straße (Firma)"), ("plz", "PLZ (Firma)"),
                      ("ort", "Ort (Firma)")):
        if not e.get(key, "").strip():
            fehlt.append(f"{name} fehlt (Einstellungen).")
    if not (e.get("steuernummer", "").strip() or e.get("ust_idnr", "").strip()):
        fehlt.append("Steuernummer oder USt-IdNr. fehlt (Einstellungen).")
    if xrechnung:
        if not e.get("email", "").strip():
            fehlt.append("E-Mail-Adresse der Firma fehlt (Einstellungen) – in der XRechnung Pflicht.")
        if not e.get("telefon", "").strip():
            fehlt.append("Telefonnummer der Firma fehlt (Einstellungen) – in der XRechnung Pflicht.")
        if not e.get("iban", "").strip():
            fehlt.append("IBAN fehlt (Einstellungen) – für die Zahlungsangaben nötig.")
    if not k:
        fehlt.append("Kein Kunde zugeordnet.")
    else:
        for key, name in (("name", "Name"), ("plz", "PLZ"), ("ort", "Ort")):
            if not (k[key] or "").strip():
                fehlt.append(f"{name} des Kunden fehlt.")
        if xrechnung and not (k["email"] or "").strip():
            fehlt.append("E-Mail-Adresse des Kunden fehlt – in der XRechnung Pflicht (elektronische Adresse).")
    if not b.positionen:
        fehlt.append("Keine Positionen.")
    return fehlt


# ---------------------------------------------------------------------------
# Erzeugen (UN/CEFACT CII D16B)
# ---------------------------------------------------------------------------

def _el(parent, tag, text=None, **attrib):
    pfx, name = tag.split(":")
    el = etree.SubElement(parent, f"{{{NS[pfx]}}}{name}", **attrib)
    if text is not None:
        el.text = str(text)
    return el


def _adresse(parent, plz, strasse, ort, land="DE"):
    a = _el(parent, "ram:PostalTradeAddress")
    if plz:
        _el(a, "ram:PostcodeCode", plz)
    if strasse:
        _el(a, "ram:LineOne", strasse)
    if ort:
        _el(a, "ram:CityName", ort)
    _el(a, "ram:CountryID", land or "DE")


def _strasse_trennen(adresse: str):
    """'12345 Musterstadt' -> ('12345', 'Musterstadt')"""
    m = re.match(r"^\s*(\d{4,5})\s+(.+)$", adresse or "")
    return (m.group(1), m.group(2)) if m else ("", adresse or "")


def cii_xml(db: Datenbank, b: Beleg, xrechnung: bool = False) -> bytes:
    """CII-XML der Rechnung erzeugen (EN 16931; mit xrechnung=True im XRechnung-3.0-Profil)."""
    e = db.einstellungen()
    k = db.kunde(b.kunde_id) if b.kunde_id else None
    root = etree.Element(f"{{{NS['rsm']}}}CrossIndustryInvoice", nsmap=NS)

    ctx = _el(root, "rsm:ExchangedDocumentContext")
    _el(_el(ctx, "ram:GuidelineSpecifiedDocumentContextParameter"), "ram:ID",
        PROFIL_XRECHNUNG if xrechnung else PROFIL_EN16931)

    doc = _el(root, "rsm:ExchangedDocument")
    _el(doc, "ram:ID", b.nummer)
    _el(doc, "ram:TypeCode", "380")  # Handelsrechnung
    _el(_el(doc, "ram:IssueDateTime"), "udt:DateTimeString", _datum(b.datum), format="102")
    _el(_el(doc, "ram:IncludedNote"), "ram:Content", e["kleinunternehmer_hinweis"] or BEFREIUNGSGRUND)
    if b.betreff:
        _el(_el(doc, "ram:IncludedNote"), "ram:Content", b.betreff)

    tx = _el(root, "rsm:SupplyChainTradeTransaction")

    # --- Positionen ---
    for i, p in enumerate(b.positionen, 1):
        li = _el(tx, "ram:IncludedSupplyChainTradeLineItem")
        _el(_el(li, "ram:AssociatedDocumentLineDocument"), "ram:LineID", str(i))
        prod = _el(li, "ram:SpecifiedTradeProduct")
        _el(prod, "ram:Name", p.bezeichnung)
        if p.beschreibung:
            _el(prod, "ram:Description", p.beschreibung)
        agr = _el(li, "ram:SpecifiedLineTradeAgreement")
        _el(_el(agr, "ram:NetPriceProductTradePrice"), "ram:ChargeAmount", _betrag(p.preis_cent))
        _el(_el(li, "ram:SpecifiedLineTradeDelivery"), "ram:BilledQuantity", _menge(p.menge),
            unitCode=einheit_code(p.einheit))
        st = _el(li, "ram:SpecifiedLineTradeSettlement")
        tax = _el(st, "ram:ApplicableTradeTax")
        _el(tax, "ram:TypeCode", "VAT")
        _el(tax, "ram:CategoryCode", "E")
        _el(tax, "ram:RateApplicablePercent", "0")
        _el(_el(st, "ram:SpecifiedTradeSettlementLineMonetarySummation"), "ram:LineTotalAmount",
            _betrag(p.summe_cent))

    # --- Verkäufer / Käufer ---
    agr = _el(tx, "ram:ApplicableHeaderTradeAgreement")
    kunden_nr = (k["nummer"] if k else "") or ""
    if xrechnung:
        # BT-10 Käuferreferenz ist in der XRechnung Pflicht (bei Behörden: Leitweg-ID)
        _el(agr, "ram:BuyerReference", (k["leitweg_id"] if k and "leitweg_id" in k.keys() and k["leitweg_id"]
                                        else kunden_nr or "n/a"))
    seller = _el(agr, "ram:SellerTradeParty")
    # BT-29 Verkäuferkennung: ohne USt-IdNr. (typisch bei Kleinunternehmern) verlangt EN 16931 (BR-CO-26)
    # eine Kennung des Verkäufers – hier die Steuernummer.
    if not e["ust_idnr"] and e["steuernummer"]:
        _el(seller, "ram:ID", e["steuernummer"])
    _el(seller, "ram:Name", e["firma_name"])
    if e["telefon"] or e["email"] or e["inhaber"]:
        kontakt = _el(seller, "ram:DefinedTradeContact")
        _el(kontakt, "ram:PersonName", e["inhaber"] or e["firma_name"])
        if e["telefon"]:
            _el(_el(kontakt, "ram:TelephoneUniversalCommunication"), "ram:CompleteNumber", e["telefon"])
        if e["email"]:
            _el(_el(kontakt, "ram:EmailURIUniversalCommunication"), "ram:URIID", e["email"])
    _adresse(seller, e["plz"], e["strasse"], e["ort"])
    if e["email"]:
        _el(_el(seller, "ram:URIUniversalCommunication"), "ram:URIID", e["email"], schemeID="EM")
    if e["ust_idnr"]:
        _el(_el(seller, "ram:SpecifiedTaxRegistration"), "ram:ID", e["ust_idnr"].replace(" ", ""), schemeID="VA")
    if e["steuernummer"]:
        _el(_el(seller, "ram:SpecifiedTaxRegistration"), "ram:ID", e["steuernummer"], schemeID="FC")

    buyer = _el(agr, "ram:BuyerTradeParty")
    if k:
        if k["nummer"]:
            _el(buyer, "ram:ID", k["nummer"])
        _el(buyer, "ram:Name", k["name"])
        if k["zusatz"]:
            _el(_el(buyer, "ram:DefinedTradeContact"), "ram:PersonName", k["zusatz"])
        _adresse(buyer, k["plz"], k["strasse"], k["ort"])
        if k["email"]:
            _el(_el(buyer, "ram:URIUniversalCommunication"), "ram:URIID", k["email"], schemeID="EM")
    else:
        zeilen = (b.anschrift or "").splitlines()
        _el(buyer, "ram:Name", zeilen[0] if zeilen else "Kunde")
        plz, ort = _strasse_trennen(zeilen[-1] if len(zeilen) > 1 else "")
        _adresse(buyer, plz, zeilen[1] if len(zeilen) > 2 else "", ort)

    # --- Lieferung / Leistungsdatum ---
    lief = _el(tx, "ram:ApplicableHeaderTradeDelivery")
    ev = _el(lief, "ram:ActualDeliverySupplyChainEvent")
    _el(_el(ev, "ram:OccurrenceDateTime"), "udt:DateTimeString", _datum(b.leistungsdatum or b.datum), format="102")

    # --- Abrechnung ---
    st = _el(tx, "ram:ApplicableHeaderTradeSettlement")
    _el(st, "ram:PaymentReference", b.nummer)
    _el(st, "ram:InvoiceCurrencyCode", "EUR")
    if e["iban"]:
        zahl = _el(st, "ram:SpecifiedTradeSettlementPaymentMeans")
        _el(zahl, "ram:TypeCode", "58")  # SEPA-Überweisung
        konto = _el(zahl, "ram:PayeePartyCreditorFinancialAccount")
        _el(konto, "ram:IBANID", e["iban"].replace(" ", "").upper())
        if e["firma_name"]:
            _el(konto, "ram:AccountName", e["firma_name"])
        if e["bic"]:
            _el(_el(zahl, "ram:PayeeSpecifiedCreditorFinancialInstitution"), "ram:BICID", e["bic"].replace(" ", ""))
    else:
        _el(_el(st, "ram:SpecifiedTradeSettlementPaymentMeans"), "ram:TypeCode", "1")  # nicht festgelegt
    summe = _betrag(b.summe_cent)
    tax = _el(st, "ram:ApplicableTradeTax")
    _el(tax, "ram:CalculatedAmount", "0.00")
    _el(tax, "ram:TypeCode", "VAT")
    _el(tax, "ram:ExemptionReason", BEFREIUNGSGRUND)
    _el(tax, "ram:BasisAmount", summe)
    _el(tax, "ram:CategoryCode", "E")
    _el(tax, "ram:RateApplicablePercent", "0")
    bed = _el(st, "ram:SpecifiedTradePaymentTerms")
    if b.faellig:
        _el(bed, "ram:Description", f"Zahlbar ohne Abzug bis {dt.date.fromisoformat(b.faellig):%d.%m.%Y}.")
        _el(_el(bed, "ram:DueDateDateTime"), "udt:DateTimeString", _datum(b.faellig), format="102")
    else:
        _el(bed, "ram:Description", "Zahlbar sofort ohne Abzug.")
    sm = _el(st, "ram:SpecifiedTradeSettlementHeaderMonetarySummation")
    _el(sm, "ram:LineTotalAmount", summe)
    _el(sm, "ram:TaxBasisTotalAmount", summe)
    _el(sm, "ram:TaxTotalAmount", "0.00", currencyID="EUR")
    _el(sm, "ram:GrandTotalAmount", summe)
    _el(sm, "ram:DuePayableAmount", summe)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)


def xml_pruefen(xml: bytes):
    """Gegen das offizielle Factur-X-EN16931-Schema (XSD) prüfen; wirft bei Fehlern."""
    import facturx
    facturx.xml_check_xsd(xml, flavor="factur-x", level="en16931")


def xrechnung_speichern(db: Datenbank, b: Beleg, pfad: str):
    xml = cii_xml(db, b, xrechnung=True)
    xml_pruefen(xml)
    with open(pfad, "wb") as f:
        f.write(xml)


def zugferd_pdf(db: Datenbank, b: Beleg, pfad: str):
    """Normale Rechnungs-PDF erzeugen und das EN16931-XML einbetten (ZUGFeRD 2 / Factur-X)."""
    import facturx
    from .ausgabe import beleg_pdf
    buf = io.BytesIO()
    beleg_pdf(db, b, buf)
    xml = cii_xml(db, b, xrechnung=False)
    e = db.einstellungen()
    pdf = facturx.generate_from_binary(
        buf.getvalue(), xml, flavor="factur-x", level="en16931", check_xsd=True,
        pdf_metadata={"author": e["firma_name"], "keywords": "Factur-X, ZUGFeRD, Rechnung",
                      "title": f"Rechnung {b.nummer}", "subject": f"Rechnung {b.nummer}"},
        lang="de-DE")
    with open(pfad, "wb") as f:
        f.write(pdf)


# ---------------------------------------------------------------------------
# Empfangene E-Rechnungen lesen
# ---------------------------------------------------------------------------

@dataclass
class Eingangsrechnung:
    format: str = ""
    nummer: str = ""
    datum: str = ""
    verkaeufer: str = ""
    verkaeufer_adresse: str = ""
    kaeufer: str = ""
    faellig: str = ""
    iban: str = ""
    netto_cent: int = 0
    steuer_cent: int = 0
    brutto_cent: int = 0
    zahlbetrag_cent: int = 0
    positionen: List[dict] = field(default_factory=list)


def _t(el, pfad, ns):
    r = el.find(pfad, ns)
    return (r.text or "").strip() if r is not None and r.text else ""


def _datum_iso(s: str) -> str:
    s = (s or "").strip()
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s[:10]


def _cent(s: str) -> int:
    return parse_euro(s) if s else 0


def eingang_lesen(daten: bytes) -> Eingangsrechnung:
    """XRechnung/ZUGFeRD lesen: XML (CII oder UBL) oder PDF mit eingebettetem XML."""
    if daten[:5] == b"%PDF-":
        import facturx
        try:
            _, xml = facturx.get_xml_from_pdf(daten, check_xsd=False)
        except Exception as ex:
            raise ValueError(f"Die PDF-Datei konnte nicht gelesen werden: {ex}")
        if not xml:
            raise ValueError("Diese PDF enthält keine E-Rechnung (kein eingebettetes ZUGFeRD/Factur-X-XML).")
        daten = xml
    try:
        root = etree.fromstring(daten, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    except etree.XMLSyntaxError as ex:
        raise ValueError(f"Keine gültige XML-Datei: {ex}")
    tag = etree.QName(root).localname
    r = Eingangsrechnung()
    if tag == "CrossIndustryInvoice":
        n = NS
        r.format = "XRechnung/ZUGFeRD (CII)"
        r.nummer = _t(root, "rsm:ExchangedDocument/ram:ID", n)
        r.datum = _datum_iso(_t(root, "rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString", n))
        tx = root.find("rsm:SupplyChainTradeTransaction", n)
        s = tx.find("ram:ApplicableHeaderTradeAgreement/ram:SellerTradeParty", n)
        r.verkaeufer = _t(s, "ram:Name", n)
        r.verkaeufer_adresse = ", ".join(x for x in (_t(s, "ram:PostalTradeAddress/ram:LineOne", n),
                                                     (_t(s, "ram:PostalTradeAddress/ram:PostcodeCode", n) + " " +
                                                      _t(s, "ram:PostalTradeAddress/ram:CityName", n)).strip()) if x)
        r.kaeufer = _t(tx, "ram:ApplicableHeaderTradeAgreement/ram:BuyerTradeParty/ram:Name", n)
        st = tx.find("ram:ApplicableHeaderTradeSettlement", n)
        r.faellig = _datum_iso(_t(st, "ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString", n))
        r.iban = _t(st, "ram:SpecifiedTradeSettlementPaymentMeans/ram:PayeePartyCreditorFinancialAccount/ram:IBANID", n)
        sm = st.find("ram:SpecifiedTradeSettlementHeaderMonetarySummation", n)
        r.netto_cent = _cent(_t(sm, "ram:TaxBasisTotalAmount", n))
        r.steuer_cent = _cent(_t(sm, "ram:TaxTotalAmount", n))
        r.brutto_cent = _cent(_t(sm, "ram:GrandTotalAmount", n))
        r.zahlbetrag_cent = _cent(_t(sm, "ram:DuePayableAmount", n)) or r.brutto_cent
        for li in tx.findall("ram:IncludedSupplyChainTradeLineItem", n):
            q = li.find("ram:SpecifiedLineTradeDelivery/ram:BilledQuantity", n)
            r.positionen.append({
                "bezeichnung": _t(li, "ram:SpecifiedTradeProduct/ram:Name", n),
                "menge": (q.text or "").strip() if q is not None else "",
                "einheit": q.get("unitCode", "") if q is not None else "",
                "preis": _t(li, "ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:ChargeAmount", n),
                "summe": _t(li, "ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeSettlementLineMonetarySummation/"
                               "ram:LineTotalAmount", n)})
    elif tag in ("Invoice", "CreditNote"):
        n = {"cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
             "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"}
        r.format = "XRechnung (UBL)" + (" – Gutschrift" if tag == "CreditNote" else "")
        r.nummer = _t(root, "cbc:ID", n)
        r.datum = _datum_iso(_t(root, "cbc:IssueDate", n))
        r.faellig = _datum_iso(_t(root, "cbc:DueDate", n))
        s = root.find("cac:AccountingSupplierParty/cac:Party", n)
        if s is not None:
            r.verkaeufer = _t(s, "cac:PartyLegalEntity/cbc:RegistrationName", n) or _t(s, "cac:PartyName/cbc:Name", n)
            r.verkaeufer_adresse = ", ".join(x for x in (_t(s, "cac:PostalAddress/cbc:StreetName", n),
                                                         (_t(s, "cac:PostalAddress/cbc:PostalZone", n) + " " +
                                                          _t(s, "cac:PostalAddress/cbc:CityName", n)).strip()) if x)
        c = root.find("cac:AccountingCustomerParty/cac:Party", n)
        if c is not None:
            r.kaeufer = _t(c, "cac:PartyLegalEntity/cbc:RegistrationName", n) or _t(c, "cac:PartyName/cbc:Name", n)
        r.iban = _t(root, "cac:PaymentMeans/cac:PayeeFinancialAccount/cbc:ID", n)
        lm = root.find("cac:LegalMonetaryTotal", n)
        if lm is not None:
            r.netto_cent = _cent(_t(lm, "cbc:TaxExclusiveAmount", n))
            r.brutto_cent = _cent(_t(lm, "cbc:TaxInclusiveAmount", n))
            r.zahlbetrag_cent = _cent(_t(lm, "cbc:PayableAmount", n)) or r.brutto_cent
        r.steuer_cent = _cent(_t(root, "cac:TaxTotal/cbc:TaxAmount", n))
        for li in root.findall("cac:InvoiceLine", n) + root.findall("cac:CreditNoteLine", n):
            q = li.find("cbc:InvoicedQuantity", n)
            if q is None:
                q = li.find("cbc:CreditedQuantity", n)
            r.positionen.append({
                "bezeichnung": _t(li, "cac:Item/cbc:Name", n),
                "menge": (q.text or "").strip() if q is not None else "",
                "einheit": q.get("unitCode", "") if q is not None else "",
                "preis": _t(li, "cac:Price/cbc:PriceAmount", n),
                "summe": _t(li, "cbc:LineExtensionAmount", n)})
    else:
        raise ValueError("Unbekanntes Format – erwartet wird eine XRechnung (CII/UBL) oder ZUGFeRD-Rechnung.")
    return r
