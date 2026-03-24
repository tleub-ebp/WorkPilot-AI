import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Settings2,
  Key,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
  Zap,
  Globe,
  Shield,
  Bot,
  Cloud,
  Star,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { cn } from '@/lib/utils';
import { TooltipProvider } from '../ui/tooltip';

interface ThemedProviderCardProps {
  provider: {
    id: string;
    name: string;
    category: string;
    description?: string;
    isConfigured: boolean;
    isWorking?: boolean;
    lastTested?: string;
    usageCount?: number;
    isPremium?: boolean;
    icon?: React.ReactNode;
    authType?: 'oauth' | 'api_key' | 'cli' | 'none';
    apiKeyMasked?: string;
  };
  onConfigure: (providerId: string) => void;
  onTest: (providerId: string) => void;
  onToggle: (providerId: string, enabled: boolean) => void;
  onRemove?: (providerId: string) => void;
  className?: string;
}

// Icônes officielles des providers - respectent le thème avec currentColor
const providerIcons: Record<string, React.ReactNode> = {
  // Anthropic — logo officiel (lettre A stylisée)
  anthropic: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Anthropic">
      <title>Anthropic</title>
      <path d="M13.827 3.52h3.603L24 20h-3.603l-6.57-16.48zm-7.258 0h3.767L16.906 20h-3.674l-1.343-3.461H5.017L3.674 20H0L6.57 3.52zm4.132 9.959L8.453 7.687 6.205 13.479h4.496z" fill="currentColor"/>
    </svg>
  ),
  claude: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Claude">
      <title>Claude</title>
      <path d="M13.827 3.52h3.603L24 20h-3.603l-6.57-16.48zm-7.258 0h3.767L16.906 20h-3.674l-1.343-3.461H5.017L3.674 20H0L6.57 3.52zm4.132 9.959L8.453 7.687 6.205 13.479h4.496z" fill="currentColor"/>
    </svg>
  ),
  // OpenAI — logo officiel (fleur vectorielle)
  openai: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="OpenAI">
      <title>OpenAI</title>
      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0L3.86 14.026a4.505 4.505 0 0 1-1.52-6.13zm16.597 3.855l-5.843-3.369 2.02-1.168a.076.076 0 0 1 .071 0l4.957 2.812a4.496 4.496 0 0 1-.692 8.115v-5.678a.795.795 0 0 0-.513-.712zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.956-2.817a4.5 4.5 0 0 1 6.683 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08-4.778 2.758a.795.795 0 0 0-.397.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" fill="currentColor"/>
    </svg>
  ),
  // Google Gemini — logo officiel (étoile 4 branches dégradée)
  gemini: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Google Gemini">
      <title>Google Gemini</title>
      <defs>
        <linearGradient id="gemini-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4285F4"/>
          <stop offset="50%" stopColor="#9B72CB"/>
          <stop offset="100%" stopColor="#D96570"/>
        </linearGradient>
      </defs>
      <path d="M12 2C12 2 13.5 8.5 18 12C13.5 15.5 12 22 12 22C12 22 10.5 15.5 6 12C10.5 8.5 12 2 12 2Z" fill="url(#gemini-grad)"/>
    </svg>
  ),
  // Mistral AI — logo officiel (blocs géométriques empilés)
  mistral: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Mistral AI">
      <title>Mistral AI</title>
      <rect x="2" y="2" width="6" height="6" fill="#F7521E"/>
      <rect x="10" y="2" width="6" height="6" fill="#F7521E"/>
      <rect x="18" y="2" width="4" height="6" fill="#F7521E"/>
      <rect x="2" y="10" width="6" height="4" fill="#F7521E"/>
      <rect x="10" y="10" width="6" height="4" fill="#F7521E"/>
      <rect x="2" y="16" width="6" height="6" fill="#F7521E"/>
      <rect x="10" y="16" width="6" height="6" fill="#F7521E"/>
      <rect x="18" y="16" width="4" height="6" fill="#F7521E"/>
    </svg>
  ),
  // DeepSeek — logo officiel (œil stylisé bleu)
  deepseek: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="DeepSeek">
      <title>DeepSeek</title>
      <path d="M22.433 9.257c-.173-.08-.537.03-.686.08-.122.03-.275.08-.428.152a9.16 9.16 0 0 0-.62-.833c-.02-.021-.04-.05-.061-.07a9.993 9.993 0 0 0-2.16-1.87A9.675 9.675 0 0 0 12.047 5c-2.627 0-5.05.985-6.847 2.607A9.7 9.7 0 0 0 2.07 14.9a9.695 9.695 0 0 0 9.692 8.594c4.68 0 8.617-3.335 9.49-7.772.061-.304-.02-.487-.183-.567-.163-.08-.396.01-.52.304a8.476 8.476 0 0 1-8.237 5.53A8.467 8.467 0 0 1 3.82 13.5a8.463 8.463 0 0 1 8.463-8.463c2.16 0 4.14.812 5.63 2.14.366.325.701.68 1.006 1.058-.437.212-.843.507-1.168.893-.61.73-.864 1.703-.7 2.637.122.71.477 1.329.995 1.773.518.446 1.168.69 1.849.69.254 0 .508-.03.752-.09.752-.192 1.34-.71 1.614-1.401.213-.548.213-1.137.01-1.642-.193-.497-.57-.894-1.078-1.126l-.002-.002zM9.697 14.596c-.294.517-.874.833-1.493.833-.325 0-.64-.082-.924-.244-.822-.467-1.107-1.512-.64-2.333l.02-.04c.02-.04.04-.08.07-.112 0-.01.01-.021.02-.03.02-.04.051-.07.071-.111.02-.03.04-.07.061-.1.01-.02.03-.041.04-.061.03-.04.07-.08.102-.121.112-.132.244-.244.386-.336a1.74 1.74 0 0 1 .894-.244c.619 0 1.199.315 1.493.833.33.578.32 1.26-.1 1.867zm5.295-1.3c-.203.347-.56.558-.955.558a1.095 1.095 0 0 1-.549-.142c-.519-.294-.702-.965-.406-1.483.203-.345.558-.558.955-.558.193 0 .376.05.548.143.518.295.701.965.406 1.482z" fill="#4D6BFE"/>
    </svg>
  ),
  // Meta — logo officiel (ruban infini stylisé bleu/violet)
  meta: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Meta">
      <title>Meta</title>
      <defs>
        <linearGradient id="meta-grad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#0082FB"/>
          <stop offset="100%" stopColor="#A33BC2"/>
        </linearGradient>
      </defs>
      <path d="M2.002 12.87c0 1.356.3 2.394.694 3.053.511.853 1.27 1.302 2.145 1.302 1.03 0 1.972-.254 3.794-2.73l1.698-2.326.005-.007 1.466-2.007c1.01-1.38 2.178-2.943 3.72-2.943 1.334 0 2.59.776 3.566 2.24.865 1.3 1.302 2.948 1.302 4.64 0 1.01-.2 1.77-.538 2.337-.328.548-.956 1.095-2.013 1.095v-2.17c.906 0 1.13-.832 1.13-1.308 0-1.283-.298-2.72-.959-3.718-.488-.74-1.121-1.17-1.787-1.17-.727 0-1.343.485-2.098 1.534l-1.505 2.059-.008.011-.44.602.019.025 1.364 1.875c.99 1.359 1.563 2.044 2.176 2.044.338 0 .685-.12.957-.367l.018-.016.946 1.784-.017.015c-.65.579-1.452.817-2.212.817-.936 0-1.747-.364-2.435-1.09a14.82 14.82 0 0 1-.605-.74l-.86-1.18-.009-.013-1.155 1.575C8.697 16.76 7.608 17.21 6.5 17.21c-1.32 0-2.396-.52-3.143-1.51-.693-.93-1.04-2.198-1.04-3.66l2.685-.17z" fill="url(#meta-grad)"/>
      <path d="M6.617 7.213c1.21 0 2.557.757 4.047 2.747.225.297.454.613.685.94l-.762 1.044-1.052-1.44C8.27 8.77 7.447 8.118 6.702 8.118c-.596 0-1.19.387-1.668 1.09-.572.845-.903 2.073-.903 3.474h-2.13c0-1.72.42-3.354 1.245-4.572.79-1.168 1.905-1.897 3.371-1.897z" fill="url(#meta-grad)"/>
    </svg>
  ),
  // Autres providers avec fallback
  ollama: <Bot className="w-5 h-5" />,
  windsurf: <Zap className="w-5 h-5" />,
  cursor: <Globe className="w-5 h-5" />,
  grok: <Cloud className="w-5 h-5" />,
  'azure-openai': <Shield className="w-5 h-5" />,
};

