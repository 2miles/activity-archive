import { useEffect, useState } from 'react';

const FEATURED_PATHS = [
  'reports/runs_log.html',
  'reports/running_volume.html',
  'heatmaps/running_distance_grid.html',
  'reports/activity_log.html',
  'heatmaps/map.html',
];

const TEXT_EXPORTS = [
  { path: 'activities.csv', label: 'Activities', format: 'CSV' },
  { path: 'reports/activity_log.txt', label: 'Activity Log', format: 'TXT' },
  { path: 'reports/runs_log.txt', label: 'Runs Log', format: 'TXT' },
  { path: 'reports/runs_log.md', label: 'Runs Log', format: 'Markdown' },
];

const FEATURED_LABELS = {
  'reports/runs_log.html': 'Running Log',
  'reports/running_volume.html': 'Running Graph',
  'heatmaps/running_distance_grid.html': 'Running Grid',
  'heatmaps/map.html': 'Activity Maps',
};

const HIDDEN_OUTPUT_PREFIXES = ['maps/', 'thumbnails/'];
const HIDDEN_OUTPUT_FILES = new Set(['README.md', '.DS_Store']);
const HIDDEN_OUTPUT_SEGMENTS = new Set(['@synoresource', '@eadir']);

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

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch (error) {
      // Fall through for browsers that expose Clipboard API on an insecure URL.
    }
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  textarea.remove();
  if (!copied) {
    throw new Error('Clipboard unavailable');
  }
}

