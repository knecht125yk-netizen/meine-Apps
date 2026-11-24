import os

import pytest
from lxml import etree

from kb.daten import Beleg, Datenbank, Position
from kb import erechnung as er


@pytest.fixture
def db():
    d = Datenbank(":memory:")
    d.einstellungen_speichern({
        "firma_name": "Holzwerkstatt Muster", "inhaber": "Erika Muster", "strasse": "Werkstattweg 3",
        "plz": "12345", "ort": "Musterstadt", "telefon": "0123 456789", "email": "info@example.de",
        "steuernummer": "12/345/67890", "iban": "DE02 1203 0000 0000 2020 51", "bic": "BYLADEM1001",
        "bank": "Musterbank"})
    return d


@pytest.fixture
def rechnung(db):
    k = db.kunde_speichern({"name": "Beispiel GmbH", "strasse": "Hauptstr. 1", "plz": "54321",
                            "ort": "Beispielort", "email": "rechnung@beispiel.de"})
    return db.beleg_speichern(Beleg("rechnung", datum="2026-11-20", kunde_id=k, betreff="Reparatur",
                                    positionen=[Position("Arbeitszeit", 2.5, "Std.", 4500, "Montage"),
                                                Position("Scharnier", 3, "Stk.", 333),
                                                Position("Anfahrt", 1, "pauschal", 2500)]))


def _ns(xml):
    return etree.fromstring(xml)


def test_xml_inhalt_und_summen(db, rechnung):
    xml = er.cii_xml(db, rechnung, xrechnung=True)
    r = _ns(xml)
    n = er.NS
    assert r.find("rsm:ExchangedDocument/ram:ID", n).text == "RE-2026-0001"
    assert r.find(".//ram:GuidelineSpecifiedDocumentContextParameter/ram:ID", n).text == er.PROFIL_XRECHNUNG
    sm = r.find(".//ram:SpecifiedTradeSettlementHeaderMonetarySummation", n)
    assert sm.find("ram:GrandTotalAmount", n).text == "147.49"     # 112,50 + 9,99 + 25,00
    assert sm.find("ram:TaxTotalAmount", n).text == "0.00"
    assert r.find(".//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax/ram:CategoryCode", n).text == "E"
    assert "§ 19 UStG" in r.find(".//ram:ExemptionReason", n).text
    einheiten = [q.get("unitCode") for q in r.findall(".//ram:BilledQuantity", n)]
    assert einheiten == ["HUR", "H87", "LS"]
    assert r.find(".//ram:IBANID", n).text == "DE02120300000000202051"
    assert r.find(".//ram:BuyerReference", n).text == "K0001"
    # Zeilensummen ergeben die Gesamtsumme
    zeilen = [float(x.text) for x in r.findall(".//ram:SpecifiedTradeSettlementLineMonetarySummation/"
                                               "ram:LineTotalAmount", n)]
    assert round(sum(zeilen), 2) == 147.49


def test_xsd_gueltig(db, rechnung):
    er.xml_pruefen(er.cii_xml(db, rechnung, xrechnung=False))
    er.xml_pruefen(er.cii_xml(db, rechnung, xrechnung=True))


def test_schematron_en16931(db, rechnung):
    """Offizielle EN16931-Geschäftsregeln (Schematron) – nur wenn saxonche installiert ist."""
    saxonche = pytest.importorskip("saxonche")
    import facturx
    xslt = os.path.join(os.path.dirname(facturx.__file__), "xsd_and_schematron", "facturx-en16931",
                        "FACTUR-X_EN16931.xslt")
    xml = er.cii_xml(db, rechnung, xrechnung=False)
    with saxonche.PySaxonProcessor(license=False) as proc:
        x = proc.new_xslt30_processor()
        exe = x.compile_stylesheet(stylesheet_file=xslt)
        doc = proc.parse_xml(xml_text=xml.decode("utf-8"))
        svrl = exe.transform_to_string(xdm_node=doc)
    fehler = etree.fromstring(svrl.encode()).findall(".//{http://purl.oclc.org/dsdl/svrl}failed-assert")
    texte = [f.findtext("{http://purl.oclc.org/dsdl/svrl}text").strip() for f in fehler
             if f.get("flag", "fatal") != "warning"]
    assert texte == []


def test_zugferd_pdf_und_wieder_einlesen(db, rechnung, tmp_path):
    p = tmp_path / "re.pdf"
    er.zugferd_pdf(db, rechnung, str(p))
    data = p.read_bytes()
    assert data[:5] == b"%PDF-"
    e = er.eingang_lesen(data)
    assert e.nummer == "RE-2026-0001"
    assert e.verkaeufer == "Holzwerkstatt Muster"
    assert e.zahlbetrag_cent == 14749
    assert len(e.positionen) == 3


def test_xrechnung_datei_einlesen(db, rechnung, tmp_path):
    p = tmp_path / "re.xml"
    er.xrechnung_speichern(db, rechnung, str(p))
    e = er.eingang_lesen(p.read_bytes())
    assert e.datum == "2026-11-20" and e.faellig == "2026-12-04"
    assert e.iban == "DE02120300000000202051"


def test_ubl_einlesen():
    ubl = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cbc:ID>2026-77</cbc:ID><cbc:IssueDate>2026-10-01</cbc:IssueDate><cbc:DueDate>2026-10-15</cbc:DueDate>
 <cac:AccountingSupplierParty><cac:Party><cac:PostalAddress><cbc:StreetName>Weg 1</cbc:StreetName>
 <cbc:CityName>Köln</cbc:CityName><cbc:PostalZone>50667</cbc:PostalZone></cac:PostalAddress>
 <cac:PartyLegalEntity><cbc:RegistrationName>Lieferant AG</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party>
 </cac:AccountingSupplierParty>
 <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">19.00</cbc:TaxAmount></cac:TaxTotal>
 <cac:LegalMonetaryTotal><cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
 <cbc:TaxInclusiveAmount currencyID="EUR">119.00</cbc:TaxInclusiveAmount>
 <cbc:PayableAmount currencyID="EUR">119.00</cbc:PayableAmount></cac:LegalMonetaryTotal>
 <cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="H87">2</cbc:InvoicedQuantity>
 <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
 <cac:Item><cbc:Name>Schrauben</cbc:Name></cac:Item><cac:Price><cbc:PriceAmount currencyID="EUR">50.00</cbc:PriceAmount></cac:Price>
 </cac:InvoiceLine></Invoice>""".encode("utf-8")
    e = er.eingang_lesen(ubl)
    assert (e.verkaeufer, e.zahlbetrag_cent, e.steuer_cent) == ("Lieferant AG", 11900, 1900)
    assert e.verkaeufer_adresse == "Weg 1, 50667 Köln"
    assert e.positionen[0]["bezeichnung"] == "Schrauben"


def test_pflichtangaben(db, rechnung):
    assert er.pflichtangaben_pruefen(db, rechnung) == []
    db.einstellungen_speichern({"email": "", "steuernummer": ""})
    fehlt = er.pflichtangaben_pruefen(db, rechnung)
    assert any("E-Mail" in f for f in fehlt) and any("Steuernummer" in f for f in fehlt)


def test_unsinnige_datei():
    with pytest.raises(ValueError):
        er.eingang_lesen(b"%PDF-1.4 kaputt")
    with pytest.raises(ValueError):
        er.eingang_lesen(b"<foo/>")
