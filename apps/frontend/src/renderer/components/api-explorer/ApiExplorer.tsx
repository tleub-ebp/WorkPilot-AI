import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import {
  Search,
  Send,
  ChevronDown,
  ChevronRight,
  Plus,
  Trash2,
  Download,
  Copy,
  Check,
  RefreshCw,
  Globe,
  Settings,
  X,
  AlertCircle,
  Loader2,
  ExternalLink,
  ScanSearch,
  Play,
  Shield,
} from 'lucide-react';
import { Button } from '@/components/ui';
import { useProjectStore } from '../../stores/project-store';
import { useProjectRouteScan } from '../../hooks/useProjectRouteScan';
import {
  useApiExplorerStore,
  makeEndpointKey,
  type ApiEnvironment,
  type OpenApiSpec,
  type OpenApiOperation,
  type OpenApiParameter,
  type AuthType,
  type OAuth2GrantType,
} from '../../stores/api-explorer-store';
import {
  useAppEmulatorStore,
  setupAppEmulatorListeners,
  openAppEmulatorDialog,
} from '../../stores/app-emulator-store';

// ── Environment Auto-Detection ───────────────────────────────────────────────

interface DetectedEnvironment {
  name: string;
  baseUrl: string;
  headers: Record<string, string>;
  source: string; // file origin
}

/** Parse a .env file content into key=value pairs */
function parseEnvFile(content: string): Record<string, string> {
  const result: Record<string, string> = {};
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx < 1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    let val = trimmed.slice(eqIdx + 1).trim();
    // Strip surrounding quotes
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    result[key] = val;
  }
  return result;
}

/** Return true if value looks like an HTTP(S) URL */
function isUrl(val: string): boolean {
  return /^https?:\/\/[^\s]+/.test(val);
}

/** Pick the most relevant URL from a parsed env object */
function pickBestUrl(vars: Record<string, string>): string | null {
  // Priority: known keys first
  const priority = [
    'VITE_BACKEND_URL',
    'BACKEND_URL',
    'API_URL',
    'API_BASE_URL',
    'REACT_APP_API_URL',
    'NEXT_PUBLIC_API_URL',
    'APP_URL',
    'BASE_URL',
  ];
  for (const key of priority) {
    if (vars[key] && isUrl(vars[key])) return vars[key];
  }
  // Fallback: any key ending in _URL, _BASE_URL, _API_URL, _ENDPOINT that looks like URL
  const urlPatterns = [/_URL$/, /_BASE_URL$/, /_API_URL$/, /_ENDPOINT$/, /_HOST$/];
  for (const [key, val] of Object.entries(vars)) {
    if (urlPatterns.some((p) => p.test(key)) && isUrl(val)) return val;
  }
  return null;
}

/** Derive a human-readable env name from a filename */
function envNameFromFile(filename: string): string {
  const base = filename.replace(/^\.env\.?/, '').replace(/^\./, '');
  if (!base) return 'Default';
  return base.charAt(0).toUpperCase() + base.slice(1);
}

async function detectEnvironmentsFromProject(projectPath: string): Promise<DetectedEnvironment[]> {
  const filesToScan = [
    '.env',
    '.env.local',
    '.env.development',
    '.env.staging',
    '.env.stage',
    '.env.production',
    '.env.prod',
    '.env.test',
    'apps/frontend/.env',
    'apps/frontend/.env.local',
    'apps/frontend/.env.staging',
    'apps/frontend/.env.production',
  ];

  const detected: DetectedEnvironment[] = [];
  const seenUrls = new Set<string>();

  for (const relPath of filesToScan) {
    const fullPath = `${projectPath}/${relPath}`.replaceAll('\\', '/');
    try {
      const result = await globalThis.electronAPI.readFile(fullPath);
      if (!result.success || !result.data) continue;

      const vars = parseEnvFile(result.data);
      const url = pickBestUrl(vars);
      if (!url || seenUrls.has(url)) continue;

      seenUrls.add(url);
      const filename = relPath.split('/').pop() ?? relPath;
      detected.push({
        name: envNameFromFile(filename),
        baseUrl: url,
        headers: {},
        source: relPath,
      });
    } catch {
      // File doesn't exist — skip silently
    }
  }

  return detected;
}

// ── Utilities ────────────────────────────────────────────────────────────────

const HTTP_METHOD_COLORS: Record<string, string> = {
  GET: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
  POST: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
  PUT: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
  DELETE: 'text-red-400 bg-red-400/10 border-red-400/30',
  PATCH: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
  HEAD: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
  OPTIONS: 'text-gray-400 bg-gray-400/10 border-gray-400/30',
};

const STATUS_COLORS: Record<string, string> = {
  '2': 'text-emerald-400',
  '3': 'text-blue-400',
  '4': 'text-amber-400',
  '5': 'text-red-400',
};

function getStatusColor(status: number): string {
  return STATUS_COLORS[String(status)[0]] ?? 'text-gray-400';
}

function prettyJson(value: string): string {
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function prettifyXml(value: string): string {
  let formatted = '';
  let indent = 0;
  const lines = value.replaceAll(/>\s*</g, '>\n<').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith('</')) indent = Math.max(0, indent - 1);
    formatted += '  '.repeat(indent) + trimmed + '\n';
    if (!trimmed.endsWith('/>') && !trimmed.startsWith('</') && /^<[^?!]/.test(trimmed) && !/<.*>.*<\/.*>/.test(trimmed)) {
      indent++;
    }
  }
  return formatted.trimEnd();
}

// HTML-escape a string for safe insertion into innerHTML
function escapeHtml(s: string): string {
  return s
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

// Returns an HTML string with syntax-highlighted JSON
function syntaxHighlightJson(value: string): string {
  let pretty: string;
  try {
    pretty = JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return escapeHtml(value);
  }
  return escapeHtml(pretty).replaceAll(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      if (match.startsWith('"')) {
        if (match.endsWith(':')) {
          return `<span style="color:var(--color-primary)">${match}</span>`;
        }
        return `<span style="color:#98c379">${match}</span>`;
      }
      if (/true|false/.test(match)) return `<span style="color:#e5c07b">${match}</span>`;
      if (/null/.test(match)) return `<span style="color:#abb2bf">${match}</span>`;
      return `<span style="color:#d19a66">${match}</span>`;
    }
  );
}

function detectContentType(headers: Record<string, string>): string {
  const ct = headers['content-type'] ?? headers['Content-Type'] ?? '';
  return ct.toLowerCase();
}

function resolveRef(ref: string, spec: OpenApiSpec): Record<string, unknown> | null {
  if (!ref.startsWith('#/')) return null;
  const parts = ref.slice(2).split('/');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let current: any = spec;
  for (const part of parts) {
    if (!current || typeof current !== 'object') return null;
    current = current[part];
  }
  return current ?? null;
}

// ── Sub-components ───────────────────────────────────────────────────────────

interface MethodBadgeProps {
  readonly method: string;
  readonly size?: 'sm' | 'md';
}
function MethodBadge({ method, size = 'sm' }: MethodBadgeProps) {
  const colors = HTTP_METHOD_COLORS[method.toUpperCase()] ?? 'text-gray-400 bg-gray-400/10 border-gray-400/30';
  const padding = size === 'md' ? 'px-2.5 py-1 text-xs' : 'px-1.5 py-0.5 text-[10px]';
  return (
    <span className={`inline-block font-mono font-bold rounded border ${padding} ${colors}`}>
      {method.toUpperCase()}
    </span>
  );
}

// ── Environment Manager Dialog ───────────────────────────────────────────────

