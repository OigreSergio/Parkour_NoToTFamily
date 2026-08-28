'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { AdminNav } from '@/components/AdminNav';
import {
  getSupabase,
  pendingSpots,
  rejectSpot,
  verifySpot,
  type Spot,
} from '@/lib/supabase';

export default function SpotsQueuePage() {
  const router = useRouter();
  const [spots, setSpots] = useState<Spot[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await getSupabase().auth.getUser();
      if (!data.user) {
        router.push('/login');
        return;
      }
      setSpots(await pendingSpots());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Caricamento non riuscito');
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onVerify(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await verifySpot(id);
      setSpots((cur) => cur?.filter((s) => s.id !== id) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operazione non riuscita');
    } finally {
      setBusyId(null);
    }
  }

  async function onReject(id: string) {
    // La motivazione è dovuta all'autore: art. 17 DSA (statement of reasons).
    const reason = window.prompt('Perché questo spot viene rifiutato?');
    if (reason === null) return;

    setBusyId(id);
    setError(null);
    try {
      await rejectSpot(id, reason);
      setSpots((cur) => cur?.filter((s) => s.id !== id) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operazione non riuscita');
    } finally {
      setBusyId(null);
    }
  }

  async function logout() {
    await getSupabase().auth.signOut();
    router.push('/login');
  }

  return (
    <div className="container">
      <AdminNav />
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>Spot in attesa</h1>
        <button className="secondary" onClick={() => void logout()}>
          Esci
        </button>
      </div>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {spots === null && !error && <p className="muted">Caricamento…</p>}
      {spots?.length === 0 && <p className="muted">Coda vuota.</p>}

      {spots?.map((spot) => (
        <div key={spot.id} className="card col">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h2 style={{ margin: 0 }}>{spot.name}</h2>
            <a
              className="muted"
              href={`https://www.openstreetmap.org/?mlat=${spot.lat}&mlon=${spot.lng}#map=18/${spot.lat}/${spot.lng}`}
              target="_blank"
              rel="noreferrer noopener"
            >
              {spot.lat.toFixed(5)}, {spot.lng.toFixed(5)}
            </a>
          </div>

          <p>
            {spot.description || (
              <span className="muted">(nessuna descrizione)</span>
            )}
          </p>

          <div className="row" style={{ flexWrap: 'wrap', gap: 12 }}>
            <Attribute label="Livello" value={spot.skill_level} />
            <Attribute label="Affollamento" value={spot.crowd_level} />
            <Attribute
              label="Acqua"
              value={
                spot.has_fountain === null
                  ? null
                  : spot.has_fountain
                    ? 'sì'
                    : 'no'
              }
            />
          </div>

          <div className="row" style={{ flexWrap: 'wrap' }}>
            {(spot.spot_photos ?? []).map((photo) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={photo.url}
                src={photo.url}
                alt=""
                style={{
                  width: 160,
                  height: 120,
                  objectFit: 'cover',
                  borderRadius: 6,
                }}
              />
            ))}
          </div>

          <div className="row">
            <button
              disabled={busyId === spot.id}
              onClick={() => void onVerify(spot.id)}
            >
              Verifica
            </button>
            <button
              className="danger"
              disabled={busyId === spot.id}
              onClick={() => void onReject(spot.id)}
            >
              Rifiuta
            </button>
            <span className="muted">
              proposto il {new Date(spot.created_at).toLocaleString('it-IT')}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Un attributo dello spot.
 *
 * `null` non è un buco da riempire: significa che nessuno l'ha ancora valutato,
 * e va detto. Mostrare un default al suo posto è ciò che ha reso inutilizzabili
 * i 1.680 spot importati.
 */
function Attribute({ label, value }: { label: string; value: string | null }) {
  return (
    <span className="muted">
      {label}:{' '}
      {value ?? <em>non valutato</em>}
    </span>
  );
}
