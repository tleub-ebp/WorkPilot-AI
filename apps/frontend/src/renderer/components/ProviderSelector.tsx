import React, { useEffect, useMemo, useState } from "react";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from './ui/select';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { useTranslation } from 'react-i18next';
import type { CanonicalProvider } from '@shared/utils/providers';
import { getStaticProviders } from '@shared/utils/providers';
import { useProviderContext } from './ProviderContext';
import { useSettingsStore } from '@/stores/settings-store';
import { detectProvider } from '@shared/utils/provider-detection';
import { useToast } from '@/hooks/use-toast';
import { AlertCircle, ExternalLink } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';

const providerIcons: Record<string, React.ReactNode> = {
  // Anthropic — logo officiel (lettre A stylisée)
  anthropic: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Anthropic">
      <title>Anthropic</title>
      <path d="M13.827 3.52h3.603L24 20h-3.603l-6.57-16.48zm-7.258 0h3.767L16.906 20h-3.674l-1.343-3.461H5.017L3.674 20H0L6.57 3.52zm4.132 9.959L8.453 7.687 6.205 13.479h4.496z" fill="#CC785C"/>
    </svg>
  ),
  claude: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Claude">
      <title>Claude</title>
      <path d="M13.827 3.52h3.603L24 20h-3.603l-6.57-16.48zm-7.258 0h3.767L16.906 20h-3.674l-1.343-3.461H5.017L3.674 20H0L6.57 3.52zm4.132 9.959L8.453 7.687 6.205 13.479h4.496z" fill="#CC785C"/>
    </svg>
  ),
  // OpenAI — logo officiel (fleur vectorielle) — currentColor pour s'adapter au thème clair/sombre
  openai: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="OpenAI">
      <title>OpenAI</title>
      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0L3.86 14.026a4.505 4.505 0 0 1-1.52-6.13zm16.597 3.855l-5.843-3.369 2.02-1.168a.076.076 0 0 1 .071 0l4.957 2.812a4.496 4.496 0 0 1-.692 8.115v-5.678a.795.795 0 0 0-.513-.712zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.956-2.817a4.5 4.5 0 0 1 6.683 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08-4.778 2.758a.795.795 0 0 0-.397.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" fill="currentColor"/>
    </svg>
  ),
  // Ollama — logo officiel (llama vectorisé simplifié) — currentColor pour s'adapter au thème, sans fond blanc
  ollama: (
    <svg width="20" height="20" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ollama">
      <title>Ollama</title>
      <circle cx="36" cy="32" r="10" fill="currentColor"/>
      <circle cx="64" cy="32" r="10" fill="currentColor"/>
      <ellipse cx="50" cy="62" rx="22" ry="18" fill="currentColor"/>
      <rect x="29" y="74" width="10" height="18" rx="5" fill="currentColor"/>
      <rect x="61" y="74" width="10" height="18" rx="5" fill="currentColor"/>
      <circle cx="32" cy="28" r="3" fill="#00000033"/>
      <circle cx="68" cy="28" r="3" fill="#00000033"/>
    </svg>
  ),
  // Google Gemini — logo officiel (étoile 4 branches dégradée)
  google: (
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
      <path d="M9.697 14.596c-.294.517-.874.833-1.493.833-.325 0-.64-.082-.924-.244-.822-.467-1.107-1.512-.64-2.333l.02-.04c.02-.04.04-.08.07-.112 0-.01.01-.021.02-.03.02-.04.051-.07.071-.111.02-.03.04-.07.061-.1.01-.02.03-.041.04-.061.03-.04.07-.08.102-.121.112-.132.244-.244.386-.336a1.74 1.74 0 0 1 .894-.244c.619 0 1.199.315 1.493.833.33.578.32 1.26-.1 1.867zm5.295-1.3c-.203.347-.56.558-.955.558a1.095 1.095 0 0 1-.549-.142c-.519-.294-.702-.965-.406-1.483.203-.345.558-.558.955-.558.193 0 .376.05.548.143.518.295.701.965.406 1.482z" fill="#4D6BFE"/>
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
  // AWS — logo officiel (smile + flèche)
  aws: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="AWS">
      <title>AWS</title>
      <path d="M6.763 10.036c0 .296.032.535.088.71.064.176.144.368.256.576.04.063.056.127.056.183 0 .08-.048.16-.152.24l-.503.335a.383.383 0 0 1-.208.072c-.08 0-.16-.04-.239-.112a2.47 2.47 0 0 1-.287-.375 6.18 6.18 0 0 1-.248-.471c-.622.734-1.405 1.101-2.347 1.101-.67 0-1.205-.191-1.596-.574-.391-.383-.59-.894-.59-1.533 0-.678.239-1.23.726-1.644.487-.415 1.133-.623 1.955-.623.272 0 .551.024.846.064.296.04.6.104.918.176v-.583c0-.607-.127-1.030-.375-1.277-.255-.248-.686-.367-1.3-.367-.28 0-.568.031-.863.103-.295.072-.583.16-.862.272a2.287 2.287 0 0 1-.28.104.488.488 0 0 1-.127.023c-.112 0-.168-.08-.168-.247v-.391c0-.128.016-.224.056-.28a.597.597 0 0 1 .224-.167c.279-.144.614-.264 1.005-.36a4.84 4.84 0 0 1 1.246-.151c.95 0 1.644.216 2.091.647.439.43.662 1.085.662 1.963v2.586zm-3.24 1.214c.263 0 .534-.048.822-.144.287-.096.543-.271.758-.51.128-.152.224-.32.272-.512.047-.191.08-.423.08-.694v-.335a6.66 6.66 0 0 0-.735-.136 6.02 6.02 0 0 0-.75-.048c-.535 0-.926.104-1.19.32-.263.215-.39.518-.39.917 0 .375.095.655.295.846.191.2.47.296.838.296zm6.41.862c-.144 0-.240-.024-.304-.08-.063-.048-.12-.16-.168-.311L7.586 5.55a1.398 1.398 0 0 1-.072-.32c0-.128.064-.2.191-.2h.783c.151 0 .255.025.31.08.065.048.113.16.16.312l1.342 5.284 1.245-5.284c.04-.16.088-.264.151-.312a.549.549 0 0 1 .32-.08h.638c.152 0 .256.025.32.08.063.048.12.16.151.312l1.261 5.348 1.381-5.348c.048-.16.104-.264.16-.312a.52.52 0 0 1 .311-.08h.743c.127 0 .2.065.2.2 0 .04-.009.08-.017.128a1.137 1.137 0 0 1-.056.2l-1.923 6.17c-.048.16-.104.263-.168.311a.51.51 0 0 1-.303.08h-.687c-.151 0-.255-.024-.32-.08-.063-.056-.119-.16-.15-.32l-1.238-5.148-1.23 5.14c-.04.16-.087.264-.15.32-.065.056-.177.08-.32.08zm10.256.215c-.415 0-.83-.048-1.229-.143-.399-.096-.71-.2-.918-.32-.128-.071-.215-.151-.247-.223a.563.563 0 0 1-.048-.224v-.407c0-.167.064-.247.183-.247.048 0 .096.008.144.024.048.016.12.048.2.08.271.12.566.215.878.279.319.064.63.096.95.096.502 0 .894-.088 1.165-.264a.86.86 0 0 0 .415-.758.778.778 0 0 0-.215-.559c-.144-.151-.416-.287-.807-.415l-1.157-.36c-.583-.183-1.014-.454-1.277-.813a1.902 1.902 0 0 1-.4-1.158c0-.335.073-.63.216-.886.144-.255.335-.479.575-.654.24-.184.51-.32.83-.415.32-.096.655-.136 1.006-.136.175 0 .359.008.535.032.183.024.35.056.518.088.16.04.312.08.455.127.144.048.256.096.336.144a.69.69 0 0 1 .24.2.43.43 0 0 1 .071.263v.375c0 .168-.064.256-.184.256a.83.83 0 0 1-.303-.096 3.652 3.652 0 0 0-1.532-.311c-.455 0-.815.071-1.062.223-.248.152-.375.383-.375.71 0 .224.08.416.24.567.159.152.454.304.877.44l1.134.358c.574.184.99.44 1.237.767.247.327.367.702.367 1.117 0 .343-.072.655-.207.926-.144.272-.336.511-.583.703-.248.2-.543.343-.886.447-.36.111-.743.167-1.166.167z" fill="currentColor"/>
      <path d="M21.422 16.956c-2.597 1.923-6.37 2.942-9.613 2.942-4.549 0-8.647-1.683-11.742-4.48-.243-.22-.025-.52.267-.349 3.342 1.947 7.47 3.12 11.733 3.12 2.877 0 6.037-.597 8.95-1.836.439-.187.808.287.405.603z" fill="#FF9900"/>
      <path d="M22.474 15.753c-.334-.428-2.204-.202-3.046-.102-.254.03-.294-.192-.064-.352 1.49-1.05 3.934-.746 4.218-.395.283.354-.075 2.81-1.472 3.98-.214.18-.418.084-.323-.153.315-.783 1.02-2.544.687-2.978z" fill="#FF9900"/>
    </svg>
  ),
};

