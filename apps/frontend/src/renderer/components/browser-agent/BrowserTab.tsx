import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useBrowserAgentStore } from '@/stores/browser-agent-store';

interface BrowserTabProps {
  readonly projectPath: string;
}

export function BrowserTab({ projectPath }: BrowserTabProps) {
  const { t } = useTranslation(['browserAgent']);
  const {
    currentUrl,
    setCurrentUrl,
    browserStatus,
    browserScreenshot,
    isCapturing,
    captureScreenshot,
  } = useBrowserAgentStore();

  const [screenshotName, setScreenshotName] = useState('');
  const [urlInput, setUrlInput] = useState(currentUrl);

  const handleNavigate = () => {
    if (!urlInput.trim()) return;
    let url = urlInput.trim();
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = `http://${url}`;
    }
    setCurrentUrl(url);
    const name = screenshotName.trim() || 'preview';
    captureScreenshot(projectPath, name, url);
  };

  const handleCapture = () => {
    if (!currentUrl) return;
    const name = screenshotName.trim() || `screenshot_${Date.now()}`;
    captureScreenshot(projectPath, name, currentUrl);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleNavigate();
    }
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* URL bar */}
      <div className="flex gap-2">
        <input
          type="text"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('browserAgent:browser.urlPlaceholder')}
          className="flex-1 px-3 py-2 rounded-md bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent-primary)]"
        />
        <button
          type="button"
          onClick={handleNavigate}
          disabled={!urlInput.trim() || isCapturing}
          className="px-4 py-2 rounded-md bg-[var(--accent-primary)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {t('browserAgent:browser.navigate')}
        </button>
      </div>

      {/* Screenshot name + capture button */}
      <div className="flex gap-2">
        <input
          type="text"
          value={screenshotName}
          onChange={(e) => setScreenshotName(e.target.value)}
          placeholder={t('browserAgent:browser.screenshotNamePlaceholder')}
          className="flex-1 px-3 py-2 rounded-md bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] text-sm focus:outline-none focus:border-[var(--accent-primary)]"
        />
        <button
          type="button"
          onClick={handleCapture}
          disabled={!currentUrl || isCapturing}
          className="px-4 py-2 rounded-md border border-[var(--border-primary)] text-[var(--text-primary)] text-sm hover:bg-[var(--bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isCapturing ? t('browserAgent:browser.capturing') : t('browserAgent:browser.captureScreenshot')}
        </button>
      </div>

      {/* Browser preview area */}
      <div className="flex-1 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] overflow-hidden flex items-center justify-center min-h-[300px]">
        {browserStatus === 'idle' && !browserScreenshot && (
          <p className="text-sm text-[var(--text-tertiary)]">
            {t('browserAgent:browser.idle')}
          </p>
        )}

        {(browserStatus === 'launching' || browserStatus === 'navigating') && (
          <div className="flex flex-col items-center gap-2">
            <div className="w-6 h-6 border-2 border-[var(--accent-primary)] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-[var(--text-secondary)]">
              {browserStatus === 'launching'
                ? t('browserAgent:browser.launching')
                : t('browserAgent:browser.navigating')}
            </p>
          </div>
        )}

        {browserScreenshot && (
          <img
            src={browserScreenshot}
            alt="Browser screenshot"
            className="max-w-full max-h-full object-contain"
          />
        )}

        {browserStatus === 'error' && !browserScreenshot && (
          <p className="text-sm text-red-400">
            {t('browserAgent:errors.screenshotFailed')}
          </p>
        )}
      </div>
    </div>
  );
}