export function ThemedProviderCard({
  provider,
  onConfigure,
  onTest,
  onToggle,
  onRemove,
  className
}: ThemedProviderCardProps) {
  const { t } = useTranslation('settings');
  const [isExpanded, setIsExpanded] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

  const ProviderIcon = providerIcons[provider.id] || <Bot className="w-5 h-5" />;

  const getStatusIndicator = () => {
    if (!provider.isConfigured) {
      return (
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-gray-400 rounded-full" />
          <span className="text-sm text-gray-500">Non configuré</span>
        </div>
      );
    }

    if (provider.isWorking === false) {
      return (
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-red-500 rounded-full" />
          <span className="text-sm text-red-600">Erreur</span>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 bg-green-500 rounded-full" />
        <span className="text-sm text-green-600">Actif</span>
      </div>
    );
  };

  return (
    <TooltipProvider>
      <div
        className={cn(
          'border rounded-lg p-4 space-y-4 transition-colors',
          !provider.isConfigured && 'border-gray-200 bg-gray-50',
          provider.isWorking === false && 'border-red-200 bg-red-50',
          provider.isConfigured && provider.isWorking !== false && 'border-gray-200 bg-white',
          className
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {/* Icon */}
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100">
              {ProviderIcon}
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-sm">{provider.name}</h3>
                {provider.isPremium && (
                  <Star className="w-3 h-3 text-yellow-500 fill-current" />
                )}
              </div>
              {provider.description && (
                <p className="text-xs text-gray-600">{provider.description}</p>
              )}
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            {getStatusIndicator()}
            
            {/* Toggle switch */}
            {provider.isConfigured && (
              <Switch
                checked={provider.isWorking !== false}
                onCheckedChange={(checked) => onToggle(provider.id, checked)}
              />
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <div className="flex gap-2">
            {!provider.isConfigured ? (
              <Button
                onClick={() => onConfigure(provider.id)}
                size="sm"
                className="h-8 px-3 text-xs"
              >
                <Key className="w-3 h-3 mr-1" />
                Configurer
              </Button>
            ) : (
              <>
                <Button
                  onClick={() => onTest(provider.id)}
                  variant="outline"
                  size="sm"
                  className="h-8 px-3 text-xs"
                >
                  <Zap className="w-3 h-3 mr-1" />
                  Tester
                </Button>
                <Button
                  onClick={() => onConfigure(provider.id)}
                  variant="outline"
                  size="sm"
                  className="h-8 px-3 text-xs"
                >
                  <Settings2 className="w-3 h-3 mr-1" />
                  Modifier
                </Button>
              </>
            )}
          </div>

          {/* Expand button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-8 w-8 p-0"
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </div>

        {/* Expanded details */}
        {isExpanded && provider.isConfigured && (
          <div className="pt-2 border-t border-gray-100 space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs text-gray-600">
                {provider.authType === 'oauth' || provider.authType === 'cli'
                  ? 'Authentification'
                  : 'Clé API'}
              </Label>
              <div className="flex items-center gap-2">
                {provider.authType === 'oauth' ? (
                  <div className="px-2 py-1 bg-blue-50 border border-blue-200 rounded text-xs font-medium text-blue-700">
                    OAuth
                  </div>
                ) : provider.authType === 'cli' ? (
                  <div className="px-2 py-1 bg-purple-50 border border-purple-200 rounded text-xs font-medium text-purple-700">
                    GitHub CLI
                  </div>
                ) : provider.apiKeyMasked ? (
                  <>
                    <div className="px-2 py-1 bg-gray-100 rounded text-xs font-mono">
                      {showApiKey ? provider.apiKeyMasked : provider.apiKeyMasked.replace(/[^.•](?=[^.•]{4})/g, '•')}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="h-6 w-6 p-0"
                    >
                      {showApiKey ? (
                        <EyeOff className="w-3 h-3" />
                      ) : (
                        <Eye className="w-3 h-3" />
                      )}
                    </Button>
                  </>
                ) : (
                  <div className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-500">
                    Non renseignée
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Dernier test</span>
              <span>{provider.lastTested ? new Date(provider.lastTested).toLocaleDateString() : 'Jamais testé'}</span>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Utilisations ce mois</span>
              <span className="font-medium text-gray-700">
                {provider.usageCount != null ? provider.usageCount : 'Non disponible'}
              </span>
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}
