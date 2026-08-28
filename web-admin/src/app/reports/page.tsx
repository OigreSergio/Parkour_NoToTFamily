'use client';

import { useCallback, useEffect, useState } from 'react';

import { AdminNav, askReason } from '@/components/AdminNav';
import {
  dismissReport,
  openReports,
  recordModeration,
  reportTarget,
  type Report,
} from '@/lib/supabase';

/**
 * La coda delle segnalazioni.
 *
 * È il meccanismo di notice-and-action dell'art. 16 DSA. Due cose lo rendono
 * reale invece che formale: le segnalazioni più vecchie stanno in cima — una
 * che invecchia è una persona che aspetta — e ogni decisione, anche
 * l'archiviazione, richiede una motivazione.
 */
export default function ReportsPage() {
  const [reports, setReports] = useState<Report[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setReports(await openReports());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Caricamento non riuscito');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(report: Report, remove: boolean) {
    const target = reportTarget(report);
    const reason = askReason(
      remove
        ? `Perché rimuovi questo ${target.kind}? (lo leggerà l'autore)`
        : 'Perché archivi la segnalazione? (lo leggerà chi ha segnalato)',
    );
    if (reason === null) return;

    setBusy(report.id);
    setError(null);
    try {
      if (remove) {
        await recordModeration({
          targetKind: target.kind,
          targetId: target.id,
          action: 'rimosso',
          reason,
          reportId: report.id,
        });
      } else {
        await dismissReport(report.id, reason);
      }
      setReports((cur) => cur?.filter((r) => r.id !== report.id) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operazione non riuscita');
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="container">
      <AdminNav />
      <h1>Segnalazioni</h1>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {reports === null && !error && <p className="muted">Caricamento…</p>}
      {reports?.length === 0 && <p className="muted">Nessuna segnalazione aperta.</p>}

      {reports?.map((report) => {
        const target = reportTarget(report);
        const age = Math.floor(
          (Date.now() - new Date(report.created_at).getTime()) / 86_400_000,
        );

        return (
          <div key={report.id} className="card col">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h2 style={{ margin: 0 }}>{target.kind}</h2>
              <span className={age >= 3 ? '' : 'muted'}>
                {age === 0 ? 'oggi' : `${age} giorni fa`}
              </span>
            </div>

            <p>{report.reason}</p>
            <p className="muted" style={{ fontSize: 13 }}>
              id: <code>{target.id}</code>
            </p>

            <div className="row">
              <button
                className="danger"
                disabled={busy === report.id}
                onClick={() => void act(report, true)}
              >
                Rimuovi il contenuto
              </button>
              <button
                className="secondary"
                disabled={busy === report.id}
                onClick={() => void act(report, false)}
              >
                Archivia
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
