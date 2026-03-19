import { useState, useCallback, useMemo } from 'react';
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
} from '../../stores/api-explorer-store';

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
    const fullPath = `${projectPath}/${relPath}`.replace(/\\/g, '/');
    try {
      const result = await window.electronAPI.readFile(fullPath);
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
  method: string;
  size?: 'sm' | 'md';
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
  onClose: () => void;
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
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newHeaders, setNewHeaders] = useState('');

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
    updateEnvironment(editId, { name: editName, baseUrl: editUrl, headers });
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
    addEnvironment({ name: newName, baseUrl: newUrl, headers });
    setIsAdding(false);
    setNewName('');
    setNewUrl('');
    setNewHeaders('');
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
                  <textarea
                    className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs font-mono text-[var(--color-text-primary)] resize-none"
                    rows={3}
                    value={editHeaders}
                    onChange={(e) => setEditHeaders(e.target.value)}
                    placeholder="Authorization: Bearer token&#10;X-API-Key: key"
                  />
                  <div className="flex gap-2 justify-end">
                    <Button size="sm" variant="outline" onClick={() => setEditId(null)}>{t('apiExplorer:actions.cancel')}</Button>
                    <Button size="sm" onClick={saveEdit}>{t('apiExplorer:actions.save')}</Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-[var(--color-text-primary)]">{env.name}</div>
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
                <label key={idx} className="flex items-center gap-2.5 cursor-pointer group">
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
            <textarea
              className="w-full bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs font-mono text-[var(--color-text-primary)] resize-none"
              rows={2}
              value={newHeaders}
              onChange={(e) => setNewHeaders(e.target.value)}
              placeholder="Authorization: Bearer token"
            />
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
  spec: OpenApiSpec;
  onClose: () => void;
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
              acc[p.name] = p.example ? String(p.example) : '';
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
  const lines: string[] = [];
  lines.push(`# ${spec.info.title}`);
  lines.push('');
  if (spec.info.description) {
    lines.push(spec.info.description);
    lines.push('');
  }
  lines.push(`**Version:** ${spec.info.version}`);
  lines.push('');

  const tagMap: Record<string, Array<{ method: string; path: string; op: OpenApiOperation }>> = {};
  for (const [path, methods] of Object.entries(spec.paths ?? {})) {
    for (const [method, op] of Object.entries(methods)) {
      const tag = op.tags?.[0] ?? 'default';
      if (!tagMap[tag]) tagMap[tag] = [];
      tagMap[tag].push({ method, path, op });
    }
  }

  for (const [tag, endpoints] of Object.entries(tagMap)) {
    lines.push(`## ${tag}`);
    lines.push('');
    for (const { method, path, op } of endpoints) {
      lines.push(`### \`${method.toUpperCase()} ${path}\``);
      lines.push('');
      if (op.summary) lines.push(`**${op.summary}**`);
      if (op.description) lines.push(op.description);
      lines.push('');
      if (op.parameters && op.parameters.length > 0) {
        lines.push('**Parameters:**');
        lines.push('');
        lines.push('| Name | In | Type | Required | Description |');
        lines.push('|------|-----|------|----------|-------------|');
        for (const param of op.parameters) {
          lines.push(
            `| \`${param.name}\` | ${param.in} | ${param.schema?.type ?? '-'} | ${param.required ? '✓' : '-'} | ${param.description ?? '-'} |`
          );
        }
        lines.push('');
      }
      if (op.responses) {
        lines.push('**Responses:**');
        lines.push('');
        lines.push('| Status | Description |');
        lines.push('|--------|-------------|');
        for (const [status, resp] of Object.entries(op.responses)) {
          lines.push(`| ${status} | ${resp.description ?? '-'} |`);
        }
        lines.push('');
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
    download(JSON.stringify(spec, null, 2), 'openapi.json', 'application/json');
  }

  function exportPostman() {
    const collection = buildPostmanCollection(spec, activeEnv?.baseUrl ?? '');
    download(JSON.stringify(collection, null, 2), 'collection.postman_collection.json', 'application/json');
  }

  function exportMarkdown() {
    download(buildMarkdownDocs(spec), `${spec.info.title.toLowerCase().replace(/\s+/g, '-')}-api.md`, 'text/markdown');
  }

  function copyOpenApi() {
    navigator.clipboard.writeText(JSON.stringify(spec, null, 2));
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

        <div className="space-y-2.5">
          {formats.map((fmt) => (
            <button
              key={fmt.label}
              onClick={fmt.action}
              className="w-full text-left flex items-center gap-3 p-3 rounded-lg border border-[var(--color-border)] hover:border-[var(--color-border-hover)] hover:bg-[var(--color-bg-secondary)] transition-all group"
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
            className="w-full flex items-center justify-center gap-2 py-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
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
  schema: Record<string, unknown>;
  spec: OpenApiSpec;
  depth?: number;
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
              {val.description && <span className="text-xs text-[var(--color-text-muted)]">— {val.description as string}</span>}
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
  method: string;
  path: string;
  operation: OpenApiOperation;
  spec: OpenApiSpec;
}
function RequestPanel({ method, path, operation, spec }: RequestPanelProps) {
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

  const setRequestPathParams = useApiExplorerStore((s) => s.setRequestPathParams);
  const setRequestQueryParams = useApiExplorerStore((s) => s.setRequestQueryParams);
  const setRequestHeaders = useApiExplorerStore((s) => s.setRequestHeaders);
  const setRequestBody = useApiExplorerStore((s) => s.setRequestBody);
  const setResponse = useApiExplorerStore((s) => s.setResponse);
  const clearResponse = useApiExplorerStore((s) => s.clearResponse);
  const setIsSendingRequest = useApiExplorerStore((s) => s.setIsSendingRequest);

  const [activeTab, setActiveTab] = useState<'params' | 'headers' | 'body'>('params');
  const [responseTab, setResponseTab] = useState<'body' | 'headers'>('body');
  const [copiedResponse, setCopiedResponse] = useState(false);

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

  // Build the resolved URL preview
  const resolvedUrl = useMemo(() => {
    let url = `${activeEnv?.baseUrl ?? ''}${path}`;
    for (const [key, val] of Object.entries(requestPathParams)) {
      if (val) url = url.replace(`{${key}}`, encodeURIComponent(val));
    }
    const qp = Object.entries(requestQueryParams).filter(([, v]) => v);
    if (qp.length > 0) {
      url += '?' + qp.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
    }
    return url;
  }, [activeEnv, path, requestPathParams, requestQueryParams]);

  async function sendRequest() {
    setIsSendingRequest(true);
    clearResponse();

    const headers: Record<string, string> = {
      ...Object.fromEntries(
        Object.entries(activeEnv?.headers ?? {}).filter(([, v]) => v)
      ),
      ...Object.fromEntries(
        Object.entries(requestHeaders).filter(([, v]) => v)
      ),
    };

    if (hasBody && requestBody) {
      headers['Content-Type'] = 'application/json';
    }

    const start = Date.now();
    try {
      const res = await fetch(resolvedUrl, {
        method: method.toUpperCase(),
        headers,
        body: hasBody && requestBody ? requestBody : undefined,
      });

      const elapsed = Date.now() - start;
      const resHeaders: Record<string, string> = {};
      res.headers.forEach((val, key) => {
        resHeaders[key] = val;
      });

      let body = '';
      const contentType = res.headers.get('content-type') ?? '';
      if (contentType.includes('application/json') || contentType.includes('text/')) {
        body = await res.text();
      } else {
        body = `[Binary content: ${contentType}]`;
      }

      setResponse({
        status: res.status,
        statusText: res.statusText,
        headers: resHeaders,
        body,
        time: elapsed,
      });
    } catch (err) {
      setResponse({
        status: 0,
        statusText: t('apiExplorer:request.networkError'),
        headers: {},
        body: String(err),
        time: Date.now() - start,
      });
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

  const tabs = [
    { id: 'params' as const, label: `${t('apiExplorer:request.params')} (${pathParams.length + queryParams.length})` },
    { id: 'headers' as const, label: `${t('apiExplorer:request.headers')} (${headerParams.length})` },
    ...(hasBody ? [{ id: 'body' as const, label: t('apiExplorer:request.body') }] : []),
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* URL bar */}
      <div className="flex items-center gap-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg px-3 py-2">
        <MethodBadge method={method} size="md" />
        <span className="font-mono text-xs text-[var(--color-text-muted)] flex-1 truncate">{resolvedUrl}</span>
        <Button
          size="sm"
          onClick={sendRequest}
          disabled={isSendingRequest}
          className="shrink-0 flex items-center gap-1.5"
        >
          {isSendingRequest ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
          {t('apiExplorer:request.send')}
        </Button>
      </div>

      {/* Request tabs */}
      <div className="border border-[var(--color-border)] rounded-lg overflow-hidden">
        <div className="flex border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-[var(--color-text-primary)] border-b-2 border-[var(--color-accent)] -mb-px bg-[var(--color-bg-primary)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-3 min-h-[100px]">
          {activeTab === 'params' && (
            <div className="space-y-3">
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
              {queryParams.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                    {t('apiExplorer:request.queryParams')}
                  </div>
                  {queryParams.map((p) => (
                    <ParamRow key={p.name} param={p} value={requestQueryParams[p.name] ?? ''} onChange={(v) => updateQueryParam(p.name, v)} />
                  ))}
                </div>
              )}
              {pathParams.length === 0 && queryParams.length === 0 && (
                <div className="text-xs text-[var(--color-text-muted)] py-4 text-center">{t('apiExplorer:request.noParams')}</div>
              )}
            </div>
          )}

          {activeTab === 'headers' && (
            <div className="space-y-2">
              {headerParams.map((p) => (
                <ParamRow key={p.name} param={p} value={requestHeaders[p.name] ?? ''} onChange={(v) => updateHeaderParam(p.name, v)} />
              ))}
              {headerParams.length === 0 && (
                <div className="text-xs text-[var(--color-text-muted)] py-4 text-center">{t('apiExplorer:request.noHeaders')}</div>
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
        </div>
      </div>

      {/* Response */}
      {(responseStatus !== null || isSendingRequest) && (
        <div className="border border-[var(--color-border)] rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]">
            <div className="flex items-center gap-3">
              <div className="flex">
                {(['body', 'headers'] as const).map((tab) => (
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
              {responseStatus !== null && (
                <div className="flex items-center gap-2 text-xs">
                  <span className={`font-mono font-bold ${getStatusColor(responseStatus)}`}>
                    {responseStatus} {responseStatusText}
                  </span>
                  {responseTime !== null && (
                    <span className="text-[var(--color-text-muted)]">{responseTime}ms</span>
                  )}
                </div>
              )}
            </div>
            {responseBody && (
              <button onClick={copyResponse} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                {copiedResponse ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
              </button>
            )}
          </div>

          <div className="p-3 max-h-72 overflow-auto">
            {isSendingRequest && !responseBody ? (
              <div className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] py-4 justify-center">
                <Loader2 size={15} className="animate-spin" />
                {t('apiExplorer:request.sending')}
              </div>
            ) : responseTab === 'body' ? (
              <pre className="text-xs font-mono text-[var(--color-text-primary)] whitespace-pre-wrap break-all">
                {prettyJson(responseBody)}
              </pre>
            ) : (
              <div className="space-y-1">
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
      )}
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
}
function EndpointDetail({ method, path, operation, spec }: EndpointDetailProps) {
  const { t } = useTranslation(['apiExplorer']);
  const [section, setSection] = useState<'overview' | 'schema' | 'test'>('overview');

  const responseCodes = Object.keys(operation.responses ?? {});
  const requestBodySchema = operation.requestBody
    ? Object.values(operation.requestBody.content ?? {})[0]?.schema
    : null;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[var(--color-border)] shrink-0">
        <div className="flex items-start gap-3">
          <MethodBadge method={method} size="md" />
          <div className="flex-1 min-w-0">
            <code className="text-sm font-mono text-[var(--color-text-primary)] break-all">{path}</code>
            {operation.summary && (
              <div className="text-sm text-[var(--color-text-secondary)] mt-1">{operation.summary}</div>
            )}
          </div>
          {operation.deprecated && (
            <span className="text-[10px] font-mono border border-amber-400/30 text-amber-400 bg-amber-400/10 rounded px-1.5 py-0.5 shrink-0">
              deprecated
            </span>
          )}
        </div>

        {/* Section tabs */}
        <div className="flex gap-1 mt-4">
          {[
            { id: 'overview' as const, label: t('apiExplorer:detail.overview') },
            { id: 'schema' as const, label: t('apiExplorer:detail.schema') },
            { id: 'test' as const, label: t('apiExplorer:detail.test') },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSection(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                section === tab.id
                  ? 'bg-[var(--color-accent)] text-white'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {section === 'overview' && (
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
                    <div
                      key={`${p.in}-${p.name}`}
                      className="flex items-start gap-3 p-2.5 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <code className="text-xs font-mono font-semibold text-[var(--color-text-primary)]">{p.name}</code>
                          <span className="text-[10px] font-mono text-[var(--color-text-muted)] border border-[var(--color-border)] rounded px-1">{p.in}</span>
                          <span className="text-[10px] font-mono text-blue-400/80">{p.schema?.type ?? 'any'}</span>
                          {p.required && <span className="text-[9px] text-red-400 border border-red-400/30 rounded px-1">required</span>}
                        </div>
                        {p.description && (
                          <p className="text-xs text-[var(--color-text-muted)] mt-1">{p.description}</p>
                        )}
                      </div>
                    </div>
                  ))}
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
                    return (
                      <div key={code} className="flex items-start gap-3 p-2.5 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
                        <span className={`font-mono text-sm font-bold shrink-0 ${getStatusColor(parseInt(code, 10))}`}>{code}</span>
                        <span className="text-sm text-[var(--color-text-secondary)]">{resp?.description ?? '—'}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {section === 'schema' && (
          <div className="space-y-6">
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

            {responseCodes.map((code) => {
              const resp = operation.responses?.[code];
              const schema = resp?.content
                ? Object.values(resp.content)[0]?.schema
                : null;
              if (!schema) return null;
              return (
                <div key={code}>
                  <h4 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                    {t('apiExplorer:detail.responseSchema')} <span className={`font-mono ml-1 ${getStatusColor(parseInt(code, 10))}`}>{code}</span>
                  </h4>
                  <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-3">
                    <SchemaViewer schema={schema as Record<string, unknown>} spec={spec} />
                  </div>
                </div>
              );
            })}

            {!requestBodySchema && responseCodes.every((code) => !operation.responses?.[code]?.content) && (
              <div className="text-sm text-[var(--color-text-muted)] text-center py-8">
                {t('apiExplorer:detail.noSchema')}
              </div>
            )}
          </div>
        )}

        {section === 'test' && (
          <RequestPanel method={method} path={path} operation={operation} spec={spec} />
        )}
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

  // Load spec from a remote OpenAPI URL (manual action only — no auto-load on mount)
  const loadSpec = useCallback(async (url: string) => {
    setIsLoadingSpec(true);
    setSpecError(null);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data: OpenApiSpec = await res.json();
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
        </div>

        {/* Environment selector */}
        <div className="flex items-center gap-1 shrink-0">
          <select
            value={activeEnvironmentId}
            onChange={(e) => setActiveEnvironment(e.target.value)}
            className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-md px-2 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-accent)] max-w-36"
          >
            {environments.map((env) => (
              <option key={env.id} value={env.id}>{env.name}</option>
            ))}
          </select>
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
                              title={`${path}${op.summary ? ` — ${op.summary}` : ''}`}
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
