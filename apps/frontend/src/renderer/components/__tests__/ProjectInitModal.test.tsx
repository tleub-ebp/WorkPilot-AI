import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import ProjectInitModal from '../ProjectInitModal';

// Mock ProviderSelector to avoid side effects
vi.mock('../ProviderSelector', () => ({
  __esModule: true,
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  default: ({ selected, setSelected }: any) => (
    <select
      data-testid="provider-select"
      value={selected}
      onChange={e => setSelected(e.target.value)}
    >
      <option value="anthropic">Anthropic (Claude)</option>
      <option value="openai">OpenAI</option>
    </select>
  )
}));

describe('ProjectInitModal', () => {
  it('affiche le wording et sélectionne le provider par défaut', () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { getByText, getByLabelText, getByTestId } = render(
      <ProjectInitModal
        open={true}
        onOpenChange={() => { /* noop */ }}
        projectName="MonProjetTest"
        onConfirm={onConfirm}
        onCancel={onCancel}
        defaultProvider="anthropic"
      />
    );
    expect(getByText(/Project initialization/i)).toBeTruthy();
    expect(getByLabelText('Project description')).toBeTruthy();
    expect(getByText('AI model provider')).toBeTruthy();
    expect((getByTestId('provider-select') as HTMLSelectElement).value).toBe('anthropic');
    expect(getByText(/Project name:/i)).toBeTruthy();
    expect(getByText(/Selected model:/i)).toBeTruthy();
  });

  it('appelle onConfirm avec la description et le provider', () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { getByLabelText, getByText, getByTestId } = render(
      <ProjectInitModal
        open={true}
        onOpenChange={() => { /* noop */ }}
        projectName="MonProjetTest"
        onConfirm={onConfirm}
        onCancel={onCancel}
        defaultProvider="anthropic"
      />
    );
    fireEvent.change(getByLabelText('Project description'), { target: { value: 'Ma super app' } });
    fireEvent.change(getByTestId('provider-select'), { target: { value: 'openai' } });
    fireEvent.click(getByText(/Create project/i));
    expect(onConfirm).toHaveBeenCalledWith('Ma super app', 'openai');
  });
});
