# Cigarr-briefen – strukturplan

## 1. Koncept

Fyra delar under ett tak:

1. **Nyheter** – kuraterat/sammanfattat från engelska och svenska källor
2. **Test** – recensioner av cigarrer
3. **Fakta** – statisk kunskapsbank om cigarrer och cigarrökning
4. **(ev.) Community** – kommentarer, betygssättning, nyhetsbrev

## 2. Nyheter – vad som faktiskt går att samla in

### Engelska källor (rikt utbud, aktiva, har RSS)
- **Halfwheel** – ledande branschblogg, nyheter + recensioner, har RSS
- **Cigar Aficionado** – störst, 23 000+ recensioner i databas
- **Cigar Coop** – dagliga nyheter, recensioner, podd
- **Cigar Journal** – internationellt fokus
- **Stogie Press / Stogie Review** – recensioner, har RSS (feeds.feedburner.com/TheStogieReview)
- **Cigar Snob Magazine** – varannan månad

→ Gott om material. En samlingssida ("Feedspot – Top 100 Cigar RSS Feeds") bekräftar att det finns ett etablerat ekosystem av RSS-flöden att bevaka.

**Viktigt:** Att bara skrapa/republicera RSS-innehåll rakt av är upphovsrättsligt problematiskt och tillför inget värde. Modellen bör vara: bevaka flödena → skriv egna korta sammanfattningar på svenska (och ev. engelska) med tydlig källhänvisning och länk till originalet. Det är samma modell som svenska nyhetssajter använder för internationella nyheter.

### Svenska källor (tunt, mest butiksdrivet)
- **Cigarrklubben.se / "Cigarrvärlden"** – har en faktisk redaktion som bedriver grävande journalistik om den svenska cigarrbranschen (regelefterlevnad, tillsyn). Separerad från butiksdelen. Bra källa för substantiella nyheter, men smal vinkel (branschgranskning, inte konsumentnyheter).
- **Swecigars.se ("Cigarrakademin")** – renodlad butiksblogg (produktlanseringar, historia). Bra bakgrundsmaterial, inte nyheter i journalistisk mening.
- **Cigarrspecialisten.se** – liknande butiksblogg.
- Diverse cigarrklubbar (Smålands Cigarrsällskap, Sydsvenska Cigarrsällskapet, Cigarrklubben Gustaf V m.fl.) – events och lokal aktivitet, ingen löpande nyhetsproduktion.
- Forumtrådar (Sweclockers, robsoft.nu) – community-diskussion, inte nyhetskälla.

→ Det finns **inget** etablerat svenskt nyhetsflöde för cigarrer i stil med Halfwheel. Det är faktiskt en lucka Cigarr-briefen kan fylla: översätt/sammanfatta de bästa engelska nyheterna till svenska, kombinerat med egen bevakning av den svenska scenen (butiker, klubbar, lagändringar).

### Praktisk insamlingsmetod
- RSS-aggregator (t.ex. enkel backend som pollar flödena) för intern överblick, redaktionell kuratering innan publicering
- En artikel/dag räcker för att hålla sidan levande i början
- Källhänvisning och länk alltid med (branschnorm, se Cigarrklubbens egen "kreddpolicy")

## 3. Test/recensioner – vad som är realistiskt

Två vägar, kan kombineras:

- **Egna recensioner**: kräver att köpa cigarrer (kostnad), tid att röka och skriva, och en tydlig betygsmodell. Ger unikt innehåll och trovärdighet, men skalar långsamt (kanske 2–4/månad till att börja med).
- **Sammanställda internationella tester**: sammanfatta konsensusbetyg från Halfwheel/Cigar Aficionado/Cigar Journal för cigarrer som säljs i Sverige – snabbare att producera, mindre unikt.

Rekommendation: starta med sammanställningar för att fylla sidan, bygg upp egna recensioner parallellt som blir kärnvärdet på sikt.

## 4. Faktadel – statisk, skrivs en gång

Kan produceras helt utan löpande research. Föreslagen struktur:

- Cigarrens historia
- Tillverkningsprocess (odling, torkning, rullning – long filler vs short filler)
- Vitolas/storlekar (ringmått, längd) – ordlista
- Smakprofiler och styrka
- Förvaring: humidor, luftfuktighet, temperatur
- Rökteknik: tända, aska, dragmotstånd, tempo
- Parning: whisky, rom, kaffe, portvin
- Cigarr vs cigarill vs pipa – skillnader
- Vanliga misstag för nybörjare
- Ordlista (t.ex. capa, wrapper, binder, filler, box press)

## 5. Juridik – viktigast att ha koll på

Sverige har en av EU:s striktaste tobakslagar (Lag 2018:2088 om tobak och liknande produkter):

- **All marknadsföring av tobak är förbjuden** – gäller även indirekt reklam och sponsring med gränsöverskridande effekt
- **Redaktionellt innehåll (journalistik) räknas inte som marknadsföring** – det är därför Cigarrklubbens redaktion kan bedriva nyhetsbevakning om branschen. Nyckeln är att hålla tydlig linje mellan redaktionellt och kommersiellt innehåll.
- Praktiska konsekvenser för Cigarr-briefen:
  - Inga bannerannonser för cigarrmärken/butiker
  - Inga affiliate-länkar med köpuppmaning ("köp här", rabattkoder) till tobaksprodukter
  - Ingen direktmarknadsföring (nyhetsbrev får informera, inte marknadsföra tobak)
  - Recensioner ska vara sakliga/journalistiska, inte säljande
  - Överväg ansvarig utgivare / utgivningsbevis om sajten växer – ger juridiskt skydd och källskydd, vilket Cigarrklubben använder aktivt

Detta är den enskilt viktigaste begränsningen för affärsmodellen – monetisering måste ske via prenumeration/donation/medlemskap, inte tobaksannonser.

## 6. Teknisk ansats

- Statisk/enkel CMS-lösning (t.ex. WordPress, Ghost, eller ett skräddarsytt Next.js-bygge) räcker gott – ingen anledning till komplex arkitektur i start
- Nyhetsflöde: enkel RSS-insamling i backend + redaktionellt gränssnitt för att skriva sammanfattningar
- Tvåspråkighet (SV/EN) hanteras enklast som separata sektioner snarare än full sajtöversättning – många internationella läsare bryr sig bara om internationella nyheter, svenska läsare vill ha svensk vinkel
- Faktadelen byggs som statiska sidor, låg underhållskostnad

## 7. Föreslagen fasindelning

1. **Fas 1** – Faktadel klar (skrivs en gång, ger sajten innehåll direkt) + 5–10 sammanställda nyhetsartiklar för att visa konceptet
2. **Fas 2** – Löpande nyhetsbevakning igång (2–3 artiklar/vecka), första egna recensionerna
3. **Fas 3** – Nyhetsbrev, ev. community-funktioner, undersök prenumerationsmodell

---

*Detta är en strukturplan, inte en färdig sajt. Naturliga nästa steg: namn/domän, wireframe för startsidan, eller ett första utkast av faktadelen.*
