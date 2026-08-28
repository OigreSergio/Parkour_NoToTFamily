# Sicurezza

## Segnalare una vulnerabilità

Scrivi a **security@pkfamily.app**, oppure apri una *security advisory* privata
su GitHub. Non aprire una issue pubblica: finché il buco è aperto, descriverlo
in chiaro serve solo a chi vuole usarlo.

Se puoi, includi:

- cosa hai trovato e cosa permette di fare;
- come riprodurlo, possibilmente in modo minimo;
- come vuoi essere citatə nel fix, o se preferisci di no.

### Quanto ci metto a rispondere

PkFAMILY lo manda avanti **una persona sola**, nel tempo libero. Quindi:

| | Tempo realistico |
| --- | --- |
| Ti dico che ho letto | entro **una settimana** |
| Ti dico cosa intendo fare | entro **due settimane** |
| Sistemo una cosa grave (dati esposti, accesso altrui) | **appena capisco come**, di solito in giorni |
| Sistemo il resto | quando c'è tempo, dicendoti quando |

La versione precedente di questo file prometteva «48 ore per la presa in carico,
14 giorni per il fix». Non era vero, e una promessa che non puoi mantenere è
peggio di un'attesa dichiarata: chi segnala resta ad aspettare una risposta che
avevi garantito.

Se una segnalazione riguarda **dati personali esposti**, scatta anche la
procedura dell'art. 33 GDPR — notifica al Garante entro 72 ore. È in
`docs/privacy/procedura-data-breach.md`, ed è indipendente dai tempi qui sopra.

### Niente ricompense

Non c'è un bug bounty e non ci sarà a breve: il servizio è gratuito e non ha
entrate. Quello che posso dare è il credito nel fix e una risposta scritta da
una persona.

## Cosa è in scope

**Sì:** l'app Flutter (`mobile/`), la console di moderazione (`web-admin/`), le
policy RLS in `supabase/migrations/`, i workflow di CI e deploy, gli header
serviti da `pkfamily.app`.

**No:** i servizi di terzi (Supabase, Cloudflare, GitHub — segnala a loro),
l'ingegneria sociale, gli attacchi fisici, e il rumore automatico dei
vulnerability scanner senza un impatto dimostrato.

Una nota su `backend/` (FastAPI): è nel repo come riferimento di dominio,
**non è deployato** e nessun percorso di codice ci arriva. Le segnalazioni su
quel codice sono benvenute ma non urgenti.

## Come è difeso, davvero

Le voci qui sotto sono quelle **implementate**, non quelle previste. La versione
precedente di questo file spuntava cose che descrivevano il backend FastAPI mai
deployato — Argon2id, rotazione dei refresh token, allowlist CORS — dando
un'impressione di solidità che il sistema vero non aveva.

- **Le policy RLS sono l'unica difesa del database.** La publishable key è nel
  bundle e ce l'hanno tutti: è pubblica per costruzione. Tutto quindi dipende da
  quelle policy, e `scripts/audit_rls.mjs` le verifica **da fuori**, come farebbe
  un estraneo. Gira in CI, ed è bloccante prima di ogni deploy in produzione.
- **La secret key non entra in nessun client.** `scripts/prepare_deploy.mjs` si
  rifiuta di pubblicare un build che ne contenga una.
- **Password**: gestite da Supabase Auth (bcrypt), minimo 12 caratteri, con il
  controllo nativo contro le password già comparse in violazioni note.
- **Email confermata** obbligatoria prima di poter scrivere in chat.
- **Rate limit** sull'invio dei messaggi, applicato da un trigger nel database:
  20 al minuto per utente. Sta lì e non nel client perché il client è
  dell'utente.
- **Header**: CSP senza `unsafe-eval`, HSTS con preload, `frame-ancestors 'none'`,
  `Permissions-Policy` che nega tutto tranne la geolocalizzazione. Il workflow di
  produzione li richiede al sito vero dopo il deploy e fallisce se mancano.
- **Nessuna risorsa di terze parti** caricata all'avvio: CanvasKit è servito da
  noi, non da `gstatic.com`.
- **Dependabot e CodeQL**: da attivare — vedi `docs/OPS_TODO.md`. Prima
  risultavano spuntati qui senza esserlo in nessuna impostazione del repository.

## Quello che non facciamo, e va saputo

- **La chat non è cifrata end-to-end.** Le policy impediscono agli altri utenti
  di leggere i tuoi messaggi, ma chi amministra il database ha accesso tecnico.
  È scritto anche nell'informativa: non è una svista, è un limite dichiarato.
- **Non c'è error tracking di terze parti.** Una decisione presa, non subita:
  vedi `docs/OPS_TODO.md`.
- **Non c'è un SOC, un on-call, né monitoraggio 24/7.** C'è una persona che
  legge la posta.
