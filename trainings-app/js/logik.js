/* Reine Logik der Trainings-App (ohne DOM) – im Browser als window.Logik, in Node per require(). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Logik = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Zufall                                                               */
  /* ------------------------------------------------------------------ */
  function rng(seed) {
    // Mulberry32 – reproduzierbar für Tests; ohne Seed Math.random
    if (seed === undefined) return Math.random;
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function zufallInt(r, min, max) { return Math.floor(r() * (max - min + 1)) + min; }
  function mischen(arr, r) {
    r = r || Math.random;
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(r() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }
  function waehle(arr, r) { return arr[Math.floor((r || Math.random)() * arr.length)]; }

  /* ------------------------------------------------------------------ */
  /* Kopfrechnen                                                          */
  /* ------------------------------------------------------------------ */
  const STUFEN = [
    { name: "Leicht", add: [1, 10], mul: [1, 10], mulB: [1, 5] },
    { name: "Mittel", add: [5, 50], mul: [2, 10], mulB: [2, 10] },
    { name: "Fortgeschritten", add: [10, 100], mul: [2, 12], mulB: [2, 12] },
    { name: "Schwer", add: [50, 500], mul: [11, 30], mulB: [2, 12] },
    { name: "Profi", add: [100, 1000], mul: [12, 99], mulB: [3, 19] },
  ];
  const ZEICHEN = { "+": "+", "-": "−", "*": "×", "/": "÷" };

  function aufgabe(op, stufe, r) {
    r = r || Math.random;
    const s = STUFEN[Math.max(0, Math.min(STUFEN.length - 1, stufe))];
    if (op === "mix") op = waehle(["+", "-", "*", "/"], r);
    let a, b, ergebnis;
    switch (op) {
      case "+":
        a = zufallInt(r, s.add[0], s.add[1]); b = zufallInt(r, s.add[0], s.add[1]); ergebnis = a + b; break;
      case "-":
        a = zufallInt(r, s.add[0], s.add[1]); b = zufallInt(r, s.add[0], s.add[1]);
        if (b > a) [a, b] = [b, a];          // keine negativen Ergebnisse
        ergebnis = a - b; break;
      case "*":
        a = zufallInt(r, s.mul[0], s.mul[1]); b = zufallInt(r, s.mulB[0], s.mulB[1]);
        if (r() < 0.5) [a, b] = [b, a];
        ergebnis = a * b; break;
      case "/":
        b = zufallInt(r, Math.max(2, s.mulB[0]), s.mulB[1]);
        ergebnis = zufallInt(r, s.mul[0], s.mul[1]);
        a = b * ergebnis; break;          // immer ganzzahlig teilbar
      default:
        throw new Error("Unbekannte Rechenart: " + op);
    }
    return { a: a, b: b, op: op, text: a + " " + ZEICHEN[op] + " " + b, ergebnis: ergebnis };
  }

  /** Punkte für eine richtige Antwort: schneller und schwerer = mehr. */
  function mathePunkte(stufe, sekunden) {
    const basis = 5 + stufe * 3;
    const bonus = Math.max(0, Math.round((8 - sekunden) * 1.5));
    return basis + bonus;
  }

  /* ------------------------------------------------------------------ */
  /* Karteikarten – Leitner-System mit 6 Fächern                          */
  /* ------------------------------------------------------------------ */
  const INTERVALLE = [0, 1, 3, 7, 16, 35]; // Tage je Fach
  const TAG = 86400000;

  function tagesanfang(ms) { const d = new Date(ms); d.setHours(0, 0, 0, 0); return d.getTime(); }

  function neueKarte(id, jetzt) { return { id: id, fach: 0, faellig: tagesanfang(jetzt), richtig: 0, falsch: 0 }; }

  /**
   * Bewertung: 0 = nochmal, 1 = schwer, 2 = gut, 3 = leicht.
   * nochmal -> Fach 0 (heute erneut), schwer -> Fach bleibt (min. 1 Tag),
   * gut -> +1 Fach, leicht -> +2 Fächer.
   */
  function bewerten(karte, note, jetzt) {
    const k = Object.assign({}, karte);
    const heute = tagesanfang(jetzt);
    if (note === 0) { k.fach = 0; k.falsch++; k.faellig = heute; return k; }
    k.richtig++;
    if (note === 2) k.fach = Math.min(INTERVALLE.length - 1, k.fach + 1);
    if (note === 3) k.fach = Math.min(INTERVALLE.length - 1, k.fach + 2);
    const tage = Math.max(1, INTERVALLE[k.fach]);
    k.faellig = heute + tage * TAG;
    return k;
  }

  function faellige(karten, jetzt) {
    const t = jetzt;
    return Object.values(karten).filter(function (k) { return k.faellig <= t; })
      .sort(function (x, y) { return x.fach - y.fach || x.faellig - y.faellig; });
  }

  /* ------------------------------------------------------------------ */
  /* Antworten vergleichen                                               */
  /* ------------------------------------------------------------------ */
  function normalisieren(s) {
    return String(s).toLowerCase()
      .replace(/[’`´]/g, "'")
      .replace(/^(to |the |a |an )/, "")
      .replace(/[.,!?;:"()]/g, "")
      .replace(/\s+/g, " ").trim();
  }

  /** Vergleicht Eingabe mit Lösung (Alternativen mit "/" getrennt). Liefert "richtig", "fast" oder "falsch". */
  function pruefeAntwort(eingabe, loesung) {
    const e = normalisieren(eingabe);
    if (!e) return "falsch";
    const varianten = String(loesung).split("/").map(normalisieren);
    if (varianten.indexOf(e) >= 0) return "richtig";
    for (const v of varianten) if (v.length > 4 && levenshtein(e, v) <= 1) return "fast";
    return "falsch";
  }

  function levenshtein(a, b) {
    const m = a.length, n = b.length;
    let prev = Array.from({ length: n + 1 }, function (_, j) { return j; });
    for (let i = 1; i <= m; i++) {
      const cur = [i];
      for (let j = 1; j <= n; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
      prev = cur;
    }
    return prev[n];
  }

  /** Satzbau: Satz in Wörter zerlegen (Satzzeichen bleiben am Wort). */
  function woerter(satz) { return satz.split(/\s+/).filter(Boolean); }

  function satzRichtig(gewaehlt, satz) {
    return normalisieren(gewaehlt.join(" ")) === normalisieren(satz);
  }

  /* ------------------------------------------------------------------ */
  /* XP, Level, Serie                                                     */
  /* ------------------------------------------------------------------ */
  function level(xp) {
    // Level n braucht insgesamt 50 * n * (n + 1) XP  (100, 300, 600, 1000 …)
    let n = 0;
    while (50 * (n + 1) * (n + 2) <= xp) n++;
    const start = 50 * n * (n + 1), ziel = 50 * (n + 1) * (n + 2);
    return { level: n + 1, imLevel: xp - start, bisNaechstes: ziel - start, anteil: (xp - start) / (ziel - start) };
  }

  function datumSchluessel(ms) {
    const d = new Date(ms);
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  /** Serie aktualisieren, wenn heute gelernt wurde. */
  function serieAktualisieren(serie, jetzt) {
    const heute = datumSchluessel(jetzt);
    const gestern = datumSchluessel(jetzt - TAG);
    const s = Object.assign({ tage: 0, letzter: "", rekord: 0 }, serie);
    if (s.letzter === heute) return s;
    s.tage = s.letzter === gestern ? s.tage + 1 : 1;
    s.letzter = heute;
    s.rekord = Math.max(s.rekord, s.tage);
    return s;
  }

  /** Aktuelle Serie zur Anzeige (0, wenn gestern und heute nicht gelernt). */
  function serieAnzeige(serie, jetzt) {
    if (!serie || !serie.letzter) return 0;
    const heute = datumSchluessel(jetzt), gestern = datumSchluessel(jetzt - TAG);
    return serie.letzter === heute || serie.letzter === gestern ? serie.tage : 0;
  }

  return {
    rng: rng, mischen: mischen, waehle: waehle, zufallInt: zufallInt,
    STUFEN: STUFEN, ZEICHEN: ZEICHEN, aufgabe: aufgabe, mathePunkte: mathePunkte,
    INTERVALLE: INTERVALLE, TAG: TAG, tagesanfang: tagesanfang, neueKarte: neueKarte, bewerten: bewerten,
    faellige: faellige, normalisieren: normalisieren, pruefeAntwort: pruefeAntwort, levenshtein: levenshtein,
    woerter: woerter, satzRichtig: satzRichtig, level: level, datumSchluessel: datumSchluessel,
    serieAktualisieren: serieAktualisieren, serieAnzeige: serieAnzeige,
  };
});
