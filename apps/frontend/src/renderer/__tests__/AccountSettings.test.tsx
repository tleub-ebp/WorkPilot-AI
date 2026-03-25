import { render, fireEvent, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { AccountSettings } from '@/components/settings/AccountSettings';

// Minimal props mock
// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
const settings = {} as any;
const onSettingsChange = vi.fn();
const isOpen = true;
const defaultConnector = { id: 'anthropic', label: 'Anthropic' };

describe('AccountSettings basic functionality', () => {
  it('renders without crashing', () => {
    render(
      <AccountSettings settings={settings} onSettingsChange={onSettingsChange} isOpen={isOpen} connector={defaultConnector} />
    );
    
    // Should render the component - just check that something renders
    expect(screen.getByText(/accounts\.claudeCode\.description/i)).toBeDefined();
  });

  it('shows add button', () => {
    render(
      <AccountSettings settings={settings} onSettingsChange={onSettingsChange} isOpen={isOpen} connector={defaultConnector} />
    );
    
    // Should have an add button
    expect(screen.getByRole('button', { name: /buttons\.add/i })).toBeDefined();
  });

  it('shows input field when add button is clicked', () => {
    render(
      <AccountSettings settings={settings} onSettingsChange={onSettingsChange} isOpen={isOpen} connector={defaultConnector} />
    );
    
    // Click add button
    const addButton = screen.getByRole('button', { name: /buttons\.add/i });
    fireEvent.click(addButton);
    
    // Should show input field
    expect(screen.getByPlaceholderText(/accounts\.claudeCode\.accountNamePlaceholder/i)).toBeDefined();
  });
});

describe('AccountSettings different connectors', () => {
  it('renders for different connector types', () => {
    render(
      <AccountSettings
        settings={settings}
        onSettingsChange={onSettingsChange}
        isOpen={isOpen}
        connector={{ id: 'openai', label: 'OpenAI' }}
      />
    );
    
    // Should render the component for OpenAI connector
    expect(screen.getByText('OpenAI')).toBeDefined();
  });
});