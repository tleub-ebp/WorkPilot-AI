// ProviderSelector gère désormais lui-même la récupération des providers et des modèles associés
import React, { useEffect, useState } from "react";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from './ui/select';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { useTranslation } from 'react-i18next';
import { getProviders, CanonicalProvider } from '../../shared/utils/providers';
import { useProviderRefreshStore } from '../stores/provider-refresh-store';
import { useProviderContext } from './ProviderContext';
import { useSettingsStore } from '../stores/settings-store';
import { detectProvider } from '../../shared/utils/provider-detection';

// SVG pictograms for providers
const providerIcons: Record<string, JSX.Element> = {
  claude: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="10" cy="10" r="9" stroke="#6C63FF" strokeWidth="2" fill="#F3F3FF" />
      <text x="50%" y="55%" textAnchor="middle" fontSize="10" fill="#6C63FF" fontWeight="bold" dy=".3em">C</text>
    </svg>
  ),
  ollama: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="16" height="16" rx="4" fill="#F5F5F5" stroke="#4CAF50" strokeWidth="2" />
      <text x="50%" y="55%" textAnchor="middle" fontSize="10" fill="#388E3C" fontWeight="bold" dy=".3em">L</text>
    </svg>
  ),
  ollama_local: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="16" height="16" rx="4" fill="#E8F5E9" stroke="#388E3C" strokeWidth="2" />
      <text x="50%" y="55%" textAnchor="middle" fontSize="10" fill="#388E3C" fontWeight="bold" dy=".3em">LLM</text>
    </svg>
  ),
  openai: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="16" height="16" rx="4" fill="#F0F4FF" stroke="#0077FF" strokeWidth="2" />
      <text x="50%" y="55%" textAnchor="middle" fontSize="10" fill="#0077FF" fontWeight="bold" dy=".3em">A</text>
    </svg>
  ),
  // Add more pictograms for other providers as needed
};

const API_BASE =
  typeof import.meta !== "undefined" &&
  import.meta.env &&
  import.meta.env.VITE_BACKEND_URL
    ? import.meta.env.VITE_BACKEND_URL
    : "";

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
  const [providers, setProviders] = useState<CanonicalProvider[]>([]);
  const [status, setStatus] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string>("");
  const { lastRefresh } = useProviderRefreshStore();
  const { selectedProvider, setSelectedProvider } = useProviderContext();
  const { profiles, setActiveProfile } = useSettingsStore();

  // Utilise le contexte si pas de props
  const selected = selectedProp || selectedProvider;
  const setSelected = (provider: string) => {
    setSelectedProvider(provider); // Toujours mettre à jour le contexte global
    console.debug('[ProviderSelector] setSelected (context)', provider);
    if (setSelectedProp !== (() => {})) {
      setSelectedProp(provider);
    }
  };

  // Récupère la liste des providers au chargement
  useEffect(() => {
    getProviders()
      .then(({ providers, status }) => {
        const sortedProviders = [
          ...providers.filter((p: CanonicalProvider) => p.name === "anthropic"),
          ...providers.filter((p: CanonicalProvider) => p.name !== "anthropic")
        ];
        setProviders(sortedProviders);
        setStatus(status || {});
        setError("");
        if (!selected && sortedProviders.some((p: CanonicalProvider) => p.name === "anthropic")) {
          setSelected("anthropic");
        } else if (!selected && sortedProviders.length > 0) {
          setSelected(sortedProviders[0].name);
        }
        // Log debug pour vérifier la sélection initiale
        console.debug('[ProviderSelector] setSelected', selected, sortedProviders);
      })
      .catch((err) => {
        setProviders([]);
        setStatus({});
        setError(
          `Erreur lors de la récupération des providers: ${err.message}`
        );
      });
  }, [lastRefresh]);

  useEffect(() => {
    // Restaure la sélection du provider au montage
    const storedProvider = localStorage.getItem('selectedProvider');
    if (storedProvider && storedProvider !== selected) {
      setSelected(storedProvider);
      // Synchronise le profil actif
      const providerProfile = profiles.find((profile) => detectProvider(profile.baseUrl) === storedProvider);
      if (providerProfile) {
        setActiveProfile(providerProfile.id);
      } else {
        setActiveProfile(null);
      }
    }
  }, []);

  useEffect(() => {
    // Synchronise le profil actif avec le provider sélectionné au montage
    if (selectedProvider) {
      const providerProfile = profiles.find((profile) => detectProvider(profile.baseUrl) === selectedProvider);
      if (providerProfile) {
        setActiveProfile(providerProfile.id);
      } else {
        setActiveProfile(null);
      }
    }
    // Récupère la liste des providers au montage pour s'assurer que les statuts sont à jour
    getProviders()
      .then(({ providers, status }) => {
        const sortedProviders = [
          ...providers.filter((p: CanonicalProvider) => p.name === "anthropic"),
          ...providers.filter((p: CanonicalProvider) => p.name !== "anthropic")
        ];
        setProviders(sortedProviders);
        setStatus(status || {});
        setError("");
        // Définit le provider sélectionné par défaut si aucun n'est déjà sélectionné
        if (!selectedProvider && sortedProviders.some((p: CanonicalProvider) => p.name === "anthropic")) {
          setSelected("anthropic");
        } else if (!selectedProvider && sortedProviders.length > 0) {
          setSelected(sortedProviders[0].name);
        }
      })
      .catch((err) => {
        setProviders([]);
        setStatus({});
        setError(
          `Erreur lors de la récupération des providers: ${err.message}`
        );
      });
  }, [selectedProvider, profiles]);

  useEffect(() => {
    // Log pour vérifier la propagation du provider sélectionné
    console.debug('[ProviderSelector] Render with selectedProvider:', selectedProvider, 'selectedProp:', selectedProp);
  }, [selectedProvider, selectedProp]);

  const handleSelect = (value: string) => {
    if (!status[value]) {
      onOpenAccountsSettings();
      return;
    }
    setSelected(value);
    // Synchronise le profil actif avec le provider sélectionné
    const providerProfile = profiles.find((profile) => detectProvider(profile.baseUrl) === value);
    if (providerProfile) {
      setActiveProfile(providerProfile.id);
    } else {
      // Si aucun profil n'existe pour ce provider, désactive le profil actif
      setActiveProfile(null);
    }
    fetch(`${API_BASE}/providers/select?provider=${value}`, {
      method: "POST",
    });
    console.debug('[ProviderSelector] handleSelect', value, profiles);
  };

  return (
    <div className="flex items-center gap-4">
      <Label htmlFor="provider-select" className="whitespace-nowrap">
        {t('providerSelector.label', 'Providers LLM')}
      </Label>
      <Select value={selected} onValueChange={handleSelect}>
        <SelectTrigger id="provider-select" className="w-[320px]">
          <SelectValue placeholder={t('providerSelector.placeholder', '-- Choisir un provider --')} />
        </SelectTrigger>
        <SelectContent>
          {providers.map((p) => (
            <SelectItem key={p.name} value={p.name} title={p.description}>
              <span className="flex items-center gap-2 truncate">
                {providerIcons[p.name] || (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
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
      {error && <div className="text-destructive ml-4 text-sm">{t('providerSelector.error', error)}</div>}
    </div>
  );
};

export default ProviderSelector;