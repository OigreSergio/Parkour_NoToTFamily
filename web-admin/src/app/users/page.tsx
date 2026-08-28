'use client';

import { useCallback, useEffect, useState } from 'react';

import { AdminNav, askReason } from '@/components/AdminNav';
import {
  liftSuspension,
  searchUsers,
  setBanned,
  setInstructor,
  suspendUser,
  type ModeratedUser,
} from '@/lib/supabase';

/**
 * Gli utenti, e le sanzioni.
 *
 * Tre livelli, non due: sospensione a tempo, ban, e in mezzo la possibilità di
 * revocare. Fra «non fare niente» e «fuori per sempre» la maggior parte dei
 * casi è una brutta giornata, non un molestatore seriale — e un sistema che
 * offre solo l'estremo finisce per non usarlo mai.
 *
 * Il ruolo `admin` non compare fra le azioni: si assegna solo a livello di
 * database, e nessun percorso dell'applicazione lo concede.
 */
export default function UsersPage() {
  const [query, setQuery] = useState('');
  const [users, setUsers] = useState<ModeratedUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async (q: string) => {
    try {
      setUsers(await searchUsers(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Caricamento non riuscito');
    }
  }, []);

  useEffect(() => {
    void load('');
  }, [load]);

  async function run(id: string, action: () => Promise<void>) {
    setBusy(id);
    setError(null);
    try {
      await action();
      await load(query);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operazione non riuscita');
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="container">
      <AdminNav />
      <h1>Utenti</h1>

      <div className="card row">
        <input
          value={query}
          placeholder="Cerca per nome"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void load(query)}
        />
        <button onClick={() => void load(query)}>Cerca</button>
      </div>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {users === null && !error && <p className="muted">Caricamento…</p>}

      {users?.map((u) => {
        const suspended =
          u.suspended_until !== null && new Date(u.suspended_until) > new Date();

        return (
          <div key={u.id} className="card col">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h2 style={{ margin: 0 }}>{u.username || '(senza nome)'}</h2>
              <span className="muted">{u.role}</span>
            </div>

            <div className="row" style={{ flexWrap: 'wrap', gap: 10 }}>
              {u.supervised && (
                <span className="muted">account supervisionato</span>
              )}
              {u.banned && <span style={{ color: 'var(--danger)' }}>bannato</span>}
              {suspended && (
                <span style={{ color: 'var(--danger)' }}>
                  sospeso fino al{' '}
                  {new Date(u.suspended_until!).toLocaleDateString('it-IT')}
                </span>
              )}
            </div>

            {u.suspension_reason && (
              <p className="muted">Motivo: {u.suspension_reason}</p>
            )}

            <div className="row" style={{ flexWrap: 'wrap' }}>
              {suspended ? (
                <button
                  className="secondary"
                  disabled={busy === u.id}
                  onClick={() => void run(u.id, () => liftSuspension(u))}
                >
                  Revoca la sospensione
                </button>
              ) : (
                [3, 7, 30].map((days) => (
                  <button
                    key={days}
                    className="secondary"
                    disabled={busy === u.id}
                    onClick={() => {
                      const why = askReason(
                        `Perché sospendi ${u.username} per ${days} giorni?`,
                      );
                      if (why) void run(u.id, () => suspendUser(u, days, why));
                    }}
                  >
                    Sospendi {days}g
                  </button>
                ))
              )}

              <button
                className={u.banned ? 'secondary' : 'danger'}
                disabled={busy === u.id}
                onClick={() => {
                  const why = askReason(
                    u.banned ? 'Perché revochi il ban?' : 'Perché banni?',
                  );
                  if (why) void run(u.id, () => setBanned(u, !u.banned, why));
                }}
              >
                {u.banned ? 'Revoca il ban' : 'Banna'}
              </button>

              {u.role !== 'admin' && (
                <button
                  className="secondary"
                  disabled={busy === u.id}
                  onClick={() => {
                    const on = u.role !== 'instructor';
                    const why = askReason(
                      on
                        ? 'Perché riconosci questa persona come istruttore?'
                        : 'Perché revochi il riconoscimento?',
                    );
                    if (why) void run(u.id, () => setInstructor(u, on, why));
                  }}
                >
                  {u.role === 'instructor'
                    ? 'Revoca istruttore'
                    : 'Riconosci istruttore'}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