function buildFeaturedArtifacts(artifacts) {
  const visibleArtifacts = artifacts.filter(
    (artifact) =>
      !HIDDEN_OUTPUT_FILES.has(artifact.path) &&
      !artifact.path
        .split('/')
        .some(
          (segment) =>
            segment.startsWith('@') ||
            HIDDEN_OUTPUT_SEGMENTS.has(segment.toLowerCase()),
        ) &&
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
  const exportPaths = new Set(TEXT_EXPORTS.map((item) => item.path));
  const exports = TEXT_EXPORTS.map((item) => {
    const artifact = byPath.get(item.path);
    return artifact ? { ...artifact, ...item } : null;
  }).filter(Boolean);
  const remaining = visibleArtifacts.filter(
    (artifact) =>
      !featuredPaths.has(artifact.path) && !exportPaths.has(artifact.path),
  );
  return { featured, exports, remaining };
}

const RunningLogPreview = () => {
  const rows = [29, 42, 55, 68];

  return (
    <svg className="artifact-preview" viewBox="0 0 132 84" aria-hidden="true">
      <rect className="preview-surface" x="1" y="1" width="130" height="82" rx="12" />
      <line x1="10" y1="12" x2="122" y2="12" stroke="#8ee05d" strokeWidth="1" />
      <rect x="10" y="19" width="9" height="2" rx="1" fill="#b7c2ba" />
      <rect x="53" y="19" width="10" height="2" rx="1" fill="#b7c2ba" />
      <rect x="84" y="19" width="9" height="2" rx="1" fill="#b7c2ba" />
      <rect x="110" y="19" width="10" height="2" rx="1" fill="#b7c2ba" />
      {rows.map((y, index) => (
        <g key={y}>
          <line x1="10" y1={y + 5} x2="122" y2={y + 5} stroke="#303a33" strokeWidth="1" />
          <rect x="10" y={y} width={15 + index * 2} height="2.5" rx="1" fill="#eef4ef" />
          <rect x="54" y={y} width="8" height="2.5" rx="1" fill="#eef4ef" />
          <rect x="83" y={y} width="13" height="2.5" rx="1" fill="#eef4ef" />
          <rect x="109" y={y} width="11" height="2.5" rx="1" fill="#eef4ef" />
        </g>
      ))}
    </svg>
  );
};

const ActivityLogPreview = () => {
  const rows = [
    [29, '#72df91'],
    [42, '#62b0ff'],
    [55, '#ff8b7b'],
    [68, '#f2c94c'],
  ];

  return (
    <svg className="artifact-preview" viewBox="0 0 132 84" aria-hidden="true">
      <rect className="preview-surface" x="1" y="1" width="130" height="82" rx="12" />
      <line x1="10" y1="12" x2="122" y2="12" stroke="#8ee05d" strokeWidth="1" />
      <rect x="10" y="19" width="9" height="2" rx="1" fill="#b7c2ba" />
      <rect x="42" y="19" width="9" height="2" rx="1" fill="#b7c2ba" />
      <rect x="82" y="19" width="10" height="2" rx="1" fill="#b7c2ba" />
      <rect x="109" y="19" width="11" height="2" rx="1" fill="#b7c2ba" />
      {rows.map(([y, typeColor], index) => (
        <g key={y}>
          <line x1="10" y1={y + 5} x2="122" y2={y + 5} stroke="#303a33" strokeWidth="1" />
          <rect x="10" y={y} width={14 + index * 2} height="2.5" rx="1" fill="#eef4ef" />
          <rect x="42" y={y} width="17" height="2.5" rx="1" fill={typeColor} />
          <rect x="83" y={y} width="8" height="2.5" rx="1" fill="#eef4ef" />
          <rect x="108" y={y} width="12" height="2.5" rx="1" fill="#eef4ef" />
        </g>
      ))}
    </svg>
  );
};

const CalendarPreview = () => {
  const fills = [
    '#1c2720',
    '#08713a',
    '#15964a',
    '#55d45f',
    '#bde64b',
    '#f2dc3f',
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

const VolumePreview = () => {
  const bars = [10, 24, 15, 36, 20, 46, 27, 55, 32, 49, 23, 52, 39, 28];

  return (
    <svg className="artifact-preview" viewBox="0 0 132 84" aria-hidden="true">
      <defs>
        <linearGradient id="volume-preview-gradient" x1="0" y1="74" x2="0" y2="16" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#08713a" />
          <stop offset="50%" stopColor="#55d45f" />
          <stop offset="100%" stopColor="#f2dc3f" />
        </linearGradient>
      </defs>
      <rect className="preview-surface" x="1" y="1" width="130" height="82" rx="12" />
      <line x1="10" y1="12" x2="122" y2="12" stroke="#8ee05d" strokeWidth="1" />
      {[22, 39, 56, 74].map((y) => (
        <line key={y} x1="14" y1={y} x2="122" y2={y} stroke="#354139" strokeWidth="1" />
      ))}
      {[41, 68, 95].map((x) => (
        <line key={x} x1={x} y1="16" x2={x} y2="74" stroke="#59665e" strokeWidth="1" opacity="0.82" />
      ))}
      {bars.map((height, index) => (
        <rect
          key={index}
          x={16 + index * 7.4}
          y={74 - height}
          width="3"
          height={height}
          fill="url(#volume-preview-gradient)"
        />
      ))}
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

const TextExportsPreview = () => {
  return (
    <svg className="artifact-preview" viewBox="0 0 132 84" aria-hidden="true">
      <rect className="preview-surface" x="1" y="1" width="130" height="82" rx="12" />
      <path d="M37 17h48l12 12v40H37z" fill="none" stroke="#657168" strokeWidth="1.5" />
      <path d="M85 17v12h12" fill="none" stroke="#657168" strokeWidth="1.5" />
      <rect x="47" y="37" width="38" height="3" rx="1.5" fill="#eef4ef" />
      <rect x="47" y="47" width="30" height="3" rx="1.5" fill="#b7c2ba" />
      <rect x="47" y="57" width="35" height="3" rx="1.5" fill="#b7c2ba" />
    </svg>
  );
};

const ArtifactPreview = ({ path }) => {
  if (path === 'reports/runs_log.html') {
    return <RunningLogPreview />;
  }
  if (path === 'reports/running_volume.html') {
    return <VolumePreview />;
  }
  if (path === 'reports/activity_log.html') {
    return <ActivityLogPreview />;
  }
  if (path === 'heatmaps/running_distance_grid.html') {
    return <CalendarPreview />;
  }
  if (path === 'heatmaps/map.html') {
    return <RoutesPreview variant="glow" />;
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

const TextExportsCard = ({ expanded, onToggle }) => (
  <button
    className="artifact-card text-exports-card"
    type="button"
    aria-expanded={expanded}
    aria-controls="text-exports-panel"
    onClick={onToggle}
  >
    <div className="text-exports-title">
      <h3>Text Exports</h3>
      <span>
        {expanded ? 'Hide files' : 'Show files'}
        <i aria-hidden="true">⌄</i>
      </span>
    </div>
    <TextExportsPreview />
  </button>
);

const TextExportsPanel = ({ artifacts, copyStatus, onCopy }) => (
  <div className="text-exports-panel" id="text-exports-panel">
    {artifacts.map((artifact) => (
      <div className="text-export-row" key={artifact.path}>
        <div>
          <strong>{artifact.label}</strong>
          <span>{artifact.format}</span>
        </div>
        <div className="text-export-actions">
          <button type="button" onClick={() => onCopy(artifact)}>
            {copyStatus[artifact.path] || 'Copy'}
          </button>
          <a href={artifact.url} target="_blank" rel="noreferrer">Open</a>
        </div>
      </div>
    ))}
  </div>
);

const App = () => {
  const [health, setHealth] = useState('loading');
  const [syncStatus, setSyncStatus] = useState(null);
  const [artifacts, setArtifacts] = useState([]);
  const [syncMessage, setSyncMessage] = useState('');
  const [syncSubmitting, setSyncSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [exportsOpen, setExportsOpen] = useState(false);
  const [copyStatus, setCopyStatus] = useState({});

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

  async function handleCopyExport(artifact) {
    setCopyStatus((current) => ({ ...current, [artifact.path]: 'Copying…' }));
    try {
      const response = await fetch(artifact.url);
      if (!response.ok) {
        throw new Error('Could not load export');
      }
      await copyText(await response.text());
      setCopyStatus((current) => ({ ...current, [artifact.path]: 'Copied' }));
      window.setTimeout(() => {
        setCopyStatus((current) => ({ ...current, [artifact.path]: 'Copy' }));
      }, 1600);
    } catch (error) {
      setCopyStatus((current) => ({ ...current, [artifact.path]: 'Failed' }));
    }
  }

  const { featured, exports, remaining } = buildFeaturedArtifacts(artifacts);
  const syncState = syncStatus?.running ? 'running' : syncStatus?.state;
  const syncStateLabel = syncStatus
    ? syncStatus.running
      ? 'Running'
      : syncStatus.state.charAt(0).toUpperCase() + syncStatus.state.slice(1)
    : 'Loading';

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <h1>Activity <span>Archive</span></h1>
        </div>

        <div className="sync-panel">
          <div className="sync-stat">
            <span className="label">Connection</span>
            <strong>{health === 'ok' ? 'Connected' : 'Unavailable'}</strong>
          </div>

          <div className="sync-stat">
            <span className="label">Status</span>
            <strong className={`sync-state ${syncState || ''}`}>
              {syncStateLabel}
            </strong>
          </div>

          <div className="sync-stat">
            <span className="label">Last sync</span>
            <strong>{formatDateTime(syncStatus?.last_success_at)}</strong>
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

          {syncMessage ? <p className="notice success">{syncMessage}</p> : null}
          {errorMessage ? <p className="notice error">{errorMessage}</p> : null}
        </div>
      </section>

      <section className="artifact-section" aria-label="Featured outputs">
        <div className="artifact-grid">
          {featured.map((artifact) => (
            <ArtifactCard key={artifact.path} artifact={artifact} />
          ))}
          <TextExportsCard
            expanded={exportsOpen}
            onToggle={() => setExportsOpen((open) => !open)}
          />
        </div>
        {exportsOpen ? (
          <TextExportsPanel
            artifacts={exports}
            copyStatus={copyStatus}
            onCopy={handleCopyExport}
          />
        ) : null}
      </section>

      {remaining.length ? (
        <section className="artifact-section" aria-label="Additional outputs">
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
      ) : null}
    </main>
  );
};

export default App;
