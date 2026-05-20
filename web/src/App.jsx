import { useEffect, useState } from 'react';

const FEATURED_PATHS = [
  'reports/runs_log.html',
  'reports/activity_log.html',
  'heatmaps/running_distance_grid.html',
  'heatmaps/all_routes_pink_purple.html',
  'heatmaps/all_routes_original.html',
];

const FEATURED_LABELS = {
  'reports/runs_log.html': 'Run Log',
  'heatmaps/running_distance_grid.html': 'Calendar Heatmap',
  'heatmaps/all_routes_pink_purple.html': 'Route Heatmap',
  'heatmaps/all_routes_original.html': 'All Routes Map',
};

const HIDDEN_OUTPUT_PREFIXES = ['maps/', 'thumbnails/'];
const HIDDEN_OUTPUT_FILES = new Set(['README.md', '.DS_Store']);

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

function buildFeaturedArtifacts(artifacts) {
  const visibleArtifacts = artifacts.filter(
    (artifact) =>
      !HIDDEN_OUTPUT_FILES.has(artifact.path) &&
      !HIDDEN_OUTPUT_PREFIXES.some((prefix) => artifact.path.startsWith(prefix)),
  );
  const byPath = new Map(
    visibleArtifacts.map((artifact) => [artifact.path, artifact]),
  );
  const featured = FEATURED_PATHS.map((path) => {
    const artifact = byPath.get(path);
    if (!artifact) {
      return null;
    }
    return {
      ...artifact,
      label: FEATURED_LABELS[path] || artifact.label,
    };
  }).filter(Boolean);
  const featuredPaths = new Set(featured.map((artifact) => artifact.path));
  const remaining = visibleArtifacts.filter(
    (artifact) => !featuredPaths.has(artifact.path),
  );
  return { featured, remaining };
}

const ListPreview = ({ variant = 'run' }) => {
  const rows =
    variant === 'activity'
      ? [
          ['#cfeee0', '#164e47', '#dff4e8'],
          ['#f0e1ff', '#5a3180', '#f7edff'],
          ['#d9e9ff', '#214f82', '#edf5ff'],
          ['#ffe3cc', '#7b4217', '#fff0e3'],
        ]
      : [
          ['#d8f3dc', '#164e47', '#edf8ef'],
          ['#cfeee0', '#164e47', '#f1faf3'],
          ['#bfe6d0', '#164e47', '#e8f6ed'],
          ['#d8f3dc', '#164e47', '#f5fbf6'],
        ];

  return (
    <svg className="artifact-preview" viewBox="0 0 132 84" aria-hidden="true">
      <rect className="preview-surface" x="1" y="1" width="130" height="82" rx="12" />
      {rows.map(([chip, line, fill], index) => {
        const y = 13 + index * 17;
        return (
          <g key={`${variant}-${index}`}>
            <rect x="12" y={y - 4} width="108" height="12" rx="6" fill={fill} />
            <circle cx="20" cy={y + 2} r="3.5" fill={chip} />
            <rect x="30" y={y - 1} width={index % 2 === 0 ? 56 : 42} height="2.5" rx="1.25" fill={line} opacity="0.8" />
            <rect x="94" y={y - 1} width="16" height="2.5" rx="1.25" fill={line} opacity="0.35" />
          </g>
        );
      })}
    </svg>
  );
};

const CalendarPreview = () => {
  const fills = [
    '#e9f7ec',
    '#d6f0dc',
    '#b9e7c5',
    '#83d79a',
    '#4fb96c',
  ];

  return (
    <svg className="artifact-preview" viewBox="0 0 132 84" aria-hidden="true">
      <rect className="preview-surface" x="1" y="1" width="130" height="82" rx="12" />
      {Array.from({ length: 7 }).map((_, row) =>
        Array.from({ length: 12 }).map((__, col) => {
          const value = (row * 3 + col * 5 + (col > 7 ? 2 : 0)) % fills.length;
          return (
            <rect
              key={`${row}-${col}`}
              x={12 + col * 9}
              y={10 + row * 9}
              width="6"
              height="6"
              rx="1.5"
              fill={fills[value]}
            />
          );
        }),
      )}
    </svg>
  );
};

