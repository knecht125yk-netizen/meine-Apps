/* Trainings-App – Oberfläche (Vanilla JS, ohne Abhängigkeiten). */
(function () {
  "use strict";
  const L = window.Logik, E = window.ENGLISCH, K = window.KOMMUNIKATION;
  const SPEICHER = "trainings-app-v1";
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const jetzt = () => Date.now();
  const inhalt = $("#inhalt");

  /* ================================================================== */
  /* Zustand                                                              */
  /* ================================================================== */
  function standard() {
    return {
      xp: 0, xpTage: {}, serie: {}, tagesziel: 50,
      mathe: { verlauf: [], best: {}, proOp: {}, einstellungen: { op: "mix", stufe: 1, modus: "zehn" }, gesamtRichtig: 0 },
      englisch: { karten: {}, lektionen: {}, wiederholt: 0, richtung: "de-en" },
      komm: { szenarien: {}, quiz: 0, zuhoeren: 0, gesehen: {} },
      erfolge: {},
      einstellungen: { ton: true, stimme: "en-GB" },
    };
  }
  function tiefMischen(ziel, quelle) {
    for (const k in quelle) {
      if (quelle[k] && typeof quelle[k] === "object" && !Array.isArray(quelle[k]) && ziel[k] && typeof ziel[k] === "object") tiefMischen(ziel[k], quelle[k]);
      else ziel[k] = quelle[k];
    }
    return ziel;
  }
  let S;
  try { S = tiefMischen(standard(), JSON.parse(localStorage.getItem(SPEICHER) || "{}")); } catch (e) { S = standard(); }
  function speichern() { try { localStorage.setItem(SPEICHER, JSON.stringify(S)); } catch (e) { /* privat-modus */ } kopfAktualisieren(); }

  function xpGeben(n, grund) {
    if (!n) return;
    const altLevel = L.level(S.xp).level;
    S.xp += n;
    const tag = L.datumSchluessel(jetzt());
    const vorher = S.xpTage[tag] || 0;
    S.xpTage[tag] = vorher + n;
    S.serie = L.serieAktualisieren(S.serie, jetzt());
    if (vorher < S.tagesziel && S.xpTage[tag] >= S.tagesziel) { toast("🎯 Tagesziel erreicht!"); konfetti(); }
    const neuLevel = L.level(S.xp).level;
    if (neuLevel > altLevel) { toast("🚀 Level " + neuLevel + " erreicht!"); konfetti(); }
    erfolgePruefen();
    speichern();
  }

  /* ================================================================== */
  /* Erfolge                                                              */
  /* ================================================================== */
  const ERFOLGE = [
    { id: "start", e: "🌱", name: "Erster Schritt", test: () => S.xp > 0 },
    { id: "lektion1", e: "📗", name: "Erste Lektion", test: () => Object.keys(S.englisch.lektionen).length >= 1 },
    { id: "lektion5", e: "📚", name: "5 Lektionen", test: () => Object.keys(S.englisch.lektionen).length >= 5 },
    { id: "lektionAlle", e: "🎓", name: "Alle Lektionen", test: () => Object.keys(S.englisch.lektionen).length >= E.lektionen.length },
    { id: "karten50", e: "🗂️", name: "50 Karten wiederholt", test: () => S.englisch.wiederholt >= 50 },
    { id: "mathe100", e: "🧮", name: "100 Rechnungen", test: () => S.mathe.gesamtRichtig >= 100 },
    { id: "mathe1000", e: "🧠", name: "1000 Rechnungen", test: () => S.mathe.gesamtRichtig >= 1000 },
    { id: "perfekt", e: "💯", name: "10 von 10", test: () => S.mathe.verlauf.some((v) => v.modus === "zehn" && v.richtig === 10) },
    { id: "szenario", e: "🗣️", name: "Szenario perfekt", test: () => K.szenarien.some((s) => S.komm.szenarien[s.id] === s.schritte.length * 2) },
    { id: "szenarienAlle", e: "🏆", name: "Alle Szenarien", test: () => K.szenarien.every((s) => S.komm.szenarien[s.id] !== undefined) },
    { id: "serie3", e: "🔥", name: "3 Tage in Folge", test: () => (S.serie.rekord || 0) >= 3 },
    { id: "serie7", e: "⚡", name: "7 Tage in Folge", test: () => (S.serie.rekord || 0) >= 7 },
    { id: "serie30", e: "👑", name: "30 Tage in Folge", test: () => (S.serie.rekord || 0) >= 30 },
    { id: "level5", e: "🌟", name: "Level 5", test: () => L.level(S.xp).level >= 5 },
  ];
  function erfolgePruefen() {
    for (const e of ERFOLGE) {
      if (!S.erfolge[e.id] && e.test()) {
        S.erfolge[e.id] = L.datumSchluessel(jetzt());
        setTimeout(() => { toast(e.e + " Erfolg: " + e.name); konfetti(); }, 900);
      }
    }
  }

  /* ================================================================== */
  /* Effekte: Toast, Ton, Konfetti, Sprache                               */
  /* ================================================================== */
  let toastTimer;
  function toast(text) {
    const t = $("#toast");
    t.textContent = text;
    t.classList.add("zeigen");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("zeigen"), 2600);
  }
  let audio;
  function ton(art) {
    if (!S.einstellungen.ton) return;
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const noten = art === "gut" ? [660, 880] : art === "fertig" ? [523, 659, 784, 1046] : [220, 180];
      noten.forEach((f, i) => {
        const o = audio.createOscillator(), g = audio.createGain();
        o.type = art === "schlecht" ? "square" : "sine";
        o.frequency.value = f;
        const t0 = audio.currentTime + i * 0.09;
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.exponentialRampToValueAtTime(art === "schlecht" ? 0.05 : 0.12, t0 + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.18);
        o.connect(g).connect(audio.destination);
        o.start(t0); o.stop(t0 + 0.2);
      });
    } catch (e) { /* kein Audio */ }
  }
  function sprechen(text) {
    if (!("speechSynthesis" in window)) { toast("Sprachausgabe wird nicht unterstützt"); return; }
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = S.einstellungen.stimme;
    u.rate = 0.9;
    const stimme = speechSynthesis.getVoices().find((v) => v.lang === u.lang) || speechSynthesis.getVoices().find((v) => v.lang.startsWith("en"));
    if (stimme) u.voice = stimme;
    speechSynthesis.speak(u);
  }
  function konfetti() {
    const c = $("#konfetti"), ctx = c.getContext("2d");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    c.width = innerWidth; c.height = innerHeight;
    const farben = ["#5b4bdb", "#ff9a3d", "#1fc8a0", "#ff5e62", "#3d8bff", "#f5a524"];
    const teile = Array.from({ length: 120 }, () => ({
      x: c.width / 2, y: c.height / 3, vx: (Math.random() - 0.5) * 14, vy: Math.random() * -12 - 4,
      g: 0.35, f: farben[Math.floor(Math.random() * farben.length)], s: Math.random() * 7 + 4, r: Math.random() * 6,
    }));
    let n = 0;
    (function bild() {
      ctx.clearRect(0, 0, c.width, c.height);
      teile.forEach((t) => {
        t.vy += t.g; t.x += t.vx; t.y += t.vy; t.r += 0.1;
        ctx.save(); ctx.translate(t.x, t.y); ctx.rotate(t.r); ctx.fillStyle = t.f;
        ctx.fillRect(-t.s / 2, -t.s / 4, t.s, t.s / 2); ctx.restore();
      });
      if (++n < 110) requestAnimationFrame(bild); else ctx.clearRect(0, 0, c.width, c.height);
    })();
  }

  /* ================================================================== */
  /* Rahmen: Kopf, Navigation, Router                                     */
  /* ================================================================== */
  function kopfAktualisieren() {
    $("#chip-serie").textContent = "🔥 " + L.serieAnzeige(S.serie, jetzt());
    $("#chip-xp").textContent = "⭐ " + S.xp;
  }
  let aufraeumen = [];
  function seite(titel, html, opt) {
    aufraeumen.forEach((f) => f()); aufraeumen = [];
    $(".rueckmeldung") && $(".rueckmeldung").remove();
    $("#titel").textContent = titel;
    $("#zurueck").hidden = !(opt && opt.zurueck);
    $("#zurueck").onclick = () => { location.hash = opt.zurueck; };
    inhalt.innerHTML = html;
    window.scrollTo(0, 0);
  }
  const ROUTEN = [
    [/^\/start$/, startSeite, "start"],
    [/^\/mathe$/, matheSeite, "mathe"],
    [/^\/mathe\/spiel$/, matheSpiel, "mathe"],
    [/^\/englisch$/, englischSeite, "englisch"],
    [/^\/englisch\/lektion\/([\w-]+)$/, lektionSeite, "englisch"],
    [/^\/englisch\/ueben\/([\w-]+)$/, lektionUeben, "englisch"],
    [/^\/englisch\/karten$/, kartenSeite, "englisch"],
    [/^\/englisch\/vokabeln$/, vokabelSeite, "englisch"],
    [/^\/kommunikation$/, kommSeite, "kommunikation"],
    [/^\/komm\/smalltalk$/, smalltalkSeite, "kommunikation"],
    [/^\/komm\/fragen$/, fragenSeite, "kommunikation"],
    [/^\/komm\/fragenquiz$/, fragenQuiz, "kommunikation"],
    [/^\/komm\/zuhoeren$/, zuhoerenSeite, "kommunikation"],
    [/^\/komm\/zuhoerenuebung$/, zuhoerenUebung, "kommunikation"],
    [/^\/komm\/szenario\/([\w-]+)$/, szenarioSeite, "kommunikation"],
    [/^\/profil$/, profilSeite, "profil"],
  ];
  function route() {
    const pfad = location.hash.replace(/^#/, "") || "/start";
    for (const [re, fn, tab] of ROUTEN) {
      const m = pfad.match(re);
      if (m) {
        $$(".leiste a").forEach((a) => a.classList.toggle("aktiv", a.dataset.tab === tab));
        fn.apply(null, m.slice(1));
        kopfAktualisieren();
        return;
      }
    }
    location.hash = "#/start";
  }
  window.addEventListener("hashchange", route);

  /* Rückmeldeleiste unten (richtig/falsch) */
  function rueckmeldung(art, titel, text, weiter) {
    $(".rueckmeldung") && $(".rueckmeldung").remove();
    const d = document.createElement("div");
    d.className = "rueckmeldung " + art;
    d.innerHTML = `<div class="innen"><b style="font-size:19px">${titel}</b>${text ? `<div style="margin:4px 0 10px">${text}</div>` : "<div style='height:8px'></div>"}
      <button class="btn breit weiter ${art === "gut" ? "gruen" : art === "schlecht" ? "rot" : ""}">Weiter</button></div>`;
    document.body.appendChild(d);
    requestAnimationFrame(() => d.classList.add("zeigen"));
    const btn = $("button.weiter", d);
    const los = () => { document.removeEventListener("keydown", taste); d.remove(); weiter(); };
    const taste = (e) => { if (e.key === "Enter") { e.preventDefault(); los(); } };
    setTimeout(() => document.addEventListener("keydown", taste), 50);
    btn.onclick = los;
    btn.focus({ preventScroll: true });
  }

  /* ================================================================== */
  /* Start                                                                */
  /* ================================================================== */
  function begruessung() {
    const h = new Date().getHours();
    return h < 11 ? "Guten Morgen" : h < 17 ? "Hallo" : "Guten Abend";
  }
  function startSeite() {
    const heuteXp = S.xpTage[L.datumSchluessel(jetzt())] || 0;
    const anteil = Math.min(100, Math.round((heuteXp / S.tagesziel) * 100));
    const lv = L.level(S.xp);
    const faellig = L.faellige(S.englisch.karten, jetzt()).length;
    const tipp = K.tipps[Math.floor(jetzt() / L.TAG) % K.tipps.length];
    const serie = L.serieAnzeige(S.serie, jetzt());
    seite("Training", `
      <section class="karte hero">
        <div class="zeile">
          <div class="wachsen">
            <h2 style="margin:0">${begruessung()}! 👋</h2>
            <div class="leise">${serie ? `🔥 ${serie} ${serie === 1 ? "Tag" : "Tage"} in Folge – weiter so!` : "Starte heute deine Lernserie!"}</div>
            <div style="margin-top:12px" class="leise">Level ${lv.level} · ${lv.imLevel}/${lv.bisNaechstes} XP</div>
            <div class="balken" style="margin-top:6px"><i style="width:${Math.round(lv.anteil * 100)}%"></i></div>
          </div>
          <div class="ring" style="--p:${anteil}"><div>${heuteXp}<br><small style="font-weight:600">/${S.tagesziel} XP</small></div></div>
        </div>
      </section>
      <div class="raster">
        <a class="modul mathe" href="#/mathe"><span class="gross">🧮</span><div><b>Kopfrechnen</b><br><small>${S.mathe.gesamtRichtig} richtige Aufgaben</small></div></a>
        <a class="modul englisch" href="#/englisch"><span class="gross">🇬🇧</span><div><b>Englisch</b><br><small>${Object.keys(S.englisch.lektionen).length}/${E.lektionen.length} Lektionen</small></div></a>
        <a class="modul komm" href="#/kommunikation"><span class="gross">💬</span><div><b>Kommunikation</b><br><small>${Object.keys(S.komm.szenarien).length}/${K.szenarien.length} Szenarien</small></div></a>
      </div>
      ${faellig ? `<a class="liste-eintrag" href="#/englisch/karten"><span class="icon">🗂️</span><div class="wachsen"><b>${faellig} Karteikarten fällig</b><div class="leise">Kurz wiederholen – 2 Minuten reichen</div></div><span class="pfeil">›</span></a>` : ""}
      <a class="liste-eintrag" href="#/mathe/spiel" id="schnellstart"><span class="icon">⚡</span><div class="wachsen"><b>Schnellstart: 60-Sekunden-Kopfrechnen</b><div class="leise">Wie viele schaffst du?</div></div><span class="pfeil">›</span></a>
      <section class="karte"><div class="leise">💡 Kommunikationstipp des Tages</div><div style="margin-top:6px;font-weight:600">${esc(tipp)}</div></section>
    `);
    $("#schnellstart").onclick = (e) => { e.preventDefault(); S.mathe.einstellungen.modus = "zeit"; speichern(); location.hash = "#/mathe/spiel"; };
  }

  /* ================================================================== */
  /* Mathe                                                                */
  /* ================================================================== */
  const MODI = { zehn: "10 Aufgaben", zeit: "60 Sekunden", endlos: "Endlos" };
  const OPS = { "+": "+", "-": "−", "*": "×", "/": "÷", mix: "Mix" };
  function matheSeite() {
    const e = S.mathe.einstellungen;
    const v = S.mathe.verlauf;
    const gesamt = v.reduce((a, x) => a + x.gesamt, 0), richtig = v.reduce((a, x) => a + x.richtig, 0);
    const quote = gesamt ? Math.round((richtig / gesamt) * 100) : 0;
    const best = S.mathe.best[bestKey(e)];
    seite("Kopfrechnen", `
      <section class="karte">
        <div class="abschnitt" style="margin-top:0">Rechenart</div>
        <div class="segment" id="seg-op">${Object.entries(OPS).map(([k, t]) => `<button data-v="${k}" class="${e.op === k ? "an" : ""}">${t}</button>`).join("")}</div>
        <div class="abschnitt">Schwierigkeit</div>
        <div class="segment" id="seg-stufe">${L.STUFEN.map((s, i) => `<button data-v="${i}" class="${e.stufe === i ? "an" : ""}" title="${s.name}">${i + 1}</button>`).join("")}</div>
        <div class="leise mitte" style="margin-top:6px" id="stufe-name">${L.STUFEN[e.stufe].name}</div>
        <div class="abschnitt">Modus</div>
        <div class="segment" id="seg-modus">${Object.entries(MODI).map(([k, t]) => `<button data-v="${k}" class="${e.modus === k ? "an" : ""}">${t}</button>`).join("")}</div>
        <div class="leise mitte" style="margin-top:10px" id="rekord">${best ? "🏆 Rekord: " + best + " Punkte" : "Noch kein Rekord in dieser Kombination"}</div>
        <a class="btn breit" style="margin-top:14px;font-size:18px" href="#/mathe/spiel">Los geht's! ▶</a>
      </section>
      <div class="abschnitt">Statistik</div>
      <section class="karte">
        <div class="stat-raster"><div><b>${gesamt}</b><span class="leise">Aufgaben</span></div><div><b>${quote}%</b><span class="leise">richtig</span></div><div><b>${v.length}</b><span class="leise">Runden</span></div></div>
        ${opStatistik()}
        <div class="abschnitt">Letzte 7 Tage (richtige Aufgaben)</div>
        ${wochenDiagramm()}
      </section>
      ${bestwerte()}
    `);
    const setze = (id, key, num) => $$("#" + id + " button").forEach((b) => b.onclick = () => {
      e[key] = num ? Number(b.dataset.v) : b.dataset.v; speichern(); matheSeite();
    });
    setze("seg-op", "op"); setze("seg-stufe", "stufe", true); setze("seg-modus", "modus");
  }
  function bestKey(e) { return e.modus + "|" + e.op + "|" + e.stufe; }
  function opStatistik() {
    const zeilen = Object.entries({ "+": "Addition", "-": "Subtraktion", "*": "Multiplikation", "/": "Division" }).map(([op, name]) => {
      const p = S.mathe.proOp[op] || { r: 0, g: 0 };
      const q = p.g ? Math.round((p.r / p.g) * 100) : 0;
      return `<div style="margin:8px 0"><div class="zeile"><span class="wachsen">${name}</span><span class="leise">${p.r}/${p.g} · ${q}%</span></div>
        <div class="balken"><i style="width:${q}%;background:linear-gradient(90deg,#1fc8a0,#18a058)"></i></div></div>`;
    }).join("");
    return `<div class="abschnitt">Nach Rechenart</div>${zeilen}`;
  }
  function wochenDiagramm() {
    const tage = [];
    for (let i = 6; i >= 0; i--) {
      const k = L.datumSchluessel(jetzt() - i * L.TAG);
      const n = S.mathe.verlauf.filter((v) => v.datum === k).reduce((a, v) => a + v.richtig, 0);
      tage.push({ k, n, t: ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"][new Date(jetzt() - i * L.TAG).getDay()] });
    }
    const max = Math.max(10, ...tage.map((t) => t.n));
    const b = 100 / 7;
    return `<svg class="diagramm" viewBox="0 0 100 60" preserveAspectRatio="none" role="img" aria-label="Richtige Aufgaben der letzten 7 Tage">
      ${tage.map((t, i) => { const h = (t.n / max) * 44; return `<rect x="${i * b + 2}" y="${48 - h}" width="${b - 4}" height="${Math.max(h, 0.6)}" rx="1.5" fill="url(#g)"/>
      <text x="${i * b + b / 2}" y="57" font-size="4.5" text-anchor="middle" fill="currentColor" opacity=".6">${t.t}</text>
      ${t.n ? `<text x="${i * b + b / 2}" y="${46 - h}" font-size="4" text-anchor="middle" fill="currentColor">${t.n}</text>` : ""}`; }).join("")}
      <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff9a3d"/><stop offset="1" stop-color="#ff5e62"/></linearGradient></defs></svg>`;
  }
  function bestwerte() {
    const e = Object.entries(S.mathe.best);
    if (!e.length) return "";
    return `<div class="abschnitt">Bestwerte</div><section class="karte">${e.sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, p]) => {
      const [m, op, st] = k.split("|");
      return `<div class="zeile" style="margin:6px 0"><span class="wachsen">${MODI[m]} · ${OPS[op]} · Stufe ${Number(st) + 1}</span><b>${p}</b></div>`;
    }).join("")}</section>`;
  }

  function matheSpiel() {
    const e = S.mathe.einstellungen;
    const st = { nr: 0, richtig: 0, punkte: 0, serie: 0, eingabe: "", zeiten: [], start: jetzt(), ende: e.modus === "zeit" ? jetzt() + 60000 : 0, aktiv: true };
    let a, t0;
    seite("Kopfrechnen", `
      <section class="uebung">
        <div class="spielkopf"><span id="sp-info"></span><span id="sp-serie"></span><span id="sp-punkte">0 P</span></div>
        <div class="balken ${e.modus === "zeit" ? "zeitbalken" : ""}" style="margin-top:8px"><i id="sp-balken" style="width:0%"></i></div>
        <div class="aufgabe-gross" id="sp-aufgabe"></div>
        <div class="antwort-anzeige" id="sp-antwort">&nbsp;</div>
        <div class="tastatur" id="sp-tasten">
          ${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `<button data-t="${n}">${n}</button>`).join("")}
          <button data-t="del" aria-label="Löschen">⌫</button><button data-t="0">0</button><button data-t="ok" class="ok" aria-label="Prüfen">✓</button>
        </div>
        ${e.modus === "endlos" ? `<button class="btn zweit breit" id="sp-stop" style="margin-top:16px">Beenden</button>` : ""}
      </section>`, { zurueck: "/mathe" });
    const anz = $("#sp-antwort");
    function neu() {
      a = L.aufgabe(e.op, e.stufe);
      st.eingabe = ""; t0 = jetzt();
      $("#sp-aufgabe").textContent = a.text + " =";
      anz.className = "antwort-anzeige"; anz.innerHTML = "&nbsp;";
      info();
    }
    function info() {
      $("#sp-info").textContent = e.modus === "zehn" ? `Aufgabe ${Math.min(st.nr + 1, 10)}/10` : e.modus === "zeit" ? "" : `${st.richtig} richtig`;
      $("#sp-punkte").textContent = st.punkte + " P";
      $("#sp-serie").textContent = st.serie >= 3 ? "🔥 " + st.serie : "";
      if (e.modus === "zehn") $("#sp-balken").style.width = st.nr * 10 + "%";
    }
    function taste(t) {
      if (!st.aktiv) return;
      if (t === "del") st.eingabe = st.eingabe.slice(0, -1);
      else if (t === "ok") return pruefen();
      else if (st.eingabe.length < 7) st.eingabe += t;
      anz.textContent = st.eingabe || " ";
    }
    function pruefen() {
      if (!st.eingabe) return;
      const sek = (jetzt() - t0) / 1000;
      const ok = Number(st.eingabe) === a.ergebnis;
      const p = S.mathe.proOp[a.op] || (S.mathe.proOp[a.op] = { r: 0, g: 0 });
      p.g++;
      st.nr++;
      if (ok) {
        p.r++; st.richtig++; st.serie++; st.zeiten.push(sek);
        st.punkte += L.mathePunkte(e.stufe, sek) + (st.serie >= 5 ? 5 : 0);
        anz.className = "antwort-anzeige richtig"; ton("gut");
      } else {
        st.serie = 0; anz.className = "antwort-anzeige falsch"; anz.textContent = st.eingabe + " → " + a.ergebnis; ton("schlecht");
      }
      st.aktiv = false;
      setTimeout(() => {
        st.aktiv = true;
        if (e.modus === "zehn" && st.nr >= 10) return fertig();
        if (e.modus === "zeit" && jetzt() >= st.ende) return fertig();
        neu();
      }, ok ? 350 : 1100);
    }
    function fertig() {
      st.aktiv = false;
      clearInterval(uhr);
      const k = bestKey(e);
      const rekord = st.punkte > (S.mathe.best[k] || 0) && st.richtig > 0;
      if (rekord) S.mathe.best[k] = st.punkte;
      S.mathe.gesamtRichtig += st.richtig;
      S.mathe.verlauf.push({ datum: L.datumSchluessel(jetzt()), modus: e.modus, op: e.op, stufe: e.stufe, richtig: st.richtig, gesamt: st.nr, punkte: st.punkte });
      if (S.mathe.verlauf.length > 500) S.mathe.verlauf.splice(0, S.mathe.verlauf.length - 500);
      const xp = Math.round(st.richtig * (1 + e.stufe * 0.5)) + (rekord ? 5 : 0);
      xpGeben(xp);
      ton("fertig");
      if (rekord || (e.modus === "zehn" && st.richtig === 10)) konfetti();
      const quote = st.nr ? Math.round((st.richtig / st.nr) * 100) : 0;
      const schnitt = st.zeiten.length ? (st.zeiten.reduce((x, y) => x + y, 0) / st.zeiten.length).toFixed(1).replace(".", ",") : "–";
      seite("Ergebnis", `
        <section class="karte mitte">
          <div class="gross-emoji">${quote >= 90 ? "🏆" : quote >= 70 ? "🎉" : quote >= 50 ? "👍" : "💪"}</div>
          <h2>${quote >= 90 ? "Hervorragend!" : quote >= 70 ? "Sehr gut!" : quote >= 50 ? "Gut gemacht!" : "Dranbleiben – Übung macht den Meister!"}</h2>
          ${rekord ? `<div class="chip" style="display:inline-block;background:#fff4d6;color:#8a5a00">🏆 Neuer Rekord!</div>` : ""}
          <div class="stat-raster" style="margin-top:16px">
            <div><b>${st.richtig}/${st.nr}</b><span class="leise">richtig</span></div>
            <div><b>${schnitt} s</b><span class="leise">Ø pro Aufgabe</span></div>
            <div><b>${st.punkte}</b><span class="leise">Punkte</span></div>
          </div>
          <div class="leise" style="margin-top:12px">+${xp} XP</div>
          <div class="knopfreihe"><a class="btn zweit" href="#/mathe">Zurück</a><button class="btn" id="nochmal">Nochmal ↻</button></div>
        </section>`, { zurueck: "/mathe" });
      $("#nochmal").onclick = () => matheSpiel();
    }
    $$("#sp-tasten button").forEach((b) => b.addEventListener("click", () => taste(b.dataset.t)));
    const tastatur = (ev) => {
      if (/^[0-9]$/.test(ev.key)) taste(ev.key);
      else if (ev.key === "Backspace") taste("del");
      else if (ev.key === "Enter") { ev.preventDefault(); taste("ok"); }
    };
    document.addEventListener("keydown", tastatur);
    let uhr = 0;
    if (e.modus === "zeit") {
      uhr = setInterval(() => {
        const rest = st.ende - jetzt();
        $("#sp-balken") && ($("#sp-balken").style.width = Math.max(0, (rest / 60000) * 100) + "%");
        $("#sp-info") && ($("#sp-info").textContent = "⏱ " + Math.max(0, Math.ceil(rest / 1000)) + " s");
        if (rest <= 0 && st.aktiv) fertig();
      }, 200);
    }
    if ($("#sp-stop")) $("#sp-stop").onclick = () => (st.nr ? fertig() : (location.hash = "#/mathe"));
    aufraeumen.push(() => { document.removeEventListener("keydown", tastatur); clearInterval(uhr); });
    neu();
  }

  /* ================================================================== */
  /* Englisch                                                             */
  /* ================================================================== */
  const WORT = {};
  E.lektionen.forEach((l) => l.woerter.forEach((w) => { WORT[w[0]] = { en: w[0], de: w[1], bspEn: w[2], bspDe: w[3], lektion: l.id }; }));

  function englischSeite() {
    const faellig = L.faellige(S.englisch.karten, jetzt()).length;
    const gelernt = Object.keys(S.englisch.karten).length;
    seite("Englisch", `
      <section class="karte" style="background:var(--englisch);color:#fff">
        <div class="zeile"><div class="wachsen"><b style="font-size:19px">Karteikarten</b>
          <div style="opacity:.9">${faellig ? faellig + " Karten heute fällig" : gelernt ? "Alles wiederholt – super! ✨" : "Starte eine Lektion, um Karten zu sammeln."}</div></div>
          <span class="gross-emoji" style="font-size:44px">🗂️</span></div>
        <div class="knopfreihe"><a class="btn zweit" href="#/englisch/karten">${faellig ? "Wiederholen" : "Trotzdem üben"}</a><a class="btn zweit" href="#/englisch/vokabeln">Alle Vokabeln (${gelernt})</a></div>
      </section>
      <div class="abschnitt">Lektionen</div>
      ${E.lektionen.map((l, i) => {
        const fort = S.englisch.lektionen[l.id];
        return `<a class="liste-eintrag" href="#/englisch/lektion/${l.id}"><span class="icon">${l.emoji}</span>
          <div class="wachsen"><b>${i + 1}. ${esc(l.titel)}</b> <span class="leise">· ${l.stufe}</span>
          <div class="leise">${fort ? `✅ ${fort.durchgaenge}× geübt · beste Quote ${fort.beste}%` : esc(l.beschreibung)}</div></div><span class="pfeil">›</span></a>`;
      }).join("")}`);
  }

  function lektionSeite(id) {
    const l = E.lektionen.find((x) => x.id === id);
    if (!l) return (location.hash = "#/englisch");
    seite(l.titel, `
      <section class="karte hero"><div class="zeile"><span class="gross-emoji" style="font-size:48px">${l.emoji}</span>
        <div class="wachsen"><b style="font-size:19px">${esc(l.titel)}</b><div class="leise">${esc(l.beschreibung)}</div></div></div>
        <a class="btn breit zweit" style="margin-top:14px" href="#/englisch/ueben/${l.id}">Lektion üben ▶</a></section>
      <div class="abschnitt">Wortschatz (${l.woerter.length}) – tippe auf 🔊</div>
      ${l.woerter.map((w) => `<div class="karte" style="padding:12px 14px;margin:8px 0"><div class="zeile">
        <button class="lautsprecher" data-sag="${esc(w[0])}" aria-label="Aussprache">🔊</button>
        <div class="wachsen"><b>${esc(w[0])}</b> – ${esc(w[1])}<div class="leise"><i>${esc(w[2])}</i> · ${esc(w[3])}</div></div></div></div>`).join("")}
      <div class="abschnitt">Grammatik-Tipps</div>
      ${l.fragen.map((f) => `<div class="karte" style="padding:12px 14px;margin:8px 0"><b>${esc(f.frage)}</b><div>${esc(f.optionen[f.richtig])}</div><div class="leise">${esc(f.erklaerung)}</div></div>`).join("")}
    `, { zurueck: "/englisch" });
    $$("[data-sag]").forEach((b) => b.onclick = () => sprechen(b.dataset.sag));
  }

  /** Übungsfolge einer Lektion erzeugen. */
  function uebungenFuer(l) {
    const w = L.mischen(l.woerter);
    const andere = (richtig, feld) => L.mischen(l.woerter.filter((x) => x[feld] !== richtig).map((x) => x[feld])).slice(0, 3);
    const u = [];
    w.slice(0, 4).forEach((x) => u.push({ typ: "mc", frage: "Was bedeutet …", gross: x[0], sag: x[0], loesung: x[1], optionen: L.mischen([x[1]].concat(andere(x[1], 1))), wort: x[0] }));
    w.slice(4, 8).forEach((x) => u.push({ typ: "mc", frage: "Wie sagt man auf Englisch …", gross: x[1], loesung: x[0], optionen: L.mischen([x[0]].concat(andere(x[0], 0))), wort: x[0], sagLoesung: true }));
    w.slice(8, 11).forEach((x) => u.push({ typ: "tippen", frage: "Übersetze ins Englische", gross: x[1], loesung: x[0], wort: x[0] }));
    L.mischen(l.lueckentexte).slice(0, 3).forEach((g) => u.push({ typ: "mc", frage: "Fülle die Lücke", gross: g.satz.replace("___", "＿＿＿"), unter: g.de, loesung: g.loesung, optionen: L.mischen(g.optionen), satz: g.satz }));
    L.mischen(l.saetze).slice(0, 2).forEach((s) => u.push({ typ: "satzbau", frage: "Bilde den Satz", gross: s.de, loesung: s.en }));
    L.mischen(l.fragen).slice(0, 2).forEach((f) => u.push({ typ: "mc", frage: f.frage, loesung: f.optionen[f.richtig], optionen: L.mischen(f.optionen), erklaerung: f.erklaerung, klein: true }));
    // gemischte Reihenfolge, aber leichte Vokabelaufgaben zuerst
    return u.slice(0, 8).concat(L.mischen(u.slice(8)));
  }

  function lektionUeben(id) {
    const l = E.lektionen.find((x) => x.id === id);
    if (!l) return (location.hash = "#/englisch");
    const queue = uebungenFuer(l);
    const gesamt = queue.length;
    let erledigt = 0, fehlerfrei = 0, i = 0;
    const falschGemacht = new Set();
    function zeigen() {
      if (!queue.length) return fertig();
      const u = queue.shift();
      i++;
      const kopf = `<div class="balken"><i style="width:${(erledigt / gesamt) * 100}%"></i></div>
        <div class="leise mitte" style="margin:10px 0">${esc(u.frage)}</div>`;
      let html;
      if (u.typ === "mc") {
        html = `${kopf}<div class="frage mitte" style="${u.klein ? "font-size:19px" : "font-size:28px"}">${esc(u.gross || "")}
          ${u.sag ? ` <button class="lautsprecher" style="background:var(--bg)" data-sag="${esc(u.sag)}">🔊</button>` : ""}</div>
          ${u.unter ? `<div class="leise mitte">${esc(u.unter)}</div>` : ""}
          <div class="optionen">${u.optionen.map((o) => `<button class="option" data-o="${esc(o)}">${esc(o)}</button>`).join("")}</div>`;
      } else if (u.typ === "tippen") {
        html = `${kopf}<div class="frage mitte" style="font-size:28px">${esc(u.gross)}</div>
          <input class="eingabe" id="tipp" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="auf Englisch …">
          <button class="btn breit" id="pruefen" style="margin-top:12px">Prüfen</button>`;
      } else {
        const teile = L.mischen(L.woerter(u.loesung));
        html = `${kopf}<div class="frage mitte" style="font-size:21px">${esc(u.gross)}</div>
          <div class="woerter-ziel" id="ziel"></div>
          <div class="woerter-pool" id="pool">${teile.map((w, k) => `<button class="wort" data-k="${k}">${esc(w)}</button>`).join("")}</div>
          <button class="btn breit" id="pruefen" style="margin-top:12px" disabled>Prüfen</button>`;
      }
      seite(l.titel, `<section class="uebung">${html}</section>`, { zurueck: "/englisch/lektion/" + l.id });
      $$("[data-sag]").forEach((b) => b.onclick = () => sprechen(b.dataset.sag));
      if (u.sag) sprechen(u.sag);

      const ergebnis = (ok, fast) => {
        if (ok) { erledigt++; if (!falschGemacht.has(u)) fehlerfrei++; ton("gut"); }
        else {
          falschGemacht.add(u); ton("schlecht");
          u.fehler = (u.fehler || 0) + 1;
          if (u.fehler < 2) queue.push(u); else erledigt++;   // höchstens einmal wiederholen
        }
        if (u.wort && ok) kartenHinzu([u.wort]);
        const loesungText = esc(u.loesung) + (u.sagLoesung || u.typ !== "mc" ? ` <button class="lautsprecher" style="background:rgba(0,0,0,.08);width:32px;height:32px;font-size:14px;margin:0" data-sag2="${esc(u.loesung)}">🔊</button>` : "");
        const text = (ok ? (fast ? "Fast perfekt – achte auf die Schreibweise: " + loesungText : (u.typ === "satzbau" || u.typ === "tippen") ? loesungText : "") : "Richtig wäre: <b>" + loesungText + "</b>")
          + (u.erklaerung ? `<div style="margin-top:4px">${esc(u.erklaerung)}</div>` : "");
        rueckmeldung(ok ? "gut" : "schlecht", ok ? (fast ? "Fast! 👍" : L.waehle(["Richtig! 🎉", "Super! ✨", "Klasse! 💪", "Genau! ✅"])) : "Nicht ganz …", text, zeigen);
        $$("[data-sag2]").forEach((b) => b.onclick = () => sprechen(b.dataset.sag2));
        if (u.typ !== "mc" || u.sagLoesung) sprechen(u.loesung);
      };
      if (u.typ === "mc") {
        $$(".option").forEach((b) => b.onclick = () => {
          const ok = b.dataset.o === u.loesung;
          $$(".option").forEach((x) => { x.disabled = true; if (x.dataset.o === u.loesung) x.classList.add("richtig"); });
          if (!ok) b.classList.add("falsch");
          ergebnis(ok);
        });
      } else if (u.typ === "tippen") {
        const inp = $("#tipp");
        setTimeout(() => inp.focus(), 50);
        const pr = () => { if (!inp.value.trim()) return; const r = L.pruefeAntwort(inp.value, u.loesung); inp.disabled = true; $("#pruefen").disabled = true; ergebnis(r !== "falsch", r === "fast"); };
        $("#pruefen").onclick = pr;
        inp.onkeydown = (ev) => { if (ev.key === "Enter") { ev.preventDefault(); ev.stopPropagation(); pr(); } };
      } else {
        const gewaehlt = [];
        const ziel = $("#ziel"), btn = $("#pruefen");
        const neuZeichnen = () => {
          ziel.innerHTML = gewaehlt.map((b, k) => `<button class="wort" data-z="${k}">${esc(b.textContent)}</button>`).join("");
          $$("[data-z]", ziel).forEach((z) => z.onclick = () => { const b = gewaehlt.splice(Number(z.dataset.z), 1)[0]; b.classList.remove("weg"); neuZeichnen(); });
          btn.disabled = !gewaehlt.length;
        };
        $$("#pool .wort").forEach((b) => b.onclick = () => { if (b.classList.contains("weg")) return; b.classList.add("weg"); gewaehlt.push(b); neuZeichnen(); });
        btn.onclick = () => { btn.disabled = true; ergebnis(L.satzRichtig(gewaehlt.map((b) => b.textContent), u.loesung)); };
      }
    }
    function fertig() {
      kartenHinzu(l.woerter.map((w) => w[0]));
      const quote = Math.round((fehlerfrei / gesamt) * 100);
      const f = S.englisch.lektionen[l.id] || { durchgaenge: 0, beste: 0 };
      f.durchgaenge++; f.beste = Math.max(f.beste, quote);
      S.englisch.lektionen[l.id] = f;
      const xp = 10 + fehlerfrei * 2;
      xpGeben(xp);
      ton("fertig"); konfetti();
      const naechste = E.lektionen[E.lektionen.indexOf(l) + 1];
      seite("Lektion geschafft", `
        <section class="karte mitte"><div class="gross-emoji">${quote >= 80 ? "🏆" : "🎉"}</div>
          <h2>Lektion „${esc(l.titel)}“ geschafft!</h2>
          <div class="stat-raster" style="margin-top:12px"><div><b>${quote}%</b><span class="leise">auf Anhieb</span></div>
          <div><b>${l.woerter.length}</b><span class="leise">Wörter im Karteikasten</span></div><div><b>+${xp}</b><span class="leise">XP</span></div></div>
          <div class="knopfreihe"><a class="btn zweit" href="#/englisch">Übersicht</a>
          ${naechste ? `<a class="btn" href="#/englisch/lektion/${naechste.id}">Nächste Lektion ›</a>` : `<a class="btn" href="#/englisch/karten">Karten wiederholen</a>`}</div>
        </section>`, { zurueck: "/englisch" });
    }
    zeigen();
  }

  function kartenHinzu(woerter) {
    let neu = 0;
    woerter.forEach((w) => { if (!S.englisch.karten[w] && WORT[w]) { S.englisch.karten[w] = L.neueKarte(w, jetzt()); neu++; } });
    if (neu) speichern();
  }

  function kartenSeite() {
    let stapel = L.faellige(S.englisch.karten, jetzt());
    let zusatz = false;
    if (!stapel.length) {
      const alle = Object.values(S.englisch.karten);
      if (!alle.length) {
        seite("Karteikarten", `<section class="karte mitte"><div class="gross-emoji">🗂️</div><h2>Noch keine Karten</h2>
          <p class="leise">Mach zuerst eine Lektion – die Wörter landen dann automatisch hier im Karteikasten.</p>
          <a class="btn" href="#/englisch/lektion/${E.lektionen[0].id}">Erste Lektion starten</a></section>`, { zurueck: "/englisch" });
        return;
      }
      stapel = L.mischen(alle).slice(0, 10);
      zusatz = true;
    }
    const gesamt = stapel.length;
    let erledigt = 0;
    const deEn = S.englisch.richtung === "de-en";
    function karte() {
      if (!stapel.length) {
        xpGeben(Math.max(2, gesamt));
        ton("fertig");
        seite("Karteikarten", `<section class="karte mitte"><div class="gross-emoji">✨</div><h2>${zusatz ? "Extra-Runde geschafft!" : "Alle fälligen Karten wiederholt!"}</h2>
          <p class="leise">${gesamt} Karten · +${Math.max(2, gesamt)} XP. Die nächsten Karten werden automatisch fällig, wenn es Zeit ist.</p>
          <div class="knopfreihe"><a class="btn zweit" href="#/englisch">Übersicht</a><a class="btn" href="#/start">Start</a></div></section>`, { zurueck: "/englisch" });
        return;
      }
      const k = stapel[0];
      const w = WORT[k.id];
      if (!w) { stapel.shift(); return karte(); }
      const vorne = deEn ? w.de : w.en, hinten = deEn ? w.en : w.de;
      seite("Karteikarten", `
        <div class="zeile"><div class="wachsen balken"><i style="width:${(erledigt / gesamt) * 100}%"></i></div><span class="leise">${erledigt}/${gesamt}</span></div>
        <div class="segment" style="margin-top:12px" id="richtung"><button data-v="de-en" class="${deEn ? "an" : ""}">Deutsch → Englisch</button><button data-v="en-de" class="${!deEn ? "an" : ""}">Englisch → Deutsch</button></div>
        <div class="karteikarte" id="kk"><div class="innen">
          <div class="seite vorne">${esc(vorne)}<div style="font-size:14px;opacity:.85;margin-top:10px;font-weight:500">Tippen zum Umdrehen</div></div>
          <div class="seite hinten"><div class="wortgross">${esc(hinten)}</div>
            <div style="margin-top:10px"><i>${esc(w.bspEn)}</i></div><div class="leise">${esc(w.bspDe)}</div>
            <button class="lautsprecher" style="background:var(--bg)" id="kk-sag">🔊</button></div>
        </div></div>
        <div class="leise mitte" id="kk-hinweis">Erinnerst du dich? Dreh die Karte um.</div>
        <div class="bewertung versteckt" id="kk-bew">
          <button style="background:#e5484d" data-n="0">Nochmal</button><button style="background:#f5a524" data-n="1">Schwer</button>
          <button style="background:#18a058" data-n="2">Gut</button><button style="background:#3d8bff" data-n="3">Leicht</button></div>
        <div class="leise mitte" style="margin-top:8px">Fach ${k.fach + 1} von ${L.INTERVALLE.length}</div>`, { zurueck: "/englisch" });
      $$("#richtung button").forEach((b) => b.onclick = () => { S.englisch.richtung = b.dataset.v; speichern(); karte(); });
      const kk = $("#kk");
      const umdrehen = () => {
        if (kk.classList.contains("umgedreht")) return;
        kk.classList.add("umgedreht"); $("#kk-bew").classList.remove("versteckt"); $("#kk-hinweis").classList.add("versteckt");
        sprechen(w.en);
      };
      kk.onclick = (ev) => { if (ev.target.id === "kk-sag") { ev.stopPropagation(); sprechen(w.en + ". " + w.bspEn); } else umdrehen(); };
      $$("#kk-bew button").forEach((b) => b.onclick = () => {
        const note = Number(b.dataset.n);
        if (!zusatz) S.englisch.karten[k.id] = L.bewerten(k, note, jetzt());
        S.englisch.wiederholt++;
        stapel.shift();
        if (note === 0) stapel.push(zusatz ? k : S.englisch.karten[k.id]);
        else erledigt++;
        ton(note === 0 ? "schlecht" : "gut");
        speichern();
        karte();
      });
      const tasten = (ev) => {
        if (ev.key === " " || ev.key === "Enter") { ev.preventDefault(); umdrehen(); }
        else if (kk.classList.contains("umgedreht") && ["1", "2", "3", "4"].includes(ev.key)) $(`#kk-bew [data-n="${Number(ev.key) - 1}"]`).click();
      };
      document.addEventListener("keydown", tasten);
      aufraeumen.push(() => document.removeEventListener("keydown", tasten));
    }
    karte();
  }

  function vokabelSeite() {
    const karten = S.englisch.karten;
    const faecher = ["Neu", "1 Tag", "3 Tage", "1 Woche", "16 Tage", "Gemeistert"];
    seite("Alle Vokabeln", `
      <input class="eingabe" id="suche" placeholder="Suchen …" style="font-size:17px;text-align:left">
      <div id="liste">${Object.values(WORT).map((w) => {
        const k = karten[w.en];
        return `<div class="karte vok" style="padding:10px 14px;margin:8px 0" data-s="${esc((w.en + " " + w.de).toLowerCase())}"><div class="zeile">
          <button class="lautsprecher" data-sag="${esc(w.en)}">🔊</button>
          <div class="wachsen"><b>${esc(w.en)}</b> – ${esc(w.de)}</div>
          <span class="leise" style="font-size:12px">${k ? "📦 " + faecher[k.fach] : "–"}</span></div></div>`;
      }).join("")}</div>`, { zurueck: "/englisch" });
    $$("[data-sag]").forEach((b) => b.onclick = () => sprechen(b.dataset.sag));
    $("#suche").oninput = (e) => { const q = e.target.value.toLowerCase(); $$(".vok").forEach((v) => v.classList.toggle("versteckt", !v.dataset.s.includes(q))); };
  }

  /* ================================================================== */
  /* Kommunikation                                                        */
  /* ================================================================== */
  function kommSeite() {
    const tipp = K.tipps[Math.floor(jetzt() / L.TAG) % K.tipps.length];
    seite("Kommunikation", `
      <section class="karte" style="background:var(--komm);color:#fff"><div class="zeile"><span style="font-size:40px">💡</span>
        <div class="wachsen"><b>Tipp des Tages</b><div style="opacity:.95">${esc(tipp)}</div></div></div></section>
      <div class="abschnitt">Wissen & Übungen</div>
      <a class="liste-eintrag" href="#/komm/smalltalk"><span class="icon">☕</span><div class="wachsen"><b>Smalltalk & Gesprächseinstiege</b><div class="leise">Themen, Einstiegsfragen, Regeln</div></div><span class="pfeil">›</span></a>
      <a class="liste-eintrag" href="#/komm/fragen"><span class="icon">❓</span><div class="wachsen"><b>Fragetechniken</b><div class="leise">${K.fragetechniken.length} Techniken + Quiz${S.komm.quiz ? " · Bestwert " + S.komm.quiz + "%" : ""}</div></div><span class="pfeil">›</span></a>
      <a class="liste-eintrag" href="#/komm/zuhoeren"><span class="icon">👂</span><div class="wachsen"><b>Aktives Zuhören</b><div class="leise">Techniken, Stolpersteine, Übung${S.komm.zuhoeren ? " · Bestwert " + S.komm.zuhoeren + "%" : ""}</div></div><span class="pfeil">›</span></a>
      <div class="abschnitt">Übungsszenarien</div>
      ${K.szenarien.map((s) => {
        const b = S.komm.szenarien[s.id];
        const max = s.schritte.length * 2;
        return `<a class="liste-eintrag" href="#/komm/szenario/${s.id}"><span class="icon">${s.emoji}</span><div class="wachsen"><b>${esc(s.titel)}</b>
          <div class="leise">${esc(s.kategorie)}${b !== undefined ? ` · Bestwert ${b}/${max} ${b === max ? "⭐" : ""}` : ""}</div></div><span class="pfeil">›</span></a>`;
      }).join("")}`);
  }

  function smalltalkSeite() {
    const st = K.smalltalk;
    let kat = 0;
    seite("Smalltalk", `
      <section class="karte">
        <div class="segment" id="kat">${st.kategorien.map((k, i) => `<button data-i="${i}" class="${i === 0 ? "an" : ""}" title="${esc(k.titel)}">${k.emoji}</button>`).join("")}</div>
        <div class="leise mitte" id="katname" style="margin-top:8px"></div>
        <div class="einstieg" id="einstieg"></div>
        <button class="btn breit" id="neu">🎲 Neuer Einstieg</button>
      </section>
      <div class="abschnitt">Goldene Regeln</div>
      <section class="karte"><ol class="schritte">${st.regeln.map((r) => `<li style="margin:6px 0">${esc(r)}</li>`).join("")}</ol></section>
      <div class="abschnitt">Gespräch vertiefen</div>
      <section class="karte">${st.vertiefen.map((v) => `<div class="zitat">${esc(v)}</div>`).join("")}</section>
      <div class="abschnitt">Alle Einstiege</div>
      ${st.kategorien.map((k) => `<details class="akkordeon"><summary>${k.emoji} ${esc(k.titel)}</summary><div>${k.einstiege.map((e) => `<div class="zitat">${esc(e)}</div>`).join("")}</div></details>`).join("")}
      <a class="btn breit" style="margin-top:12px" href="#/komm/szenario/smalltalk_event">Smalltalk-Szenario üben ▶</a>
    `, { zurueck: "/kommunikation" });
    let letzter = "";
    const neu = () => {
      const k = st.kategorien[kat];
      $("#katname").textContent = k.titel;
      let e; do { e = L.waehle(k.einstiege); } while (e === letzter && k.einstiege.length > 1);
      letzter = e;
      $("#einstieg").textContent = "„" + e + "“";
    };
    $$("#kat button").forEach((b) => b.onclick = () => { kat = Number(b.dataset.i); $$("#kat button").forEach((x) => x.classList.toggle("an", x === b)); neu(); });
    $("#neu").onclick = () => { neu(); if (!S.komm.gesehen.smalltalk) { S.komm.gesehen.smalltalk = 1; xpGeben(2); } };
    neu();
  }

  function fragenSeite() {
    seite("Fragetechniken", `
      <a class="btn breit" href="#/komm/fragenquiz" style="margin:6px 0 8px">🎯 Quiz: Fragetyp erkennen</a>
      ${K.fragetechniken.map((f) => `<details class="akkordeon"><summary>${f.emoji} ${esc(f.name)}</summary><div>
        <p>${esc(f.erklaerung)}</p>${f.beispiele.map((b) => `<div class="zitat">„${esc(b)}“</div>`).join("")}
        <p><b>Wann?</b> ${esc(f.wann)}</p><p class="leise">⚠️ ${esc(f.achtung)}</p></div></details>`).join("")}
    `, { zurueck: "/kommunikation" });
  }

  /** Generischer Multiple-Choice-Durchlauf. fragen: [{frage, unter?, optionen:[{text, wert(0-2), feedback?}]}] */
  function mcDurchlauf(titel, zurueck, fragen, abschluss) {
    let i = 0, punkte = 0;
    const max = fragen.length * 2;
    function zeigen() {
      if (i >= fragen.length) return abschluss(punkte, max);
      const f = fragen[i];
      seite(titel, `<section class="uebung">
        <div class="balken"><i style="width:${(i / fragen.length) * 100}%"></i></div>
        <div class="leise mitte" style="margin-top:10px">${esc(f.ueber || "")}</div>
        <div class="frage mitte" style="font-size:20px">${esc(f.frage)}</div>
        ${f.unter ? `<div class="leise mitte">${esc(f.unter)}</div>` : ""}
        <div class="optionen">${f.optionen.map((o, k) => `<button class="option" data-k="${k}">${esc(o.text)}</button>`).join("")}</div></section>`, { zurueck: zurueck });
      $$(".option").forEach((b) => b.onclick = () => {
        const o = f.optionen[Number(b.dataset.k)];
        punkte += o.wert;
        $$(".option").forEach((x) => {
          x.disabled = true;
          const w = f.optionen[Number(x.dataset.k)].wert;
          if (w === 2) x.classList.add("richtig");
        });
        if (o.wert < 2) b.classList.add(o.wert === 1 ? "okay" : "falsch");
        ton(o.wert === 2 ? "gut" : "schlecht");
        i++;
        rueckmeldung(o.wert === 2 ? "gut" : o.wert === 1 ? "mittel" : "schlecht",
          o.wert === 2 ? "Sehr gut! ✅" : o.wert === 1 ? "Geht so 🤔" : "Eher ungünstig ❌", esc(o.feedback || ""), zeigen);
      });
    }
    zeigen();
  }

  function fragenQuiz() {
    const namen = K.fragetechniken.map((f) => f.name);
    const fragen = L.mischen(K.fragequiz).slice(0, 8).map((q) => {
      const falsch = L.mischen(namen.filter((n) => n !== q.typ)).slice(0, 3);
      const t = K.fragetechniken.find((f) => f.name === q.typ);
      return { ueber: "Welche Fragetechnik ist das?", frage: "„" + q.frage + "“",
        optionen: L.mischen([q.typ].concat(falsch)).map((n) => ({ text: n, wert: n === q.typ ? 2 : 0, feedback: n === q.typ ? t.erklaerung : "Richtig: " + q.typ + " – " + t.erklaerung })) };
    });
    mcDurchlauf("Fragetechniken-Quiz", "/komm/fragen", fragen, (p, max) => {
      const quote = Math.round((p / max) * 100);
      S.komm.quiz = Math.max(S.komm.quiz, quote);
      xpGeben(5 + Math.round(p / 2));
      abschlussSeite("Quiz beendet", quote, "/komm/fragen", "#/komm/fragenquiz");
    });
  }

  function zuhoerenSeite() {
    const z = K.zuhoeren;
    seite("Aktives Zuhören", `
      <section class="karte hero"><b style="font-size:18px">Zuhören ist mehr als Schweigen.</b>
        <div class="leise">Aktiv zuhören heißt: verstehen wollen, nicht antworten wollen. Es schafft Vertrauen und verhindert Missverständnisse.</div>
        <a class="btn zweit breit" style="margin-top:12px" href="#/komm/zuhoerenuebung">🎯 Übung starten</a></section>
      <div class="abschnitt">Techniken</div>
      ${z.techniken.map((t) => `<details class="akkordeon"><summary>${t.emoji} ${esc(t.name)}</summary><div><p>${esc(t.erklaerung)}</p><div class="zitat">${esc(t.beispiel)}</div></div></details>`).join("")}
      <div class="abschnitt">Stolpersteine – lieber vermeiden</div>
      <section class="karte">${z.stolpersteine.map((s) => `<div style="margin:6px 0">🚫 ${esc(s)}</div>`).join("")}</section>
    `, { zurueck: "/kommunikation" });
  }

  function zuhoerenUebung() {
    const fragen = L.mischen(K.zuhoeren.uebungen).map((u) => ({ ueber: "Dein Gegenüber sagt:", frage: "„" + u.aussage + "“", unter: "Welche Reaktion zeigt aktives Zuhören am besten?",
      optionen: L.mischen(u.optionen).map((o) => ({ text: o.text, wert: o.gut, feedback: o.feedback })) }));
    mcDurchlauf("Übung: Aktives Zuhören", "/komm/zuhoeren", fragen, (p, max) => {
      const quote = Math.round((p / max) * 100);
      S.komm.zuhoeren = Math.max(S.komm.zuhoeren, quote);
      xpGeben(5 + Math.round(p / 2));
      abschlussSeite("Übung beendet", quote, "/komm/zuhoeren", "#/komm/zuhoerenuebung");
    });
  }

  function szenarioSeite(id) {
    const s = K.szenarien.find((x) => x.id === id);
    if (!s) return (location.hash = "#/kommunikation");
    seite(s.titel, `
      <section class="karte" style="background:var(--komm);color:#fff"><div class="gross-emoji" style="font-size:44px">${s.emoji}</div>
        <b style="font-size:19px">${esc(s.titel)}</b><p style="margin:8px 0 0">${esc(s.situation)}</p></section>
      <section class="karte"><b>🎯 Ziel</b><p style="margin:6px 0">${esc(s.ziel)}</p>
        <b>🧭 ${esc(s.modell.name)}</b><ol class="schritte">${s.modell.schritte.map((x) => `<li>${esc(x)}</li>`).join("")}</ol></section>
      <button class="btn breit" id="start">Szenario durchspielen ▶</button>
      <div class="abschnitt">Tipps</div>
      <section class="karte">${s.tipps.map((t) => `<div style="margin:6px 0">✔️ ${esc(t)}</div>`).join("")}</section>
    `, { zurueck: "/kommunikation" });
    $("#start").onclick = () => {
      const fragen = s.schritte.map((st, k) => ({ ueber: `Schritt ${k + 1} von ${s.schritte.length}`, frage: st.text,
        optionen: L.mischen(st.optionen).map((o) => ({ text: o.text, wert: o.punkte, feedback: o.feedback })) }));
      mcDurchlauf(s.titel, "/komm/szenario/" + s.id, fragen, (p, max) => {
        const alt = S.komm.szenarien[s.id];
        S.komm.szenarien[s.id] = Math.max(alt === undefined ? 0 : alt, p);
        xpGeben(8 + p * 2);
        abschlussSeite(s.titel, Math.round((p / max) * 100), "/kommunikation", "#/komm/szenario/" + s.id, `${p}/${max} Punkte`,
          `<section class="karte" style="text-align:left"><b>Merke dir:</b>${s.tipps.slice(0, 3).map((t) => `<div style="margin:6px 0">✔️ ${esc(t)}</div>`).join("")}</section>`);
      });
    };
  }

  function abschlussSeite(titel, quote, zurueck, nochmal, zusatz, extraHtml) {
    ton("fertig");
    if (quote >= 80) konfetti();
    seite(titel, `<section class="karte mitte"><div class="gross-emoji">${quote >= 90 ? "🏆" : quote >= 70 ? "🎉" : quote >= 50 ? "👍" : "💪"}</div>
      <h2>${quote >= 90 ? "Hervorragend!" : quote >= 70 ? "Sehr gut!" : quote >= 50 ? "Gut gemacht!" : "Übung macht den Meister!"}</h2>
      <div style="font-size:34px;font-weight:800">${quote}%</div>${zusatz ? `<div class="leise">${zusatz}</div>` : ""}
      <div class="knopfreihe"><a class="btn zweit" href="#${zurueck}">Zurück</a><a class="btn" href="${nochmal}" id="nochmal">Nochmal ↻</a></div></section>${extraHtml || ""}`, { zurueck: zurueck });
    $("#nochmal").onclick = (e) => { if (location.hash === nochmal) { e.preventDefault(); route(); } };
  }

  /* ================================================================== */
  /* Profil & Einstellungen                                               */
  /* ================================================================== */
  function profilSeite() {
    const lv = L.level(S.xp);
    const tage = Object.keys(S.xpTage).length;
    seite("Profil", `
      <section class="karte hero"><div class="zeile"><span class="gross-emoji" style="font-size:50px">🧑‍🎓</span><div class="wachsen">
        <b style="font-size:20px">Level ${lv.level}</b><div class="leise">${S.xp} XP gesamt · noch ${lv.bisNaechstes - lv.imLevel} XP bis Level ${lv.level + 1}</div>
        <div class="balken" style="margin-top:8px"><i style="width:${Math.round(lv.anteil * 100)}%"></i></div></div></div></section>
      <section class="karte"><div class="stat-raster">
        <div><b>🔥 ${L.serieAnzeige(S.serie, jetzt())}</b><span class="leise">Serie</span></div>
        <div><b>${S.serie.rekord || 0}</b><span class="leise">Rekord-Serie</span></div>
        <div><b>${tage}</b><span class="leise">Lerntage</span></div></div></section>
      <div class="abschnitt">Erfolge (${Object.keys(S.erfolge).length}/${ERFOLGE.length})</div>
      <section class="karte"><div class="erfolge">${ERFOLGE.map((e) => `<div class="erfolg ${S.erfolge[e.id] ? "" : "zu"}"><span class="e">${e.e}</span>${esc(e.name)}</div>`).join("")}</div></section>
      <div class="abschnitt">Einstellungen</div>
      <section class="karte">
        <div class="leise">Tagesziel</div>
        <div class="segment" id="ziel">${[20, 50, 100, 200].map((z) => `<button data-v="${z}" class="${S.tagesziel === z ? "an" : ""}">${z} XP</button>`).join("")}</div>
        <div class="leise" style="margin-top:12px">Englische Aussprache</div>
        <div class="segment" id="stimme"><button data-v="en-GB" class="${S.einstellungen.stimme === "en-GB" ? "an" : ""}">🇬🇧 Britisch</button><button data-v="en-US" class="${S.einstellungen.stimme === "en-US" ? "an" : ""}">🇺🇸 Amerikanisch</button></div>
        <div class="leise" style="margin-top:12px">Töne</div>
        <div class="segment" id="ton"><button data-v="1" class="${S.einstellungen.ton ? "an" : ""}">🔊 An</button><button data-v="0" class="${!S.einstellungen.ton ? "an" : ""}">🔇 Aus</button></div>
      </section>
      <div class="abschnitt">Daten</div>
      <section class="karte">
        <p class="leise" style="margin-top:0">Dein Fortschritt wird nur auf diesem Gerät gespeichert. Mit Export/Import kannst du ihn sichern oder auf ein anderes Gerät übertragen.</p>
        <div class="knopfreihe"><button class="btn zweit" id="export">⬇️ Exportieren</button><button class="btn zweit" id="import">⬆️ Importieren</button></div>
        <input type="file" id="datei" accept="application/json,.json">
        <button class="btn rot breit" id="reset" style="margin-top:12px">Fortschritt zurücksetzen</button>
      </section>
      <section class="karte"><b>📱 Als App installieren</b>
        <p class="leise" style="margin-bottom:0"><b>iPhone:</b> In Safari öffnen → Teilen-Symbol → „Zum Home-Bildschirm“.<br>
        <b>PC (Chrome/Edge):</b> Install-Symbol in der Adressleiste → „Installieren“.<br>Danach funktioniert die App auch offline.</p></section>
    `);
    $$("#ziel button").forEach((b) => b.onclick = () => { S.tagesziel = Number(b.dataset.v); speichern(); profilSeite(); });
    $$("#stimme button").forEach((b) => b.onclick = () => { S.einstellungen.stimme = b.dataset.v; speichern(); profilSeite(); sprechen("Hello! Nice to meet you."); });
    $$("#ton button").forEach((b) => b.onclick = () => { S.einstellungen.ton = b.dataset.v === "1"; speichern(); profilSeite(); ton("gut"); });
    $("#export").onclick = () => {
      const blob = new Blob([JSON.stringify(S, null, 1)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "trainings-app-fortschritt-" + L.datumSchluessel(jetzt()) + ".json";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    };
    $("#import").onclick = () => $("#datei").click();
    $("#datei").onchange = (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const r = new FileReader();
      r.onload = () => {
        try {
          const d = JSON.parse(r.result);
          if (typeof d !== "object" || d === null || typeof d.xp !== "number") throw new Error();
          if (!confirm("Aktuellen Fortschritt durch die importierte Datei ersetzen?")) return;
          S = tiefMischen(standard(), d); speichern(); toast("✅ Fortschritt importiert"); profilSeite();
        } catch (err) { toast("⚠️ Datei ist keine gültige Sicherung"); }
      };
      r.readAsText(f);
    };
    $("#reset").onclick = () => {
      if (confirm("Wirklich den gesamten Fortschritt löschen? Das kann nicht rückgängig gemacht werden.")) {
        S = standard(); speichern(); toast("Fortschritt zurückgesetzt"); profilSeite();
      }
    };
  }

  /* ================================================================== */
  /* Start                                                                */
  /* ================================================================== */
  if ("speechSynthesis" in window) speechSynthesis.getVoices();
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
  }
  route();
})();
