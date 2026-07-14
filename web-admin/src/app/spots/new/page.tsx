'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { api } from '@/lib/api';

/**
 * Admin-only form: spots created here skip the moderation queue and are
 * published as `verified` immediately (the backend records the audit event).
 */
export default function NewSpotPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [difficulty, setDifficulty] = useState(1);
  const [photoUrls, setPhotoUrls] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const latNum = Number(lat);
    const lngNum = Number(lng);
    if (Number.isNaN(latNum) || latNum < -90 || latNum > 90) {
      setError('Latitude must be a number between -90 and 90.');
      return;
    }
    if (Number.isNaN(lngNum) || lngNum < -180 || lngNum > 180) {
      setError('Longitude must be a number between -180 and 180.');
      return;
    }

    setSaving(true);
    try {
      await api.createSpot({
        name,
        description,
        location: { lat: latNum, lng: lngNum },
        difficulty,
        photo_urls: photoUrls
          .split('\n')
          .map((u) => u.trim())
          .filter(Boolean),
      });
      router.push('/spots');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create spot');
      if (err instanceof Error && err.message.toLowerCase().includes('unauth')) {
        router.push('/login');
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="container" style={{ maxWidth: 560 }}>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>Add spot</h1>
        <Link href="/spots">
          <button className="secondary">Back to queue</button>
        </Link>
      </div>
      <p className="muted">
        Spots created here are published immediately as verified — double-check the
        location and photos before saving.
      </p>

      <form onSubmit={submit} className="card col">
        <label className="col">
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            minLength={2}
            maxLength={120}
            required
          />
        </label>
        <label className="col">
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={2000}
            rows={3}
          />
        </label>
        <div className="row">
          <label className="col" style={{ flex: 1 }}>
            Latitude
            <input
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              placeholder="45.46420"
              required
            />
          </label>
          <label className="col" style={{ flex: 1 }}>
            Longitude
            <input
              value={lng}
              onChange={(e) => setLng(e.target.value)}
              placeholder="9.18998"
              required
            />
          </label>
        </div>
        <label className="col">
          Difficulty (1–5)
          <input
            type="number"
            min={1}
            max={5}
            value={difficulty}
            onChange={(e) => setDifficulty(Number(e.target.value))}
            required
          />
        </label>
        <label className="col">
          Photo URLs (one per line)
          <textarea
            value={photoUrls}
            onChange={(e) => setPhotoUrls(e.target.value)}
            rows={3}
            placeholder="https://…"
          />
        </label>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
        <button type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Create verified spot'}
        </button>
      </form>
    </div>
  );
}
