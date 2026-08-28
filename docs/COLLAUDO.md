# Collaudo prima del tag

Quello che va provato **a mano su staging** prima di pubblicare, e che nessuno
script può provare al posto tuo.

Non è una formalità: i test verificano che il codice faccia quello che il codice
dice: qui si verifica che l'app faccia quello che *serve*. Sono due cose diverse,
e la seconda si scopre solo usandola.

Regola: se un passaggio non fa quello che dice questa pagina, **fermati e
scrivilo** invece di andare avanti. Un collaudo che si conclude sempre con «tutto
ok» non ha collaudato niente.

---

## 0. Prima di cominciare

Queste devono essere già fatte, altrimenti metà del collaudo non è eseguibile:

- [ ] migration da `0003` a `0010` applicate sul progetto di staging
- [ ] **sessioni anonime attive** (Dashboard → Authentication → Sign In /
      Providers). Senza, la mappa è vuota per chiunque non abbia un account —
      vedi la nota in testa a `0010_gate_anche_senza_login.sql`
- [ ] spot importati (`scripts/import_spots_supabase.mjs`)
- [ ] almeno un video nel percorso «Inizia da qui»
- [ ] un secondo account, per provare chat, blocco e segnalazioni: da soli non
      si collauda una community

## 1. Quello che dicono gli script

Da fare per primo: se qui c'è rosso, il resto del collaudo è tempo perso.

```sh
# Cosa può fare un estraneo, e cosa può fare uno che è dentro
SUPABASE_URL=… SUPABASE_PUBLISHABLE_KEY=… node scripts/audit_rls.mjs --sessione

# Cosa risponde davvero il sito
node scripts/check_headers.mjs https://staging.pkfamily.app
```

- [ ] `audit_rls.mjs --sessione` esce 0
- [ ] `check_headers.mjs` esce 0

Sui **«non concludenti»**: su una tabella vuota «non ho ricevuto righe» non
dimostra che la policy filtri. Rilancia dopo aver scritto qualcosa in quelle
tabelle — una segnalazione, un messaggio — e guarda se restano tali.

## 2. Chi arriva e non si registra

- [ ] apri staging in una **finestra anonima**: compare il gate di sicurezza
- [ ] i cinque documenti legali si aprono **da lì**, prima di decidere
- [ ] **rifiuta** → resti dentro, mappa vuota, striscia «Mappa senza spot»
- [ ] i video restano completi
- [ ] con il gate rifiutato, chiedi gli spot all'API a mano:
      ```sh
      curl -s 'https://<ref>.supabase.co/rest/v1/spots?select=id,lat,lng&limit=3' \
        -H 'apikey: sb_publishable_…'
      ```
      **deve tornare `[]`.** Se tornano coordinate, il rifiuto è una schermata e
      non un rifiuto: è il buco che la migration `0010` chiude
- [ ] «Rivedi l'avviso» → accetta → gli spot compaiono senza ricaricare
- [ ] ricarica la pagina: il gate **non** ricompare

## 3. Registrarsi

- [ ] data di nascita che dà **meno di 16 anni** → registrazione bloccata, e
      compare «Chiedi a un genitore» — un muro no, una strada sì
- [ ] esattamente 16 anni compiuti oggi → passa
- [ ] le due checkbox (Termini, informativa) sono **separate e non spuntate**;
      il «Leggi» accanto a ciascuna apre il documento giusto
- [ ] senza spuntarle non si può proseguire
- [ ] arriva l'email di conferma; **prima** di confermarla, prova a scrivere in
      chat → deve essere impedito
- [ ] conferma, poi login

## 4. La mappa

- [ ] a zoom basso i marker sono raggruppati; a zoom alto si separano
- [ ] con ~1.700 spot lo scorrimento non impunta (provalo **da telefono**, non
      dal portatile: è lì che si usa)
- [ ] uno spot `da_completare` si distingue a colpo d'occhio da uno `verificato`
- [ ] la scheda di uno spot non valutato dice **«non valutato»**, non
      «intermedio»: un default travestito da valutazione è peggio di un buco
- [ ] la versione breve dell'avvertenza c'è in ogni scheda
- [ ] le foto mostrano autore e licenza
- [ ] **la posizione la chiede solo al tocco** di «dove sono», mai all'avvio
- [ ] nega il permesso → la mappa continua a funzionare
- [ ] concedilo → la mappa si centra, e nel pannello di rete del browser
      **nessuna richiesta contiene le tue coordinate**

