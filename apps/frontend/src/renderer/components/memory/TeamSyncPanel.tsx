import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import type { TeamSyncStatus, TeamSyncPeer, TeamSyncEpisode } from '../../../preload/api/modules/team-sync-api';

interface Props {
  readonly projectDir: string;
}

type SyncMode = 'directory' | 'http';

const EPISODE_TYPE_COLORS: Record<string, string> = {
  session_insight: 'text-blue-400',
  pattern: 'text-green-400',
  gotcha: 'text-red-400',
  codebase_discovery: 'text-purple-400',
  task_outcome: 'text-yellow-400',
  qa_result: 'text-cyan-400',
  historical_context: 'text-gray-400',
};

function EpisodeTypeBadge({ type }: Readonly<{ type: string }>) {
  const { t } = useTranslation('teamSync');
  const color = EPISODE_TYPE_COLORS[type] ?? 'text-gray-400';
  return (
    <span className={`text-xs font-mono px-1.5 py-0.5 rounded bg-white/10 ${color}`}>
      {t(`episodes.types.${type}`, { defaultValue: type })}
    </span>
  );
}

function StatCard({ label, value }: Readonly<{ label: string; value: number | string }>) {
  return (
    <div className="flex flex-col items-center rounded-lg bg-white/5 border border-white/10 px-5 py-3 min-w-[110px]">
      <span className="text-2xl font-bold text-white">{value}</span>
      <span className="text-xs text-white/50 mt-0.5 text-center">{label}</span>
    </div>
  );
}

