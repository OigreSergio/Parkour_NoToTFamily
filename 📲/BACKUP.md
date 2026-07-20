# 📲 Backup — Parkour NoToT Family

Collegamento diretto al backup e piano di rotazione a 24 ore.

## Collegamenti diretti

| Cosa | Link |
| --- | --- |
| Manifest del backup (questo ciclo di 24h) | [`backup-latest.json`](./backup-latest.json) |
| Bundle completo (tutti i branch, artifact 24h) | [Workflow "Daily backup" → run più recente → Artifacts](https://github.com/OigreSergio/Parkour_NoToTFamily/actions/workflows/backup.yml) |
| Repository | <https://github.com/OigreSergio/Parkour_NoToTFamily> |
| Pagina admin (web-admin → `/backup`) | route `/backup` della dashboard |

## Come funziona la rotazione (24h)

Ogni 24 ore il workflow [`.github/workflows/backup.yml`](../.github/workflows/backup.yml):

1. **Distrugge** il manifest precedente (`backup-latest.json`) e lo **rigenera**
   da zero con `scripts/make_backup.py`: elenco di tutti i branch con SHA del
   commit, link diretto di download per ciascuno e checksum SHA-256 dei
   dataset (es. fontanelle di Roma).
2. Crea un **`git bundle` completo** (tutta la storia, tutti i branch) e lo
   carica come artifact con **retention di 1 giorno**: l'artifact si
   autodistrugge dopo 24h e viene ricreato dal run successivo.

Il campo `expires_at` nel manifest indica quando il ciclo corrente scade.
Il workflow può anche essere lanciato a mano (`workflow_dispatch`).

## Ripristino

```bash
# 1. Scarica l'artifact "parkour-notot-full-backup" dall'ultimo run
# 2. Ripristina tutto (ogni branch):
git clone parkour-notot-full-backup.bundle restored/
cd restored && git branch -a

# In alternativa: scarica lo zip_url di un singolo branch dal manifest
```

## Cosa copre

- **Tutti i branch remoti**, incluse le linee di lavoro delle altre sessioni
  (auth/spot-submission, Supabase RLS, status page `gh-pages`, dependabot…):
  qualunque commit pushato è dentro il bundle.
- I **dataset** generati (con checksum per verificarne l'integrità).

> Nota: il lavoro **non pushato** che vive solo nel working tree di una
> sessione remota non è raggiungibile da nessun backup — va committato e
> pushato dalla sessione stessa per entrare nel ciclo.
