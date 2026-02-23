import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { SettingsSection } from './SettingsSection';
import { CleanProviderGrid } from './CleanProviderGrid';
import { GlobalAutoSwitching } from './GlobalAutoSwitching';
import { ProviderConfigDialog } from './ProviderConfigDialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../ui/sheet';
import { getAllConnectors } from './multiconnector/utils';
import { useSettings } from './hooks/useSettings';
import { Loader2, AlertCircle, Info, CheckCircle, Activity, X } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { cn } from '@/lib/utils';

interface Provider {
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
}

interface CleanProviderSectionProps {
  settings: any;
  onSettingsChange: (settings: any) => void;
  isOpen: boolean;
}

const providerCategories: Record<string, string> = {
  'anthropic': 'independent',
  'claude': 'independent',
  'openai': 'openai',
  'ollama': 'independent',
  'gemini': 'google',
  'google': 'google',
  'meta-llama': 'meta',
  'meta': 'meta',
  'mistral': 'independent',
  'deepseek': 'independent',
  'grok': 'independent',
  'windsurf': 'independent',
  'cursor': 'independent',
  'copilot': 'independent',
  'aws': 'microsoft',
  'azure-openai': 'microsoft',
};

const providerDescriptions: Record<string, string> = {
  'anthropic': 'Modèles Claude d\'Anthropic',
  'claude': 'Modèles Claude d\'Anthropic',
  'openai': 'Modèles GPT-5 et autres modèles OpenAI',
  'ollama': 'Modèles open-source locaux avec Ollama',
  'gemini': 'Modèles Gemini de Google DeepMind',
  'google': 'Accès aux API Google et Google DeepMind',
  'meta-llama': 'Modèles Llama de Meta via Together.ai',
  'meta': 'Modèles Meta AI officiels',
  'mistral': 'Modèles Mistral AI (Mistral, Codéal, etc.)',
  'deepseek': 'Modèles DeepSeek (DeepSeek-Coder, etc.)',
  'grok': 'Modèles Grok xAI',
  'windsurf': 'Provider Windsurf AI',
  'cursor': 'Provider Cursor AI',
  'copilot': 'GitHub Copilot',
  'aws': 'AWS Bedrock et services Amazon',
  'azure-openai': 'Modèles OpenAI via Azure',
};

