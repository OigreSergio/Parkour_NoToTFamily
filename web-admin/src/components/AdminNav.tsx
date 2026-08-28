'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const SECTIONS = [
  { href: '/spots', label: 'Spot in attesa' },
  { href: '/reports', label: 'Segnalazioni' },
  { href: '/contributions', label: 'Contributi' },
  { href: '/users', label: 'Utenti' },
] as const;

export function AdminNav() {
  const here = usePathname();

  return (
    <nav className="row" style={{ gap: 4, flexWrap: 'wrap', marginBottom: 16 }}>
      {SECTIONS.map((s) => (
        <Link
          key={s.href}
          href={s.href}
          style={{
            padding: '6px 12px',
            borderRadius: 8,
            textDecoration: 'none',
            fontWeight: here === s.href ? 700 : 400,
            border: '1px solid var(--border, #333)',
          }}
        >
          {s.label}
        </Link>
      ))}
    </nav>
  );
}

/**
 * Chiede una motivazione, e non accetta il vuoto.
 *
 * Ogni decisione di moderazione deve averne una: l'art. 17 DSA impone di dire
 * all'autore perché, e una casella facoltativa si lascia vuota sempre.
 */
export function askReason(question: string): string | null {
  const answer = window.prompt(question);
  if (answer === null) return null;
  if (answer.trim() === '') {
    window.alert('La motivazione è obbligatoria: va comunicata all\'autore.');
    return null;
  }
  return answer.trim();
}