## 5. Proporre uno spot

- [ ] proponi uno spot: lo vedi tu, in attesa
- [ ] da un **altro account**: non si vede
- [ ] non si può marcare da soli come verificato
- [ ] dalla console di moderazione, rifiutalo con una motivazione
- [ ] la motivazione **arriva nel profilo** di chi l'ha proposto (art. 17 DSA)
- [ ] proponine un altro, verificalo: compare sulla mappa per tutti

## 6. Chat

Serve il secondo account.

- [ ] chat privata: i messaggi arrivano in tempo reale da entrambe le parti
- [ ] gruppo: crea, invita, scrivi, esci
- [ ] **blocca** l'altro account → non riesce più a scriverti
- [ ] segnala un messaggio → la segnalazione arriva in moderazione, e
      **l'altro non sa di essere stato segnalato né da chi**
- [ ] manda 25 messaggi di fila → al ventunesimo nel minuto arriva un rifiuto,
      non un errore incomprensibile
- [ ] la nota «la chat non è cifrata end-to-end» è visibile nella schermata

## 7. Account supervisionato

- [ ] percorso «Chiedi a un genitore»: arriva **una sola** email
- [ ] l'adulto apre il link, crea il proprio account, dichiara ≥18 anni
- [ ] il profilo risulta `supervised`, e **la chat nasce spenta**
- [ ] con la chat spenta, prova a scrivere **via API** con il token di
      quell'account: deve rifiutare. Se passa, il vincolo è solo in UI e non
      vale niente
- [ ] il genitore la attiva dalle impostazioni → ora si può scrivere

## 8. I diritti, che devono essere pulsanti

- [ ] **«Scarica i miei dati»** → JSON con profilo, spot, contributi, messaggi.
      Aprilo e controlla che ci sia davvero tutto: un export incompleto è
      peggio di nessun export, perché sembra una risposta
- [ ] **«Elimina account»** → conferma via email, 30 giorni di grazia
- [ ] dopo la cancellazione: profilo, spot proposti e contributi spariti
- [ ] **i messaggi già inviati restano nelle conversazioni altrui, senza il
      nome.** È la cosa che l'informativa promette, ed è quella che si dimentica
      di verificare

## 9. Il ripristino del backup

Lo «Scenario B» di `📲/README.md` non è un piano finché non è stato provato
almeno una volta. Un backup che nessuno ha mai ripristinato è un file, non un
backup.

- [ ] crea un progetto Supabase **vuoto** (region UE)
- [ ] applica le migration da `0003` a `0010`
- [ ] ripristina l'ultimo backup
- [ ] confronta i conteggi con l'originale: spot, video, foto, profili
- [ ] **fai partire l'app contro quel progetto** e apri la mappa: è l'unico modo
      di sapere se i dati sono ripristinati *e utilizzabili*, non solo presenti
- [ ] cancella il progetto di prova

Segna qui quanto ci hai messo: serve a sapere quanto dura un disastro.

    Tempo di ripristino misurato: ______

## 10. Sul telefono, in strada

L'app si usa in piedi, con una mano, con il sole sullo schermo e la rete che va
e viene. Non si collauda seduti.

- [ ] installala come PWA da telefono (Aggiungi a schermata Home)
- [ ] aprila **in 4G, non in wifi**: quanto ci mette la prima volta? Il bundle
      pesa 31 MB e il service worker se li porta giù tutti — vedi
      `docs/OPS_TODO.md` §12-bis
- [ ] riaprila senza rete: cosa succede? Deve dire qualcosa, non restare bianca
- [ ] i tocchi si prendono con il pollice, i testi si leggono al sole

## 11. Prima di mettere il tag

- [ ] tutto qui sopra è spuntato, o quello che non lo è è **scritto** da qualche
      parte con il motivo
- [ ] `docs/OPS_TODO.md`: le voci 🔴 sono chiuse
- [ ] il nome del titolare è in `note-legali.md` (niente parentesi quadre)
- [ ] i testi legali sono passati da un professionista
- [ ] il dominio risponde, i DPA sono accettati, le caselle email esistono

Poi:

```sh
git tag -a v1.0.0 -m "Primo lancio pubblico"
git push origin v1.0.0
```

Il workflow rifà analyze, test e audit RLS prima di pubblicare, e dopo il deploy
chiede al sito vero se gli header ci sono. Se qualcosa non torna, il deploy
fallisce **prima** che il tag diventi il sito.
