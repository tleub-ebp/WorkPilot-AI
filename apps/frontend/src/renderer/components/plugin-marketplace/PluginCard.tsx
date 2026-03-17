import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Shield,
  Eye,
  Zap,
  Globe,
  MessageSquare,
  FileText,
  BarChart3,
  Code,
  Layers,
  GitBranch,
  Palette,
  Moon,
  Sun,
  Search,
  TestTube,
  CheckCircle2,
  Star,
  Download,
  Loader2,
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn } from '@/lib/utils';
import type { MarketplacePlugin } from '@shared/types/plugin-marketplace';

const PLUGIN_ICONS: Record<string, React.ElementType> = {
  Shield,
  Eye,
  Zap,
  Globe,
  MessageSquare,
  FileText,
  BarChart3,
  Code,
  Layers,
  GitBranch,
  Palette,
  Moon,
  Sun,
  Search,
  TestTube,
};

const TYPE_BADGE_CLASSES: Record<string, string> = {
  agent: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  integration: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  'spec-template': 'bg-green-500/10 text-green-500 border-green-500/20',
  theme: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
  'custom-prompt': 'bg-pink-500/10 text-pink-500 border-pink-500/20',
};

interface PluginCardProps {
  plugin: MarketplacePlugin;
  isInstalled: boolean;
  isInstalling: boolean;
  onInstall: () => void;
  onUninstall: () => void;
}

export function PluginCard({
  plugin,
  isInstalled,
  isInstalling,
  onInstall,
  onUninstall,
}: PluginCardProps) {
  const { t } = useTranslation(['common']);
  const [showFullDesc, setShowFullDesc] = useState(false);
  const IconComponent = PLUGIN_ICONS[plugin.icon] ?? Code;

  const typeLabel: Record<string, string> = {
    agent: t('common:pluginMarketplace.types.agent'),
    integration: t('common:pluginMarketplace.types.integration'),
    'spec-template': t('common:pluginMarketplace.types.specTemplate'),
    theme: t('common:pluginMarketplace.types.theme'),
    'custom-prompt': t('common:pluginMarketplace.types.customPrompt'),
  };

  return (
    <div
      className={cn(
        'group flex flex-col rounded-xl border border-border bg-card p-5 transition-all duration-200',
        'hover:border-primary/30 hover:shadow-md hover:shadow-primary/5'
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg"
          style={{
            backgroundColor: `${plugin.color}20`,
            border: `1px solid ${plugin.color}40`,
          }}
        >
          <IconComponent className="h-5 w-5" style={{ color: plugin.color }} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate font-semibold text-sm">{plugin.name}</h3>
            {plugin.verified && (
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-blue-500" />
            )}
          </div>
          <p className="text-xs text-muted-foreground truncate">{plugin.tagline}</p>
        </div>
      </div>

      {/* Type badge + author */}
      <div className="mt-3 flex items-center gap-2">
        <span
          className={cn(
            'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium',
            TYPE_BADGE_CLASSES[plugin.type]
          )}
        >
          {typeLabel[plugin.type]}
        </span>
        <span className="text-xs text-muted-foreground truncate">by {plugin.author}</span>
      </div>

      {/* Description */}
      <p
        className={cn(
          'mt-3 text-xs text-muted-foreground leading-relaxed',
          !showFullDesc && 'line-clamp-2'
        )}
      >
        {plugin.description}
      </p>
      {plugin.description.length > 120 && (
        <button
          type="button"
          onClick={() => setShowFullDesc(!showFullDesc)}
          className="mt-1 text-[10px] text-primary hover:underline text-left"
        >
          {showFullDesc ? t('common:actions.showLess') : t('common:actions.showMore')}
        </button>
      )}

      {/* Stats */}
      <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
          {plugin.rating.toFixed(1)}
          <span className="text-muted-foreground/60">({plugin.ratingCount})</span>
        </span>
        <span className="flex items-center gap-1">
          <Download className="h-3 w-3" />
          {plugin.downloads.toLocaleString()}
        </span>
        <span className="ml-auto text-muted-foreground/60">v{plugin.version}</span>
      </div>

      {/* Tags */}
      <div className="mt-3 flex flex-wrap gap-1">
        {plugin.tags.slice(0, 3).map((tag) => (
          <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
            {tag}
          </Badge>
        ))}
        {plugin.tags.length > 3 && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
            +{plugin.tags.length - 3}
          </Badge>
        )}
      </div>

      {/* Action */}
      <div className="mt-4">
        {isInstalled ? (
          <Button
            variant="outline"
            size="sm"
            className="w-full text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
            onClick={onUninstall}
          >
            {t('common:pluginMarketplace.actions.uninstall')}
          </Button>
        ) : (
          <Button
            size="sm"
            className="w-full"
            onClick={onInstall}
            disabled={isInstalling}
          >
            {isInstalling ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                {t('common:pluginMarketplace.actions.installing')}
              </>
            ) : (
              t('common:pluginMarketplace.actions.install')
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