const RoutesPreview = ({ variant = 'original' }) => {
  const routes = [
    'M14 24 L38 24 L38 42 L64 42 L64 28 L96 28 L96 57 L120 57',
    'M17 60 L37 60 L37 44 L64 44 L64 61 L88 61 L88 45 L117 45',
    'M25 15 L25 34 L51 34 L51 43 L78 43 L78 33 L111 33',
    'M13 50 L31 50 L31 35 L63 35 L63 17 L93 17 L93 34 L119 34',
    'M52 71 L52 56 L66 56 L66 41 L96 41 L96 20',
    'M21 43 L48 43 L48 31 L65 31 L65 43 L101 43 L101 62',
    'M32 66 L32 52 L63 52 L63 43 L87 43 L87 25',
    'M37 44 L64 44 L64 43 L92 43',
    'M39 42 L64 42 L64 44 L94 44',
    'M35 45 L63 45 L63 42 L90 42',
  ];
  const isGlow = variant === 'glow';

  return (
    <svg className="artifact-preview route-preview" viewBox="0 0 132 84" aria-hidden="true">
      <rect className="preview-surface" x="1" y="1" width="130" height="82" rx="12" />
      <path d="M0 57 L132 18" stroke="#dce8dc" strokeWidth="1" opacity="0.8" />
      <path d="M0 27 L132 66" stroke="#dce8dc" strokeWidth="1" opacity="0.65" />
      {routes.map((route) =>
        isGlow ? (
          <g key={route}>
            <path d={route} fill="none" stroke="#33006E" strokeWidth="6" strokeLinecap="round" opacity="0.1" />
            <path d={route} fill="none" stroke="#FF006E" strokeWidth="1.5" strokeLinecap="round" opacity="0.66" />
          </g>
        ) : (
          <path key={route} d={route} fill="none" stroke="#FF006E" strokeWidth="1.5" strokeLinecap="round" opacity="1" />
        ),
      )}
    </svg>
  );
};

const ArtifactPreview = ({ path }) => {
  if (path === 'reports/runs_log.html') {
    return <ListPreview />;
  }
  if (path === 'reports/activity_log.html') {
    return <ListPreview variant="activity" />;
  }
  if (path === 'heatmaps/running_distance_grid.html') {
    return <CalendarPreview />;
  }
  if (path === 'heatmaps/all_routes_pink_purple.html') {
    return <RoutesPreview variant="glow" />;
  }
  if (path === 'heatmaps/all_routes_original.html') {
    return <RoutesPreview />;
  }

  return null;
};

const ArtifactCard = ({ artifact }) => {
  return (
    <a
      className="artifact-card"
      href={artifact.url}
      target="_blank"
      rel="noreferrer"
    >
      <h3>{artifact.label}</h3>
      <ArtifactPreview path={artifact.path} />
    </a>
  );
};

const StatusPill = ({ state, running }) => {
  const tone = running ? 'running' : state;

  return (
    <span className={`status-pill ${tone}`}>
      {running ? 'Running' : state.charAt(0).toUpperCase() + state.slice(1)}
    </span>
  );
};

const App = () => {
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
          <h1>Activity Archive Dashboard</h1>
          <p>
            Sync new Strava activity data into your local archive, then view
            custom heatmaps, data grids, route maps, and run logs.
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
            <span className="eyebrow">Open</span>
            <h2>Maps and Logs</h2>
          </div>
          <p>
            Quick links to the views you use most: run logs, activity logs,
            heatmaps, and route maps.
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
            <span className="eyebrow">Files</span>
            <h2>More Outputs</h2>
          </div>
          <p>Additional generated files from the local archive.</p>
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
            </a>
          ))}
        </div>
      </section>
    </main>
  );
};

export default App;
