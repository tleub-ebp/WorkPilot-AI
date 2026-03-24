import React from 'react';
import { Button, } from '../../ui';
import { Info, Check, Star, Trash2, AlertCircle, Plus } from 'lucide-react';
import type { MultiConnectorProvider, MultiConnectorAccount } from './types';
import { saveUserProviderConfig } from './utils';

interface Props {
  provider: MultiConnectorProvider;
  // Ajoutez ici les callbacks pour les actions (activer, supprimer, etc.)
}

const AccountConnectorCard: React.FC<Props> = ({ provider }) => {
  // TODO: brancher les actions réelles (activer, supprimer, etc.)
  // TODO: internationalisation des labels
  // TODO: gestion des états d'édition, d'ajout, etc.
  const testApiKey = async (provider: string, apiKey: string, baseUrl?: string) => {
    // Appel à un endpoint backend de test (à adapter selon l’API réelle)
    try {
      const res = await fetch(`/providers/test-key/${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, base_url: baseUrl })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      
      const data = await res.json();
      if (data.success) {
        // Met à jour la config avec validated:true
        saveUserProviderConfig(provider, { api_key: apiKey, base_url: baseUrl, validated: true });
        alert('Clé API validée avec succès !');
      } else {
        saveUserProviderConfig(provider, { api_key: apiKey, base_url: baseUrl, validated: false });
        alert('Clé API invalide ou refusée.');
      }
    } catch (_e) {
      saveUserProviderConfig(provider, { api_key: apiKey, base_url: baseUrl, validated: false });
      alert('Erreur lors du test de la clé API.');
    }
  };

  return (
    <div className="rounded-lg bg-muted/30 border border-border p-4 mb-4 min-w-[340px] max-w-[420px]">
      {/* Header modernisé */}
      <div className="text-center mb-6">
        <div className="flex justify-center mb-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            {/* Logo dynamique à ajouter ici si disponible */}
            {provider.logoUrl ? (
              <img src={provider.logoUrl} alt={provider.label} className="h-8 w-8" />
            ) : (
              <span className="text-2xl font-bold uppercase">{provider.label.charAt(0)}</span>
            )}
          </div>
        </div>
        <h2 className="text-xl font-bold text-foreground tracking-tight">{provider.label}</h2>
        <p className="mt-1 text-muted-foreground text-sm">
          {/* Description dynamique ou générique */}
          {provider.docUrl ? (
            <>
              Gérer vos comptes {provider.label}. <a href={provider.docUrl} target="_blank" rel="noopener noreferrer" className="underline text-primary">Documentation</a>
            </>
          ) : (
            <>Gérer vos comptes {provider.label}.</>
          )}
        </p>
      </div>
      {/* Statut général du connecteur (exemple simple, à adapter selon logique réelle) */}
      <div className="mb-4">
        {provider.accounts.length === 0 ? (
          <div className="flex items-center gap-2 p-3 rounded-lg border border-destructive/30 bg-destructive/5">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <span className="text-sm text-destructive">Aucun compte configuré pour ce connecteur.</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 p-3 rounded-lg border border-success/30 bg-success/5">
            <Check className="h-5 w-5 text-success" />
            <span className="text-sm text-success">{provider.accounts.length} compte(s) configuré(s).</span>
          </div>
        )}
      </div>
      {/* Liste des comptes */}
      <div className="space-y-2 mb-4">
        {provider.accounts.length === 0 ? null : (
          provider.accounts.map((account: MultiConnectorAccount) => (
            <div key={account.id} className="rounded-lg border transition-colors border-border bg-background">
              <div className="flex items-center justify-between p-3 hover:bg-muted/50">
                <div className="flex items-center gap-3">
                  <div className="h-7 w-7 rounded-full flex items-center justify-center text-xs font-medium shrink-0 bg-primary/10">
                    {account.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-foreground">{account.name}</span>
                      {account.isActive && (
                        <span className="text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded flex items-center gap-1">
                          <Star className="h-3 w-3" />
                          Actif
                        </span>
                      )}
                      {account.status === 'connected' && (
                        <span className="text-xs bg-success/20 text-success px-1.5 py-0.5 rounded flex items-center gap-1">
                          <Check className="h-3 w-3" />
                          Connecté
                        </span>
                      )}
                      {account.status === 'error' && (
                        <span className="text-xs bg-destructive/20 text-destructive px-1.5 py-0.5 rounded flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          Erreur
                        </span>
                      )}
                      {account.status === 'disconnected' && (
                        <span className="text-xs bg-warning/20 text-warning px-1.5 py-0.5 rounded">Non configuré</span>
                      )}
                    </div>
                    {account.email && (
                      <span className="text-xs text-muted-foreground">{account.email}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="outline" size="sm" className="gap-1 h-7 text-xs">Activer</Button>
                  <Button variant="outline" size="sm" className="gap-1 h-7 text-xs" onClick={() => testApiKey(provider.provider, account.apiKey || '', account.baseUrl)}>Tester</Button>
                  {account.apiKey && (
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"><Trash2 className="h-3 w-3" /></Button>
                  )}
                </div>
              </div>
              {/* Section avancée (édition, token, usage, etc.) à ajouter ici si besoin */}
            </div>
          ))
        )}
      </div>
      {/* Bouton d’ajout de compte */}
      <div className="flex items-center gap-2 justify-center">
        <Button size="sm" className="gap-1 shrink-0">
          <Plus className="h-3 w-3" />
          Ajouter un compte
        </Button>
      </div>
      {/* Section d’information/documentation */}
      {provider.docUrl && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="link"
            size="sm"
            className="text-muted-foreground gap-1"
            asChild
          >
            <a href={provider.docUrl} target="_blank" rel="noopener noreferrer">
              En savoir plus sur {provider.label}
              <Info className="h-4 w-4 ml-1" />
            </a>
          </Button>
        </div>
      )}
    </div>
  );
};
export default AccountConnectorCard;

// Exemple d’appel à saveConfiguredProviders (à placer dans la logique d’ajout/suppression de compte)
// saveConfiguredProviders(listeDesProvidersActuels);