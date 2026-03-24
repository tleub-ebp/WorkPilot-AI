import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, } from '@testing-library/react';
import { NaturalLanguageGitDialog } from '@/components/natural-language-git/NaturalLanguageGitDialog';
import { useNaturalLanguageGitStore } from '@/stores/natural-language-git-store';
import { useProjectStore } from '@/stores/project-store';

// Mock stores
vi.mock('@/stores/natural-language-git-store');
vi.mock('@/stores/project-store');

// Mock translation
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('NaturalLanguageGitDialog', () => {
  const mockStore = {
    isOpen: false,
    phase: 'idle' as 'idle' | 'processing' | 'complete' | 'error',
    status: '',
    error: null as string | null,
    naturalLanguageCommand: '',
    streamingOutput: '',
    result: null as {
      generatedCommand: string;
      explanation: string;
      executionOutput: string;
      success: boolean;
    } | null,
    closeDialog: vi.fn(),
    openDialog: vi.fn(),
    setNaturalLanguageCommand: vi.fn(),
    reset: vi.fn(),
  };

  const mockProjectStore = {
    selectedProjectId: 'project-123' as string | null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useNaturalLanguageGitStore as any).mockReturnValue(mockStore);
    (useProjectStore as any).mockReturnValue(mockProjectStore);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should not render when dialog is closed', () => {
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.queryByText('naturalLanguageGit:title')).not.toBeInTheDocument();
  });

  it('should render when dialog is open', () => {
    mockStore.isOpen = true;
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.getByText('naturalLanguageGit:title')).toBeInTheDocument();
    expect(screen.getByText('naturalLanguageGit:description')).toBeInTheDocument();
  });

  it('should show command input field', () => {
    mockStore.isOpen = true;
    render(<NaturalLanguageGitDialog />);
    
    const textarea = screen.getByLabelText('naturalLanguageGit:command.label');
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveAttribute('placeholder', 'naturalLanguageGit:command.placeholder');
  });

  it('should show examples text', () => {
    mockStore.isOpen = true;
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.getByText('naturalLanguageGit:command.examples')).toBeInTheDocument();
  });

  it('should show no project warning when no project selected', () => {
    mockStore.isOpen = true;
    mockProjectStore.selectedProjectId = null;
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.getByText('naturalLanguageGit:errors.noProject')).toBeInTheDocument();
  });

  it('should show execute button when idle', () => {
    mockStore.isOpen = true;
    mockStore.naturalLanguageCommand = 'show changes';
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.getByText('naturalLanguageGit:actions.execute')).toBeInTheDocument();
    expect(screen.getByText('naturalLanguageGit:actions.close')).toBeInTheDocument();
  });

  it('should disable execute button when no command', () => {
    mockStore.isOpen = true;
    mockStore.naturalLanguageCommand = '';
    render(<NaturalLanguageGitDialog />);
    
    const executeButton = screen.getByText('naturalLanguageGit:actions.execute');
    expect(executeButton).toBeDisabled();
  });

  it('should show processing state', () => {
    mockStore.isOpen = true;
    mockStore.phase = 'processing';
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.getByText('naturalLanguageGit:status.processing')).toBeInTheDocument();
    expect(screen.getByText('naturalLanguageGit:actions.close')).toBeInTheDocument();
  });

  it('should show error state', () => {
    mockStore.isOpen = true;
    mockStore.phase = 'error';
    mockStore.error = 'Test error';
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.getByText('naturalLanguageGit:status.error')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
    expect(screen.getByText('naturalLanguageGit:actions.tryAgain')).toBeInTheDocument();
  });

  it('should show streaming output during processing', () => {
    mockStore.isOpen = true;
    mockStore.phase = 'processing';
    mockStore.streamingOutput = 'Processing...\nAnalyzing...';
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.getByText('naturalLanguageGit:result.streamingOutput')).toBeInTheDocument();
    expect(screen.getByText('Processing...\nAnalyzing...')).toBeInTheDocument();
  });

  it('should show result when complete', () => {
    mockStore.isOpen = true;
    mockStore.phase = 'complete';
    mockStore.result = {
      generatedCommand: 'git status',
      explanation: 'Shows the working tree status',
      executionOutput: 'On branch main\nnothing to commit',
      success: true,
    };
    render(<NaturalLanguageGitDialog />);
    
    expect(screen.getByText('naturalLanguageGit:result.generatedCommand')).toBeInTheDocument();
    expect(screen.getByText('git status')).toBeInTheDocument();
    expect(screen.getByText('naturalLanguageGit:result.explanation')).toBeInTheDocument();
    expect(screen.getByText('Shows the working tree status')).toBeInTheDocument();
    expect(screen.getByText('naturalLanguageGit:result.executionOutput')).toBeInTheDocument();
    expect(screen.getByText('On branch main\nnothing to commit')).toBeInTheDocument();
    expect(screen.getByText('naturalLanguageGit:result.executionSuccess')).toBeInTheDocument();
    expect(screen.getByText('naturalLanguageGit:actions.newCommand')).toBeInTheDocument();
  });

  it('should call closeDialog when close button clicked', async () => {
    mockStore.isOpen = true;
    render(<NaturalLanguageGitDialog />);
    
    const closeButton = screen.getByText('naturalLanguageGit:actions.close');
    fireEvent.click(closeButton);
    
    expect(mockStore.closeDialog).toHaveBeenCalled();
  });

  it('should call setNaturalLanguageCommand when input changes', async () => {
    mockStore.isOpen = true;
    render(<NaturalLanguageGitDialog />);
    
    const textarea = screen.getByLabelText('naturalLanguageGit:command.label');
    fireEvent.change(textarea, { target: { value: 'undo last commit' } });
    
    expect(mockStore.setNaturalLanguageCommand).toHaveBeenCalledWith('undo last commit');
  });

  it('should call reset when try again clicked', async () => {
    mockStore.isOpen = true;
    mockStore.phase = 'error';
    render(<NaturalLanguageGitDialog />);
    
    const tryAgainButton = screen.getByText('naturalLanguageGit:actions.tryAgain');
    fireEvent.click(tryAgainButton);
    
    expect(mockStore.reset).toHaveBeenCalled();
  });

  it('should call reset when new command clicked', async () => {
    mockStore.isOpen = true;
    mockStore.phase = 'complete';
    render(<NaturalLanguageGitDialog />);
    
    const newCommandButton = screen.getByText('naturalLanguageGit:actions.newCommand');
    fireEvent.click(newCommandButton);
    
    expect(mockStore.reset).toHaveBeenCalled();
  });
});
