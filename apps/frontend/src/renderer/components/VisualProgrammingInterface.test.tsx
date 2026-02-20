import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import { VisualProgrammingInterface } from './VisualProgrammingInterface';

describe('VisualProgrammingInterface', () => {
  it('renders the main title and buttons', () => {
    render(<VisualProgrammingInterface />);
    expect(screen.getByText('🎨 Visual Programming Interface')).toBeInTheDocument();
    expect(screen.getByText('New Flowchart')).toBeInTheDocument();
    expect(screen.getByText('New Architecture Diagram')).toBeInTheDocument();
    expect(screen.getByText('New Mockup')).toBeInTheDocument();
    expect(screen.getByText('Reverse: Code → Visual')).toBeInTheDocument();
    expect(screen.getByText('Visual editor coming soon...')).toBeInTheDocument();
    expect(screen.getByText('Export Code')).toBeInTheDocument();
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByText('Load')).toBeInTheDocument();
  });

  it('permet d’ajouter un bloc template avec framework via drag & drop', async () => {
    render(<VisualProgrammingInterface />);
    // Simule le drag & drop d’un bloc FrontEnd
    const frontendBlock = screen.getByText(/FrontEnd/i);
    const canvas = screen.getByRole('region'); // ou autre sélecteur du canvas
    fireEvent.dragStart(frontendBlock, { dataTransfer: { setData: vi.fn() } });
    fireEvent.drop(canvas, { dataTransfer: { getData: () => 'frontend' }, clientX: 200, clientY: 200 });
    // Le modal de choix de framework doit apparaître
    await waitFor(() => screen.getByText(/Choisissez le framework/i));
    // Sélectionne React
    fireEvent.click(screen.getByText(/React/i));
    // Vérifie que le node a été ajouté avec le bon label
    await waitFor(() => screen.getByText(/FrontEnd \(React\)/i));
  });
});