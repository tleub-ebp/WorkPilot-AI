import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { SettingsSection } from './SettingsSection';
import { CleanProviderGrid } from './CleanProviderGrid';
import { getAllConnectors } from './multiconnector/utils';
import { Loader2, AlertCircle, Info, X, Activity, CheckCircle, XCircle } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../ui/sheet';
import { GlobalAutoSwitching } from './GlobalAutoSwitching';
import { ProviderConfigDialog } from './ProviderConfigDialog';
import { getStaticProviders } from '@shared/utils/providers';
import { useSettingsStore } from '@/stores/settings-store';
import { useToast } from '@/hooks/use-toast';
import { ProviderService } from '@shared/services/providerService';
import type { APIProfile } from '@shared/types/profile';

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
  const { toast } = useToast();
  const [connectors, setConnectors] = useState<Array<{ id: string, label: string }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testingProviders, setTestingProviders] = useState<Set<string>>(new Set());
  const [autoSwitchingOpen, setAutoSwitchingOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);

  // Utiliser les profiles comme le ProviderSelector
  const { profiles, setActiveProfile } = useSettingsStore();

  // Charger les connecteurs
  useEffect(() => {
    const loadConnectors = async () => {
      setIsLoading(true);
      setError(null);
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

  // Utiliser la même logique que ProviderSelector pour déterminer le statut
  const { providers: staticProviders, status } = useMemo(
    () => getStaticProviders(profiles),
    [profiles]
  );

  // Transformer les providers statiques en providers pour la grille
  const providers: Provider[] = staticProviders.map(provider => {
    const mappedProvider = {
      id: provider.name,
      name: provider.label,
      category: providerCategories[provider.name] || 'independent',
      description: t(`sections.accounts.providers.${provider.name}`) || provider.description,
      isConfigured: status[provider.name] || false,
      isWorking: status[provider.name] ? true : undefined,
      lastTested: status[provider.name] ? new Date().toISOString() : undefined,
      usageCount: Math.floor(Math.random() * 100),
      isPremium: ['anthropic', 'claude', 'openai', 'gemini'].includes(provider.name),
    };
    
    return mappedProvider;
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
      // Vérifier si des profiles de test sont nécessaires et les ajouter
      const updatedProfiles = await ensureTestProfiles();
      
      // Passer les profiles mis à jour au ProviderService
      ProviderService.setProfiles(updatedProfiles);
      
      // Utiliser le vrai service de test du provider
      const result = await ProviderService.testProvider(providerId);
      
      if (result.success) {
        // Mettre à jour le statut du provider pour indiquer qu'il fonctionne
        // TODO: Mettre à jour le statut dans le store ou l'état local
        
        // Afficher un toast de succès avec détails
        let description = t('sections.accounts.providerCard.testSuccessDescription', { 
          providerName: providerId 
        });
        
        if (result.details) {
          if (result.details.modelCount) {
            description += ` (${t('sections.accounts.providerCard.testDetails.modelsAvailable', { count: result.details.modelCount })})`;
          } else if (result.details.model) {
            description += ` (${t('sections.accounts.providerCard.testDetails.modelUsed', { model: result.details.model })})`;
          }
        }
        
        toast({
          title: t('sections.accounts.providerCard.testSuccess'),
          description,
        });
        
        // Test provider success
      } else {
        // Afficher un toast d'erreur avec le message réel de l'API
        toast({
          variant: 'destructive',
          title: t('sections.accounts.providerCard.testError'),
          description: t('sections.accounts.providerCard.testErrorDescription', { 
            providerName: providerId,
            error: result.message
          }),
        });
        
        console.error('Test failed:', providerId, result.message);
      }
      
    } catch (err) {
      console.error('Test error:', err);
      
      // Afficher un toast d'erreur générique
      toast({
        variant: 'destructive',
        title: t('sections.accounts.providerCard.testError'),
        description: t('sections.accounts.providerCard.testErrorDescription', { 
          providerName: providerId,
          error: t('sections.accounts.providerCard.errors.unknownError')
        }),
      });
    } finally {
      setTestingProviders(prev => {
        const newSet = new Set(prev);
        newSet.delete(providerId);
        return newSet;
      });
    }
  };

  // Fonction pour s'assurer que les profiles de test existent
  const ensureTestProfiles = async () => {
    const { profiles, saveProfile } = useSettingsStore.getState();
    
    // Profiles de test à ajouter
    const testProfiles = [
      {
        name: 'Anthropic Test',
        baseUrl: 'https://api.anthropic.com',
        apiKey: 'sk-ant-test-key-placeholder', // À remplacer par une vraie clé
      },
      {
        name: 'Google Gemini Test',
        baseUrl: 'https://generativelanguage.googleapis.com',
        apiKey: 'test-google-key-placeholder', // À remplacer par une vraie clé
      },
      {
        name: 'Mistral Test',
        baseUrl: 'https://api.mistral.ai',
        apiKey: 'test-mistral-key-placeholder', // À remplacer par une vraie clé
      }
    ];

    let addedProfiles = [];
    
    for (const testProfile of testProfiles) {
      const exists = profiles.some(p => 
        p.baseUrl === testProfile.baseUrl || 
        p.name === testProfile.name
      );
      
      if (!exists) {
        // Adding test profile
        await saveProfile(testProfile);
        addedProfiles.push(testProfile.name);
      }
    }
    
    // Si des profiles ont été ajoutés, informer l'utilisateur
    if (addedProfiles.length > 0) {
      toast({
        title: 'Profiles de test ajoutés',
        description: `${addedProfiles.join(', ')} ont été créés. Configurez vos clés API pour tester.`,
        duration: 5000,
      });
    }
    
    // Rafraîchir les profiles après ajout
    const { profiles: updatedProfiles } = useSettingsStore.getState();
    return updatedProfiles;
  };

  const handleToggle = (providerId: string, enabled: boolean) => {
    // Pour l'instant, on ne fait rien car on utilise les profiles
    // Toggle provider
  };

  const handleRemove = (providerId: string) => {
    // Pour l'instant, on ne fait rien car on utilise les profiles
    // Remove provider
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

        <div className="flex gap-6">
          {/* Colonne de gauche - Providers (prend toute la largeur si auto-switching fermé) */}
          <div className={autoSwitchingOpen ? "flex-2" : "flex-1"}>
            {/* Alertes simples */}
          {providers.filter(p => p.isConfigured).length === 0 && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                {t('sections.accounts.alerts.noProviders')}
              </AlertDescription>
            </Alert>
          )}

          {providers.filter(p => p.isWorking === false).length > 0 && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {t('sections.accounts.alerts.providerErrors', { 
                  count: providers.filter(p => p.isWorking === false).length 
                })}
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
              testingProviders={testingProviders}
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
