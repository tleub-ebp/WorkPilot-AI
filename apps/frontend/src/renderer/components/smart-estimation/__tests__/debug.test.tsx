import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

// Mock the stores
const mockStore = {
  isOpen: true,
  phase: 'idle',
  status: '',
  streamingOutput: '',
  result: null,
  error: null,
  initialTaskDescription: '',
  openDialog: vi.fn(),
  closeDialog: vi.fn(),
  setPhase: vi.fn(),
  setStatus: vi.fn(),
  appendStreamingOutput: vi.fn(),
  setResult: vi.fn(),
  setError: vi.fn(),
  reset: vi.fn(),
  setState: vi.fn(),
};

vi.mock('@/stores/smart-estimation-store', () => ({
  useSmartEstimationStore: () => mockStore,
  startSmartEstimation: vi.fn(),
  setupSmartEstimationListeners: vi.fn(() => vi.fn()),
}));

vi.mock('@/stores/project-store', () => ({
  useProjectStore: () => ({
    selectedProjectId: 'test-project-id',
    projects: [{ id: 'test-project-id', name: 'Test Project' }]
  }),
}));

// Mock UI components
vi.mock('@/components/ui/dialog', () => ({
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  Dialog: ({ children, open }: any) => 
    open ? <div data-testid="dialog">{children}</div> : null,
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  DialogContent: ({ children }: any) => <div data-testid="dialog-content">{children}</div>,
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  DialogHeader: ({ children }: any) => <div data-testid="dialog-header">{children}</div>,
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  DialogTitle: ({ children }: any) => <div data-testid="dialog-title">{children}</div>,
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  DialogDescription: ({ children }: any) => <div data-testid="dialog-description">{children}</div>,
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  DialogFooter: ({ children }: any) => <div data-testid="dialog-footer">{children}</div>,
}));

vi.mock('@/components/ui/textarea', () => ({
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  Textarea: ({ value, onChange, disabled, placeholder, id }: any) => (
    <textarea
      value={value}
      onChange={onChange}
      disabled={disabled}
      placeholder={placeholder}
      id={id}
      data-testid="task-textarea"
    />
  ),
}));

vi.mock('@/components/ui/label', () => ({
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  Label: ({ children, htmlFor }: any) => <label htmlFor={htmlFor}>{children}</label>,
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

import SmartEstimationDialog from '../SmartEstimationDialog';

describe('Debug Test', () => {
  it('should render dialog when open', () => {
    // biome-ignore lint/suspicious/noConsole: logging retained for debugging
    console.log('Mock store:', mockStore);
    
    render(<SmartEstimationDialog />);
    
    // biome-ignore lint/suspicious/noConsole: logging retained for debugging
    console.log('Document body:', document.body.innerHTML);
    
    expect(screen.getByTestId('dialog')).toBeInTheDocument();
  });
});
