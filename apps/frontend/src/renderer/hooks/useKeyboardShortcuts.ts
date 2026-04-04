import { useCallback, useEffect } from "react";

/**
 * Global keyboard shortcuts hook.
 * Listens for modifier-key combos (Ctrl+K, Ctrl+1-5, Ctrl+/, Ctrl+N, etc.)
 * and fires the appropriate callback.
 *
 * Feature 9.4 — Raccourcis clavier globaux.
 */

interface KeyboardShortcutActions {
	onCommandPalette: () => void;
	onKeyboardShortcuts: () => void;
	onNewTask: () => void;
	onOpenSettings: () => void;
	onNavigate: (view: string) => void;
}

export function useKeyboardShortcuts({
	onCommandPalette,
	onKeyboardShortcuts,
	onNewTask,
	onOpenSettings,
	onNavigate,
}: KeyboardShortcutActions) {
	const handleKeyDown = useCallback(
		(e: KeyboardEvent) => {
			// Skip when typing in inputs
			if (
				e.target instanceof HTMLInputElement ||
				e.target instanceof HTMLTextAreaElement ||
				e.target instanceof HTMLSelectElement ||
				(e.target as HTMLElement)?.isContentEditable
			) {
				return;
			}

			const ctrl = e.ctrlKey || e.metaKey;

			// --- Ctrl / Cmd combos ---
			if (ctrl) {
				switch (e.key.toLowerCase()) {
					case "k":
						e.preventDefault();
						onCommandPalette();
						return;
					case "/":
						e.preventDefault();
						onKeyboardShortcuts();
						return;
					case "n":
						e.preventDefault();
						onNewTask();
						return;
					case ",":
						e.preventDefault();
						onOpenSettings();
						return;
					case "1":
						e.preventDefault();
						onNavigate("kanban");
						return;
					case "2":
						e.preventDefault();
						onNavigate("terminals");
						return;
					case "3":
						e.preventDefault();
						onNavigate("insights");
						return;
					case "4":
						e.preventDefault();
						onNavigate("roadmap");
						return;
					case "5":
						e.preventDefault();
						onOpenSettings();
						return;
				}
			}
		},
		[
			onCommandPalette,
			onKeyboardShortcuts,
			onNewTask,
			onOpenSettings,
			onNavigate,
		],
	);

	useEffect(() => {
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [handleKeyDown]);
}
