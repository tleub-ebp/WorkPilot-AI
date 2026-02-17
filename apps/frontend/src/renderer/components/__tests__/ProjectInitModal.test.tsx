import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import ProjectInitModal from '../ProjectInitModal';

// Mock ProviderSelector to avoid side effects
vi.mock('../ProviderSelector', () => ({
  __esModule: true,
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
        onOpenChange={() => {}}
        projectName="MonProjetTest"
        onConfirm={onConfirm}
        onCancel={onCancel}
        defaultProvider="anthropic"
      />
    );
    expect(getByText('Initialisation du projet "MonProjetTest"')).toBeTruthy();
    expect(getByLabelText('Description du projet')).toBeTruthy();
    expect(getByText('Fournisseur de modèle IA')).toBeTruthy();
    expect(getByTestId('provider-select').value).toBe('anthropic');
    expect(getByText('Nom du projet:')).toBeTruthy();
    expect(getByText('Modèle sélectionné:')).toBeTruthy();
  });

  it('appelle onConfirm avec la description et le provider', () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const { getByLabelText, getByText, getByTestId } = render(
      <ProjectInitModal
        open={true}
        onOpenChange={() => {}}
        projectName="MonProjetTest"
        onConfirm={onConfirm}
        onCancel={onCancel}
        defaultProvider="anthropic"
      />
    );
    fireEvent.change(getByLabelText('Description du projet'), { target: { value: 'Ma super app' } });
    fireEvent.change(getByTestId('provider-select'), { target: { value: 'openai' } });
    fireEvent.click(getByText('Créer le projet "MonProjetTest"'));
    expect(onConfirm).toHaveBeenCalledWith('Ma super app', 'openai');
  });
});
