// Prüft die Lerninhalte auf Vollständigkeit und Konsistenz.
const test = require("node:test");
const assert = require("node:assert/strict");
const E = require("../js/inhalt-englisch.js");
const K = require("../js/inhalt-kommunikation.js");

test("Englisch: jede Lektion ist vollständig", () => {
  const ids = new Set();
  const woerter = new Set();
  assert.ok(E.lektionen.length >= 10);
  for (const l of E.lektionen) {
    assert.ok(!ids.has(l.id), "doppelte ID " + l.id); ids.add(l.id);
    assert.ok(l.woerter.length >= 10, l.id);
    for (const w of l.woerter) {
      assert.equal(w.length, 4, l.id + ": " + w[0]);
      assert.ok(!woerter.has(w[0]), "doppeltes Wort " + w[0]); woerter.add(w[0]);
    }
    for (const g of l.lueckentexte) {
      assert.equal((g.satz.match(/___/g) || []).length, 1, g.satz);
      assert.ok(g.optionen.includes(g.loesung), g.satz);
      assert.equal(new Set(g.optionen).size, g.optionen.length, g.satz);
    }
    for (const s of l.saetze) assert.ok(s.en.split(" ").length >= 3 && s.de, s.en);
    for (const f of l.fragen) assert.ok(f.richtig >= 0 && f.richtig < f.optionen.length && f.erklaerung, f.frage);
  }
});

test("Kommunikation: Quiz-Typen existieren, Szenarien haben je eine beste Antwort", () => {
  const namen = new Set(K.fragetechniken.map((f) => f.name));
  for (const q of K.fragequiz) assert.ok(namen.has(q.typ), q.typ);
  for (const s of K.szenarien) {
    assert.ok(s.schritte.length >= 2 && s.modell.schritte.length >= 3 && s.tipps.length, s.id);
    for (const schritt of s.schritte) {
      assert.ok(schritt.optionen.some((o) => o.punkte === 2), s.id + ": " + schritt.text);
      for (const o of schritt.optionen) assert.ok(o.feedback && [0, 1, 2].includes(o.punkte));
    }
  }
  for (const u of K.zuhoeren.uebungen) assert.ok(u.optionen.some((o) => o.gut === 2));
  assert.ok(K.tipps.length >= 7);
});
