// Ausführen mit:  node --test tests/
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../js/logik.js");

test("Kopfrechnen: Aufgaben sind korrekt und ganzzahlig", () => {
  const r = L.rng(42);
  for (let stufe = 0; stufe < L.STUFEN.length; stufe++) {
    for (const op of ["+", "-", "*", "/", "mix"]) {
      for (let i = 0; i < 300; i++) {
        const a = L.aufgabe(op, stufe, r);
        const erwartet = { "+": a.a + a.b, "-": a.a - a.b, "*": a.a * a.b, "/": a.a / a.b }[a.op];
        assert.equal(a.ergebnis, erwartet, a.text);
        assert.ok(Number.isInteger(a.ergebnis), a.text);
        assert.ok(a.ergebnis >= 0, a.text);
        if (a.op === "/") assert.ok(a.b >= 2);
      }
    }
  }
});

test("Kopfrechnen: Stufe Leicht bleibt im kleinen Zahlenraum", () => {
  const r = L.rng(1);
  for (let i = 0; i < 200; i++) {
    const a = L.aufgabe("+", 0, r);
    assert.ok(a.a <= 10 && a.b <= 10);
  }
  assert.throws(() => L.aufgabe("%", 0, r));
});

test("Punkte: schneller gibt mehr", () => {
  assert.ok(L.mathePunkte(2, 2) > L.mathePunkte(2, 7));
  assert.ok(L.mathePunkte(4, 5) > L.mathePunkte(0, 5));
  assert.equal(L.mathePunkte(0, 20), 5);
});

test("Leitner: Fächer und Fälligkeit", () => {
  const jetzt = new Date(2026, 10, 20, 15, 0).getTime();
  const heute = L.tagesanfang(jetzt);
  let k = L.neueKarte("hello", jetzt);
  assert.equal(L.faellige({ hello: k }, jetzt).length, 1);
  k = L.bewerten(k, 2, jetzt);            // gut -> Fach 1, morgen
  assert.equal(k.fach, 1);
  assert.equal(k.faellig, heute + L.TAG);
  assert.equal(L.faellige({ hello: k }, jetzt).length, 0);
  k = L.bewerten(k, 3, jetzt);            // leicht -> Fach 3, 7 Tage
  assert.equal(k.fach, 3);
  assert.equal(k.faellig, heute + 7 * L.TAG);
  k = L.bewerten(k, 1, jetzt);            // schwer -> Fach bleibt
  assert.equal(k.fach, 3);
  k = L.bewerten(k, 0, jetzt);            // nochmal -> zurück, heute fällig
  assert.equal(k.fach, 0);
  assert.equal(k.faellig, heute);
  assert.equal(k.falsch, 1);
  assert.equal(k.richtig, 3);
  for (let i = 0; i < 10; i++) k = L.bewerten(k, 3, jetzt);
  assert.equal(k.fach, L.INTERVALLE.length - 1);
});

test("Antworten: Normalisierung, Alternativen, Tippfehler", () => {
  assert.equal(L.pruefeAntwort("The House", "house"), "richtig");
  assert.equal(L.pruefeAntwort("to go", "go"), "richtig");
  assert.equal(L.pruefeAntwort("autumn", "autumn/fall"), "richtig");
  assert.equal(L.pruefeAntwort("fall", "autumn/fall"), "richtig");
  assert.equal(L.pruefeAntwort("breakfst", "breakfast"), "fast");
  assert.equal(L.pruefeAntwort("dog", "cat"), "falsch");
  assert.equal(L.pruefeAntwort("", "cat"), "falsch");
  assert.equal(L.pruefeAntwort("I’m fine!", "I'm fine"), "richtig");
});

test("Satzbau", () => {
  const s = "Where is the station?";
  const w = L.woerter(s);
  assert.deepEqual(w, ["Where", "is", "the", "station?"]);
  assert.ok(L.satzRichtig(w, s));
  assert.ok(!L.satzRichtig(["is", "Where", "the", "station?"], s));
});

test("Level-Berechnung", () => {
  assert.equal(L.level(0).level, 1);
  assert.equal(L.level(99).level, 1);
  assert.equal(L.level(100).level, 2);
  assert.equal(L.level(300).level, 3);
  const l = L.level(450);
  assert.equal(l.level, 3);
  assert.equal(l.imLevel, 150);
  assert.equal(l.bisNaechstes, 300);
});

test("Serie (Tage in Folge)", () => {
  const tag1 = new Date(2026, 10, 18, 9).getTime();
  let s = L.serieAktualisieren({}, tag1);
  assert.equal(s.tage, 1);
  s = L.serieAktualisieren(s, tag1 + 3600e3);          // gleicher Tag
  assert.equal(s.tage, 1);
  s = L.serieAktualisieren(s, tag1 + L.TAG);           // nächster Tag
  assert.equal(s.tage, 2);
  assert.equal(L.serieAnzeige(s, tag1 + 2 * L.TAG), 2);  // gestern gelernt -> zählt noch
  assert.equal(L.serieAnzeige(s, tag1 + 3 * L.TAG), 0);  // Lücke
  s = L.serieAktualisieren(s, tag1 + 3 * L.TAG);
  assert.equal(s.tage, 1);
  assert.equal(s.rekord, 2);
});

test("Mischen ist eine Permutation", () => {
  const a = [1, 2, 3, 4, 5, 6, 7, 8];
  const m = L.mischen(a, L.rng(7));
  assert.deepEqual([...m].sort((x, y) => x - y), a);
  assert.deepEqual(a, [1, 2, 3, 4, 5, 6, 7, 8]);
});
