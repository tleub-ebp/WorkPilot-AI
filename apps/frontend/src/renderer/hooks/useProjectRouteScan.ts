import { useEffect, useCallback } from 'react';
import { useProjectStore } from '../stores/project-store';
import { useApiExplorerStore } from '../stores/api-explorer-store';
import type { OpenApiSpec } from '../stores/api-explorer-store';

/**
 * Watches the active project and automatically scans its source code for API
 * routes in the background whenever the active project changes.
 *
 * Call this hook once at the App root so scanning starts regardless of which
 * view is currently visible.
 *
 * @returns `rescan` — call this to force a re-scan of the current project
 *          (e.g. when new endpoints have been developed).
 */
export function useProjectRouteScan() {
  const projects = useProjectStore((s) => s.projects);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId);

  const activeProject = projects.find(
    (p) => p.id === (activeProjectId ?? selectedProjectId)
  );

  const setSpec = useApiExplorerStore((s) => s.setSpec);
  const setSpecSource = useApiExplorerStore((s) => s.setSpecSource);
  const setIsProjectScanning = useApiExplorerStore((s) => s.setIsProjectScanning);
  const setProjectScanError = useApiExplorerStore((s) => s.setProjectScanError);
  const setScannedProjectId = useApiExplorerStore((s) => s.setScannedProjectId);
  const setLastProjectScanAt = useApiExplorerStore((s) => s.setLastProjectScanAt);
  const setSpecError = useApiExplorerStore((s) => s.setSpecError);

  const scan = useCallback(
    async (projectId: string, projectPath: string, projectName: string) => {
      setIsProjectScanning(true);
      setProjectScanError(null);
      try {
        const result = await window.electronAPI.scanProjectRoutes(
          projectPath,
          projectName
        );
        if (result.success && result.data) {
          setSpec(result.data as OpenApiSpec);
          setSpecSource('scan');
          setSpecError(null);
          setScannedProjectId(projectId);
          setLastProjectScanAt(Date.now());
        } else {
          setProjectScanError(result.error ?? 'Failed to scan project routes');
        }
      } catch (err) {
        setProjectScanError(String(err));
      } finally {
        setIsProjectScanning(false);
      }
    },
    [setSpec, setSpecSource, setIsProjectScanning, setProjectScanError,
     setScannedProjectId, setLastProjectScanAt, setSpecError]
  );

  // Auto-scan whenever the active project changes
  const _projectId = activeProject?.id;
  useEffect(() => {
    if (!activeProject) return;
    void scan(
      activeProject.id,
      activeProject.path,
      activeProject.name ?? activeProject.path.split(/[/\\]/).pop() ?? 'Project'
    );
    // Only re-run when the project identity changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProject, scan]);

  const rescan = useCallback(() => {
    if (!activeProject) return;
    void scan(
      activeProject.id,
      activeProject.path,
      activeProject.name ?? activeProject.path.split(/[/\\]/).pop() ?? 'Project'
    );
  }, [activeProject, scan]);

  return { rescan };
}