function capitalize(str: string) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

interface ProviderSelectorProps {
  selected?: string;
  setSelected?: (provider: string) => void;
  onOpenAccountsSettings?: () => void;
}

// Ce composant synchronise le provider sélectionné via ProviderContext pour un usage temps réel dans UsageIndicator et AuthStatusIndicator
export const ProviderSelector: React.FC<ProviderSelectorProps> = ({ selected: selectedProp = '', setSelected: setSelectedProp = () => {}, onOpenAccountsSettings = () => {} }) => {
  const { t } = useTranslation();
  const { selectedProvider, setSelectedProvider } = useProviderContext();
  const { profiles, setActiveProfile } = useSettingsStore();
  const { toast } = useToast();
  const [showAuthDialog, setShowAuthDialog] = useState(false);
  const [pendingProvider, setPendingProvider] = useState<string>('');

  // Utilise le contexte si pas de props
  const selected = selectedProp || selectedProvider;
  const setSelected = (provider: string) => {
    setSelectedProvider(provider);
    if (typeof setSelectedProp === 'function') {
      setSelectedProp(provider);
    }
  };

  // Build static provider list from PROVIDER_MODELS_MAP + profile auth status
  const { providers, status } = useMemo(
    () => getStaticProviders(profiles),
    [profiles]
  );

  // Set default provider on mount if none selected
  useEffect(() => {
    if (!selected && providers.length > 0) {
      const defaultProvider = providers.find((p) => p.name === 'anthropic') ?? providers[0];
      setSelected(defaultProvider.name);
    }
  }, [providers]);

  // Restore persisted provider selection from localStorage on mount
  useEffect(() => {
    const storedProvider = localStorage.getItem('selectedProvider');
    if (storedProvider && storedProvider !== selected) {
      setSelected(storedProvider);
      const providerProfile = profiles.find((profile) => detectProvider(profile.baseUrl) === storedProvider);
      if (providerProfile) {
        setActiveProfile(providerProfile.id);
      } else {
        setActiveProfile(null);
      }
    }
  }, []);

  const handleSelect = (value: string) => {
    if (!status[value]) {
      // Trouver le provider pour afficher son nom dans le dialog
      const provider = providers.find(p => p.name === value);
      setPendingProvider(provider?.label || value);
      setShowAuthDialog(true);
      return;
    }
    setSelected(value);
    localStorage.setItem('selectedProvider', value);
    const providerProfile = profiles.find((profile) => detectProvider(profile.baseUrl) === value);
    if (providerProfile) {
      setActiveProfile(providerProfile.id);
    } else {
      setActiveProfile(null);
    }
  };

  const handleConfirmAuthRedirect = () => {
    setShowAuthDialog(false);
    onOpenAccountsSettings();
    
    // Afficher un toast pour informer l'utilisateur
    toast({
      title: t('providerSelector.authRedirect.title', 'Redirection vers les comptes'),
      description: t('providerSelector.authRedirect.description', `Configuration de ${pendingProvider} requise`),
      duration: 3000,
    });
  };

  return (
    <>
      <div className="flex items-center gap-4">
        <Label htmlFor="provider-select" className="whitespace-nowrap">
          {t('providerSelector.label', "Fournisseur de modèle IA")}
        </Label>
        <Select value={selected} onValueChange={handleSelect}>
          <SelectTrigger id="provider-select" className="w-full">
            <SelectValue placeholder={t('providerSelector.placeholder', '-- Choisir un provider --')} />
          </SelectTrigger>
          <SelectContent>
            {providers.map((p: CanonicalProvider) => (
              <SelectItem key={p.name} value={p.name} title={p.description}>
                <span className="flex items-center gap-2 truncate">
                  {providerIcons[p.name] || (
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label={p.label}>
                      <title>{p.label}</title>
                      <circle cx="10" cy="10" r="9" stroke="#BDBDBD" strokeWidth="2" fill="#F5F5F5" />
                      <text x="50%" y="55%" textAnchor="middle" fontSize="10" fill="#BDBDBD" fontWeight="bold" dy=".3em">{capitalize(p.label.charAt(0))}</text>
                    </svg>
                  )}
                  <span className="truncate">{p.label}</span>
                  {status[p.name] ? (
                    <Badge variant="success">{t('providerSelector.status.ok', 'OK')}</Badge>
                  ) : (
                    <Badge variant="warning">{t('providerSelector.status.notAuthenticated', 'Non authentifié')}</Badge>
                  )}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Dialog de confirmation pour la redirection vers les comptes */}
      <AlertDialog open={showAuthDialog} onOpenChange={setShowAuthDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-500" />
              {t('providerSelector.authDialog.title', 'Authentification requise')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('providerSelector.authDialog.description', `Le fournisseur "${pendingProvider}" n'est pas encore configuré.`)}{' '}
              {t('providerSelector.authDialog.subDescription', 'Pour utiliser ce provider, vous devez d\'abord ajouter vos clés d\'API dans la section "Comptes".')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>
              {t('providerSelector.authDialog.cancel', 'Annuler')}
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmAuthRedirect} className="flex items-center gap-2">
              <ExternalLink className="h-4 w-4" />
              {t('providerSelector.authDialog.confirm', 'Aller aux comptes')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default ProviderSelector;