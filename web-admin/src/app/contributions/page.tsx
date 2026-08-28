'use client';

import { useCallback, useEffect, useState } from 'react';

import { AdminNav, askReason } from '@/components/AdminNav';
import {
  acceptContribution,
  pendingContributions,
  rejectContribution,
  type Contribution,
} from '@/lib/supabase';

/**
 * Quello che la community racconta degli spot importati.
 *
 * È l'unico canale da cui possono arrivare livello, affollamento e descrizione
 * dei 1.680 spot che nessuno ha mai visitato: nessuna API li conosce. Ogni
 * contributo accettato porta uno spot da «da completare» a «verificato».
 */
export default function ContributionsPage() {
  const [items, setItems] = useState<Contribution[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await pendingContributions());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Caricamento non riuscito');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(c: Contribution, accept: boolean) {
    const reason = accept
      ? ''
      : askReason('Perché rifiuti il contributo? (lo leggerà chi lo ha scritto)');
    if (!accept && reason === null) return;

    setBusy(c.id);
    setError(null);
    try {
      if (accept) {
        await acceptContribution(c);
      } else {
        await rejectContribution(c, reason!);
      }
      setItems((cur) => cur?.filter((x) => x.id !== c.id) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operazione non riuscita');
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="container">
      <AdminNav />
      <h1>Contributi agli spot</h1>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {items === null && !error && <p className="muted">Caricamento…</p>}
      {items?.length === 0 && <p className="muted">Niente da rivedere.</p>}

      {items?.map((c) => (
        <div key={c.id} className="card col">
          <h2 style={{ margin: 0 }}>{c.spots?.name ?? 'Spot'}</h2>

          {c.description && <p>{c.description}</p>}

          <div className="row" style={{ flexWrap: 'wrap', gap: 12 }}>
            <span className="muted">Livello: {c.skill_level ?? '—'}</span>
            <span className="muted">Affollamento: {c.crowd_level ?? '—'}</span>
            <span className="muted">
              Acqua:{' '}
              {c.has_fountain === null ? '—' : c.has_fountain ? 'sì' : 'no'}
            </span>
          </div>
          <p className="muted" style={{ fontSize: 13 }}>
            I campi lasciati in bianco non sovrascrivono quello che c&apos;è già.
          </p>

          <div className="row">
            <button disabled={busy === c.id} onClick={() => void decide(c, true)}>
              Accetta
            </button>
            <button
              className="danger"
              disabled={busy === c.id}
              onClick={() => void decide(c, false)}
            >
              Rifiuta
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
