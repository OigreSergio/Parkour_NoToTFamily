# PkPASS — inviti a pagamento (demo)

Infrastruttura live su `gh-pages` per l'accesso su invito con prezzo
simbolico di 5 € (demo). Flusso completo:

```
utente → /invito/ (ordine + bonifico) → mail ordine all'admin
admin  → verifica accredito in banca → console admin → genera link+QR invito
utente → apre link/QR → gate valida la firma → registra il dispositivo
         (mail automatica all'admin) → entra nell'app
```

## Componenti (branch `gh-pages`)

| File | Ruolo |
| ---- | ----- |
| `index.html` (root) | Gate "Anteprima privata": valida `#pass=<payload>.<firma>`, salva il pass, registra ogni **nuovo dispositivo** con una mail automatica a `adminpkfamily@gmail.com`, poi apre l'app. Dispositivi già registrati: benvenuto + redirect. |
| `invito/index.html` | Ordine demo: dati utente → codice ordine `PK-XXXXX` → istruzioni bonifico (IBAN `IT43C0366901600025878603502`, beneficiario Sergiu Ionut Hanganu, causale `TEST Pk webapp PK-XXXXX`) con pulsanti copia → invio ordine via mail. |
| `t/<segreto>/admin-inviti.html` | Console admin (non linkata): genera inviti link+QR (ruolo member o admin, legati al codice ordine) e tiene il **registro ordini** (stati: attesa → pagato → invito, totale incassato, export CSV). |
| `t/<segreto>/index.html` | L'app controlla il pass firmato in `localStorage`: senza invito valido rimanda al gate. |

## Tracciamento

- **Pagamenti**: la causale contiene il codice ordine → l'accredito in banca
  si abbina all'ordine ricevuto via mail; il registro nella console admin è
  il libro mastro della demo (locale al dispositivo admin, esportabile CSV).
- **Dispositivi**: il link-invito è condivisibile, ma la prima apertura su
  ogni dispositivo genera una mail "Nuovo dispositivo — invito PK-XXXXX" con
  device ID e browser: l'admin vede quanti device usa ogni invito.

## Limiti (dichiarati) della demo

- La firma dei token è verificata client-side con un segreto presente nelle
  pagine: tiene fuori i curiosi, non un attaccante che legge il sorgente.
- La registrazione dispositivi passa da `mailto:`: l'utente deve premere
  Invia sulla mail.
- Il pagamento è un bonifico manuale: nessuna verifica automatica.

## Fase 6 — versione reale (Supabase)

1. Tabelle `orders` (codice, contatto, stato, importo) e `devices`
   (invite_code, device_id, user_agent, created_at) con RLS: insert anonimo
   su `devices`, lettura solo admin — la registrazione diventa automatica e
   silenziosa, niente più mailto.
2. Token generati/verificati da una Edge Function (segreto server-side).
3. Pagamento con PSP (Stripe/PayPal) al posto del bonifico manuale;
   l'entitlement `base` viene concesso alla conferma del pagamento e il
   ruolo admin resta legato al profilo Supabase, non al token.
