import { useEffect, useRef } from 'react';
import { Keyboard, X } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ShortcutEntry {
  keys: string;
  label: string;
}

interface ShortcutGroup {
  title: string;
  shortcuts: ShortcutEntry[];
}

interface KeyboardShortcutsOverlayProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ---------------------------------------------------------------------------
// Shortcut definitions
// ---------------------------------------------------------------------------

const SHORTCUT_GROUPS: ShortcutGroup[] = [
  {
    title: 'Navigation',
    shortcuts: [
      { keys: 'Ctrl+1', label: 'Go to Kanban' },
      { keys: 'Ctrl+2', label: 'Go to Terminals' },
      { keys: 'Ctrl+3', label: 'Go to Insights' },
      { keys: 'Ctrl+4', label: 'Go to Roadmap' },
      { keys: 'Ctrl+5', label: 'Go to Settings' },
      { keys: 'K', label: 'Kanban (sidebar)' },
      { keys: 'A', label: 'Terminals (sidebar)' },
      { keys: 'N', label: 'Insights (sidebar)' },
      { keys: 'D', label: 'Roadmap (sidebar)' },
      { keys: 'I', label: 'Ideation (sidebar)' },
    ],
  },
  {
    title: 'General',
    shortcuts: [
      { keys: 'Ctrl+K', label: 'Command Palette' },
      { keys: 'Ctrl+/', label: 'Keyboard Shortcuts' },
      { keys: 'Ctrl+N', label: 'New Task' },
      { keys: 'Ctrl+,', label: 'Open Settings' },
      { keys: 'Ctrl+T', label: 'Add Project' },
      { keys: 'Escape', label: 'Close dialog / overlay' },
    ],
  },
  {
    title: 'Terminal',
    shortcuts: [
      { keys: 'Ctrl+Shift+T', label: 'New Terminal' },
    ],
  },
  {
    title: 'Sidebar',
    shortcuts: [
      { keys: 'L', label: 'Changelog' },
      { keys: 'C', label: 'Context' },
      { keys: 'M', label: 'Agent Tools' },
      { keys: 'W', label: 'Worktrees' },
      { keys: 'G', label: 'GitHub Issues' },
      { keys: 'P', label: 'GitHub PRs' },
    ],
  },
];

// ---------------------------------------------------------------------------
// Kbd component
// ---------------------------------------------------------------------------

function Kbd({ children }: { children: string }) {
  const parts = children.split('+');
  return (
    <span className="inline-flex items-center gap-0.5">
      {parts.map((part, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
        <span key={i}>
          {i > 0 && <span className="mx-0.5 text-muted-foreground/50">+</span>}
          <kbd className="inline-flex h-6 min-w-6 items-center justify-center rounded border border-border bg-secondary px-1.5 font-mono text-[11px] font-medium text-foreground shadow-sm">
            {part}
          </kbd>
        </span>
      ))}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function KeyboardShortcutsOverlay({ open, onOpenChange }: KeyboardShortcutsOverlayProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onOpenChange(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    // biome-ignore lint/a11y/noNoninteractiveElementInteractions: interactive handler is intentional
    // biome-ignore lint/a11y/noStaticElementInteractions: interactive handler is intentional
    // biome-ignore lint/a11y/useKeyWithClickEvents: keyboard events handled elsewhere
    <div
      className="fixed inset-0 z-100 flex items-center justify-center"
      onClick={() => onOpenChange(false)}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* Panel */}
      // biome-ignore lint/a11y/noNoninteractiveElementInteractions: interactive handler is intentional
      // biome-ignore lint/a11y/noStaticElementInteractions: interactive handler is intentional
      // biome-ignore lint/a11y/useKeyWithClickEvents: keyboard events handled elsewhere
      // biome-ignore lint/a11y/noNoninteractiveElementInteractions lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: intentional
      <div
        ref={overlayRef}
        className="relative w-full max-w-2xl max-h-[80vh] overflow-hidden rounded-xl border border-border bg-card shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-3">
            <Keyboard className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Keyboard Shortcuts</h2>
          </div>
          <button type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto p-6 max-h-[calc(80vh-130px)]">
          <div className="grid grid-cols-2 gap-8">
            {SHORTCUT_GROUPS.map((group) => (
              <div key={group.title}>
                <h3 className="mb-3 text-sm font-semibold text-foreground uppercase tracking-wider">
                  {group.title}
                </h3>
                <div className="space-y-2">
                  {group.shortcuts.map((shortcut) => (
                    <div
                      key={shortcut.keys}
                      className="flex items-center justify-between gap-4 rounded-lg px-2 py-1.5 hover:bg-accent/30 transition-colors"
                    >
                      <span className="text-sm text-foreground">{shortcut.label}</span>
                      <Kbd>{shortcut.keys}</Kbd>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-border px-6 py-3 text-center text-xs text-muted-foreground">
          Press <Kbd>Escape</Kbd> to close &middot; Single-key shortcuts work when not typing in an input
        </div>
      </div>
    </div>
  );
}
