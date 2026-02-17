import React, { useEffect, useState } from 'react';
import type { LLMProvider } from './types';
import { Card, CardContent } from '../../ui/card';
import { Button } from '../../ui/button';
import { saveUserProviderConfig } from './utils';

interface Props {
  provider: LLMProvider;
  onSave: (data: any) => void;
  onCancel: () => void;
}

const AccountForm: React.FC<Props> = ({ provider, onSave, onCancel }) => {
  const [models, setModels] = useState<string[]>([]);
  useEffect(() => {
    fetch(`/providers/models/${provider}`)
      .then(res => res.json())
      .then(data => setModels(data.models || []));
  }, [provider]);

  const handleSave = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const name = (form.elements[0] as HTMLInputElement).value;
    const apiKey = (form.elements[1] as HTMLInputElement).value;
    const oauthToken = provider === 'anthropic' || provider === 'claude' ? (form.elements[2] as HTMLInputElement).value : undefined;
    const baseUrl = (form.elements[provider === 'anthropic' || provider === 'claude' ? 3 : 2] as HTMLInputElement).value;
    const model = (form.elements[provider === 'anthropic' || provider === 'claude' ? 4 : 3] as HTMLSelectElement).value;
    const config: any = { model };
    if (apiKey) config.api_key = apiKey;
    if (oauthToken) config.oauth_token = oauthToken;
    if (baseUrl) config.base_url = baseUrl;
    saveUserProviderConfig(provider, config);
    onSave({ name, apiKey, oauthToken, baseUrl, model });
  };

  // TODO: Afficher les champs dynamiquement selon le provider
  return (
    <Card className="border border-info/30 bg-info/10 max-w-md mx-auto">
      <CardContent className="p-6">
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <h3 className="text-lg font-bold mb-2">Ajouter un compte {provider}</h3>
          <input className="input input-bordered" placeholder="Nom du compte" required />
          <input className="input input-bordered" placeholder="Clé API" />
          {(provider === 'anthropic' || provider === 'claude') && (
            <input className="input input-bordered" placeholder="Token OAuth Claude Code" />
          )}
          <input className="input input-bordered" placeholder="Base URL (optionnel)" />
          <select className="input input-bordered" required>
            <option value="">-- Choisir un modèle --</option>
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          {/* TODO: Champs spécifiques selon le provider */}
          <div className="flex gap-3 mt-4">
            <Button type="submit" className="flex-1">Enregistrer</Button>
            <Button type="button" variant="outline" onClick={onCancel} className="flex-1">Annuler</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
export default AccountForm;