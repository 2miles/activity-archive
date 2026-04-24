import { useEffect, useState } from 'react';

const FEATURED_PATHS = [
  'heatmaps/running_distance_grid.html',
  'heatmaps/all_routes_pink_purple.html',
  'heatmaps/all_routes_original.html',
  'reports/runs_log.txt',
  'reports/activity_log.txt',
];

function formatDateTime(value) {
  if (!value) {
    return 'Never';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function sortArtifacts(artifacts) {
  return [...artifacts].sort((a, b) => a.label.localeCompare(b.label));
}

function bytesLabel(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unit = units[0];

  for (const nextUnit of units) {
    unit = nextUnit;
    if (value < 1024 || nextUnit === units.at(-1)) {
      break;
    }
    value /= 1024;
  }

  return `${value.toFixed(value >= 10 ? 0 : 1)} ${unit}`;
}

function buildFeaturedArtifacts(artifacts) {
  const byPath = new Map(
    artifacts.map((artifact) => [artifact.path, artifact]),
  );
  const featured = FEATURED_PATHS.map((path) => byPath.get(path)).filter(
    Boolean,
  );
  const featuredPaths = new Set(featured.map((artifact) => artifact.path));
  const remaining = artifacts.filter(
    (artifact) => !featuredPaths.has(artifact.path),
  );
  return { featured, remaining };
}

function ArtifactCard({ artifact }) {
  return (
    <a
      className="artifact-card"
      href={artifact.url}
      target="_blank"
      rel="noreferrer"
    >
      <div className="artifact-kind">{artifact.kind}</div>
      <h3>{artifact.label}</h3>
      <p>{artifact.path}</p>
      <span>{bytesLabel(artifact.bytes)}</span>
    </a>
  );
}

function StatusPill({ state, running }) {
  const tone = running ? 'running' : state;

  return (
    <span className={`status-pill ${tone}`}>
      {running ? 'Running' : state.charAt(0).toUpperCase() + state.slice(1)}
    </span>
  );
}

export default function App() {
  const [health, setHealth] = useState('loading');
  const [syncStatus, setSyncStatus] = useState(null);
  const [artifacts, setArtifacts] = useState([]);
  const [syncMessage, setSyncMessage] = useState('');
  const [syncSubmitting, setSyncSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        const [healthResponse, statusResponse, artifactsResponse] =
          await Promise.all([
            fetch('/api/health'),
            fetch('/api/sync/status'),
            fetch('/api/artifacts'),
          ]);

        if (!healthResponse.ok || !statusResponse.ok || !artifactsResponse.ok) {
          throw new Error('Backend request failed');
        }

        const [healthJson, statusJson, artifactsJson] = await Promise.all([
          healthResponse.json(),
          statusResponse.json(),
          artifactsResponse.json(),
        ]);

        if (cancelled) {
          return;
        }

        setHealth(healthJson.status);
        setSyncStatus(statusJson);
        setArtifacts(sortArtifacts(artifactsJson));
        setErrorMessage('');
      } catch (error) {
        if (!cancelled) {
          setHealth('error');
          setErrorMessage('Could not reach the FastAPI server.');
        }
      }
    }

    loadDashboard();

    const timer = window.setInterval(loadDashboard, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  async function handleSync() {
    setSyncSubmitting(true);
    setSyncMessage('');
    setErrorMessage('');

    try {
      const response = await fetch('/api/sync', {
        method: 'POST',
      });
      const payload = await response.json();

      if (!response.ok) {
        const message = payload?.detail?.message || 'Could not start sync.';
        setSyncMessage(message);
        if (payload?.detail?.status) {
          setSyncStatus(payload.detail.status);
        }
        return;
      }

      setSyncStatus(payload.status);
      setSyncMessage(payload.message);
    } catch (error) {
      setErrorMessage('Sync request failed.');
    } finally {
      setSyncSubmitting(false);
    }
  }

  const { featured, remaining } = buildFeaturedArtifacts(artifacts);

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="eyebrow">Activity Archive</span>
          <h1>Local dashboard for your Strava archive pipeline.</h1>
          <p>
            Trigger sync, check the current pipeline state, and open the
            generated reports and heatmaps from one place.
          </p>
        </div>

        <div className="sync-panel">
          <div className="sync-topline">
            <div>
              <span className="label">Backend</span>
              <strong>{health === 'ok' ? 'Connected' : 'Unavailable'}</strong>
            </div>
            {syncStatus ? (
              <StatusPill
                state={syncStatus.state}
                running={syncStatus.running}
              />
            ) : null}
          </div>

          <button
            className="sync-button"
            type="button"
            onClick={handleSync}
            disabled={syncSubmitting || syncStatus?.running || health !== 'ok'}
          >
            {syncSubmitting
              ? 'Starting...'
              : syncStatus?.running
                ? 'Sync Running'
                : 'Run Sync'}
          </button>

          <dl className="status-grid">
            <div>
              <dt>Last started</dt>
              <dd>{formatDateTime(syncStatus?.last_started_at)}</dd>
            </div>
            <div>
              <dt>Last finished</dt>
              <dd>{formatDateTime(syncStatus?.last_finished_at)}</dd>
            </div>
            <div>
              <dt>Last success</dt>
              <dd>{formatDateTime(syncStatus?.last_success_at)}</dd>
            </div>
            <div>
              <dt>Last error</dt>
              <dd>{syncStatus?.last_error || 'None'}</dd>
            </div>
          </dl>

          {syncMessage ? <p className="notice success">{syncMessage}</p> : null}
          {errorMessage ? <p className="notice error">{errorMessage}</p> : null}
        </div>
      </section>

      <section className="content-section">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Featured</span>
            <h2>Primary outputs</h2>
          </div>
          <p>
            The highest-signal reports and visualizations from the current
            derived set.
          </p>
        </div>

        <div className="artifact-grid">
          {featured.map((artifact) => (
            <ArtifactCard key={artifact.path} artifact={artifact} />
          ))}
        </div>
      </section>

      <section className="content-section secondary">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Archive View</span>
            <h2>All listed artifacts</h2>
          </div>
          <p>Non-image outputs exposed by the FastAPI server.</p>
        </div>

        <div className="artifact-list">
          {remaining.map((artifact) => (
            <a
              key={artifact.path}
              className="artifact-row"
              href={artifact.url}
              target="_blank"
              rel="noreferrer"
            >
              <span>{artifact.label}</span>
              <span>{artifact.kind}</span>
              <span>{bytesLabel(artifact.bytes)}</span>
            </a>
          ))}
        </div>
      </section>
    </main>
  );
}
