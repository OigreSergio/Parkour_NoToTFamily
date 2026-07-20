'use client';

import { useEffect, useState } from 'react';

const REPO_URL = 'https://github.com/OigreSergio/Parkour_NoToTFamily';
// 📲 url-encoded — the backup folder at the repo root.
const FOLDER_URL = `${REPO_URL}/tree/main/%F0%9F%93%B2`;
const MANIFEST_RAW_URL =
  'https://raw.githubusercontent.com/OigreSergio/Parkour_NoToTFamily/main/%F0%9F%93%B2/backup-latest.json';
const WORKFLOW_URL = `${REPO_URL}/actions/workflows/backup.yml`;

interface BackupBranch {
  name: string;
  sha: string;
  zip_url: string;
  branch_url: string;
}

interface BackupManifest {
  generated_at: string;
  expires_at: string;
  branches: BackupBranch[];
  datasets: { path: string; sha256: string; bytes: number }[];
}

/// Admin logistics view of the 24h backup rotation (📲 folder): shows the
/// live manifest, whether the current cycle is still valid, and the direct
/// links to regenerate or download the full bundle. Read-only — the rotation
/// itself runs in CI (.github/workflows/backup.yml).
export default function BackupPage() {
  const [manifest, setManifest] = useState<BackupManifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(MANIFEST_RAW_URL, { cache: 'no-store' })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: BackupManifest) => setManifest(data))
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load manifest'),
      );
  }, []);

  const expired =
    manifest !== null && new Date(manifest.expires_at).getTime() < Date.now();

  return (
    <div className="container">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h1>📲 Backup (24h rotation)</h1>
        <a href={WORKFLOW_URL} target="_blank" rel="noreferrer">
          Run / history →
        </a>
      </div>

      <div className="card col">
        <p>
          The <a href={FOLDER_URL} target="_blank" rel="noreferrer">📲 folder</a>{' '}
          holds the backup manifest, destroyed and regenerated every 24 hours by
          the <a href={WORKFLOW_URL} target="_blank" rel="noreferrer">Daily backup</a>{' '}
          workflow. The full repository bundle (every branch) is an artifact of the
          same run and self-destructs after 1 day.
        </p>
        <p className="muted">
          Restore: download the artifact, then{' '}
          <code>git clone parkour-notot-full-backup.bundle restored/</code>
        </p>
      </div>

      {error && (
        <p style={{ color: 'var(--danger)' }}>
          Could not load the live manifest ({error}) — open the{' '}
          <a href={FOLDER_URL} target="_blank" rel="noreferrer">📲 folder</a>{' '}
          directly.
        </p>
      )}
      {manifest === null && !error && <p className="muted">Loading manifest…</p>}

      {manifest && (
        <div className="card col">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h2 style={{ margin: 0 }}>Current cycle</h2>
            <span style={{ color: expired ? 'var(--danger)' : 'var(--ok)' }}>
              {expired ? 'EXPIRED — next run will regenerate' : 'VALID'}
            </span>
          </div>
          <p className="muted">
            Generated {new Date(manifest.generated_at).toLocaleString()} — expires{' '}
            {new Date(manifest.expires_at).toLocaleString()}
          </p>

          <h2>Branches covered ({manifest.branches.length})</h2>
          {manifest.branches.map((branch) => (
            <div key={branch.name} className="row" style={{ justifyContent: 'space-between' }}>
              <a href={branch.branch_url} target="_blank" rel="noreferrer">
                {branch.name}
              </a>
              <span className="row" style={{ gap: 12 }}>
                <code className="muted">{branch.sha.slice(0, 10)}</code>
                <a href={branch.zip_url}>zip</a>
              </span>
            </div>
          ))}

          {manifest.datasets.length > 0 && (
            <>
              <h2>Dataset checksums</h2>
              {manifest.datasets.map((dataset) => (
                <p key={dataset.path} className="muted" style={{ margin: 0 }}>
                  <code>{dataset.path}</code> — sha256{' '}
                  <code>{dataset.sha256.slice(0, 16)}…</code> ({dataset.bytes} bytes)
                </p>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
