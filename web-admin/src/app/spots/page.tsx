'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { api, clearTokens, type Spot } from '@/lib/api';

export default function SpotsQueuePage() {
  const router = useRouter();
  const [spots, setSpots] = useState<Spot[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  // Per-spot "I confirm the photos show a real, suitable location" attestation.
  const [photosConfirmed, setPhotosConfirmed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    if (!photosConfirmed[id]) return;
    setBusyId(id);
    try {
      await api.verifySpot(id, true);
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
        <div className="row">
          <Link href="/spots/new">
            <button>Add spot</button>
          </Link>
          <button className="secondary" onClick={logout}>
            Log out
          </button>
        </div>
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
            {spot.photo_urls.length === 0 && (
              <span className="muted">No photos — cannot be verified.</span>
            )}
            {spot.photo_urls.map((url) => (
              <a key={url} href={url} target="_blank" rel="noreferrer">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={url}
                  alt=""
                  style={{ width: 160, height: 120, objectFit: 'cover', borderRadius: 6 }}
                />
              </a>
            ))}
          </div>
          <label className="row" style={{ gap: 8 }}>
            <input
              type="checkbox"
              checked={photosConfirmed[spot.id] ?? false}
              disabled={spot.photo_urls.length === 0}
              onChange={(e) =>
                setPhotosConfirmed((cur) => ({ ...cur, [spot.id]: e.target.checked }))
              }
            />
            I confirm the photos are real and show a publicly accessible, parkour-suitable
            location.
          </label>
          <div className="row">
            <button
              disabled={busyId === spot.id || !photosConfirmed[spot.id]}
              onClick={() => verify(spot.id)}
            >
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
