'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { api, clearTokens, type Spot } from '@/lib/api';

export default function SpotsQueuePage() {
  const router = useRouter();
  const [spots, setSpots] = useState<Spot[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    try {
      setSpots(await api.pendingSpots());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
      if (err instanceof Error && err.message.toLowerCase().includes('unauth')) {
        router.push('/login');
      }
    }
  }

  async function verify(id: string) {
    setBusyId(id);
    try {
      await api.verifySpot(id);
      setSpots((cur) => cur?.filter((s) => s.id !== id) ?? null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed');
    } finally {
      setBusyId(null);
    }
  }

  async function reject(id: string) {
    const reason = window.prompt('Why is this spot being rejected?');
    if (!reason) return;
    setBusyId(id);
    try {
      await api.rejectSpot(id, reason);
      setSpots((cur) => cur?.filter((s) => s.id !== id) ?? null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed');
    } finally {
      setBusyId(null);
    }
  }

  function logout() {
    clearTokens();
    router.push('/login');
  }

  return (
    <div className="container">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>Pending spots</h1>
        <button className="secondary" onClick={logout}>
          Log out
        </button>
      </div>

      {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      {spots === null && !error && <p className="muted">Loading…</p>}
      {spots?.length === 0 && <p className="muted">Queue is empty — nice.</p>}

      {spots?.map((spot) => (
        <div key={spot.id} className="card col">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h2 style={{ margin: 0 }}>{spot.name}</h2>
            <span className="muted">
              {spot.location.lat.toFixed(5)}, {spot.location.lng.toFixed(5)}
            </span>
          </div>
          <p>{spot.description || <span className="muted">(no description)</span>}</p>
          <div className="row" style={{ flexWrap: 'wrap' }}>
            {spot.photo_urls.map((url) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={url}
                src={url}
                alt=""
                style={{ width: 160, height: 120, objectFit: 'cover', borderRadius: 6 }}
              />
            ))}
          </div>
          <div className="row">
            <button disabled={busyId === spot.id} onClick={() => verify(spot.id)}>
              Verify
            </button>
            <button
              className="danger"
              disabled={busyId === spot.id}
              onClick={() => reject(spot.id)}
            >
              Reject
            </button>
            <span className="muted">submitted {new Date(spot.created_at).toLocaleString()}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