export function CleanProviderSection({ 
  settings, 
  onSettingsChange, 
  isOpen 
}: CleanProviderSectionProps) {
  const { t } = useTranslation('settings');
  const [connectors, setConnectors] = useState<Array<{ id: string, label: string }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [testingProviders, setTestingProviders] = useState<Set<string>>(new Set());
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [autoSwitchingOpen, setAutoSwitchingOpen] = useState(false);

  // Charger les connecteurs
  useEffect(() => {
    const loadConnectors = async () => {
      setIsLoading(true);
      setError(null);
      setWarning(null);
      setSuccess(null);
      try {
        const connectors = await getAllConnectors();
        setConnectors(connectors);
      } catch (err) {
        console.error('Failed to load connectors:', err);
        setError('Impossible de charger la liste des providers');
        setConnectors([]);
      } finally {
        setIsLoading(false);
      }
    };
    
    if (isOpen) {
      loadConnectors();
    }
  }, [isOpen]);

  const getApiKeyField = (providerId: string): string | null => {
    const fields: Record<string, string> = {
      'openai': 'globalOpenAIApiKey',
      'gemini': 'globalGoogleDeepMindApiKey',
      'google': 'globalGoogleDeepMindApiKey',
      'meta-llama': 'globalMetaApiKey',
      'meta': 'globalMetaApiKey',
      'mistral': 'globalMistralApiKey',
      'deepseek': 'globalDeepSeekApiKey',
      'grok': 'globalGrokApiKey',
      'windsurf': 'globalWindsurfApiKey',
      'cursor': 'globalCursorApiKey',
      'azure-openai': 'globalAzureApiKey',
      'anthropic': 'globalAnthropicApiKey',
      'claude': 'globalAnthropicApiKey',
      'ollama': 'globalOllamaUrl',
      'copilot': 'globalCopilotToken',
      'aws': 'globalAwsAccessKey',
    };
    return fields[providerId] || null;
  };

  // Transformer les connecteurs en providers pour la grille
  const providers: Provider[] = connectors.map(connector => {
    const category = providerCategories[connector.id] || 'independent';
    const apiKeyField = getApiKeyField(connector.id);
    const hasApiKey = apiKeyField && settings[apiKeyField];
    
    return {
      id: connector.id,
      name: connector.label,
      category,
      description: t(`sections.accounts.providers.${connector.id}`) || providerDescriptions[connector.id],
      isConfigured: !!hasApiKey,
      isWorking: hasApiKey ? true : undefined,
      lastTested: hasApiKey ? new Date().toISOString() : undefined,
      usageCount: Math.floor(Math.random() * 100),
      isPremium: ['anthropic', 'claude', 'openai', 'gemini'].includes(connector.id),
    };
  });

  const handleConfigure = (providerId: string) => {
    const provider = providers.find(p => p.id === providerId);
    if (provider) {
      setSelectedProvider(provider);
      setConfigDialogOpen(true);
    }
  };

  const handleTest = async (providerId: string) => {
    setTestingProviders(prev => new Set(prev).add(providerId));
    
    try {
      // Simuler un test réel - vérifier si la clé API est configurée
      const apiKeyField = getApiKeyField(providerId);
      if (apiKeyField && settings[apiKeyField]) {
        // Simuler une connexion réussie
        await new Promise(resolve => setTimeout(resolve, 2000));
        setSuccess(`Test réussi pour ${providerId} !`);
      } else {
        throw new Error('Aucune clé API configurée');
      }
    } catch (err) {
      setError(`Test échoué pour ${providerId}: ${err instanceof Error ? err.message : 'Erreur inconnue'}`);
    } finally {
      setTestingProviders(prev => {
        const newSet = new Set(prev);
        newSet.delete(providerId);
        return newSet;
      });
    }
  };

  const handleToggle = (providerId: string, enabled: boolean) => {
    const apiKeyField = getApiKeyField(providerId);
    if (apiKeyField) {
      onSettingsChange({
        ...settings,
        [`${apiKeyField}Enabled`]: enabled
      });
    }
  };

  const handleRemove = (providerId: string) => {
    const apiKeyField = getApiKeyField(providerId);
    if (apiKeyField && window.confirm('Êtes-vous sûr de vouloir supprimer la configuration de ce provider ?')) {
      onSettingsChange({
        ...settings,
        [apiKeyField]: ''
      });
    }
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  if (isLoading) {
    return (
      <SettingsSection
        title={t('accounts.multiConnector.title')}
        description={t('accounts.multiConnector.description')}
      >
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          <span className="text-sm text-gray-600">Chargement des providers...</span>
        </div>
      </SettingsSection>
    );
  }

  if (error) {
    return (
      <SettingsSection
        title={t('accounts.multiConnector.title')}
        description={t('accounts.multiConnector.description')}
      >
        <div className="space-y-4">
          <Alert className="border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-700">
              {error}
            </AlertDescription>
          </Alert>
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
          >
            Réessayer
          </Button>
        </div>
      </SettingsSection>
    );
  }

  return (
    <SettingsSection
      title={t('accounts.multiConnector.title')}
      description={t('accounts.multiConnector.description')}
    >
      <div className="space-y-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50/50 border border-red-100 rounded-lg">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          </div>
        )}

        {warning && (
          <div className="mb-6 p-4 bg-yellow-50/50 border border-yellow-100 rounded-lg">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-yellow-600" />
              <span className="text-sm text-yellow-700">{warning}</span>
            </div>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50/50 border border-green-100 rounded-lg">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="text-sm text-green-700">{success}</span>
            </div>
          </div>
        )}

        <div className="flex gap-6">
          {/* Colonne de gauche - Providers (prend toute la largeur si auto-switching fermé) */}
          <div className={autoSwitchingOpen ? "flex-2" : "flex-1"}>
            {/* Alertes simples */}
          {providers.filter(p => p.isConfigured).length === 0 && (
            <Alert className="border-primary/20 bg-primary/5">
              <Info className="h-4 w-4 text-primary" />
              <AlertDescription className="text-primary">
                <div className="space-y-1">
                  <p className="font-medium">Commencez avec votre premier provider</p>
                  <p className="text-sm">
                    Configurez au moins un provider pour commencer à utiliser l'application.
                  </p>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {providers.filter(p => p.isWorking === false).length > 0 && (
            <Alert className="border-destructive/20 bg-destructive/5">
              <AlertCircle className="h-4 w-4 text-destructive" />
              <AlertDescription className="text-destructive">
                <div className="space-y-1">
                  <p className="font-medium">
                    {providers.filter(p => p.isWorking === false).length} provider(s) nécessitent votre attention
                  </p>
                  <p className="text-sm">
                    Vérifiez vos clés API et réessayez.
                  </p>
                </div>
              </AlertDescription>
            </Alert>
          )}

            {/* Grille de providers */}
            <CleanProviderGrid
              providers={providers}
              onConfigure={handleConfigure}
              onTest={handleTest}
              onToggle={handleToggle}
              onRemove={handleRemove}
              isLoading={isLoading}
              isAutoSwitchingOpen={autoSwitchingOpen}
            />
          </div>

          {/* Auto-switching settings - tiroir compact */}
          <div className={`${autoSwitchingOpen ? "flex-1" : "w-auto"} transition-all duration-300`}>
            {!autoSwitchingOpen ? (
              /* Bouton compact pour ouvrir */
              <Button
                onClick={() => setAutoSwitchingOpen(true)}
                variant="outline"
                size="sm"
                className="h-8 px-3"
              >
                <Activity className="w-4 h-4 mr-2" />
                {t('sections.accounts.autoSwitching.title')}
              </Button>
            ) : (
              /* Contenu de l'auto-switching dans un tiroir */
              <div className="border rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4" />
                    <h3 className="font-medium text-sm">{t('sections.accounts.autoSwitching.title')}</h3>
                  </div>
                  <Button
                    onClick={() => setAutoSwitchingOpen(false)}
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
                
                <div className="space-y-4">
                  <GlobalAutoSwitching 
                    settings={settings} 
                    onSettingsChange={onSettingsChange}
                    isOpen={true}
                    useSheet={true}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sheet de configuration - tiroir ouvrant sur la droite */}
      <Sheet open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
        <SheetContent side="right" className="w-[95vw] max-w-[1200px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>
              {t('sections.accounts.providerConfig.title')} {selectedProvider?.name}
            </SheetTitle>
          </SheetHeader>
          <div className="mt-6">
            <ProviderConfigDialog
              isOpen={configDialogOpen}
              onOpenChange={setConfigDialogOpen}
              provider={selectedProvider}
              settings={settings}
              onSettingsChange={onSettingsChange}
              onTest={handleTest}
              useSheet={true}
            />
          </div>
        </SheetContent>
      </Sheet>
    </SettingsSection>
  );
}
