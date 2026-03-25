/**
 * Module-level "one-shot" signal for opening the TaskDetailModal on a specific tab.
 * Set before calling onClick() on a TaskCard to make the modal open on a given tab.
 */
let _pendingInitialTab: string | null = null;

export function setPendingTaskDetailTab(tab: string): void {
  _pendingInitialTab = tab;
}

export function consumePendingTaskDetailTab(): string | null {
  const tab = _pendingInitialTab;
  _pendingInitialTab = null;
  return tab;
}
