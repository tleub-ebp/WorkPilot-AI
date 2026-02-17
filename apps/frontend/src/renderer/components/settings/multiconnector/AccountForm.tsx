import React, { useEffect, useState } from 'react';
import type { LLMProvider } from './types';
import { Card, CardContent } from '../../ui/card';
import { Button } from '../../ui/button';
import { saveUserProviderConfig } from './utils';
import { useTranslation } from 'react-i18next';

interface Props {
  provider: LLMProvider;
  onSave: (data: any) => void;
  onCancel: () => void;
}

// Configuration des champs par provider avec clés i18n
const providerFields: Record<string, Array<{ name: string; labelKey: string; type: string; required?: boolean; placeholderKey?: string }>> = {
  'openai': [
    { name: 'name', labelKey: 'settings.accounts.form.name', type: 'text', required: true, placeholderKey: 'settings.accounts.form.namePlaceholder' },
    { name: 'apiKey', labelKey: 'settings.accounts.form.apiKey', type: 'text', required: true, placeholderKey: 'settings.accounts.form.apiKeyPlaceholder' },
    { name: 'baseUrl', labelKey: 'settings.accounts.form.baseUrl', type: 'text', required: false, placeholderKey: 'settings.accounts.form.baseUrlPlaceholder' },
  ],
  'claude': [
    { name: 'name', labelKey: 'settings.accounts.form.name', type: 'text', required: true, placeholderKey: 'settings.accounts.form.namePlaceholder' },
    { name: 'apiKey', labelKey: 'settings.accounts.form.apiKey', type: 'text', required: true, placeholderKey: 'settings.accounts.form.apiKeyPlaceholder' },
    { name: 'oauthToken', labelKey: 'settings.accounts.form.oauthToken', type: 'text', required: false, placeholderKey: 'settings.accounts.form.oauthTokenPlaceholder' },
    { name: 'baseUrl', labelKey: 'settings.accounts.form.baseUrl', type: 'text', required: false, placeholderKey: 'settings.accounts.form.baseUrlPlaceholder' },
  ],
  'mistral': [
    { name: 'name', labelKey: 'settings.accounts.form.name', type: 'text', required: true, placeholderKey: 'settings.accounts.form.namePlaceholder' },
    { name: 'apiKey', labelKey: 'settings.accounts.form.apiKey', type: 'text', required: true, placeholderKey: 'settings.accounts.form.apiKeyPlaceholder' },
    { name: 'baseUrl', labelKey: 'settings.accounts.form.baseUrl', type: 'text', required: false, placeholderKey: 'settings.accounts.form.baseUrlPlaceholder' },
  ],
  // Ajoutez d'autres providers ici si besoin
};

const getFieldsForProvider = (provider: string) => {
  return providerFields[provider] || providerFields['openai']; // fallback générique
};

const AccountForm: React.FC<Props> = ({ provider, onSave, onCancel }) => {
  const { t } = useTranslation(['settings']);
  const [models, setModels] = useState<string[]>([]);
  const [formState, setFormState] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch(`/providers/models/${provider}`)
      .then(res => res.json())
      .then(data => setModels(data.models || []));
    setFormState({}); // reset form on provider change
  }, [provider]);

  const fields = getFieldsForProvider(provider);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormState({ ...formState, [e.target.name]: e.target.value });
  };

  const handleSave = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const model = formState['model'] || '';
    const config: any = { model };
    if (formState['apiKey']) config.api_key = formState['apiKey'];
    if (formState['oauthToken']) config.oauth_token = formState['oauthToken'];
    if (formState['baseUrl']) config.base_url = formState['baseUrl'];
    saveUserProviderConfig(provider, config);
    onSave({ ...formState, model });
  };

  return (
    <Card className="border border-info/30 bg-info/10 max-w-md mx-auto">
      <CardContent className="p-6">
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <h3 className="text-lg font-bold mb-2">{t('settings.accounts.form.addAccount', { provider })}</h3>
          {fields.map(field => (
            <input
              key={field.name}
              name={field.name}
              className="input input-bordered"
              placeholder={t(field.placeholderKey || field.labelKey)}
              required={field.required}
              type={field.type}
              value={formState[field.name] || ''}
              onChange={handleChange}
            />
          ))}
          <select
            className="input input-bordered"
            name="model"
            required
            value={formState['model'] || ''}
            onChange={handleChange}
          >
            <option value="">{t('settings.accounts.form.chooseModel')}</option>
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <div className="flex gap-3 mt-4">
            <Button type="submit" className="flex-1">{t('settings.accounts.form.save')}</Button>
            <Button type="button" variant="outline" onClick={onCancel} className="flex-1">{t('settings.accounts.form.cancel')}</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
export default AccountForm;