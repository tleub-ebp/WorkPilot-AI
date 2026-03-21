import { useTranslation } from 'react-i18next';
import { Image as ImageIcon, Cpu } from 'lucide-react';
import { useVisualToCodeStore } from '../../stores/visual-to-code-store';
import { DesignImportPanel } from './DesignImportPanel';
import { CanvasPanel } from './CanvasPanel';

/**
 * VisualToCodeHub — unified hub combining:
 * - Design Import tab: upload designs (screenshots, Figma, wireframes) → AI generates code
 * - Canvas tab: interactive ReactFlow diagram builder → AI generates code, or Code → Visual
 *
 * Both panels are kept mounted (CSS show/hide) to preserve ReactFlow canvas state
 * when switching between tabs.
 */
export function VisualToCodeHub() {
  const { t } = useTranslation('visualToCode');
  const { activeMode, setActiveMode } = useVisualToCodeStore();

  return (
    <div className="h-full flex flex-col">
      {/* Tab bar */}
      <div className="flex gap-1 px-4 pt-3 pb-0 border-b shrink-0">
        <button
          type="button"
          onClick={() => setActiveMode('design-import')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors ${
            activeMode === 'design-import'
              ? 'border-violet-500 text-violet-700 dark:text-violet-300'
              : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
          }`}
        >
          <ImageIcon className="h-4 w-4" />
          {t('tabs.designImport')}
        </button>
        <button
          type="button"
          onClick={() => setActiveMode('canvas')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors ${
            activeMode === 'canvas'
              ? 'border-violet-500 text-violet-700 dark:text-violet-300'
              : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
          }`}
        >
          <Cpu className="h-4 w-4" />
          {t('tabs.canvas')}
        </button>
      </div>

      {/* Panels — both mounted, one hidden via CSS to preserve ReactFlow state */}
      <div
        className="flex-1 overflow-hidden flex flex-col min-h-0"
        style={{ display: activeMode === 'design-import' ? 'flex' : 'none' }}
      >
        <DesignImportPanel />
      </div>
      <div
        className="flex-1 overflow-hidden flex flex-col min-h-0"
        style={{ display: activeMode === 'canvas' ? 'flex' : 'none' }}
      >
        <CanvasPanel />
      </div>
    </div>
  );
}
