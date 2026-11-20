/* Inhalte Kommunikationstraining (eigene Texte). */
(function (root) {
  const SMALLTALK = {
    regeln: [
      "Mit etwas Gemeinsamem beginnen: Ort, Anlass, Wetter, Essen – das, was ihr gerade beide erlebt.",
      "Offene Fragen stellen („Wie …?“, „Was …?“) statt Ja/Nein-Fragen.",
      "Auf Details der Antwort eingehen – daraus entsteht die nächste Frage.",
      "Etwas von sich erzählen (Selbstoffenbarung in kleinen Dosen) schafft Vertrauen.",
      "Tabu für den Einstieg: Geld, Politik, Religion, Krankheit, Lästern.",
      "Elegant beenden: „Schön, dich kennengelernt zu haben – ich hole mir noch was zu trinken.“",
    ],
    kategorien: [
      {
        titel: "Veranstaltung & Feier", emoji: "🎉",
        einstiege: [
          "Woher kennst du die Gastgeberin?",
          "Warst du letztes Jahr auch schon hier?",
          "Hast du das Buffet schon probiert? Was kannst du empfehlen?",
          "Was hat dich heute hierher gebracht?",
          "Die Musik ist super – weißt du, wer die ausgesucht hat?",
        ],
      },
      {
        titel: "Arbeit & Netzwerken", emoji: "💼",
        einstiege: [
          "Woran arbeitest du gerade – was macht dir daran am meisten Spaß?",
          "Wie bist du zu deinem Beruf gekommen?",
          "Welcher Vortrag hat dir heute bisher am besten gefallen?",
          "Was ist bei euch im Moment das größte Thema?",
          "Wie lange bist du schon im Unternehmen?",
        ],
      },
      {
        titel: "Freizeit & Hobbys", emoji: "🚴",
        einstiege: [
          "Was machst du am liebsten, wenn du mal einen freien Tag hast?",
          "Hast du in letzter Zeit eine gute Serie oder ein gutes Buch entdeckt?",
          "Planst du schon etwas fürs Wochenende?",
          "Welches Hobby würdest du gern noch anfangen?",
          "Wo bist du aufgewachsen – und was vermisst du von dort?",
        ],
      },
      {
        titel: "Reisen & Urlaub", emoji: "🌍",
        einstiege: [
          "Was war dein schönster Urlaub bisher?",
          "Gibt es ein Land, das du unbedingt noch sehen möchtest?",
          "Bist du eher Strand- oder Bergmensch?",
          "Hast du einen Geheimtipp für einen Wochenendausflug?",
        ],
      },
      {
        titel: "Alltag & Situation", emoji: "☕",
        einstiege: [
          "Ganz schön voll heute – ist das hier immer so?",
          "Den Kaffee hier finde ich richtig gut. Kommst du öfter her?",
          "Was für ein Wetter! Hast du heute noch was draußen vor?",
          "Entschuldigung, wissen Sie, ob der Zug hier pünktlich ist? … Fahren Sie öfter diese Strecke?",
        ],
      },
    ],
    vertiefen: [
      "„Wie meinst du das genau?“",
      "„Erzähl mal – wie kam es dazu?“",
      "„Was war daran das Schwierigste/Schönste?“",
      "„Das klingt spannend – was hat dich daran gereizt?“",
      "„Und wie ging es dann weiter?“",
    ],
  };

  const FRAGETECHNIKEN = [
    { name: "Offene Fragen", emoji: "🔓", erklaerung: "Beginnen mit W-Wörtern (Wie, Was, Warum, Welche …). Sie laden zum Erzählen ein und liefern Informationen.",
      beispiele: ["Wie hast du das Projekt erlebt?", "Was ist dir dabei wichtig?", "Welche Ideen hast du?"],
      wann: "Gespräch eröffnen, Informationen sammeln, Meinungen erfahren.", achtung: "„Warum“ kann wie ein Vorwurf klingen – besser „Was war der Grund …?“" },
    { name: "Geschlossene Fragen", emoji: "🔒", erklaerung: "Lassen sich mit Ja/Nein oder einem Wort beantworten.",
      beispiele: ["Bist du einverstanden?", "Passt dir Dienstag?", "Hast du den Bericht bekommen?"],
      wann: "Entscheidungen herbeiführen, Fakten prüfen, Gespräch abschließen.", achtung: "Zu viele hintereinander wirken wie ein Verhör." },
    { name: "Alternativfragen", emoji: "↔️", erklaerung: "Geben zwei (oder mehr) Möglichkeiten vor.",
      beispiele: ["Lieber Dienstag oder Donnerstag?", "Möchtest du das per Mail oder telefonisch besprechen?"],
      wann: "Entscheidungen erleichtern, Termine finden.", achtung: "Wirkt manipulativ, wenn wichtige Optionen fehlen." },
    { name: "Nachfragen / Präzisieren", emoji: "🔍", erklaerung: "Machen Unklares konkret.",
      beispiele: ["Was genau meinst du mit „bald“?", "Kannst du ein Beispiel nennen?", "Wer ist „die anderen“?"],
      wann: "Missverständnisse vermeiden, Pauschalaussagen auflösen.", achtung: "Neugierig statt prüfend klingen." },
    { name: "Spiegelnde Fragen", emoji: "🪞", erklaerung: "Geben das Gehörte (oder Gefühl) als Frage zurück.",
      beispiele: ["Du bist also enttäuscht, weil die Absprache nicht eingehalten wurde?", "Habe ich richtig verstanden, dass dir die Zeit fehlt?"],
      wann: "Verständnis sichern, Gefühle anerkennen.", achtung: "Nicht jede Aussage wiederholen – sonst wirkt es mechanisch." },
    { name: "Hypothetische Fragen", emoji: "💭", erklaerung: "Spielen eine Möglichkeit gedanklich durch („Angenommen …“).",
      beispiele: ["Angenommen, Budget spielt keine Rolle – was würdest du tun?", "Was wäre, wenn wir es einfach mal testen?"],
      wann: "Denkblockaden lösen, kreative Lösungen finden, Einwände prüfen.", achtung: "Bei sehr konkreten Problemen nicht ausweichen." },
    { name: "Skalierungsfragen", emoji: "📏", erklaerung: "Machen Einschätzungen messbar (0–10).",
      beispiele: ["Wie zufrieden bist du auf einer Skala von 1 bis 10?", "Was bräuchte es, damit aus der 6 eine 7 wird?"],
      wann: "Feedback, Coaching, Fortschritt sichtbar machen.", achtung: "Die Folgefrage („Was fehlt zur nächsten Stufe?“) ist der eigentliche Gewinn." },
    { name: "Zirkuläre Fragen", emoji: "🔄", erklaerung: "Fragen nach der Sicht einer dritten Person.",
      beispiele: ["Was würde deine Kollegin dazu sagen?", "Wie würde ein Kunde die Situation beschreiben?"],
      wann: "Perspektivwechsel anregen, festgefahrene Konflikte lockern.", achtung: "Nicht für Klatsch über Abwesende nutzen." },
    { name: "Suggestivfragen (vermeiden!)", emoji: "⚠️", erklaerung: "Legen die Antwort nahe und setzen unter Druck.",
      beispiele: ["Du willst doch sicher auch, dass das klappt, oder?", "Sie sind doch bestimmt meiner Meinung?"],
      wann: "Möglichst gar nicht – sie zerstören Vertrauen.", achtung: "Erkennen und neutral umformulieren: „Wie siehst du das?“" },
  ];

  // Quiz: Fragetyp erkennen
  const FRAGEQUIZ = [
    { frage: "Wie bist du auf die Idee gekommen?", typ: "Offene Fragen" },
    { frage: "Hast du morgen Zeit?", typ: "Geschlossene Fragen" },
    { frage: "Treffen wir uns um 10 oder um 14 Uhr?", typ: "Alternativfragen" },
    { frage: "Was genau meinst du mit „zu teuer“?", typ: "Nachfragen / Präzisieren" },
    { frage: "Du ärgerst dich also, weil du nicht informiert wurdest?", typ: "Spiegelnde Fragen" },
    { frage: "Angenommen, wir hätten doppelt so viel Zeit – was würdest du ändern?", typ: "Hypothetische Fragen" },
    { frage: "Wie sicher bist du dir auf einer Skala von 1 bis 10?", typ: "Skalierungsfragen" },
    { frage: "Was würde dein Chef sagen, wenn er das hört?", typ: "Zirkuläre Fragen" },
    { frage: "Das siehst du doch genauso, oder?", typ: "Suggestivfragen (vermeiden!)" },
    { frage: "Welche Erfahrungen hast du damit gemacht?", typ: "Offene Fragen" },
    { frage: "Ist der Bericht fertig?", typ: "Geschlossene Fragen" },
    { frage: "Was fehlt, damit du von einer 5 auf eine 7 kommst?", typ: "Skalierungsfragen" },
  ];

  const ZUHOEREN = {
    techniken: [
      { name: "Aufmerksamkeit zeigen", emoji: "👀", erklaerung: "Blickkontakt, zugewandte Haltung, Nicken, kurze Signale („mhm“, „verstehe“). Handy weg!", beispiel: "Du legst das Handy umgedreht weg und drehst dich der Person zu." },
      { name: "Paraphrasieren", emoji: "🔁", erklaerung: "Den Inhalt mit eigenen Worten zusammenfassen – zeigt Verständnis und deckt Missverständnisse auf.", beispiel: "„Du sagst also, dass das Projekt zu spät startet, weil die Freigabe fehlt.“" },
      { name: "Gefühle verbalisieren", emoji: "❤️", erklaerung: "Das wahrgenommene Gefühl benennen – vorsichtig, als Angebot.", beispiel: "„Das klingt, als wärst du ziemlich frustriert darüber.“" },
      { name: "Nachfragen", emoji: "❓", erklaerung: "Offene Fragen stellen, um tiefer zu verstehen – nicht um zu bewerten.", beispiel: "„Was war für dich der schwierigste Moment?“" },
      { name: "Zusammenfassen", emoji: "🧾", erklaerung: "Am Ende eines Abschnitts die wichtigsten Punkte bündeln.", beispiel: "„Zusammengefasst: Termin verschieben, Budget prüfen, Team informieren – richtig?“" },
      { name: "Pausen aushalten", emoji: "⏸️", erklaerung: "Nicht sofort antworten oder Lösungen anbieten. Stille gibt Raum zum Weiterdenken.", beispiel: "Nach einer Aussage 3 Sekunden warten, bevor du sprichst." },
    ],
    stolpersteine: [
      "Sofort Ratschläge geben („Du musst einfach …“)",
      "Von sich selbst erzählen („Das kenne ich, bei mir war das viel schlimmer …“)",
      "Bewerten oder herunterspielen („Ist doch nicht so schlimm.“)",
      "Unterbrechen und Sätze beenden",
      "Innerlich schon die Antwort formulieren, statt zuzuhören",
    ],
    uebungen: [
      { aussage: "Ich habe jetzt drei Wochenenden durchgearbeitet und keiner hat es überhaupt bemerkt.",
        optionen: [
          { text: "Das klingt, als würdest du dir mehr Anerkennung für deinen Einsatz wünschen.", gut: 2, feedback: "Sehr gut: Gefühl und Bedürfnis werden verbalisiert, ohne zu bewerten." },
          { text: "Du musst halt lernen, Nein zu sagen.", gut: 0, feedback: "Ein ungefragter Ratschlag – die Person fühlt sich nicht verstanden." },
          { text: "Ich arbeite auch oft am Wochenende.", gut: 0, feedback: "Lenkt auf dich selbst – das Gespräch kippt." },
        ] },
      { aussage: "Ich weiß nicht, ob ich den neuen Job annehmen soll. Das Gehalt ist besser, aber ich mag mein Team so sehr.",
        optionen: [
          { text: "Nimm ihn! Geld ist wichtig.", gut: 0, feedback: "Entscheidung abgenommen statt zugehört." },
          { text: "Du bist also hin- und hergerissen zwischen dem besseren Gehalt und deinem Team. Was wiegt für dich gerade schwerer?", gut: 2, feedback: "Paraphrasieren + offene Frage: hilft beim eigenen Sortieren." },
          { text: "Hm, schwierig.", gut: 1, feedback: "Zeigt Präsenz, bringt das Gespräch aber kaum weiter." },
        ] },
      { aussage: "Mein Vater ist im Krankenhaus und ich muss trotzdem die Präsentation morgen halten.",
        optionen: [
          { text: "Ach, das wird schon wieder.", gut: 0, feedback: "Spielt die Sorge herunter – wirkt abwertend." },
          { text: "Oh je. Das ist gerade ganz schön viel auf einmal für dich. Wie geht es dir damit?", gut: 2, feedback: "Anteilnahme + offene Frage – genau richtig." },
          { text: "Soll ich die Präsentation für dich übernehmen?", gut: 1, feedback: "Hilfsbereit, aber erst zuhören, dann Hilfe anbieten." },
        ] },
      { aussage: "Das Meeting war mal wieder total chaotisch.",
        optionen: [
          { text: "Was genau lief denn chaotisch?", gut: 2, feedback: "Präzisierende Nachfrage – du verstehst, was gemeint ist." },
          { text: "Meetings sind immer chaotisch.", gut: 0, feedback: "Verallgemeinerung, kein echtes Interesse." },
          { text: "Wer hat denn moderiert? Der kann das einfach nicht.", gut: 0, feedback: "Bewertung über Dritte – fördert Lästern statt Klärung." },
        ] },
      { aussage: "Ich habe die Prüfung bestanden!",
        optionen: [
          { text: "Glückwunsch! Du strahlst ja richtig – wie fühlt sich das an?", gut: 2, feedback: "Freude spiegeln und Raum geben – auch positive Gefühle wollen gehört werden." },
          { text: "Cool. Ich hab übrigens morgen auch eine.", gut: 0, feedback: "Thema sofort auf dich gelenkt." },
          { text: "War die nicht eh leicht?", gut: 0, feedback: "Schmälert den Erfolg." },
        ] },
      { aussage: "Ich habe das Gefühl, im Team werden meine Ideen ignoriert.",
        optionen: [
          { text: "Habe ich richtig verstanden, dass du dir mehr Gehör für deine Vorschläge wünschst? Gab es eine konkrete Situation?", gut: 2, feedback: "Spiegeln + Nachfragen nach Beispiel: sehr gutes aktives Zuhören." },
          { text: "Das bildest du dir bestimmt nur ein.", gut: 0, feedback: "Absprechen der Wahrnehmung – verletzt." },
          { text: "Dann sag deine Ideen einfach lauter.", gut: 0, feedback: "Schneller Ratschlag ohne Verständnis der Situation." },
        ] },
    ],
  };

  /* Szenarien: Schritte mit Antwortoptionen (punkte 2 = sehr gut, 1 = okay, 0 = ungünstig) */
  const SZENARIEN = [
    {
      id: "feedback", titel: "Feedback geben", emoji: "🗣️", kategorie: "Feedback",
      situation: "Dein Kollege Jonas hat in den letzten zwei Wochen dreimal Abgabetermine verpasst. Dadurch musstest du Aufgaben nachts fertigstellen. Du möchtest das ansprechen.",
      ziel: "Konstruktives Feedback geben, das die Beziehung erhält und eine Veränderung bewirkt.",
      modell: { name: "SBI-Modell (Situation – Verhalten – Wirkung)", schritte: ["Situation: Wann und wo genau?", "Verhalten: Was hast du beobachtet (ohne Bewertung)?", "Wirkung: Welche Folge hatte es für dich/das Team?", "Wunsch: Was wünschst du dir künftig?", "Dialog: Sicht des anderen erfragen."] },
      schritte: [
        { text: "Wie beginnst du das Gespräch?", optionen: [
          { text: "„Hast du kurz 10 Minuten? Ich würde gern etwas zur Zusammenarbeit an den letzten Abgaben besprechen.“", punkte: 2, feedback: "Gut: Rahmen klären, Thema ankündigen, kein Überfall." },
          { text: "„Jonas, so geht das nicht weiter!“", punkte: 0, feedback: "Angriff – Jonas geht sofort in die Verteidigung." },
          { text: "„Ähm … alles gut bei dir? … Ach, egal.“", punkte: 0, feedback: "Zu vage – das eigentliche Anliegen kommt nicht an." },
        ] },
        { text: "Jonas: „Klar, worum geht's?“ – Wie beschreibst du das Problem?", optionen: [
          { text: "„Du bist total unzuverlässig.“", punkte: 0, feedback: "Bewertung der Person statt Beschreibung des Verhaltens." },
          { text: "„Bei den Berichten am 3., 8. und 14. kamen deine Teile erst nach der Frist. Ich habe sie dann abends fertigmachen müssen und war ziemlich gestresst.“", punkte: 2, feedback: "Perfekt nach SBI: konkrete Situation, beobachtbares Verhalten, Wirkung als Ich-Botschaft." },
          { text: "„Du kommst immer zu spät mit allem.“", punkte: 0, feedback: "„Immer“ ist eine Verallgemeinerung – lädt zum Widerspruch ein." },
        ] },
        { text: "Jonas wirkt betroffen: „Oh … das war mir nicht klar.“ Was nun?", optionen: [
          { text: "„Wie hast du die letzten Wochen erlebt? Gibt es etwas, das dich ausbremst?“", punkte: 2, feedback: "Sehr gut: Sicht erfragen – vielleicht gibt es Gründe (Überlastung, unklare Prioritäten)." },
          { text: "„Jetzt weißt du's ja.“", punkte: 0, feedback: "Beendet den Dialog – keine gemeinsame Lösung." },
          { text: "„Ist nicht so schlimm, vergiss es.“", punkte: 1, feedback: "Nett gemeint, aber du nimmst dein Anliegen zurück." },
        ] },
        { text: "Jonas: „Ich hänge parallel noch im Kundenprojekt und verliere den Überblick.“ Wie schließt du ab?", optionen: [
          { text: "„Danke, dass du das sagst. Mein Wunsch: Gib mir bitte zwei Tage vorher Bescheid, wenn es eng wird – dann planen wir um. Passt das für dich?“", punkte: 2, feedback: "Klarer Wunsch + Vereinbarung + Zustimmung einholen." },
          { text: "„Das ist dein Problem.“", punkte: 0, feedback: "Abwertend und lösungslos." },
          { text: "„Na gut, dann mache ich halt weiter deine Sachen.“", punkte: 0, feedback: "Ironie/Passiv-Aggression – das Problem bleibt." },
        ] },
      ],
      tipps: ["Zeitnah und unter vier Augen.", "Beobachtung statt Interpretation („Du kamst 20 Minuten später“ statt „Du bist respektlos“).", "Ich-Botschaften nutzen.", "Mit einer konkreten Vereinbarung enden.", "Auch Positives gezielt und konkret benennen."],
    },
    {
      id: "konflikt", titel: "Konflikt lösen", emoji: "⚡", kategorie: "Konflikt",
      situation: "Deine Nachbarin beschwert sich lautstark im Treppenhaus, dass dein Fahrrad schon wieder den Flur blockiert. Du bist genervt, weil ihr Kinderwagen dort auch steht.",
      ziel: "Die Situation deeskalieren und eine faire Lösung finden.",
      modell: { name: "Deeskalation & Ich-Botschaften", schritte: ["Ruhig bleiben, durchatmen, Lautstärke senken.", "Zuhören und das Anliegen anerkennen.", "Eigene Sicht als Ich-Botschaft schildern.", "Gemeinsame Interessen finden.", "Lösung vereinbaren."] },
      schritte: [
        { text: "Nachbarin: „Ihr Fahrrad steht SCHON WIEDER im Weg! Das ist doch unmöglich!“ – Deine erste Reaktion?", optionen: [
          { text: "„Und Ihr Kinderwagen? Der steht doch auch da!“", punkte: 0, feedback: "Gegenangriff – der Streit eskaliert." },
          { text: "„Okay, ich merke, das ärgert Sie richtig. Erzählen Sie – was ist passiert?“", punkte: 2, feedback: "Deeskalierend: Gefühl anerkennen, Raum geben." },
          { text: "Wortlos das Rad wegstellen und gehen.", punkte: 1, feedback: "Löst den Moment, aber der Konflikt schwelt weiter." },
        ] },
        { text: "Nachbarin: „Ich bin mit dem Kinderwagen fast gestürzt!“ – Was sagst du?", optionen: [
          { text: "„Das tut mir leid, das wollte ich nicht. Gut, dass nichts passiert ist.“", punkte: 2, feedback: "Bedauern über die Folge äußern – wirkt Wunder, ohne Schuld komplett zu übernehmen." },
          { text: "„Dann passen Sie halt besser auf.“", punkte: 0, feedback: "Schuldzuweisung – verhärtet die Fronten." },
          { text: "„Das übertreiben Sie jetzt.“", punkte: 0, feedback: "Abwertung der Wahrnehmung." },
        ] },
        { text: "Sie wird ruhiger. Wie bringst du deine Sicht ein?", optionen: [
          { text: "„Ich habe ehrlich gesagt das Problem, dass ich keinen Platz im Keller habe. Und der Flur ist ja für uns beide eng – vielleicht finden wir eine Lösung, die für beide passt?“", punkte: 2, feedback: "Ich-Botschaft + gemeinsames Interesse: perfekt." },
          { text: "„Sie stellen Ihren Kinderwagen ja auch immer da hin.“", punkte: 0, feedback: "Vorwurf mit „immer“ – öffnet den Streit neu." },
          { text: "„Na ja, ist halt so.“", punkte: 0, feedback: "Keine Lösungsbereitschaft." },
        ] },
        { text: "Nachbarin: „Und was schlagen Sie vor?“", optionen: [
          { text: "„Wie wäre es: Ich hänge das Rad an die Wandhalterung links, und Ihr Kinderwagen bekommt die Nische rechts. Sollen wir das eine Woche testen?“", punkte: 2, feedback: "Konkreter Vorschlag + Testphase senkt die Hürde für Zustimmung." },
          { text: "„Keine Ahnung, das ist Sache der Hausverwaltung.“", punkte: 1, feedback: "Kann sinnvoll sein, wirkt aber wie Abschieben." },
          { text: "„Ich stelle es hin, wo ich will.“", punkte: 0, feedback: "Eskaliert erneut." },
        ] },
      ],
      tipps: ["Erst das Gefühl anerkennen, dann über Fakten reden.", "„Wir“-Formulierungen für gemeinsame Ziele.", "Nicht „immer/nie“ sagen.", "Lösungen als Experiment anbieten („Lass es uns eine Woche testen“).", "Bei starker Eskalation: Gespräch vertagen."],
    },
    {
      id: "verhandlung", titel: "Gehalt verhandeln", emoji: "🤝", kategorie: "Verhandlung",
      situation: "Du hast seit zwei Jahren keine Gehaltserhöhung bekommen, aber zusätzliche Verantwortung übernommen (Einarbeitung neuer Kollegen, ein Großkunde). Das Jahresgespräch mit deiner Chefin steht an.",
      ziel: "Eine Gehaltserhöhung (Ziel: +8 %) erreichen, ohne die Beziehung zu belasten.",
      modell: { name: "Harvard-Konzept", schritte: ["Menschen und Probleme getrennt behandeln.", "Auf Interessen konzentrieren, nicht auf Positionen.", "Mehrere Optionen entwickeln.", "Objektive Kriterien nutzen (Marktwert, Leistung).", "Eigene Alternative kennen (BATNA)."] },
      schritte: [
        { text: "Wie bereitest du dich vor?", optionen: [
          { text: "Erfolge mit Zahlen sammeln, Marktgehalt recherchieren, Wunschbetrag und Untergrenze festlegen.", punkte: 2, feedback: "Objektive Kriterien sind dein stärkstes Argument." },
          { text: "Spontan reingehen – ich weiß ja, was ich leiste.", punkte: 0, feedback: "Ohne Belege bleibt es bei Gefühl gegen Gefühl." },
          { text: "Kollegen fragen, was sie verdienen, und das als Argument nutzen.", punkte: 1, feedback: "Gut als Info, aber „X verdient mehr“ ist ein schwaches Argument im Gespräch." },
        ] },
        { text: "Chefin: „Was möchten Sie heute besprechen?“", optionen: [
          { text: "„Ich möchte über meine Entwicklung und mein Gehalt sprechen. Seit dem letzten Gespräch habe ich zwei neue Aufgaben übernommen …“", punkte: 2, feedback: "Klar und mit Fokus auf Leistung." },
          { text: "„Ich brauche mehr Geld, die Mieten steigen.“", punkte: 0, feedback: "Private Gründe sind kein Leistungsargument." },
          { text: "„Ach, eigentlich nichts Besonderes …“", punkte: 0, feedback: "Du verschenkst die Gelegenheit." },
        ] },
        { text: "Chefin: „Das Budget ist dieses Jahr leider knapp.“", optionen: [
          { text: "„Das verstehe ich. Welche Möglichkeiten sehen Sie – vielleicht eine gestaffelte Erhöhung oder eine Erhöhung ab Juli plus Weiterbildung?“", punkte: 2, feedback: "Interesse erkannt (Budget), Optionen entwickelt – klassisch Harvard." },
          { text: "„Dann kündige ich.“", punkte: 0, feedback: "Drohung ohne Not – beschädigt Vertrauen (und ist nur sinnvoll, wenn du es ernst meinst)." },
          { text: "„Okay, dann vielleicht nächstes Jahr.“", punkte: 0, feedback: "Zu schnell aufgegeben." },
        ] },
        { text: "Chefin: „Ich könnte 5 % ab Januar anbieten.“", optionen: [
          { text: "„Danke, das ist ein guter Schritt. Mit Blick auf die zusätzlichen Aufgaben hatte ich an 8 % gedacht. Könnten wir uns auf 6 % ab Januar und eine erneute Prüfung nach sechs Monaten einigen?“", punkte: 2, feedback: "Wertschätzung + Begründung + konkreter Kompromiss mit Zukunftsoption." },
          { text: "„Nein, 8 % oder gar nichts.“", punkte: 0, feedback: "Positionsdenken – wenig Spielraum." },
          { text: "„Okay, passt.“", punkte: 1, feedback: "Akzeptabel, aber du lässt Verhandlungsspielraum liegen." },
        ] },
      ],
      tipps: ["Erst Leistung, dann Zahl nennen.", "Eine konkrete Zahl nennen (Anker), leicht über dem Ziel.", "Schweigen nach dem Nennen der Zahl aushalten.", "Neben Geld auch andere Optionen kennen (Weiterbildung, Homeoffice, Urlaub).", "Ergebnis schriftlich festhalten."],
    },
    {
      id: "kritik", titel: "Kritik annehmen", emoji: "🛡️", kategorie: "Feedback",
      situation: "Dein Teamleiter sagt nach einer Präsentation: „Die Folien waren überladen und du hast zu schnell gesprochen.“",
      ziel: "Kritik konstruktiv aufnehmen, ohne in Rechtfertigung zu verfallen.",
      modell: { name: "Kritik annehmen in 4 Schritten", schritte: ["Zuhören bis zum Ende.", "Nachfragen und konkretisieren.", "Danken (nicht unbedingt zustimmen).", "Entscheiden, was du umsetzt."] },
      schritte: [
        { text: "Deine erste Reaktion?", optionen: [
          { text: "„Ich hatte ja auch nur zwei Tage Zeit!“", punkte: 0, feedback: "Rechtfertigung – wirkt, als würdest du nicht zuhören." },
          { text: "Kurz durchatmen: „Okay. Welche Folien meinst du besonders?“", punkte: 2, feedback: "Nachfragen macht die Kritik nutzbar." },
          { text: "„Hm.“ (beleidigt schweigen)", punkte: 0, feedback: "Signalisiert Kränkung, kein Lernen." },
        ] },
        { text: "Teamleiter: „Vor allem die Zahlenfolien – da stand zu viel Text.“", optionen: [
          { text: "„Danke, das hilft mir. Hättest du einen Tipp, wie viel auf eine Folie gehört?“", punkte: 2, feedback: "Dank + Bitte um Rat: zeigt Professionalität." },
          { text: "„Andere fanden die gut.“", punkte: 0, feedback: "Abwehr durch Gegenbeispiel." },
          { text: "„Ja, stimmt, ich bin einfach schlecht in Präsentationen.“", punkte: 0, feedback: "Abwertung der eigenen Person – Kritik betrifft das Verhalten, nicht dich." },
        ] },
        { text: "Wie schließt du ab?", optionen: [
          { text: "„Ich nehme mit: max. 3 Punkte pro Folie und langsamer sprechen. Magst du mir beim nächsten Mal wieder Feedback geben?“", punkte: 2, feedback: "Konkrete Vorsätze + Feedbackschleife." },
          { text: "„Okay, war's das?“", punkte: 0, feedback: "Wirkt abweisend." },
          { text: "„Mal sehen.“", punkte: 1, feedback: "Unverbindlich – wenig überzeugend." },
        ] },
      ],
      tipps: ["Kritik betrifft dein Verhalten, nicht deinen Wert.", "Nicht sofort rechtfertigen – erst verstehen.", "Du musst nicht allem zustimmen, aber du kannst danken.", "Bei unfairer Kritik: sachlich nach Beispielen fragen."],
    },
    {
      id: "neinsagen", titel: "Nein sagen", emoji: "✋", kategorie: "Konflikt",
      situation: "Eine Kollegin fragt dich am Freitagnachmittag, ob du ihre Präsentation für Montag noch „schnell“ überarbeiten kannst. Du hast eigentlich Pläne fürs Wochenende.",
      ziel: "Freundlich, aber klar ablehnen – ohne schlechtes Gewissen.",
      modell: { name: "Freundliches Nein", schritte: ["Verständnis zeigen.", "Klar Nein sagen (ohne lange Ausreden).", "Optional: Alternative anbieten.", "Beim Nein bleiben, wenn nachgehakt wird."] },
      schritte: [
        { text: "Kollegin: „Kannst du mir bitte helfen? Ist auch nicht viel.“", optionen: [
          { text: "„Ich verstehe, dass es eng ist. Dieses Wochenende geht es bei mir leider nicht.“", punkte: 2, feedback: "Verständnis + klares Nein – fair und eindeutig." },
          { text: "„Äh … vielleicht … mal sehen …“", punkte: 0, feedback: "Unklar – sie wird davon ausgehen, dass du hilfst." },
          { text: "„Immer kommst du in letzter Minute!“", punkte: 0, feedback: "Vorwurf statt Grenze." },
        ] },
        { text: "Kollegin: „Bitte, nur eine Stunde, du bist so gut darin!“", optionen: [
          { text: "„Danke, das freut mich. Trotzdem: nein, dieses Wochenende nicht. Ich kann dir aber Montag früh 20 Minuten Feedback geben.“", punkte: 2, feedback: "Bei der Grenze bleiben + realistische Alternative." },
          { text: "„Na gut …“ (seufzend)", punkte: 0, feedback: "Nachgegeben – und du ärgerst dich das ganze Wochenende." },
          { text: "Ausführlich erklären, warum du nicht kannst.", punkte: 1, feedback: "Zu viele Begründungen laden zum Verhandeln ein." },
        ] },
      ],
      tipps: ["Ein Nein zu einer Bitte ist kein Nein zur Person.", "Kurz begründen reicht – keine Rechtfertigungsrede.", "Bedenkzeit erbitten: „Ich sag dir in einer Stunde Bescheid.“", "Die „Broken Record“-Technik: freundlich dasselbe wiederholen."],
    },
    {
      id: "smalltalk_event", titel: "Smalltalk auf einem Event", emoji: "🥂", kategorie: "Smalltalk",
      situation: "Du bist auf einer Firmenfeier und kennst kaum jemanden. Am Stehtisch steht eine Person allein mit einem Getränk.",
      ziel: "Ein angenehmes Gespräch beginnen, vertiefen und elegant beenden.",
      modell: { name: "Smalltalk-Bogen", schritte: ["Kontakt: Blick, Lächeln, kurzer Einstieg.", "Gemeinsamkeit: Situation/Ort aufgreifen.", "Vertiefen: offene Fragen, auf Details eingehen.", "Selbst etwas erzählen.", "Freundlich verabschieden."] },
      schritte: [
        { text: "Wie steigst du ein?", optionen: [
          { text: "Lächeln: „Hi, ist hier noch Platz? Ich bin Alex aus dem Vertrieb.“", punkte: 2, feedback: "Einfach, offen, mit Namen – perfekt." },
          { text: "„Na, auch so gelangweilt?“", punkte: 0, feedback: "Negativer Einstieg – heikel auf Firmenfeiern." },
          { text: "Wortlos dazustellen und aufs Handy schauen.", punkte: 0, feedback: "Kein Kontakt entsteht." },
        ] },
        { text: "Person: „Hi, ich bin Kim, aus der IT.“ – Wie geht's weiter?", optionen: [
          { text: "„Schön! Woran arbeitet ihr gerade in der IT – ist bei euch auch so viel los vor dem Jahresende?“", punkte: 2, feedback: "Offene Frage + Bezug zur Situation." },
          { text: "„Ah, IT. Mein Laptop ist übrigens total langsam …“", punkte: 0, feedback: "Klassiker – bitte nicht. Kim ist privat hier." },
          { text: "„Cool.“", punkte: 0, feedback: "Gesprächskiller." },
        ] },
        { text: "Kim: „Wir stellen gerade auf ein neues System um – stressig, aber spannend.“", optionen: [
          { text: "„Spannend klingt gut! Was ist für dich der spannendste Teil daran?“", punkte: 2, feedback: "Auf das positive Detail eingehen und vertiefen." },
          { text: "„Das neue System wird bestimmt wieder Chaos.“", punkte: 0, feedback: "Pessimistisch und abwertend." },
          { text: "„Bei uns im Vertrieb ist auch Stress …“ und dann 5 Minuten von dir erzählen.", punkte: 1, feedback: "Etwas von sich zu erzählen ist gut – aber nicht das Gespräch übernehmen." },
        ] },
        { text: "Nach 10 Minuten möchtest du weiter. Wie beendest du das Gespräch?", optionen: [
          { text: "„Kim, schön dich kennenzulernen! Ich hole mir noch was zu essen – vielleicht sehen wir uns später noch.“", punkte: 2, feedback: "Freundlich, mit Grund und positivem Abschluss." },
          { text: "Einfach weggehen, wenn Kim kurz wegschaut.", punkte: 0, feedback: "Unhöflich." },
          { text: "„Ich muss mal …“", punkte: 1, feedback: "Geht, wirkt aber abrupt." },
        ] },
      ],
      tipps: ["Die Person, die allein steht, freut sich meist über Ansprache.", "Name wiederholen hilft beim Merken.", "Zuhören > selbst reden (ca. 60/40).", "Gemeinsamkeiten suchen.", "Positiv bleiben – keine Lästereien."],
    },
  ];

  const TIPPS = [
    "Stelle heute in jedem Gespräch mindestens eine offene Frage.",
    "Wiederhole heute einmal mit eigenen Worten, was dein Gegenüber gesagt hat.",
    "Ersetze „Ja, aber …“ durch „Ja, und …“ – und beobachte die Wirkung.",
    "Lege beim nächsten Gespräch dein Handy außer Sichtweite.",
    "Halte nach einer Frage drei Sekunden Stille aus.",
    "Benenne heute ein Gefühl: „Das klingt, als wärst du …“",
    "Mache jemandem heute ein konkretes Kompliment für ein Verhalten.",
    "Formuliere eine Kritik als Ich-Botschaft statt als Du-Botschaft.",
    "Frage heute jemanden nach seiner Meinung, bevor du deine sagst.",
    "Beende ein Gespräch bewusst freundlich mit einem Ausblick („Bis Montag!“).",
    "Merke dir heute den Namen einer neuen Person und benutze ihn.",
    "Sag einmal bewusst Nein – freundlich und ohne lange Erklärung.",
  ];

  const KOMMUNIKATION = { smalltalk: SMALLTALK, fragetechniken: FRAGETECHNIKEN, fragequiz: FRAGEQUIZ,
    zuhoeren: ZUHOEREN, szenarien: SZENARIEN, tipps: TIPPS };
  if (typeof module === "object" && module.exports) module.exports = KOMMUNIKATION;
  else root.KOMMUNIKATION = KOMMUNIKATION;
})(typeof self !== "undefined" ? self : this);
