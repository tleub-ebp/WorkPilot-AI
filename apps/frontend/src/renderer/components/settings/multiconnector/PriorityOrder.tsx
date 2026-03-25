import React from 'react';
import type { LLMProvider } from './types';
import { useSettingsStore } from '@/stores/settings-store';
import { useTranslation } from 'react-i18next';

const initialOrder: LLMProvider[] = [
  'claude', 'copilot', 'openai', 'gemini', 'meta', 'mistral', 'deepseek', 'AWS', 'grok', 'ollama'
];

const PriorityOrder: React.FC = () => {
  const { t } = useTranslation(['settings']);
  const providerPriorityOrder = useSettingsStore((s) => s.settings.providerPriorityOrder) || initialOrder;
  const setProviderPriorityOrder = useSettingsStore((s) => s.setProviderPriorityOrder);

  const move = (from: number, to: number) => {
    if (to < 0 || to >= providerPriorityOrder.length) return;
    const newOrder = [...providerPriorityOrder];
    const [item] = newOrder.splice(from, 1);
    newOrder.splice(to, 0, item);
    setProviderPriorityOrder(newOrder);
  };

  return (
    <div>
      <h2 style={{ fontSize: 18, marginBottom: 8 }}>{t('settings.accounts.priorityOrder.title')}</h2>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {providerPriorityOrder.map((provider, idx) => (
          <li key={provider} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ flex: 1 }}>{provider}</span>
            <button type="button" onClick={() => move(idx, idx - 1)} disabled={idx === 0} aria-label={t('settings.accounts.priorityOrder.up')}>↑</button>
            <button type="button" onClick={() => move(idx, idx + 1)} disabled={idx === providerPriorityOrder.length - 1} aria-label={t('settings.accounts.priorityOrder.down')}>↓</button>
          </li>
        ))}
      </ul>
    </div>
  );
};
export default PriorityOrder;