export function TeamSyncPanel({ projectDir }: Readonly<Props>) {
  const { t } = useTranslation('teamSync');
  const api = globalThis.electronAPI;

  const [status, setStatus] = useState<TeamSyncStatus | null>(null);
  const [peers, setPeers] = useState<TeamSyncPeer[]>([]);
  const [selectedPeer, setSelectedPeer] = useState<string | null>(null);
  const [peerEpisodes, setPeerEpisodes] = useState<TeamSyncEpisode[]>([]);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  // Config form state
  const [showConfig, setShowConfig] = useState(false);
  const [configMode, setConfigMode] = useState<SyncMode>('directory');
  const [configSyncPath, setConfigSyncPath] = useState('');
  const [configTeamId, setConfigTeamId] = useState('default');
  const [configMemberId, setConfigMemberId] = useState('');
  const [configServerUrl, setConfigServerUrl] = useState('');
  const [configServerPort, setConfigServerPort] = useState(7749);
  const [configAutoSync, setConfigAutoSync] = useState(30);
  const [configAutoPush, setConfigAutoPush] = useState(true);
  const [savingConfig, setSavingConfig] = useState(false);

  const showFeedback = (type: 'success' | 'error', msg: string) => {
    setFeedback({ type, msg });
    setTimeout(() => setFeedback(null), 4000);
  };

  const loadStatus = useCallback(async () => {
    setLoadingStatus(true);
    try {
      const res = await api.teamSyncGetStatus(projectDir);
      if (res.success && res.data) {
        const s = res.data as TeamSyncStatus;
        setStatus(s);
        // Seed config form from current status
        setConfigMode(s.mode);
        setConfigSyncPath(s.sync_path);
        setConfigTeamId(s.team_id);
        setConfigMemberId(s.member_id);
        setConfigServerUrl(s.server_url);
        setConfigServerPort(s.server_port);
      }
    } finally {
      setLoadingStatus(false);
    }
  }, [projectDir, api]);

  const loadPeers = useCallback(async () => {
    const res = await api.teamSyncListPeers(projectDir);
    if (res.success && res.data) setPeers(res.data as TeamSyncPeer[]);
  }, [projectDir, api]);

  useEffect(() => {
    loadStatus();
    loadPeers();

    const unsub = api.onTeamSyncServerStatus((s: { running: boolean; port: number }) => {
      setStatus((prev) => prev ? { ...prev, server_running: s.running, server_port: s.port } : prev);
    });
    return unsub;
  }, [loadStatus, loadPeers, api]);

  const handlePush = async () => {
    setPushing(true);
    try {
      const res = await api.teamSyncPush(projectDir);
      if (res.success) {
        showFeedback('success', t('feedback.pushSuccess', { count: res.data?.episode_count ?? '?' }));
        loadStatus();
        loadPeers();
      } else {
        showFeedback('error', t('feedback.pushError', { error: res.error }));
      }
    } finally {
      setPushing(false);
    }
  };

  const handlePull = async () => {
    setPulling(true);
    try {
      const res = await api.teamSyncPull(projectDir);
      const data = res.data;
      if (res.success) {
        const count = data?.imported ?? 0;
        const peerCount = (data?.peers ?? []).length;
        if (count > 0) {
          showFeedback('success', t('feedback.pullSuccess', { count, peers: peerCount }));
        } else {
          showFeedback('success', t('feedback.pullNone'));
        }
        loadStatus();
        loadPeers();
      } else {
        showFeedback('error', t('feedback.pullError', { error: res.error }));
      }
    } finally {
      setPulling(false);
    }
  };

  const handleToggleServer = async () => {
    if (status?.server_running) {
      await api.teamSyncStopServer();
      showFeedback('success', t('feedback.serverStopped'));
    } else {
      const res = await api.teamSyncStartServer(projectDir, configServerPort);
      if (res.success) {
        showFeedback('success', t('feedback.serverStarted', { port: res.port }));
      } else {
        showFeedback('error', t('feedback.serverError', { error: res.error }));
      }
    }
  };

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    try {
      await api.teamSyncConfigure(projectDir, {
        mode: configMode,
        sync_path: configSyncPath,
        team_id: configTeamId,
        member_id: configMemberId,
        server_url: configServerUrl,
        server_port: configServerPort,
        auto_sync_interval: configAutoSync,
        auto_push: configAutoPush,
      });
      showFeedback('success', t('config.saved'));
      setShowConfig(false);
      loadStatus();
    } finally {
      setSavingConfig(false);
    }
  };

  const handleViewPeerEpisodes = async (memberId: string) => {
    if (selectedPeer === memberId) {
      setSelectedPeer(null);
      setPeerEpisodes([]);
      return;
    }
    setSelectedPeer(memberId);
    const res = await api.teamSyncGetPeerEpisodes(projectDir, memberId);
    if (res.success && res.data) setPeerEpisodes(res.data as TeamSyncEpisode[]);
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">{t('title')}</h2>
          <p className="text-sm text-white/50 mt-1">{t('subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <button type="button"
            onClick={() => { loadStatus(); loadPeers(); }}
            disabled={loadingStatus}
            className="px-3 py-1.5 rounded-md text-sm bg-white/10 hover:bg-white/15 text-white/70 disabled:opacity-40 transition-colors"
          >
            {t('actions.refresh')}
          </button>
          <button type="button"
            onClick={() => setShowConfig(!showConfig)}
            className="px-3 py-1.5 rounded-md text-sm bg-white/10 hover:bg-white/15 text-white/70 transition-colors"
          >
            ⚙
          </button>
        </div>
      </div>

      {/* Feedback toast */}
      {feedback && (
        <div className={`px-4 py-2 rounded-lg text-sm font-medium ${feedback.type === 'success' ? 'bg-green-500/20 text-green-300 border border-green-500/30' : 'bg-red-500/20 text-red-300 border border-red-500/30'}`}>
          {feedback.msg}
        </div>
      )}

      {/* Status bar */}
      <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm ${status?.enabled ? 'border-green-500/30 bg-green-500/10 text-green-300' : 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300'}`}>
        <span className={`w-2 h-2 rounded-full ${status?.enabled ? 'bg-green-400' : 'bg-yellow-400'}`} />
        {status?.enabled ? t('status.enabled') : t('status.disabled')}
        {status?.server_running && (
          <span className="ml-auto text-xs text-white/50">
            {t('status.serverRunning', { port: status.server_port })}
          </span>
        )}
      </div>

      {/* Stats */}
      {status?.enabled && (
        <div className="flex gap-3 flex-wrap">
          <StatCard label={t('stats.localEpisodes')} value={status.local_episode_count} />
          <StatCard label={t('stats.importedEpisodes')} value={status.imported_episode_count} />
          <StatCard label={t('stats.peers')} value={peers.length} />
        </div>
      )}

      {/* Config panel */}
      {showConfig && (
        <div className="rounded-xl border border-white/10 bg-white/5 p-5 flex flex-col gap-4">
          <h3 className="font-medium text-white text-sm">{t('config.title')}</h3>

          {/* Mode */}
          <div className="flex flex-col gap-1">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
            <label className="text-xs text-white/60">{t('config.mode')}</label>
            <div className="flex gap-2">
              {(['directory', 'http'] as SyncMode[]).map((m) => (
                <button type="button"
                  key={m}
                  onClick={() => setConfigMode(m)}
                  className={`flex-1 py-1.5 rounded-md text-sm transition-colors ${configMode === m ? 'bg-blue-600 text-white' : 'bg-white/10 text-white/60 hover:bg-white/15'}`}
                >
                  {t(`config.mode${m === 'directory' ? 'Directory' : 'Http'}`)}
                </button>
              ))}
            </div>
            <p className="text-xs text-white/40 mt-1">
              {t(`config.mode${configMode === 'directory' ? 'Directory' : 'Http'}Hint`)}
            </p>
          </div>

          {/* Mode-specific fields */}
          {configMode === 'directory' ? (
            <div className="flex flex-col gap-1">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
              <label className="text-xs text-white/60">{t('config.syncPath')}</label>
              <input
                value={configSyncPath}
                onChange={(e) => setConfigSyncPath(e.target.value)}
                placeholder={t('config.syncPathPlaceholder')}
                className="w-full bg-white/10 border border-white/15 rounded-md px-3 py-1.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-blue-500/60"
              />
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
                <label className="text-xs text-white/60">{t('config.serverUrl')}</label>
                <input
                  value={configServerUrl}
                  onChange={(e) => setConfigServerUrl(e.target.value)}
                  placeholder={t('config.serverUrlPlaceholder')}
                  className="w-full bg-white/10 border border-white/15 rounded-md px-3 py-1.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-blue-500/60"
                />
              </div>
              <div className="flex gap-3">
                <div className="flex flex-col gap-1 flex-1">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
                  <label className="text-xs text-white/60">{t('config.serverPort')}</label>
                  <input
                    type="number"
                    value={configServerPort}
                    onChange={(e) => setConfigServerPort(Number(e.target.value))}
                    className="w-full bg-white/10 border border-white/15 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500/60"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Team + member */}
          <div className="flex gap-3">
            <div className="flex flex-col gap-1 flex-1">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
              <label className="text-xs text-white/60">{t('config.teamId')}</label>
              <input
                value={configTeamId}
                onChange={(e) => setConfigTeamId(e.target.value)}
                placeholder={t('config.teamIdPlaceholder')}
                className="w-full bg-white/10 border border-white/15 rounded-md px-3 py-1.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-blue-500/60"
              />
            </div>
            <div className="flex flex-col gap-1 flex-1">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
              <label className="text-xs text-white/60">{t('config.memberId')}</label>
              <input
                value={configMemberId}
                onChange={(e) => setConfigMemberId(e.target.value)}
                placeholder={t('config.memberIdPlaceholder')}
                className="w-full bg-white/10 border border-white/15 rounded-md px-3 py-1.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-blue-500/60"
              />
            </div>
          </div>

          {/* Auto-sync */}
          <div className="flex items-center justify-between">
            <div className="flex flex-col gap-1 flex-1 mr-4">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
              <label className="text-xs text-white/60">{t('config.autoSyncInterval')}</label>
              <input
                type="number"
                value={configAutoSync}
                onChange={(e) => setConfigAutoSync(Number(e.target.value))}
                className="w-28 bg-white/10 border border-white/15 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500/60"
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={configAutoPush}
                onChange={(e) => setConfigAutoPush(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm text-white/70">{t('config.autoPush')}</span>
            </label>
          </div>

          <button type="button"
            onClick={handleSaveConfig}
            disabled={savingConfig}
            className="self-end px-4 py-1.5 rounded-md text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 transition-colors"
          >
            {savingConfig ? '…' : t('config.save')}
          </button>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <button type="button"
          onClick={handlePush}
          disabled={pushing || !status?.enabled}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm disabled:opacity-40 transition-colors"
        >
          {pushing ? (
            <span className="animate-spin">⟳</span>
          ) : '↑'}
          {t('actions.push')}
        </button>
        <button type="button"
          onClick={handlePull}
          disabled={pulling || !status?.enabled}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-medium text-sm disabled:opacity-40 transition-colors"
        >
          {pulling ? (
            <span className="animate-spin">⟳</span>
          ) : '↓'}
          {t('actions.pull')}
        </button>
        {configMode === 'http' && (
          <button type="button"
            onClick={handleToggleServer}
            className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${status?.server_running ? 'bg-red-600/80 hover:bg-red-500 text-white' : 'bg-white/10 hover:bg-white/15 text-white/70'}`}
          >
            {status?.server_running ? t('actions.stopServer') : t('actions.startServer')}
          </button>
        )}
      </div>

      {/* Peers list */}
      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-medium text-white/70">{t('peers.title')}</h3>
        {peers.length === 0 ? (
          <p className="text-sm text-white/40 italic">{t('peers.nopeers')}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {peers.map((peer) => (
              <div key={peer.member_id} className="rounded-lg border border-white/10 bg-white/5 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-600/30 flex items-center justify-center text-sm font-medium text-blue-300">
                      {peer.member_id[0]?.toUpperCase() ?? '?'}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">
                        {peer.member_id}
                        {peer.is_self && <span className="ml-1.5 text-xs text-white/40">{t('peers.you')}</span>}
                      </div>
                      <div className="text-xs text-white/40">
                        {peer.exported_at
                          ? t('peers.lastExport', { date: new Date(peer.exported_at).toLocaleString() })
                          : t('peers.neverExported')}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-white/50 bg-white/10 px-2 py-0.5 rounded-full">
                      {t('peers.episodes', { count: peer.episode_count })}
                    </span>
                    {!peer.is_self && (
                      <button type="button"
                        onClick={() => handleViewPeerEpisodes(peer.member_id)}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        {selectedPeer === peer.member_id ? '▲' : '▼'} {t('peers.viewEpisodes')}
                      </button>
                    )}
                  </div>
                </div>

                {/* Expanded episodes */}
                {selectedPeer === peer.member_id && (
                  <div className="border-t border-white/10 px-4 py-3 flex flex-col gap-2 bg-black/20 max-h-64 overflow-y-auto">
                    <h4 className="text-xs font-medium text-white/50">{t('episodes.title', { member: peer.member_id })}</h4>
                    {peerEpisodes.length === 0 ? (
                      <p className="text-xs text-white/30 italic">{t('episodes.empty')}</p>
                    ) : (
                      peerEpisodes.slice(0, 50).map((ep) => (
                        <div key={`${ep.type}-${ep.spec}-${ep.timestamp}`} className="flex flex-col gap-1 bg-white/5 rounded-md px-3 py-2">
                          <div className="flex items-center gap-2">
                            <EpisodeTypeBadge type={ep.type} />
                            <span className="text-xs text-white/30">{ep.spec}</span>
                            <span className="ml-auto text-xs text-white/20">{ep.timestamp ? new Date(ep.timestamp).toLocaleDateString() : ''}</span>
                          </div>
                          <p className="text-xs text-white/70 line-clamp-3 leading-relaxed">{ep.content}</p>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>!status?.enabled && (
        <div className="rounded-xl border border-white/10 bg-white/5 p-5">
          <h3 className="text-sm font-medium text-white mb-3">{t('help.title')}</h3>
          <ol className="flex flex-col gap-2">
            {(['step1', 'step2', 'step3', 'step4'] as const).map((step, i) => (
              <li key={step} className="flex gap-3 text-sm text-white/60">
                <span className="w-5 h-5 rounded-full bg-blue-600/30 text-blue-300 text-xs flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                {t(`help.${step}`)}
              </li>
            ))}
          </ol>
          <button type="button"
            onClick={() => setShowConfig(true)}
            className="mt-4 px-4 py-1.5 rounded-md text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors"
          >
            {t('config.title')} →
          </button>
        </div>
      )
    </div>
  );
}

export default TeamSyncPanel;