interface EnvironmentManagerProps {
  readonly onClose: () => void;
}
function EnvironmentManager({ onClose }: EnvironmentManagerProps) {
  const { t } = useTranslation(['apiExplorer']);
  const environments = useApiExplorerStore((s) => s.environments);
  const addEnvironment = useApiExplorerStore((s) => s.addEnvironment);
  const updateEnvironment = useApiExplorerStore((s) => s.updateEnvironment);
  const removeEnvironment = useApiExplorerStore((s) => s.removeEnvironment);

  // Project path for auto-detection
  const projects = useProjectStore((s) => s.projects);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);
  const activeProject = projects.find(
    (p) => p.id === (activeProjectId ?? selectedProjectId)
  );

  const [editId, setEditId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editUrl, setEditUrl] = useState('');
  const [editHeaders, setEditHeaders] = useState('');
  const [editToken, setEditToken] = useState('');
  const [editTokenVisible, setEditTokenVisible] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newHeaders, setNewHeaders] = useState('');
  const [newToken, setNewToken] = useState('');
  const [newTokenVisible, setNewTokenVisible] = useState(false);

  // Auto-detection state
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectedEnvs, setDetectedEnvs] = useState<DetectedEnvironment[]>([]);
  const [selectedDetected, setSelectedDetected] = useState<Set<number>>(new Set());

  async function runDetection() {
    if (!activeProject?.path) return;
    setIsDetecting(true);
    setDetectedEnvs([]);
    try {
      const results = await detectEnvironmentsFromProject(activeProject.path);
      // Filter out URLs already in the list
      const existingUrls = new Set(environments.map((e) => e.baseUrl));
      const fresh = results.filter((r) => !existingUrls.has(r.baseUrl));
      setDetectedEnvs(fresh);
      setSelectedDetected(new Set(fresh.map((_, i) => i)));
    } finally {
      setIsDetecting(false);
    }
  }

  function importDetected() {
    for (const idx of selectedDetected) {
      const env = detectedEnvs[idx];
      if (env) addEnvironment({ name: env.name, baseUrl: env.baseUrl, headers: env.headers });
    }
    setDetectedEnvs([]);
    setSelectedDetected(new Set());
  }

  function toggleDetected(idx: number) {
    setSelectedDetected((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  }

  function startEdit(env: ApiEnvironment) {
    setEditId(env.id);
    setEditName(env.name);
    setEditUrl(env.baseUrl);
    setEditToken(env.token ?? '');
    setEditTokenVisible(false);
    setEditHeaders(
      Object.entries(env.headers)
        .map(([k, v]) => `${k}: ${v}`)
        .join('\n')
    );
  }

  function saveEdit() {
    if (!editId) return;
    const headers: Record<string, string> = {};
    for (const line of editHeaders.split('\n')) {
      const idx = line.indexOf(':');
      if (idx > 0) {
        headers[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      }
    }
    updateEnvironment(editId, { name: editName, baseUrl: editUrl, headers, token: editToken || undefined });
    setEditId(null);
  }

  function addNew() {
    const headers: Record<string, string> = {};
    for (const line of newHeaders.split('\n')) {
      const idx = line.indexOf(':');
      if (idx > 0) {
        headers[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      }
    }
    addEnvironment({ name: newName, baseUrl: newUrl, headers, token: newToken || undefined });
    setIsAdding(false);
    setNewName('');
    setNewUrl('');
    setNewHeaders('');
    setNewToken('');
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl shadow-2xl w-full max-w-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">
            {t('apiExplorer:environments.title')}
          </h2>
          <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          {environments.map((env) => (
            <div key={env.id} className="border border-[var(--color-border)] rounded-lg p-3">
              {editId === env.id ? (
                <div className="space-y-2">
                  <input
                    className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-sm text-[var(--color-text-primary)]"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    placeholder={t('apiExplorer:environments.namePlaceholder')}
                  />
                  <input
                    className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-sm font-mono text-[var(--color-text-primary)]"
                    value={editUrl}
                    onChange={(e) => setEditUrl(e.target.value)}
                    placeholder="https://api.example.com"
                  />
                  <div className="relative">
                    <div className="text-[10px] text-[var(--color-text-muted)] mb-0.5">{t('apiExplorer:environments.token')}</div>
                    <div className="flex gap-1">
                      <input
                        type={editTokenVisible ? 'text' : 'password'}
                        className="flex-1 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs font-mono text-[var(--color-text-primary)]"
                        value={editToken}
                        onChange={(e) => setEditToken(e.target.value)}
                        placeholder={t('apiExplorer:environments.tokenPlaceholder')}
                      />
                      <button
                        type="button"
                        onClick={() => setEditTokenVisible((v) => !v)}
                        className="px-2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] rounded bg-[var(--color-bg-secondary)] transition-colors"
                      >
                        {editTokenVisible ? '🙈' : '👁'}
                      </button>
                    </div>
                  </div>
                  <div className="text-[10px] text-[var(--color-text-muted)] mb-0.5">{t('apiExplorer:environments.headers')}</div>
                  <textarea
                    className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs font-mono text-[var(--color-text-primary)] resize-none"
                    rows={3}
                    value={editHeaders}
                    onChange={(e) => setEditHeaders(e.target.value)}
                    placeholder="X-API-Key: key&#10;X-Custom: value"
                  />
                  <div className="flex gap-2 justify-end">
                    <Button size="sm" variant="outline" onClick={() => setEditId(null)}>{t('apiExplorer:actions.cancel')}</Button>
                    <Button size="sm" onClick={saveEdit}>{t('apiExplorer:actions.save')}</Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-medium text-(--color-text-primary)">{env.name}</div>
                      {env.token && (
                        <span className="text-[9px] font-mono bg-amber-400/10 text-amber-400 border border-amber-400/20 rounded px-1 py-0.5">
                          Bearer ••••
                        </span>
                      )}
                    </div>
                    <div className="text-xs font-mono text-[var(--color-text-muted)] mt-0.5">{env.baseUrl}</div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => startEdit(env)}
                      className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] p-1 rounded transition-colors"
                    >
                      <Settings size={14} />
                    </button>
                    {!env.isDefault && (
                      <button
                        onClick={() => removeEnvironment(env.id)}
                        className="text-[var(--color-text-muted)] hover:text-red-400 p-1 rounded transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Auto-detected environments */}
        {detectedEnvs.length > 0 && (
          <div className="mt-3 border border-emerald-400/20 bg-emerald-400/5 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-xs font-semibold text-emerald-400">{t('apiExplorer:environments.detected')} ({detectedEnvs.length})</span>
              <div className="flex gap-1.5">
                <button onClick={() => setDetectedEnvs([])} className="text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                  {t('apiExplorer:actions.cancel')}
                </button>
                <Button size="sm" onClick={importDetected} disabled={selectedDetected.size === 0}>
                  {t('apiExplorer:environments.importSelected')} ({selectedDetected.size})
                </Button>
              </div>
            </div>
            <div className="space-y-1.5">
              {detectedEnvs.map((env, idx) => (
                <label key={`${env.name}-${env.baseUrl}`} className="flex items-center gap-2.5 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selectedDetected.has(idx)}
                    onChange={() => toggleDetected(idx)}
                    className="accent-emerald-400 shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-[var(--color-text-primary)]">{env.name}</span>
                      <span className="text-[9px] font-mono text-[var(--color-text-muted)] border border-[var(--color-border)] rounded px-1">{env.source}</span>
                    </div>
                    <span className="text-[10px] font-mono text-emerald-400/80 truncate block">{env.baseUrl}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {isAdding ? (
          <div className="mt-3 border border-[var(--color-border)] rounded-lg p-3 space-y-2">
            <input
              className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-sm text-[var(--color-text-primary)]"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t('apiExplorer:environments.namePlaceholder')}
              autoFocus
            />
            <input
              className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-sm font-mono text-[var(--color-text-primary)]"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://api.example.com"
            />
            <div>
              <div className="text-[10px] text-[var(--color-text-muted)] mb-0.5">{t('apiExplorer:environments.token')}</div>
              <div className="flex gap-1">
                <input
                  type={newTokenVisible ? 'text' : 'password'}
                  className="flex-1 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs font-mono text-[var(--color-text-primary)]"
                  value={newToken}
                  onChange={(e) => setNewToken(e.target.value)}
                  placeholder={t('apiExplorer:environments.tokenPlaceholder')}
                />
                <button
                  type="button"
                  onClick={() => setNewTokenVisible((v) => !v)}
                  className="px-2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] rounded bg-[var(--color-bg-secondary)] transition-colors"
                >
                  {newTokenVisible ? '🙈' : '👁'}
                </button>
              </div>
            </div>
            <div>
              <div className="text-[10px] text-[var(--color-text-muted)] mb-0.5">{t('apiExplorer:environments.headers')}</div>
              <textarea
                className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs font-mono text-[var(--color-text-primary)] resize-none"
                rows={2}
                value={newHeaders}
                onChange={(e) => setNewHeaders(e.target.value)}
                placeholder="X-API-Key: key"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setIsAdding(false)}>{t('apiExplorer:actions.cancel')}</Button>
              <Button size="sm" onClick={addNew} disabled={!newName || !newUrl}>{t('apiExplorer:actions.add')}</Button>
            </div>
          </div>
        ) : (
          <div className="mt-3 flex gap-2">
            {activeProject && (
              <button
                onClick={runDetection}
                disabled={isDetecting}
                className="flex-1 border border-dashed border-emerald-400/30 rounded-lg py-2 text-sm text-emerald-400/70 hover:text-emerald-400 hover:border-emerald-400/50 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isDetecting ? <Loader2 size={13} className="animate-spin" /> : <ScanSearch size={13} />}
                {isDetecting ? t('apiExplorer:environments.detecting') : t('apiExplorer:environments.detect')}
              </button>
            )}
            <button
              onClick={() => setIsAdding(true)}
              className="flex-1 border border-dashed border-[var(--color-border)] rounded-lg py-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-hover)] transition-colors flex items-center justify-center gap-2"
            >
              <Plus size={14} />
              {t('apiExplorer:environments.addNew')}
            </button>
          </div>
        )}
      </div>
    </div>,
    document.getElementById('root') ?? document.body
  );
}

// ── Export Dialog ────────────────────────────────────────────────────────────

interface ExportDialogProps {
  readonly spec: OpenApiSpec;
  readonly onClose: () => void;
}

function buildPostmanCollection(spec: OpenApiSpec, baseUrl: string) {
  const items: unknown[] = [];
  const tagMap: Record<string, unknown[]> = {};

  for (const [path, methods] of Object.entries(spec.paths ?? {})) {
    for (const [method, op] of Object.entries(methods)) {
      if (['get', 'post', 'put', 'delete', 'patch', 'head', 'options'].includes(method)) {
        const tags = op.tags ?? ['default'];
        const request: Record<string, unknown> = {
          method: method.toUpperCase(),
          header: Object.entries(
            op.parameters?.filter((p) => p.in === 'header').reduce<Record<string, string>>((acc, p) => {
              acc[p.name] = p.example ? JSON.stringify(p.example) : '';
              return acc;
            }, {}) ?? {}
          ).map(([key, value]) => ({ key, value })),
          url: {
            raw: `${baseUrl}${path}`,
            host: [baseUrl],
            path: path.split('/').filter(Boolean).map((s) => (s.startsWith('{') ? `:${s.slice(1, -1)}` : s)),
          },
        };
        if (op.requestBody) {
          const contentType = Object.keys(op.requestBody.content ?? {})[0] ?? 'application/json';
          request.body = {
            mode: 'raw',
            raw: JSON.stringify(op.requestBody.content?.[contentType]?.example ?? {}, null, 2),
            options: { raw: { language: 'json' } },
          };
        }
        const item = { name: op.summary ?? `${method.toUpperCase()} ${path}`, request };
        for (const tag of tags) {
          if (!tagMap[tag]) tagMap[tag] = [];
          tagMap[tag].push(item);
        }
      }
    }
  }

  for (const [tag, tagItems] of Object.entries(tagMap)) {
    items.push({ name: tag, item: tagItems });
  }

  return {
    info: {
      name: spec.info.title,
      description: spec.info.description ?? '',
      schema: 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
    },
    item: items,
  };
}

function buildMarkdownDocs(spec: OpenApiSpec): string {
  const lines: string[] = [
    `# ${spec.info.title}`,
    '',
  ];
  
  if (spec.info.description) {
    lines.push(spec.info.description, '');
  }
  
  lines.push(`**Version:** ${spec.info.version}`, '');

  const tagMap: Record<string, Array<{ method: string; path: string; op: OpenApiOperation }>> = {};
  for (const [path, methods] of Object.entries(spec.paths ?? {})) {
    for (const [method, op] of Object.entries(methods)) {
      const tag = op.tags?.[0] ?? 'default';
      if (!tagMap[tag]) tagMap[tag] = [];
      tagMap[tag].push({ method, path, op });
    }
  }

  for (const [tag, endpoints] of Object.entries(tagMap)) {
    lines.push(`## ${tag}`, '');
    
    for (const { method, path, op } of endpoints) {
      lines.push(`### \`${method.toUpperCase()} ${path}\``, '');
      
      if (op.summary) lines.push(`**${op.summary}**`);
      if (op.description) lines.push(op.description);
      lines.push('');
      
      if (op.parameters && op.parameters.length > 0) {
        lines.push(
          '**Parameters:**',
          '',
          '| Name | In | Type | Required | Description |',
          '|------|----|------|----------|-------------|',
          ...op.parameters.map(param => 
            `| \`${param.name}\` | ${param.in} | ${param.schema?.type ?? '-'} | ${param.required ? '✓' : '-'} | ${param.description ?? '-'} |`
          ),
          ''
        );
      }
      if (op.responses) {
        lines.push(
          '**Responses:**',
          '',
          '| Status | Description |',
          '|--------|-------------|',
          ...Object.entries(op.responses).map(([status, resp]) => 
            `| ${status} | ${resp.description ?? '-'} |`
          ),
          ''
        );
      }
    }
  }
  return lines.join('\n');
}

function ExportDialog({ spec, onClose }: ExportDialogProps) {
  const { t } = useTranslation(['apiExplorer']);
  const environments = useApiExplorerStore((s) => s.environments);
  const activeEnvironmentId = useApiExplorerStore((s) => s.activeEnvironmentId);
  const activeEnv = environments.find((e) => e.id === activeEnvironmentId) ?? environments[0];
  const [copied, setCopied] = useState(false);

  const httpMethods = ['get', 'post', 'put', 'delete', 'patch', 'head', 'options'];

  const allEndpoints = useMemo(() => {
    const endpoints: Array<{ key: string; method: string; path: string }> = [];
    for (const [path, methods] of Object.entries(spec.paths ?? {})) {
      for (const method of Object.keys(methods)) {
        if (httpMethods.includes(method)) {
          endpoints.push({ key: `${method}::${path}`, method, path });
        }
      }
    }
    return endpoints;
  }, [spec]);

  const [selectedEndpoints, setSelectedEndpoints] = useState<Set<string>>(
    () => new Set(allEndpoints.map((e) => e.key))
  );

  const allSelected = selectedEndpoints.size === allEndpoints.length;

  function toggleEndpoint(key: string) {
    setSelectedEndpoints((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAll() {
    if (allSelected) {
      setSelectedEndpoints(new Set());
    } else {
      setSelectedEndpoints(new Set(allEndpoints.map((e) => e.key)));
    }
  }

  function getFilteredSpec(): OpenApiSpec {
    if (selectedEndpoints.size === allEndpoints.length) return spec;
    const filteredPaths: Record<string, Record<string, OpenApiOperation>> = {};
    for (const [path, methods] of Object.entries(spec.paths ?? {})) {
      const filteredMethods: Record<string, OpenApiOperation> = {};
      for (const [method, op] of Object.entries(methods)) {
        if (selectedEndpoints.has(`${method}::${path}`)) {
          filteredMethods[method] = op;
        }
      }
      if (Object.keys(filteredMethods).length > 0) {
        filteredPaths[path] = filteredMethods;
      }
    }
    return { ...spec, paths: filteredPaths };
  }

  function download(content: string, filename: string, mime: string) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportOpenApi() {
    download(JSON.stringify(getFilteredSpec(), null, 2), 'openapi.json', 'application/json');
  }

  function exportPostman() {
    const collection = buildPostmanCollection(getFilteredSpec(), activeEnv?.baseUrl ?? '');
    download(JSON.stringify(collection, null, 2), 'collection.postman_collection.json', 'application/json');
  }

  function exportMarkdown() {
    const filtered = getFilteredSpec();
    download(buildMarkdownDocs(filtered), `${filtered.info.title.toLowerCase().replaceAll(/\s+/g, '-')}-api.md`, 'text/markdown');
  }

  function copyOpenApi() {
    navigator.clipboard.writeText(JSON.stringify(getFilteredSpec(), null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const formats = [
    {
      label: 'OpenAPI 3.x JSON',
      description: t('apiExplorer:export.openapiDesc'),
      icon: '{}',
      action: exportOpenApi,
    },
    {
      label: 'Postman Collection v2.1',
      description: t('apiExplorer:export.postmanDesc'),
      icon: '📮',
      action: exportPostman,
    },
    {
      label: 'Markdown Documentation',
      description: t('apiExplorer:export.markdownDesc'),
      icon: 'MD',
      action: exportMarkdown,
    },
  ];

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">
            {t('apiExplorer:export.title')}
          </h2>
          <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
            <X size={18} />
          </button>
        </div>

        {allEndpoints.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[var(--color-text-secondary)]">
                {t('apiExplorer:export.endpoints', { selected: selectedEndpoints.size, total: allEndpoints.length })}
              </span>
              <button
                onClick={toggleAll}
                className="text-xs text-[var(--color-primary)] hover:underline"
              >
                {allSelected ? t('apiExplorer:export.deselectAll') : t('apiExplorer:export.selectAll')}
              </button>
            </div>
            <div className="max-h-40 overflow-y-auto rounded-lg border border-[var(--color-border)] divide-y divide-[var(--color-border)]">
              {allEndpoints.map((ep) => (
                <label
                  key={ep.key}
                  className="flex items-center gap-2.5 px-3 py-1.5 cursor-pointer hover:bg-[var(--color-bg-secondary)] select-none"
                >
                  <input
                    type="checkbox"
                    checked={selectedEndpoints.has(ep.key)}
                    onChange={() => toggleEndpoint(ep.key)}
                    className="shrink-0 accent-[var(--color-primary)]"
                  />
                  <MethodBadge method={ep.method} />
                  <span className="text-xs text-[var(--color-text-secondary)] truncate font-mono">{ep.path}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2.5">
          {formats.map((fmt) => (
            <button
              key={fmt.label}
              onClick={fmt.action}
              disabled={selectedEndpoints.size === 0}
              className="w-full text-left flex items-center gap-3 p-3 rounded-lg border border-[var(--color-border)] hover:border-[var(--color-border-hover)] hover:bg-[var(--color-bg-secondary)] transition-all group disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <div className="w-10 h-10 rounded-lg bg-[var(--color-bg-tertiary)] flex items-center justify-center text-xs font-bold font-mono text-[var(--color-text-secondary)] shrink-0">
                {fmt.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-[var(--color-text-primary)]">{fmt.label}</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{fmt.description}</div>
              </div>
              <Download size={15} className="text-[var(--color-text-muted)] group-hover:text-[var(--color-text-primary)] transition-colors shrink-0" />
            </button>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
          <button
            onClick={copyOpenApi}
            disabled={selectedEndpoints.size === 0}
            className="w-full flex items-center justify-center gap-2 py-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
            {copied ? t('apiExplorer:export.copied') : t('apiExplorer:export.copySpec')}
          </button>
        </div>
      </div>
    </div>,
    document.getElementById('root') ?? document.body
  );
}

// ── Schema Viewer ────────────────────────────────────────────────────────────

interface SchemaViewerProps {
  readonly schema: Record<string, unknown>;
  readonly spec: OpenApiSpec;
  readonly depth?: number;
}
function SchemaViewer({ schema, spec, depth = 0 }: SchemaViewerProps) {
  const resolved = useMemo(() => {
    if (schema.$ref && typeof schema.$ref === 'string') {
      return resolveRef(schema.$ref, spec) ?? schema;
    }
    return schema;
  }, [schema, spec]);

  const type = resolved.type as string | undefined;
  const properties = resolved.properties as Record<string, Record<string, unknown>> | undefined;
  const required = resolved.required as string[] | undefined;
  const items = resolved.items as Record<string, unknown> | undefined;
  const description = resolved.description as string | undefined;

  if (depth > 4) return <span className="text-[var(--color-text-muted)] text-xs">...</span>;

  if (type === 'object' && properties) {
    return (
      <div className={depth > 0 ? 'ml-3 border-l border-[var(--color-border)] pl-3' : ''}>
        {Object.entries(properties).map(([key, val]) => (
          <div key={key} className="py-0.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs text-[var(--color-text-primary)] font-medium">{key}</span>
              {required?.includes(key) && (
                <span className="text-[9px] text-red-400 font-mono border border-red-400/30 rounded px-1">required</span>
              )}
              <span className="text-[10px] font-mono text-blue-400/80">{(val.type as string) ?? (val.$ref ? '↗ ref' : '?')}</span>
              {!!val.description && <span className="text-xs text-[var(--color-text-muted)]">— {String(val.description)}</span>}
            </div>
            {(val.type === 'object' || val.$ref || val.type === 'array') && (
              <SchemaViewer schema={val} spec={spec} depth={depth + 1} />
            )}
          </div>
        ))}
      </div>
    );
  }

  if (type === 'array' && items) {
    return (
      <div className={depth > 0 ? 'ml-3 border-l border-[var(--color-border)] pl-3' : ''}>
        <span className="text-xs text-[var(--color-text-muted)]">items:</span>
        <SchemaViewer schema={items} spec={spec} depth={depth + 1} />
      </div>
    );
  }

  return (
    <span className="text-xs text-[var(--color-text-muted)]">
      {type ?? 'any'}{description ? ` — ${description}` : ''}
    </span>
  );
}

// ── Request Panel ────────────────────────────────────────────────────────────

interface RequestPanelProps {
  readonly method: string;
  readonly path: string;
  readonly operation: OpenApiOperation;
  readonly spec: OpenApiSpec;
  readonly onOpenEnvManager: () => void;
}
function RequestPanel({ method, path, operation, spec, onOpenEnvManager }: RequestPanelProps) {
  const { t } = useTranslation(['apiExplorer']);
  const environments = useApiExplorerStore((s) => s.environments);
  const activeEnvironmentId = useApiExplorerStore((s) => s.activeEnvironmentId);
  const activeEnv = environments.find((e) => e.id === activeEnvironmentId) ?? environments[0];

  const requestPathParams = useApiExplorerStore((s) => s.requestPathParams);
  const requestQueryParams = useApiExplorerStore((s) => s.requestQueryParams);
  const requestHeaders = useApiExplorerStore((s) => s.requestHeaders);
  const requestBody = useApiExplorerStore((s) => s.requestBody);
  const isSendingRequest = useApiExplorerStore((s) => s.isSendingRequest);
  const responseStatus = useApiExplorerStore((s) => s.responseStatus);
  const responseStatusText = useApiExplorerStore((s) => s.responseStatusText);
  const responseHeaders = useApiExplorerStore((s) => s.responseHeaders);
  const responseBody = useApiExplorerStore((s) => s.responseBody);
  const responseTime = useApiExplorerStore((s) => s.responseTime);

  const requestAuth = useApiExplorerStore((s) => s.requestAuth);
  const setRequestPathParams = useApiExplorerStore((s) => s.setRequestPathParams);
  const setRequestQueryParams = useApiExplorerStore((s) => s.setRequestQueryParams);
  const setRequestHeaders = useApiExplorerStore((s) => s.setRequestHeaders);
  const setRequestBody = useApiExplorerStore((s) => s.setRequestBody);
  const setRequestAuth = useApiExplorerStore((s) => s.setRequestAuth);
  const setResponse = useApiExplorerStore((s) => s.setResponse);
  const clearResponse = useApiExplorerStore((s) => s.clearResponse);
  const setIsSendingRequest = useApiExplorerStore((s) => s.setIsSendingRequest);
  const updateEnvironment = useApiExplorerStore((s) => s.updateEnvironment);

  const [showAuthToken, setShowAuthToken] = useState(false);
  const [showAuthPassword, setShowAuthPassword] = useState(false);
  const [showOAuth2Secret, setShowOAuth2Secret] = useState(false);
  const [showOAuth2Token, setShowOAuth2Token] = useState(false);
  const [isGettingOAuth2Token, setIsGettingOAuth2Token] = useState(false);
  const [oauth2TokenError, setOAuth2TokenError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'params' | 'auth' | 'headers' | 'body' | 'docs'>('params');
  const [responseTab, setResponseTab] = useState<'body' | 'headers'>('body');
  const [responseFormat, setResponseFormat] = useState<'pretty' | 'raw' | 'preview'>('pretty');
  const [responseLanguage, setResponseLanguage] = useState<ResponseLanguage>('auto');
  const [responsePanelHeight, setResponsePanelHeight] = useState(240);
  const isDraggingDivider = useRef(false);
  const dragStartY = useRef(0);
  const dragStartHeight = useRef(0);
  const [copiedResponse, setCopiedResponse] = useState(false);
  const [savedToken, setSavedToken] = useState(false);

  // Extract a token from a JSON response body (common field names)
  const TOKEN_FIELDS = ['access_token', 'token', 'jwt', 'auth_token', 'id_token', 'bearer_token', 'accessToken', 'authToken', 'idToken'];
  const extractedToken = useMemo<string | null>(() => {
    if (!responseBody || !responseStatus || responseStatus < 200 || responseStatus >= 300) return null;
    try {
      const json = JSON.parse(responseBody) as Record<string, unknown>;
      for (const field of TOKEN_FIELDS) {
        if (typeof json[field] === 'string' && json[field].length > 10) {
          return json[field];
        }
      }
    } catch { /* not JSON */ }
    return null;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [responseBody, responseStatus]);

  // Auto-select the best format and language when a new response arrives
  useEffect(() => {
    if (!responseBody) return;
    const ct = detectContentType(responseHeaders);
    setResponseLanguage('auto');
    if (ct.includes('text/html')) {
      setResponseFormat('preview');
    } else {
      setResponseFormat('pretty');
    }
  }, [responseBody, responseHeaders]);

  // Drag-to-resize response panel
  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!isDraggingDivider.current) return;
      const delta = dragStartY.current - e.clientY;
      setResponsePanelHeight(Math.max(80, Math.min(700, dragStartHeight.current + delta)));
    }
    function onMouseUp() {
      if (!isDraggingDivider.current) return;
      isDraggingDivider.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  function saveTokenToEnv() {
    if (!extractedToken || !activeEnv) return;
    updateEnvironment(activeEnv.id, { token: extractedToken });
    setRequestAuth({ type: 'inherited' });
    setSavedToken(true);
    setTimeout(() => setSavedToken(false), 2500);
  }

  // Custom key/value rows (free-form, not from spec)
  const [customQueryRows, setCustomQueryRows] = useState<Array<{ id: string; enabled: boolean; key: string; value: string }>>([]);
  const [customHeaderRows, setCustomHeaderRows] = useState<Array<{ id: string; enabled: boolean; key: string; value: string }>>([]);

  function addCustomQueryRow() {
    setCustomQueryRows((r) => [...r, { id: `cqr-${Date.now()}`, enabled: true, key: '', value: '' }]);
  }
  function updateCustomQueryRow(id: string, field: CustomRowField, val: CustomRowValue) {
    setCustomQueryRows((r) => r.map((row) => row.id === id ? { ...row, [field]: val } : row));
  }
  function removeCustomQueryRow(id: string) {
    setCustomQueryRows((r) => r.filter((row) => row.id !== id));
  }

  function addCustomHeaderRow() {
    setCustomHeaderRows((r) => [...r, { id: `chr-${Date.now()}`, enabled: true, key: '', value: '' }]);
  }
  function updateCustomHeaderRow(id: string, field: CustomRowField, val: CustomRowValue) {
    setCustomHeaderRows((r) => r.map((row) => row.id === id ? { ...row, [field]: val } : row));
  }
  function removeCustomHeaderRow(id: string) {
    setCustomHeaderRows((r) => r.filter((row) => row.id !== id));
  }

  const pathParams = useMemo(
    () => (operation.parameters ?? []).filter((p) => p.in === 'path'),
    [operation.parameters]
  );
  const queryParams = useMemo(
    () => (operation.parameters ?? []).filter((p) => p.in === 'query'),
    [operation.parameters]
  );
  const headerParams = useMemo(
    () => (operation.parameters ?? []).filter((p) => p.in === 'header'),
    [operation.parameters]
  );

  const hasBody = method.toLowerCase() !== 'get' && method.toLowerCase() !== 'head' && operation.requestBody;

  const responseCodes = Object.keys(operation.responses ?? {});
  const requestBodySchema = operation.requestBody
    ? Object.values(operation.requestBody.content ?? {})[0]?.schema
    : null;

  // Build the resolved URL preview
  const resolvedUrl = useMemo(() => {
    let url = `${activeEnv?.baseUrl ?? ''}${path}`;
    for (const [key, val] of Object.entries(requestPathParams)) {
      if (val) url = url.replace(`{${key}}`, encodeURIComponent(val));
    }
    const qp = [
      ...Object.entries(requestQueryParams).filter(([, v]) => v),
      ...customQueryRows.filter((r) => r.enabled && r.key).map((r) => [r.key, r.value] as [string, string]),
    ];
    if (qp.length > 0) {
      url += '?' + qp.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
    }
    return url;
  }, [activeEnv, path, requestPathParams, requestQueryParams, customQueryRows]);

  async function sendRequest() {
    setIsSendingRequest(true);
    clearResponse();

    const headers: Record<string, string> = {
      // Environment-level headers
      ...Object.fromEntries(Object.entries(activeEnv?.headers ?? {}).filter(([, v]) => v)),
      // Spec-defined header params
      ...Object.fromEntries(Object.entries(requestHeaders).filter(([, v]) => v)),
      // User-added custom headers
      ...Object.fromEntries(customHeaderRows.filter((r) => r.enabled && r.key).map((r) => [r.key, r.value])),
    };

    // Build final URL — resolvedUrl already includes spec+custom query params, but for API key in query we rebuild
    let finalUrl = resolvedUrl;

    // Authentication
    if (requestAuth.type === 'bearer' && requestAuth.bearer) {
      headers['Authorization'] = `Bearer ${requestAuth.bearer}`;
    } else if (requestAuth.type === 'basic' && (requestAuth.username || requestAuth.password)) {
      headers['Authorization'] = `Basic ${btoa(`${requestAuth.username}:${requestAuth.password}`)}`;
    } else if (requestAuth.type === 'apikey' && requestAuth.keyName && requestAuth.keyValue) {
      if (requestAuth.keyLocation === 'header') {
        headers[requestAuth.keyName] = requestAuth.keyValue;
      } else {
        // Append API key to query string
        const sep = finalUrl.includes('?') ? '&' : '?';
        finalUrl += `${sep}${encodeURIComponent(requestAuth.keyName)}=${encodeURIComponent(requestAuth.keyValue)}`;
      }
    } else if (requestAuth.type === 'inherited') {
      if (activeEnv?.token && !headers['Authorization'] && !headers['authorization']) {
        headers['Authorization'] = `Bearer ${activeEnv.token}`;
      }
    } else if (requestAuth.type === 'oauth2' && requestAuth.oauth2AccessToken) {
      const prefix = requestAuth.oauth2HeaderPrefix || 'Bearer';
      headers['Authorization'] = `${prefix} ${requestAuth.oauth2AccessToken}`;
    }
    // type === 'none' → no Authorization header added

    if (hasBody && requestBody) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const result = await globalThis.electronAPI.proxyHttpRequest({
        url: finalUrl,
        method: method.toUpperCase(),
        headers,
        body: hasBody && requestBody ? requestBody : undefined,
      });

      setResponse({
        status: result.status ?? 0,
        statusText: result.statusText ?? (result.success ? 'OK' : t('apiExplorer:request.networkError')),
        headers: result.headers ?? {},
        body: result.body ?? '',
        time: result.time ?? 0,
      });
    } catch (err) {
      setResponse({
        status: 0,
        statusText: t('apiExplorer:request.networkError'),
        headers: {},
        body: String(err),
        time: 0,
      });
    }
  }

  async function handleGetOAuth2Token() {
    setIsGettingOAuth2Token(true);
    setOAuth2TokenError(null);
    try {
      const { oauth2GrantType, oauth2TokenUrl, oauth2AuthUrl, oauth2ClientId, oauth2ClientSecret, oauth2Scope } = requestAuth;

      if (oauth2GrantType === 'authorization_code') {
        // For auth code flow, open auth URL in browser — user pastes token manually
        if (oauth2AuthUrl) {
          window.open(oauth2AuthUrl, '_blank');
        }
        setIsGettingOAuth2Token(false);
        return;
      }

      if (!oauth2TokenUrl) {
        setOAuth2TokenError(t('apiExplorer:auth.oauth2.missingTokenUrl'));
        setIsGettingOAuth2Token(false);
        return;
      }

      const body = new URLSearchParams();
      body.append('grant_type', oauth2GrantType);
      if (oauth2ClientId) body.append('client_id', oauth2ClientId);
      if (oauth2ClientSecret) body.append('client_secret', oauth2ClientSecret);
      if (oauth2Scope) body.append('scope', oauth2Scope);
      if (oauth2GrantType === 'password') {
        body.append('username', requestAuth.username);
        body.append('password', requestAuth.password);
      }

      const res = await fetch(oauth2TokenUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      });
      const data = await res.json() as Record<string, unknown>;
      if (typeof data.access_token === 'string') {
        setRequestAuth({ oauth2AccessToken: data.access_token });
      } else {
        const errDesc = typeof data.error_description === 'string' ? data.error_description : null;
        const errCode = typeof data.error === 'string' ? data.error : null;
        setOAuth2TokenError(errDesc ?? errCode ?? t('apiExplorer:auth.oauth2.tokenError'));
      }
    } catch (err) {
      setOAuth2TokenError(String(err));
    } finally {
      setIsGettingOAuth2Token(false);
    }
  }

  function copyResponse() {
    navigator.clipboard.writeText(responseBody);
    setCopiedResponse(true);
    setTimeout(() => setCopiedResponse(false), 2000);
  }

  function updatePathParam(name: string, value: string) {
    setRequestPathParams({ ...requestPathParams, [name]: value });
  }

  function updateQueryParam(name: string, value: string) {
    setRequestQueryParams({ ...requestQueryParams, [name]: value });
  }

  function updateHeaderParam(name: string, value: string) {
    setRequestHeaders({ ...requestHeaders, [name]: value });
  }

  const authIsActive = requestAuth.type !== 'inherited' && requestAuth.type !== 'none';
  const authInherited = requestAuth.type === 'inherited' && !!activeEnv?.token;
  const tabs = [
    { id: 'params' as const, label: `${t('apiExplorer:request.params')} (${pathParams.length + queryParams.length})` },
    { id: 'auth' as const, label: t('apiExplorer:request.auth'), badge: authIsActive || authInherited },
    { id: 'headers' as const, label: `${t('apiExplorer:request.headers')} (${headerParams.length})` },
    ...(hasBody ? [{ id: 'body' as const, label: t('apiExplorer:request.body') }] : []),
    { id: 'docs' as const, label: t('apiExplorer:detail.docs') },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* URL bar — Postman-style */}
      <div className="px-5 pt-4 pb-0 shrink-0">
      <div className="flex items-stretch bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg overflow-hidden">
        <div className="flex items-center px-3 border-r border-[var(--color-border)] shrink-0 bg-[var(--color-bg-tertiary)]">
          <MethodBadge method={method} size="md" />
        </div>
        <span className="font-mono text-sm text-[var(--color-text-primary)] flex-1 px-3 py-2.5 truncate">{resolvedUrl}</span>
        <Button
          size="sm"
          onClick={sendRequest}
          disabled={isSendingRequest}
          className="shrink-0 m-1.5 flex items-center gap-1.5 px-4"
        >
          {isSendingRequest ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
          {t('apiExplorer:request.send')}
        </Button>
      </div>
      </div>

      {/* Request tabs */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="flex border-b border-[var(--color-border)] px-5">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-4 py-2 text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? 'text-[var(--color-text-primary)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {tab.label}
              {'badge' in tab && tab.badge && (
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
              )}
              {activeTab === tab.id && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
              )}
            </button>
          ))}
        </div>

        <div className="px-5 pt-3 pb-4 min-h-[100px]">
          {activeTab === 'params' && (
            <div className="space-y-4">
              {pathParams.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                    {t('apiExplorer:request.pathParams')}
                  </div>
                  {pathParams.map((p) => (
                    <ParamRow key={p.name} param={p} value={requestPathParams[p.name] ?? ''} onChange={(v) => updatePathParam(p.name, v)} />
                  ))}
                </div>
              )}
              <div>
                {queryParams.length > 0 && (
                  <>
                    <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                      {t('apiExplorer:request.queryParams')}
                    </div>
                    {queryParams.map((p) => (
                      <ParamRow key={p.name} param={p} value={requestQueryParams[p.name] ?? ''} onChange={(v) => updateQueryParam(p.name, v)} />
                    ))}
                    {customQueryRows.length > 0 && <div className="my-2 border-t border-[var(--color-border)]" />}
                  </>
                )}
                <KeyValueEditor
                  rows={customQueryRows}
                  onAdd={addCustomQueryRow}
                  onUpdate={updateCustomQueryRow}
                  onRemove={removeCustomQueryRow}
                  keyPlaceholder={t('apiExplorer:request.paramKey')}
                  valuePlaceholder={t('apiExplorer:request.paramValue')}
                  addLabel={t('apiExplorer:request.addParam')}
                />
              </div>
            </div>
          )}

          {activeTab === 'headers' && (
            <div className="space-y-3">
              {headerParams.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                    {t('apiExplorer:request.specHeaders')}
                  </div>
                  {headerParams.map((p) => (
                    <ParamRow key={p.name} param={p} value={requestHeaders[p.name] ?? ''} onChange={(v) => updateHeaderParam(p.name, v)} />
                  ))}
                  <div className="mt-3 border-t border-[var(--color-border)]" />
                </div>
              )}
              <KeyValueEditor
                rows={customHeaderRows}
                onAdd={addCustomHeaderRow}
                onUpdate={updateCustomHeaderRow}
                onRemove={removeCustomHeaderRow}
                keyPlaceholder={t('apiExplorer:request.headerKey')}
                valuePlaceholder={t('apiExplorer:request.headerValue')}
                addLabel={t('apiExplorer:request.addHeader')}
              />
            </div>
          )}

          {activeTab === 'auth' && (
            <div className="space-y-4">
              {/* Auth type selector */}
              <div>
                <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1.5">
                  {t('apiExplorer:auth.type')}
                </label>
                <CustomSelect
                  value={requestAuth.type}
                  onChange={(v) => setRequestAuth({ type: v as AuthType })}
                  options={(['inherited', 'none', 'bearer', 'basic', 'apikey', 'oauth2'] as AuthType[]).map((type) => ({
                    value: type,
                    label: t(`apiExplorer:auth.types.${type}`),
                  }))}
                />
              </div>

              {/* Inherited from environment */}
              {requestAuth.type === 'inherited' && (
                <div className={`rounded-lg p-3 text-xs ${activeEnv?.token ? 'bg-amber-400/5 border border-amber-400/20' : 'bg-[var(--color-bg-secondary)] border border-[var(--color-border)]'}`}>
                  {activeEnv?.token ? (
                    <div className="flex items-start gap-2">
                      <span className="text-amber-400 mt-0.5">🔑</span>
                      <div>
                        <div className="font-medium text-amber-400">{t('apiExplorer:auth.inheritedFrom', { env: activeEnv.name })}</div>
                        <div className="text-[var(--color-text-muted)] mt-0.5 font-mono">
                          Authorization: Bearer ••••{activeEnv.token.slice(-6)}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-[var(--color-text-muted)]">
                      {t('apiExplorer:auth.noEnvToken', { env: activeEnv?.name ?? 'Local' })}
                      <button
                        type="button"
                        onClick={onOpenEnvManager}
                        className="ml-1 text-[var(--color-primary)] hover:underline focus:outline-none font-medium"
                      >
                        {t('apiExplorer:auth.configureEnv')}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* No auth */}
              {requestAuth.type === 'none' && (
                <div className="text-xs text-[var(--color-text-muted)] bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-3">
                  {t('apiExplorer:auth.noAuthDesc')}
                </div>
              )}

              {/* Bearer Token */}
              {requestAuth.type === 'bearer' && (
                <div className="space-y-2">
                  <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block">
                    {t('apiExplorer:auth.token')}
                  </label>
                  <div className="flex gap-2">
                    <input
                      type={showAuthToken ? 'text' : 'password'}
                      className="flex-1 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                      value={requestAuth.bearer}
                      onChange={(e) => setRequestAuth({ bearer: e.target.value })}
                      placeholder={t('apiExplorer:auth.tokenPlaceholder')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowAuthToken((v) => !v)}
                      className="px-3 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] rounded-md bg-[var(--color-bg-secondary)] transition-colors text-sm"
                    >
                      {showAuthToken ? '🙈' : '👁'}
                    </button>
                  </div>
                  <div className="text-[10px] text-[var(--color-text-muted)]">{t('apiExplorer:auth.bearerHint')}</div>
                </div>
              )}

              {/* Basic Auth */}
              {requestAuth.type === 'basic' && (
                <div className="space-y-2">
                  <div>
                    <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
                      {t('apiExplorer:auth.username')}
                    </label>
                    <input
                      type="text"
                      className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                      value={requestAuth.username}
                      onChange={(e) => setRequestAuth({ username: e.target.value })}
                      placeholder={t('apiExplorer:auth.usernamePlaceholder')}
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
                      {t('apiExplorer:auth.password')}
                    </label>
                    <div className="flex gap-2">
                      <input
                        type={showAuthPassword ? 'text' : 'password'}
                        className="flex-1 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                        value={requestAuth.password}
                        onChange={(e) => setRequestAuth({ password: e.target.value })}
                        placeholder="••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowAuthPassword((v) => !v)}
                        className="px-3 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] rounded-md bg-[var(--color-bg-secondary)] transition-colors text-sm"
                      >
                        {showAuthPassword ? '🙈' : '👁'}
                      </button>
                    </div>
                  </div>
                  <div className="text-[10px] text-[var(--color-text-muted)]">{t('apiExplorer:auth.basicHint')}</div>
                </div>
              )}

              {/* API Key */}
              {requestAuth.type === 'apikey' && (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
                        {t('apiExplorer:auth.keyName')}
                      </label>
                      <input
                        type="text"
                        className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                        value={requestAuth.keyName}
                        onChange={(e) => setRequestAuth({ keyName: e.target.value })}
                        placeholder="X-API-Key"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
                        {t('apiExplorer:auth.addTo')}
                      </label>
                      <CustomSelect
                        value={requestAuth.keyLocation}
                        onChange={(v) => setRequestAuth({ keyLocation: v as 'header' | 'query' })}
                        options={[
                          { value: 'header', label: t('apiExplorer:auth.locationHeader') },
                          { value: 'query', label: t('apiExplorer:auth.locationQuery') },
                        ]}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
                      {t('apiExplorer:auth.keyValue')}
                    </label>
                    <input
                      type="text"
                      className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                      value={requestAuth.keyValue}
                      onChange={(e) => setRequestAuth({ keyValue: e.target.value })}
                      placeholder={t('apiExplorer:auth.keyValuePlaceholder')}
                    />
                  </div>
                </div>
              )}

              {/* OAuth 2.0 */}
              {requestAuth.type === 'oauth2' && (
                <div className="space-y-3">
                  {/* Grant Type */}
                  <div>
                    <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider block mb-1">
                      {t('apiExplorer:auth.oauth2.grantType')}
                    </label>
                    <CustomSelect
                      value={requestAuth.oauth2GrantType}
                      onChange={(v) => setRequestAuth({ oauth2GrantType: v as OAuth2GrantType })}
                      options={[
                        { value: 'client_credentials', label: t('apiExplorer:auth.oauth2.grants.client_credentials') },
                        { value: 'authorization_code', label: t('apiExplorer:auth.oauth2.grants.authorization_code') },
                        { value: 'password', label: t('apiExplorer:auth.oauth2.grants.password') },
                      ]}
                    />
                  </div>

                  {/* Configure New Token */}
                  <div className="border border-[var(--color-border)] rounded-lg p-3 space-y-2.5">
                    <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                      {t('apiExplorer:auth.oauth2.configureToken')}
                    </div>

                    {/* Auth URL — only for authorization_code */}
                    {requestAuth.oauth2GrantType === 'authorization_code' && (
                      <div>
                        <label className="text-[10px] text-[var(--color-text-muted)] block mb-1">{t('apiExplorer:auth.oauth2.authUrl')}</label>
                        <input
                          type="url"
                          className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                          value={requestAuth.oauth2AuthUrl}
                          onChange={(e) => setRequestAuth({ oauth2AuthUrl: e.target.value })}
                          placeholder="https://auth.example.com/authorize"
                        />
                      </div>
                    )}

                    {/* Token URL */}
                    {requestAuth.oauth2GrantType !== 'authorization_code' && (
                      <div>
                        <label className="text-[10px] text-[var(--color-text-muted)] block mb-1">{t('apiExplorer:auth.oauth2.tokenUrl')}</label>
                        <input
                          type="url"
                          className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                          value={requestAuth.oauth2TokenUrl}
                          onChange={(e) => setRequestAuth({ oauth2TokenUrl: e.target.value })}
                          placeholder="https://auth.example.com/token"
                        />
                      </div>
                    )}

                    {/* Client ID */}
                    <div>
                      <label className="text-[10px] text-[var(--color-text-muted)] block mb-1">{t('apiExplorer:auth.oauth2.clientId')}</label>
                      <input
                        type="text"
                        className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                        value={requestAuth.oauth2ClientId}
                        onChange={(e) => setRequestAuth({ oauth2ClientId: e.target.value })}
                        placeholder="client_id"
                      />
                    </div>

                    {/* Client Secret */}
                    <div>
                      <label className="text-[10px] text-[var(--color-text-muted)] block mb-1">{t('apiExplorer:auth.oauth2.clientSecret')}</label>
                      <div className="flex gap-2">
                        <input
                          type={showOAuth2Secret ? 'text' : 'password'}
                          className="flex-1 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                          value={requestAuth.oauth2ClientSecret}
                          onChange={(e) => setRequestAuth({ oauth2ClientSecret: e.target.value })}
                          placeholder="client_secret"
                        />
                        <button
                          type="button"
                          onClick={() => setShowOAuth2Secret((v) => !v)}
                          className="px-2.5 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] rounded-md bg-[var(--color-bg-primary)] transition-colors text-sm"
                        >
                          {showOAuth2Secret ? '🙈' : '👁'}
                        </button>
                      </div>
                    </div>

                    {/* Scope */}
                    <div>
                      <label className="text-[10px] text-[var(--color-text-muted)] block mb-1">{t('apiExplorer:auth.oauth2.scope')}</label>
                      <input
                        type="text"
                        className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                        value={requestAuth.oauth2Scope}
                        onChange={(e) => setRequestAuth({ oauth2Scope: e.target.value })}
                        placeholder="openid profile email"
                      />
                    </div>

                    {/* Password fields — only for password grant */}
                    {requestAuth.oauth2GrantType === 'password' && (
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[10px] text-[var(--color-text-muted)] block mb-1">{t('apiExplorer:auth.username')}</label>
                          <input
                            type="text"
                            className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                            value={requestAuth.username}
                            onChange={(e) => setRequestAuth({ username: e.target.value })}
                            placeholder={t('apiExplorer:auth.usernamePlaceholder')}
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-[var(--color-text-muted)] block mb-1">{t('apiExplorer:auth.password')}</label>
                          <input
                            type="password"
                            className="w-full bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                            value={requestAuth.password}
                            onChange={(e) => setRequestAuth({ password: e.target.value })}
                            placeholder="••••••••"
                          />
                        </div>
                      </div>
                    )}

                    {/* Error */}
                    {oauth2TokenError && (
                      <div className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-md px-2.5 py-1.5">
                        {oauth2TokenError}
                      </div>
                    )}

                    {/* Get Token button */}
                    <button
                      type="button"
                      onClick={handleGetOAuth2Token}
                      disabled={isGettingOAuth2Token}
                      className="w-full py-2 rounded-md text-xs font-semibold bg-[var(--color-primary)] text-[var(--color-primary-foreground)] hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center justify-center gap-2"
                    >
                      {isGettingOAuth2Token && <Loader2 size={12} className="animate-spin" />}
                      {requestAuth.oauth2GrantType === 'authorization_code'
                        ? t('apiExplorer:auth.oauth2.openBrowser')
                        : t('apiExplorer:auth.oauth2.getToken')}
                    </button>
                  </div>

                  {/* Current Token */}
                  <div className="space-y-2">
                    <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                      {t('apiExplorer:auth.oauth2.currentToken')}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type={showOAuth2Token ? 'text' : 'password'}
                        className="flex-1 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                        value={requestAuth.oauth2AccessToken}
                        onChange={(e) => setRequestAuth({ oauth2AccessToken: e.target.value })}
                        placeholder={t('apiExplorer:auth.oauth2.tokenPlaceholder')}
                      />
                      <button
                        type="button"
                        onClick={() => setShowOAuth2Token((v) => !v)}
                        className="px-3 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)] rounded-md bg-[var(--color-bg-secondary)] transition-colors text-sm"
                      >
                        {showOAuth2Token ? '🙈' : '👁'}
                      </button>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-[var(--color-text-muted)]">{t('apiExplorer:auth.oauth2.headerPrefix')}</span>
                      <input
                        type="text"
                        className="w-24 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
                        value={requestAuth.oauth2HeaderPrefix}
                        onChange={(e) => setRequestAuth({ oauth2HeaderPrefix: e.target.value })}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'body' && hasBody && (
            <div>
              <textarea
                className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded p-2 text-xs font-mono text-[var(--color-text-primary)] resize-none focus:outline-none focus:border-[var(--color-accent)] min-h-[120px]"
                value={requestBody}
                onChange={(e) => setRequestBody(e.target.value)}
                placeholder={getBodyPlaceholder(operation, spec)}
                spellCheck={false}
              />
              <button
                onClick={() => {
                  const placeholder = getBodyPlaceholder(operation, spec);
                  if (placeholder && placeholder !== '{}') setRequestBody(placeholder);
                }}
                className="mt-1.5 text-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                {t('apiExplorer:request.fillExample')}
              </button>
            </div>
          )}

          {activeTab === 'docs' && (
            <div className="space-y-6">
              {operation.description && (
                <div>
                  <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                    {t('apiExplorer:detail.description')}
                  </h4>
                  <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{operation.description}</p>
                </div>
              )}
              {(operation.parameters ?? []).length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                    {t('apiExplorer:detail.parameters')}
                  </h4>
                  <div className="space-y-2">
                    {(operation.parameters ?? []).map((p) => (
                      <div key={`${p.in}-${p.name}`} className="flex items-start gap-3 p-2.5 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <code className="text-xs font-mono font-semibold text-[var(--color-text-primary)]">{p.name}</code>
                            <span className="text-[10px] font-mono text-[var(--color-text-muted)] border border-[var(--color-border)] rounded px-1">{p.in}</span>
                            <span className="text-[10px] font-mono text-blue-400/80">{p.schema?.type ?? 'any'}</span>
                            {p.required && <span className="text-[9px] text-red-400 border border-red-400/30 rounded px-1">required</span>}
                          </div>
                          {p.description && <p className="text-xs text-[var(--color-text-muted)] mt-1">{p.description}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {requestBodySchema && (
                <div>
                  <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                    {t('apiExplorer:detail.requestBody')}
                  </h4>
                  <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-3">
                    <SchemaViewer schema={requestBodySchema as Record<string, unknown>} spec={spec} />
                  </div>
                </div>
              )}
              {responseCodes.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                    {t('apiExplorer:detail.responses')}
                  </h4>
                  <div className="space-y-2">
                    {responseCodes.map((code) => {
                      const resp = operation.responses?.[code];
                      const schema = resp?.content ? Object.values(resp.content)[0]?.schema : null;
                      return (
                        <div key={code} className="space-y-1">
                          <div className="flex items-start gap-3 p-2.5 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
                            <span className={`font-mono text-sm font-bold shrink-0 ${getStatusColor(parseInt(code, 10))}`}>{code}</span>
                            <span className="text-sm text-[var(--color-text-secondary)]">{resp?.description ?? '—'}</span>
                          </div>
                          {schema && (
                            <div className="ml-4 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-3">
                              <SchemaViewer schema={schema as Record<string, unknown>} spec={spec} />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {!operation.description && (operation.parameters ?? []).length === 0 && !requestBodySchema && responseCodes.length === 0 && (
                <div className="text-sm text-[var(--color-text-muted)] text-center py-8">
                  {t('apiExplorer:detail.noSchema')}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Response */}
      {(responseStatus !== null || isSendingRequest) && (
        <>
          {/* Drag handle */}
          <div
            className="shrink-0 h-2 flex items-center justify-center cursor-row-resize group select-none"
            onMouseDown={(e) => {
              isDraggingDivider.current = true;
              dragStartY.current = e.clientY;
              dragStartHeight.current = responsePanelHeight;
              document.body.style.cursor = 'row-resize';
              document.body.style.userSelect = 'none';
            }}
          >
            <div className="w-10 h-0.5 rounded-full bg-[var(--color-border)] group-hover:bg-[var(--color-primary)] transition-colors" />
          </div>

        <div
          className="shrink-0 border border-[var(--color-border)] rounded-lg overflow-hidden flex flex-col"
          style={{ height: responsePanelHeight }}
        >
          {/* Response toolbar */}
          <div className="flex items-center justify-between px-3 py-2 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] shrink-0">
            <div className="flex items-center gap-3">
              {/* Body / Headers tabs */}
              <div className="flex">
                {(['headers', 'body'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setResponseTab(tab)}
                    className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                      responseTab === tab
                        ? 'text-[var(--color-text-primary)] bg-[var(--color-bg-primary)]'
                        : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                    }`}
                  >
                    {t(`apiExplorer:response.${tab}`)}
                  </button>
                ))}
              </div>
              {/* Format selector — only when viewing body with content */}
              {responseTab === 'body' && responseBody && (
                <div className="flex items-center gap-1 border-l border-[var(--color-border)] pl-3">
                  {/* Segmented control wrapper */}
                  <div className="flex items-center rounded-md border border-[var(--color-border)] bg-[var(--color-bg-tertiary)] p-0.5 gap-0.5">
                    {/* "Formaté" + language dropdown grouped */}
                    <div className={`flex items-center rounded transition-colors ${
                      responseFormat === 'pretty'
                        ? 'bg-[var(--color-bg-primary)] shadow-sm'
                        : 'hover:bg-[var(--color-bg-secondary)]'
                    }`}>
                      <button
                        onClick={() => setResponseFormat('pretty')}
                        className={`px-2.5 py-1 text-[11px] font-medium transition-colors ${
                          responseFormat === 'pretty'
                            ? 'text-[var(--color-text-primary)]'
                            : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
                        }`}
                      >
                        {t('apiExplorer:response.format.pretty')}
                      </button>
                      <LangDropdown
                        value={responseLanguage}
                        onChange={setResponseLanguage}
                        t={t}
                        active={responseFormat === 'pretty'}
                        onActivate={() => setResponseFormat('pretty')}
                      />
                    </div>
                    {/* "Brut" */}
                    <button
                      onClick={() => setResponseFormat('raw')}
                      className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                        responseFormat === 'raw'
                          ? 'bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] shadow-sm'
                          : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)]'
                      }`}
                    >
                      {t('apiExplorer:response.format.raw')}
                    </button>
                    {/* "Aperçu" — only for HTML responses */}
                    {detectContentType(responseHeaders).includes('text/html') && (
                      <button
                        onClick={() => setResponseFormat('preview')}
                        className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                          responseFormat === 'preview'
                            ? 'bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] shadow-sm'
                            : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)]'
                        }`}
                      >
                        {t('apiExplorer:response.format.preview')}
                      </button>
                    )}
                  </div>
                </div>
              )}
              {responseStatus !== null && (
                <div className="flex items-center gap-2 text-xs">
                  <span className={`font-mono font-bold ${getStatusColor(responseStatus)}`}>
                    {responseStatus} {responseStatusText}
                  </span>
                  {responseTime !== null && (
                    <span className="text-[var(--color-text-muted)]">{responseTime}ms</span>
                  )}
                  {responseBody && (
                    <span className="text-[var(--color-text-muted)]">
                      {(new TextEncoder().encode(responseBody).length / 1024).toFixed(1)} KB
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              {extractedToken && (
                <button
                  onClick={saveTokenToEnv}
                  title={t('apiExplorer:response.saveTokenTitle')}
                  className={`flex items-center gap-1.5 px-2 py-0.5 text-[11px] rounded border transition-colors ${
                    savedToken
                      ? 'text-emerald-400 border-emerald-500/40 bg-emerald-400/10'
                      : 'text-[var(--color-text-muted)] border-[var(--color-border)] hover:text-[var(--color-primary)] hover:border-[var(--color-primary)]/40'
                  }`}
                >
                  {savedToken ? <Check size={11} /> : <Shield size={11} />}
                  {savedToken ? t('apiExplorer:response.tokenSaved') : t('apiExplorer:response.saveToken')}
                </button>
              )}
              {responseBody && (
                <button onClick={copyResponse} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                  {copiedResponse ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                </button>
              )}
            </div>
          </div>

          {/* Response content — fills remaining height */}
          <div className="flex-1 min-h-0 overflow-auto">
            {isSendingRequest && !responseBody ? (
              <div className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] h-full justify-center">
                <Loader2 size={15} className="animate-spin" />
                {t('apiExplorer:request.sending')}
              </div>
            ) : responseTab === 'body' ? (
              responseFormat === 'preview' ? (
                <iframe
                  srcDoc={responseBody}
                  sandbox=""
                  title={t('apiExplorer:response.format.preview')}
                  className="w-full h-full border-0"
                  style={{ background: '#fff' }}
                />
              ) : (
                <div className="p-3">
                  {responseFormat === 'raw' ? (
                    <pre className="text-xs font-mono text-[var(--color-text-primary)] whitespace-pre-wrap break-all">
                      {responseBody}
                    </pre>
                  ) : (
                    /* pretty */
                    (() => {
                      const ct = detectContentType(responseHeaders);
                      const effectiveLang = responseLanguage !== 'auto'
                        ? responseLanguage
                        : ct.includes('xml') || ct.includes('svg')
                          ? 'xml'
                          : ct.includes('text/html')
                            ? 'html'
                            : ct.includes('json')
                              ? 'json'
                              : 'text';

                      if (effectiveLang === 'xml' || effectiveLang === 'html') {
                        const isXmlLike = responseBody.trimStart().startsWith('<');
                        return (
                          <>
                            {!isXmlLike && responseLanguage !== 'auto' && (
                              <p className="mb-2 text-[11px] text-amber-400">
                                {t('apiExplorer:response.format.mismatch', { format: effectiveLang.toUpperCase() })}
                              </p>
                            )}
                            <pre className="text-xs font-mono text-[var(--color-text-primary)] whitespace-pre-wrap break-all">
                              {isXmlLike ? prettifyXml(responseBody) : responseBody}
                            </pre>
                          </>
                        );
                      }
                      if (effectiveLang === 'text') {
                        return (
                          <pre className="text-xs font-mono text-[var(--color-text-primary)] whitespace-pre-wrap break-all">
                            {responseBody}
                          </pre>
                        );
                      }
                      // JSON
                      let isValidJson = true;
                      try { JSON.parse(responseBody); } catch { isValidJson = false; }
                      return (
                        <>
                          {!isValidJson && responseLanguage !== 'auto' && (
                            <p className="mb-2 text-[11px] text-amber-400">
                              {t('apiExplorer:response.format.mismatch', { format: 'JSON' })}
                            </p>
                          )}
                          <pre
                            className="text-xs font-mono whitespace-pre-wrap break-all"
                            // biome-ignore lint/security/noDangerouslySetInnerHtml: content is HTML-escaped before highlighting
                            dangerouslySetInnerHTML={{ __html: isValidJson ? syntaxHighlightJson(responseBody) : escapeHtml(responseBody) }}
                          />
                        </>
                      );
                    })()
                  )}
                </div>
              )
            ) : (
              <div className="p-3 space-y-1">
                {Object.entries(responseHeaders).map(([k, v]) => (
                  <div key={k} className="flex gap-2 text-xs">
                    <span className="font-mono text-[var(--color-text-muted)] shrink-0">{k}:</span>
                    <span className="font-mono text-[var(--color-text-primary)] break-all">{v}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        </>
      )}
    </div>
  );
}

// ── Compact language dropdown for the response toolbar ───────────────────────
const LANG_OPTIONS = ['auto', 'json', 'xml', 'html', 'text'] as const;
type ResponseLanguage = (typeof LANG_OPTIONS)[number];

interface LangDropdownProps {
  value: ResponseLanguage;
  onChange: (v: ResponseLanguage) => void;
  t: (key: string) => string;
  active?: boolean;
  onActivate?: () => void;
}
function LangDropdown({ value, onChange, t, active = true, onActivate }: LangDropdownProps) {
  const [open, setOpen] = useState(false);
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);
  const portalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      const target = e.target as Node;
      if (btnRef.current?.closest('[data-lang-dropdown]')?.contains(target)) return;
      if (portalRef.current?.contains(target)) return;
      setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  function handleOpen() {
    onActivate?.();
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      setDropdownPos({ top: rect.bottom + 4, left: rect.left });
    }
    setOpen((v) => !v);
  }

  return (
    <div className="relative" data-lang-dropdown="">
      <button
        ref={btnRef}
        type="button"
        onClick={handleOpen}
        className={`flex items-center gap-0.5 pl-0 pr-1.5 py-1 text-[11px] transition-colors cursor-pointer ${
          active
            ? 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
            : 'text-[var(--color-text-muted)]/60 hover:text-[var(--color-text-muted)]'
        }`}
      >
        {t(`apiExplorer:response.format.lang.${value}`)}
        <ChevronDown size={10} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && createPortal(
        <div
          ref={portalRef}
          data-lang-dropdown=""
          className="fixed min-w-[80px] border border-[var(--color-border)] rounded-md shadow-2xl overflow-hidden"
          style={{ top: dropdownPos.top, left: dropdownPos.left, zIndex: 2147483647, backgroundColor: 'var(--card, var(--color-bg-secondary))', isolation: 'isolate' }}
        >
          {LANG_OPTIONS.map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => { onChange(lang); setOpen(false); }}
              className={`flex items-center gap-1.5 w-full px-2.5 py-1.5 text-[11px] text-left transition-colors hover:bg-(--color-bg-secondary) ${
                lang === value
                  ? 'text-[var(--color-primary)]'
                  : 'text-[var(--color-text-secondary)]'
              }`}
            >
              {lang === value && <Check size={10} className="shrink-0" />}
              {lang !== value && <span className="w-[10px] shrink-0" />}
              {t(`apiExplorer:response.format.lang.${lang}`)}
            </button>
          ))}
        </div>,
        document.body
      )}
    </div>
  );
}

interface CustomSelectOption {
  value: string;
  label: string;
}
interface CustomSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: CustomSelectOption[];
  className?: string;
}
function CustomSelect({ value, onChange, options, className }: CustomSelectProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const selected = options.find((o) => o.value === value);

  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div
      ref={containerRef}
      className={`relative ${className ?? ''}`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center justify-between w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-3 py-2 text-[length:inherit] text-[var(--color-text-primary)] hover:border-[var(--color-border-hover)] focus:outline-none focus:border-[var(--color-accent)] cursor-pointer transition-colors"
      >
        <span>{selected?.label ?? value}</span>
        <ChevronDown size={14} className={`text-[var(--color-text-muted)] shrink-0 ml-2 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute z-50 top-full left-0 min-w-full w-max mt-1 bg-[var(--card)] border border-[var(--color-border)] rounded-md shadow-xl overflow-hidden" style={{ backdropFilter: 'none' }}>
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => { onChange(opt.value); setOpen(false); }}
              className={`flex items-center gap-2 w-full px-3 py-2 text-[length:inherit] text-left transition-colors hover:bg-[var(--color-bg-secondary)] ${
                opt.value === value
                  ? 'text-[var(--color-text-primary)] bg-[var(--color-bg-secondary)]'
                  : 'text-[var(--color-text-secondary)]'
              }`}
            >
              {opt.value === value && <Check size={13} className="shrink-0 text-[var(--color-primary)]" />}
              {opt.value !== value && <span className="w-[13px] shrink-0" />}
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface KVRow { id: string; enabled: boolean; key: string; value: string; }

type CustomRowField = 'key' | 'value' | 'enabled';
type CustomRowValue = string | boolean;

interface KeyValueEditorProps {
  rows: KVRow[];
  onAdd: () => void;
  onUpdate: (id: string, field: CustomRowField, val: CustomRowValue) => void;
  onRemove: (id: string) => void;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
  addLabel: string;
}
function KeyValueEditor({ rows, onAdd, onUpdate, onRemove, keyPlaceholder = 'Key', valuePlaceholder = 'Value', addLabel }: KeyValueEditorProps) {
  return (
    <div className="space-y-1.5">
      {rows.map((row) => (
        <div key={row.id} className="flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={row.enabled}
            onChange={(e) => onUpdate(row.id, 'enabled', e.target.checked)}
            className="w-3.5 h-3.5 shrink-0 accent-[var(--color-primary)] cursor-pointer"
          />
          <input
            className="flex-1 min-w-0 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1.5 text-xs font-mono text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]"
            value={row.key}
            onChange={(e) => onUpdate(row.id, 'key', e.target.value)}
            placeholder={keyPlaceholder}
          />
          <input
            className="flex-1 min-w-0 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1.5 text-xs font-mono text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]"
            value={row.value}
            onChange={(e) => onUpdate(row.id, 'value', e.target.value)}
            placeholder={valuePlaceholder}
          />
          <button
            type="button"
            onClick={() => onRemove(row.id)}
            className="shrink-0 p-1 text-[var(--color-text-muted)] hover:text-red-400 transition-colors"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={onAdd}
        className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors py-1"
      >
        <Plus size={13} />
        {addLabel}
      </button>
    </div>
  );
}

function ParamRow({ param, value, onChange }: { param: OpenApiParameter; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2 mb-1.5">
      <div className="w-32 shrink-0">
        <span className="text-xs font-mono text-[var(--color-text-secondary)]">{param.name}</span>
        {param.required && <span className="text-red-400 ml-0.5">*</span>}
      </div>
      <input
        className="flex-1 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={param.example ? String(param.example) : param.description ?? ''}
      />
    </div>
  );
}

function getBodyPlaceholder(operation: OpenApiOperation, spec: OpenApiSpec): string {
  if (!operation.requestBody) return '{}';
  const content = operation.requestBody.content ?? {};
  const jsonContent = content['application/json'];
  if (!jsonContent) return '{}';

  if (jsonContent.example) {
    return JSON.stringify(jsonContent.example, null, 2);
  }

  if (jsonContent.schema) {
    const schema = jsonContent.schema.$ref
      ? resolveRef(jsonContent.schema.$ref, spec) ?? jsonContent.schema
      : jsonContent.schema;

    if (schema.example) return JSON.stringify(schema.example, null, 2);

    // Build example from schema
    const example = buildExampleFromSchema(schema as Record<string, unknown>, spec, 0);
    return JSON.stringify(example, null, 2);
  }

  return '{}';
}

function buildExampleFromSchema(schema: Record<string, unknown>, spec: OpenApiSpec, depth: number): unknown {
  if (depth > 3) return null;
  const resolved = schema.$ref && typeof schema.$ref === 'string'
    ? (resolveRef(schema.$ref, spec) ?? schema)
    : schema;

  const type = resolved.type as string | undefined;
  const properties = resolved.properties as Record<string, Record<string, unknown>> | undefined;
  const items = resolved.items as Record<string, unknown> | undefined;
  const example = resolved.example;

  if (example !== undefined) return example;

  if (type === 'object' || (!type && properties)) {
    const obj: Record<string, unknown> = {};
    for (const [key, prop] of Object.entries(properties ?? {})) {
      obj[key] = buildExampleFromSchema(prop, spec, depth + 1);
    }
    return obj;
  }
  if (type === 'array') return items ? [buildExampleFromSchema(items, spec, depth + 1)] : [];
  if (type === 'string') return (resolved.enum as string[])?.[0] ?? 'string';
  if (type === 'number' || type === 'integer') return 0;
  if (type === 'boolean') return true;
  return null;
}

// ── Endpoint Detail ──────────────────────────────────────────────────────────

interface EndpointDetailProps {
  method: string;
  path: string;
  operation: OpenApiOperation;
  spec: OpenApiSpec;
  onOpenEnvManager: () => void;
}
function EndpointDetail({ method, path, operation, spec, onOpenEnvManager }: EndpointDetailProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 shrink-0 border-b border-[var(--color-border)]">
        <div className="flex items-start gap-2.5">
          <MethodBadge method={method} size="md" />
          <div className="flex-1 min-w-0">
            <code className="text-sm font-mono text-[var(--color-text-primary)] break-all">{path}</code>
            {operation.summary && (
              <div className="text-xs text-[var(--color-text-secondary)] mt-0.5">{operation.summary}</div>
            )}
          </div>
          {operation.deprecated && (
            <span className="text-[10px] font-mono border border-amber-400/30 text-amber-400 bg-amber-400/10 rounded px-1.5 py-0.5 shrink-0">
              deprecated
            </span>
          )}
        </div>
      </div>

      {/* Request builder — always visible, like Postman */}
      <div className="flex-1 overflow-hidden">
        <RequestPanel method={method} path={path} operation={operation} spec={spec} onOpenEnvManager={onOpenEnvManager} />
      </div>
    </div>
  );
}

// ── Endpoint List ────────────────────────────────────────────────────────────

interface EndpointGroup {
  tag: string;
  tagDescription?: string;
  endpoints: Array<{ method: string; path: string; op: OpenApiOperation }>;
}

function buildGroups(spec: OpenApiSpec, search: string): EndpointGroup[] {
  const tagMap: Record<string, EndpointGroup> = {};
  const tagOrder: string[] = spec.tags?.map((t) => t.name) ?? [];

  for (const [path, methods] of Object.entries(spec.paths ?? {})) {
    for (const [method, op] of Object.entries(methods)) {
      if (!['get', 'post', 'put', 'delete', 'patch', 'head', 'options'].includes(method)) continue;

      const searchLower = search.toLowerCase();
      if (
        search &&
        !path.toLowerCase().includes(searchLower) &&
        !op.summary?.toLowerCase().includes(searchLower) &&
        !op.operationId?.toLowerCase().includes(searchLower)
      ) {
        continue;
      }

      const tags = op.tags?.length ? op.tags : ['default'];
      for (const tag of tags) {
        if (!tagMap[tag]) {
          const tagMeta = spec.tags?.find((t) => t.name === tag);
          tagMap[tag] = { tag, tagDescription: tagMeta?.description, endpoints: [] };
          if (!tagOrder.includes(tag)) tagOrder.push(tag);
        }
        tagMap[tag].endpoints.push({ method, path, op });
      }
    }
  }

  return tagOrder.filter((t) => tagMap[t]).map((t) => tagMap[t]);
}

// ── Main ApiExplorer Component ───────────────────────────────────────────────

export function ApiExplorer() {
  const { t } = useTranslation(['apiExplorer']);

  const spec = useApiExplorerStore((s) => s.spec);
  const specUrl = useApiExplorerStore((s) => s.specUrl);
  const isLoadingSpec = useApiExplorerStore((s) => s.isLoadingSpec);
  const specError = useApiExplorerStore((s) => s.specError);
  const specSource = useApiExplorerStore((s) => s.specSource);
  const isProjectScanning = useApiExplorerStore((s) => s.isProjectScanning);
  const projectScanError = useApiExplorerStore((s) => s.projectScanError);
  const lastProjectScanAt = useApiExplorerStore((s) => s.lastProjectScanAt);
  const environments = useApiExplorerStore((s) => s.environments);
  const activeEnvironmentId = useApiExplorerStore((s) => s.activeEnvironmentId);
  const selectedEndpointKey = useApiExplorerStore((s) => s.selectedEndpointKey);
  const searchQuery = useApiExplorerStore((s) => s.searchQuery);
  const collapsedTags = useApiExplorerStore((s) => s.collapsedTags);

  const setSpec = useApiExplorerStore((s) => s.setSpec);
  const setSpecUrl = useApiExplorerStore((s) => s.setSpecUrl);
  const setSpecSource = useApiExplorerStore((s) => s.setSpecSource);
  const setIsLoadingSpec = useApiExplorerStore((s) => s.setIsLoadingSpec);
  const setSpecError = useApiExplorerStore((s) => s.setSpecError);
  const setActiveEnvironment = useApiExplorerStore((s) => s.setActiveEnvironment);
  const setSelectedEndpointKey = useApiExplorerStore((s) => s.setSelectedEndpointKey);
  const setSearchQuery = useApiExplorerStore((s) => s.setSearchQuery);
  const toggleTag = useApiExplorerStore((s) => s.toggleTag);
  const clearRequestState = useApiExplorerStore((s) => s.clearRequestState);

  const [showEnvManager, setShowEnvManager] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [urlInput, setUrlInput] = useState(specUrl);

  // Background scan hook — rescan() forces a new scan of the active project
  const { rescan } = useProjectRouteScan();

  const activeEnv = environments.find((e) => e.id === activeEnvironmentId) ?? environments[0];

  // App Emulator integration
  const emulatorPhase = useAppEmulatorStore((s) => s.phase);
  const emulatorUrl = useAppEmulatorStore((s) => s.url);
  const emulatorStatus = useAppEmulatorStore((s) => s.status);
  const updateEnvironment = useApiExplorerStore((s) => s.updateEnvironment);

  // Set up IPC listeners for emulator events
  useEffect(() => {
    return setupAppEmulatorListeners();
  }, []);

  // When emulator becomes running, auto-sync active environment base URL
  const prevEmulatorPhase = useRef(emulatorPhase);
  useEffect(() => {
    if (emulatorPhase === 'running' && emulatorUrl && prevEmulatorPhase.current !== 'running') {
      if (activeEnv) {
        updateEnvironment(activeEnv.id, { baseUrl: emulatorUrl });
      }
    }
    prevEmulatorPhase.current = emulatorPhase;
  }, [emulatorPhase, emulatorUrl, activeEnv, updateEnvironment]);

  function handleEmulatorToggle() {
    // Always open the dialog — stop is handled inside the dialog
    openAppEmulatorDialog();
  }

  // Load spec from a remote OpenAPI URL (via main process proxy to bypass CSP)
  const loadSpec = useCallback(async (url: string) => {
    setIsLoadingSpec(true);
    setSpecError(null);
    try {
      const result = await globalThis.electronAPI.proxyHttpRequest({ url, method: 'GET', headers: { Accept: 'application/json' } });
      if (!result.success || !result.status || result.status >= 400) {
        throw new Error(`HTTP ${result.status ?? 0}: ${result.statusText ?? 'Error'}`);
      }
      const data: OpenApiSpec = JSON.parse(result.body ?? '');
      setSpec(data);
      setSpecSource('url');
    } catch (err) {
      setSpecError(String(err));
      setSpec(null);
    } finally {
      setIsLoadingSpec(false);
    }
  }, [setIsLoadingSpec, setSpecError, setSpec, setSpecSource]);

  function applySpecUrl() {
    if (urlInput !== specUrl) {
      setSpecUrl(urlInput);
    }
    void loadSpec(urlInput);
  }

  const groups = useMemo(
    () => (spec ? buildGroups(spec, searchQuery) : []),
    [spec, searchQuery]
  );

  const totalEndpoints = useMemo(
    () => groups.reduce((acc, g) => acc + g.endpoints.length, 0),
    [groups]
  );

  // Find the selected endpoint
  const selectedEndpoint = useMemo(() => {
    if (!selectedEndpointKey || !spec) return null;
    const [method, ...pathParts] = selectedEndpointKey.split(':');
    const path = pathParts.join(':');
    const op = spec.paths?.[path]?.[method.toLowerCase()];
    if (!op) return null;
    return { method, path, op };
  }, [selectedEndpointKey, spec]);

  function selectEndpoint(method: string, path: string) {
    setSelectedEndpointKey(makeEndpointKey(method, path));
    clearRequestState();
  }

  // Emulator button derived values (avoids nested ternaries in JSX)
  const isEmulatorBusy = emulatorPhase === 'detecting' || emulatorPhase === 'starting';
  const isEmulatorRunning = emulatorPhase === 'running';
  const emulatorBtnClass = isEmulatorRunning
    ? 'shrink-0 gap-1.5 border-emerald-500/50 text-emerald-400 hover:bg-emerald-400/10'
    : 'shrink-0 gap-1.5';
  const emulatorBtnTitle = isEmulatorRunning
    ? (emulatorStatus || emulatorUrl || '')
    : t('apiExplorer:emulator.run');
  let emulatorBtnLabel = t('apiExplorer:emulator.run');
  if (emulatorPhase === 'detecting') emulatorBtnLabel = t('apiExplorer:emulator.detecting');
  else if (emulatorPhase === 'starting') emulatorBtnLabel = t('apiExplorer:emulator.starting');
  else if (isEmulatorRunning) emulatorBtnLabel = t('apiExplorer:emulator.running');

  return (
    <div className="flex flex-col h-full bg-[var(--color-bg-primary)] text-[var(--color-text-primary)]">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border)] shrink-0 bg-[var(--color-bg-primary)]">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Globe size={16} className="text-[var(--color-text-muted)] shrink-0" />
          <input
            className="flex-1 min-w-0 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-2.5 py-1.5 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)]"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && applySpecUrl()}
            placeholder="http://127.0.0.1:9000/openapi.json"
          />
          <Button
            size="sm"
            variant="outline"
            onClick={applySpecUrl}
            disabled={isLoadingSpec}
            className="shrink-0"
          >
            {isLoadingSpec ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={rescan}
            disabled={isProjectScanning}
            className="shrink-0 gap-1.5"
            title={t('apiExplorer:scan.tooltip')}
          >
            {isProjectScanning
              ? <Loader2 size={13} className="animate-spin" />
              : <ScanSearch size={13} />}
            <span className="text-[11px]">
              {isProjectScanning ? t('apiExplorer:scan.scanning') : t('apiExplorer:scan.resync')}
            </span>
          </Button>

          {/* App Emulator toggle button */}
          <Button
            size="sm"
            variant="outline"
            onClick={handleEmulatorToggle}
            disabled={isEmulatorBusy}
            className={emulatorBtnClass}
            title={emulatorBtnTitle}
          >
            {isEmulatorBusy && <Loader2 size={13} className="animate-spin" />}
            {!isEmulatorBusy && <Play size={13} />}
            <span className="text-[11px]">{emulatorBtnLabel}</span>
            {isEmulatorRunning && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
            )}
          </Button>
        </div>

        {/* Environment selector */}
        <div className="flex items-center gap-1 shrink-0">
          <CustomSelect
            value={activeEnvironmentId}
            onChange={setActiveEnvironment}
            options={[
              { value: '', label: t('apiExplorer:environments.placeholder') },
              ...environments.map((env) => ({ value: env.id, label: env.name })),
            ]}
            className="max-w-36 text-xs"
          />
          <button
            onClick={() => setShowEnvManager(true)}
            className="p-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)] rounded-md transition-colors"
            title={t('apiExplorer:environments.manage')}
          >
            <Settings size={14} />
          </button>
        </div>

        {/* Export */}
        {spec && (
          <button
            onClick={() => setShowExport(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md transition-colors shrink-0"
          >
            <Download size={13} />
            {t('apiExplorer:actions.export')}
          </button>
        )}
      </div>

      {/* Main layout */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <div className="w-64 shrink-0 flex flex-col border-r border-[var(--color-border)] bg-[var(--color-bg-primary)]">
          {/* Spec info + scan status + search */}
          <div className="p-3 border-b border-[var(--color-border)]">
            {/* Scan status banner */}
            {isProjectScanning && (
              <div className="flex items-center gap-1.5 mb-2 text-[10px] text-[var(--color-text-muted)]">
                <Loader2 size={10} className="animate-spin shrink-0" />
                <span>{t('apiExplorer:scan.scanning')}</span>
              </div>
            )}

            {/* Project scan error */}
            {projectScanError && !isProjectScanning && (
              <div className="flex items-start gap-1.5 mb-2 p-2 bg-amber-400/10 border border-amber-400/20 rounded-md">
                <AlertCircle size={11} className="text-amber-400 shrink-0 mt-0.5" />
                <span className="text-[10px] text-amber-400/80 break-all">{projectScanError}</span>
              </div>
            )}

            {spec && (
              <div className="mb-2.5">
                <div className="flex items-center gap-2 mb-0.5">
                  <div className="text-sm font-semibold text-[var(--color-text-primary)] truncate flex-1">{spec.info.title}</div>
                  {/* Source badge */}
                  {specSource === 'scan' && (
                    <span className="shrink-0 text-[9px] font-medium px-1.5 py-0.5 rounded bg-emerald-400/10 text-emerald-400 border border-emerald-400/20">
                      {t('apiExplorer:scan.sourceBadge')}
                    </span>
                  )}
                  {specSource === 'url' && (
                    <span className="shrink-0 text-[9px] font-medium px-1.5 py-0.5 rounded bg-blue-400/10 text-blue-400 border border-blue-400/20">
                      URL
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-[var(--color-text-muted)] font-mono">
                  v{spec.info.version} · {totalEndpoints} {t('apiExplorer:sidebar.endpoints')}
                  {specSource === 'scan' && lastProjectScanAt && (
                    <span className="ml-1 opacity-60">
                      · {t('apiExplorer:scan.scannedAt', { time: new Date(lastProjectScanAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) })}
                    </span>
                  )}
                </div>
              </div>
            )}
            <div className="relative">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
              <input
                className="w-full pl-7 pr-2 py-1.5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)]"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('apiExplorer:sidebar.search')}
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
                  <X size={11} />
                </button>
              )}
            </div>
          </div>

          {/* Endpoint list */}
          <div className="flex-1 overflow-y-auto">
            {isLoadingSpec && (
              <div className="flex items-center justify-center py-12 gap-2 text-sm text-[var(--color-text-muted)]">
                <Loader2 size={15} className="animate-spin" />
                {t('apiExplorer:sidebar.loading')}
              </div>
            )}

            {specError && (
              <div className="p-3">
                <div className="flex items-start gap-2 p-3 bg-red-400/10 border border-red-400/20 rounded-lg">
                  <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-medium text-red-400">{t('apiExplorer:sidebar.loadError')}</div>
                    <div className="text-[10px] text-red-400/70 mt-1 font-mono break-all">{specError}</div>
                  </div>
                </div>
              </div>
            )}

            {!isLoadingSpec && !specError && groups.length === 0 && spec && (
              <div className="text-xs text-[var(--color-text-muted)] text-center py-8">
                {t('apiExplorer:sidebar.noResults')}
              </div>
            )}

            {groups.map((group) => {
              const isCollapsed = collapsedTags.includes(group.tag);
              return (
                <div key={group.tag}>
                  <button
                    onClick={() => toggleTag(group.tag)}
                    className="w-full flex items-center justify-between px-3 py-2 hover:bg-[var(--color-bg-secondary)] transition-colors group"
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      {isCollapsed ? (
                        <ChevronRight size={12} className="text-[var(--color-text-muted)] shrink-0" />
                      ) : (
                        <ChevronDown size={12} className="text-[var(--color-text-muted)] shrink-0" />
                      )}
                      <span className="text-xs font-semibold text-[var(--color-text-secondary)] truncate">{group.tag}</span>
                    </div>
                    <span className="text-[10px] text-[var(--color-text-muted)] font-mono shrink-0 ml-1">
                      {group.endpoints.length}
                    </span>
                  </button>

                  {!isCollapsed && (
                    <div>
                      {group.endpoints.map(({ method, path, op }) => {
                        const key = makeEndpointKey(method, path);
                        const isSelected = selectedEndpointKey === key;
                        const endpointTitle = op.summary ? `${path} — ${op.summary}` : path;
                        return (
                          <button
                            key={key}
                            onClick={() => selectEndpoint(method, path)}
                            className={`w-full flex items-center gap-2 px-3 py-2 text-left transition-colors group ${
                              isSelected
                                ? 'bg-[var(--color-accent)]/10 border-r-2 border-[var(--color-accent)]'
                                : 'hover:bg-[var(--color-bg-secondary)]'
                            }`}
                          >
                            <MethodBadge method={method} />
                            <span
                              className={`text-xs font-mono truncate flex-1 ${
                                isSelected ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)]'
                              }`}
                              title={endpointTitle}
                            >
                              {path}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Active env indicator */}
          {activeEnv && (
            <div className="px-3 py-2 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                <span className="text-[10px] font-mono text-[var(--color-text-muted)] truncate">{activeEnv.baseUrl}</span>
              </div>
            </div>
          )}
        </div>

        {/* Detail panel */}
        <div className="flex-1 min-w-0 overflow-hidden">
          {selectedEndpoint ? (
            <EndpointDetail
              method={selectedEndpoint.method}
              path={selectedEndpoint.path}
              operation={selectedEndpoint.op}
              spec={spec!}
              onOpenEnvManager={() => setShowEnvManager(true)}
            />
          ) : (
            <EmptyState spec={spec} isLoading={isLoadingSpec} t={t} />
          )}
        </div>
      </div>

      {/* Dialogs */}
      {showEnvManager && <EnvironmentManager onClose={() => setShowEnvManager(false)} />}
      {showExport && spec && <ExportDialog spec={spec} onClose={() => setShowExport(false)} />}
    </div>
  );
}

function EmptyState({
  spec,
  isLoading,
  t,
}: {
  spec: OpenApiSpec | null;
  isLoading: boolean;
  t: (key: string) => string;
}) {
  if (isLoading) return null;
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-[var(--color-text-muted)]">
      <div className="w-16 h-16 rounded-2xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)] flex items-center justify-center">
        <ExternalLink size={24} className="opacity-40" />
      </div>
      <div className="text-center">
        <div className="text-sm font-medium text-[var(--color-text-secondary)] mb-1">
          {spec ? t('apiExplorer:empty.selectEndpoint') : t('apiExplorer:empty.noSpec')}
        </div>
        <div className="text-xs text-[var(--color-text-muted)]">
          {spec ? t('apiExplorer:empty.selectEndpointHint') : t('apiExplorer:empty.noSpecHint')}
        </div>
      </div>
    </div>
  );
}
