'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { getSupabase, isAdmin, isConfigured } from '@/lib/supabase';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const db = getSupabase();
      const { error: authError } = await db.auth.signInWithPassword({
        email,
        password,
      });
      if (authError) throw new Error(authError.message);

      // Le RLS bloccherebbero comunque un non-admin, ma lasciarlo entrare in una
      // schermata che poi non fa niente è solo confusione.
      if (!(await isAdmin())) {
        await db.auth.signOut();
        throw new Error('Questo account non ha i permessi di moderazione.');
      }

      router.push('/spots');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Accesso non riuscito');
    } finally {
      setLoading(false);
    }
  }

  if (!isConfigured) {
    return (
      <div className="container" style={{ maxWidth: 520 }}>
        <h1>Console di moderazione</h1>
        <div className="card">
          <p>
            Configurazione Supabase assente. Imposta{' '}
            <code>NEXT_PUBLIC_SUPABASE_URL</code> e{' '}
            <code>NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY</code> — vedi{' '}
            <code>.env.example</code>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container" style={{ maxWidth: 420 }}>
      <h1>Console di moderazione</h1>
      <form onSubmit={submit} className="card col">
        <label className="col">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <label className="col">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Accesso…' : 'Entra'}
        </button>
      </form>
    </div>
  );
}
