import React from 'react';
import type { MultiConnectorAccount, LLMProvider } from './types';

interface Props {
  accounts: MultiConnectorAccount[];
  provider: LLMProvider;
}

// biome-ignore lint/correctness/noUnusedFunctionParameters: parameter kept for API compatibility
const AccountList: React.FC<Props> = ({ accounts, provider }) => {
  if (!accounts.length) {
    return <div style={{ color: '#888', fontSize: 14 }}>Aucun compte configuré.</div>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {accounts.map((account) => (
        <div key={account.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 8, border: '1px solid #eee', borderRadius: 4 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 500 }}>{account.name}</div>
            <div style={{ fontSize: 12, color: '#888' }}>{account.email || account.baseUrl}</div>
          </div>
          <div style={{ fontSize: 12, color: account.status === 'connected' ? 'green' : account.status === 'error' ? 'red' : '#888' }}>
            {account.status}
          </div>
          <button type="button" style={{ fontSize: 12, marginRight: 4 }}>Activer</button>
          <button type="button" style={{ fontSize: 12, marginRight: 4 }}>Tester</button>
          {account.apiKey && (
            <button type="button" style={{ fontSize: 12, color: 'red' }}>Supprimer</button>
          )}
        </div>
      ))}
    </div>
  );
};
export default AccountList;