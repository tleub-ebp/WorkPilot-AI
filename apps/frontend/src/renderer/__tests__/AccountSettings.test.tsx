import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import { AccountSettings } from '@/components/settings/AccountSettings';

// Minimal props mock
const settings = {} as any;
const onSettingsChange = jest.fn();
const isOpen = true;

describe('AccountSettings add form', () => {
  it('toggles add form and handles input', () => {
    render(
      <AccountSettings settings={settings} onSettingsChange={onSettingsChange} isOpen={isOpen} />
    );
    // Find and click the add button
    const addButton = screen.getByRole('button', { name: /ajouter|add/i });
    fireEvent.click(addButton);
    // Input should appear
    expect(screen.getByPlaceholderText(/nom du compte|account name/i)).toBeInTheDocument();
    // Fill input
    fireEvent.change(screen.getByPlaceholderText(/nom du compte|account name/i), { target: { value: 'Test Account' } });
    // Cancel
    fireEvent.click(screen.getByRole('button', { name: /annuler|cancel/i }));
    // Input should disappear
    expect(screen.queryByPlaceholderText(/nom du compte|account name/i)).not.toBeInTheDocument();
  });
});

describe('AccountSettings multi-connector', () => {
  it('shows OAuth-only message for OAuth connectors', () => {
    render(
      <AccountSettings
        settings={settings}
        onSettingsChange={onSettingsChange}
        isOpen={isOpen}
        connector={{ id: 'claude', label: 'Claude' }}
      />
    );
    const addButton = screen.getByRole('button', { name: /ajouter|add/i });
    fireEvent.click(addButton);
    expect(screen.getByText(/OAuth uniquement|OAuth only/i)).toBeInTheDocument();
  });

  it('shows API Key input for API Key connectors', () => {
    render(
      <AccountSettings
        settings={settings}
        onSettingsChange={onSettingsChange}
        isOpen={isOpen}
        connector={{ id: 'openai', label: 'OpenAI' }}
      />
    );
    const addButton = screen.getByRole('button', { name: /ajouter|add/i });
    fireEvent.click(addButton);
    expect(screen.getByPlaceholderText(/clé api|api key/i)).toBeInTheDocument();
  });
});