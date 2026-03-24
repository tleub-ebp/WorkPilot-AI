import { app } from 'electron';
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync, Dirent } from 'node:fs';
import path from 'node:path';
import { v4 as uuidv4 } from 'uuid';
import type { Project, ProjectSettings, Task, TaskStatus, TaskMetadata, ImplementationPlan, ReviewReason, PlanSubtask, KanbanPreferences, ExecutionPhase, Subtask } from '../shared/types';
import { DEFAULT_PROJECT_SETTINGS, AUTO_BUILD_PATHS, getSpecsDir, JSON_ERROR_PREFIX, JSON_ERROR_TITLE_SUFFIX, TASK_STATUS_PRIORITY } from '../shared/constants';
import { getAutoBuildPath, isInitialized } from './project-initializer';
import { getTaskWorktreeDir } from './worktree-paths';
import { findAllSpecPaths } from './utils/spec-path-helpers';
import { ensureAbsolutePath } from './utils/path-helpers';

interface TabState {
  openProjectIds: string[];
  activeProjectId: string | null;
  tabOrder: string[];
}

interface StoreData {
  projects: Project[];
  settings: Record<string, unknown>;
  tabState?: TabState;
  kanbanPreferences?: Record<string, KanbanPreferences>;
}

interface TasksCacheEntry {
  tasks: Task[];
  timestamp: number;
}

/**
 * Persistent storage for projects and settings
 */
export class ProjectStore {
  private readonly storePath: string;
  private readonly data: StoreData;
  private readonly tasksCache: Map<string, TasksCacheEntry> = new Map();
  private readonly CACHE_TTL_MS = 3000; // 3 seconds TTL for task cache

  constructor() {
    // Store in app's userData directory
    const userDataPath = app.getPath('userData');
    const storeDir = path.join(userDataPath, 'store');

    // Ensure directory exists
    if (!existsSync(storeDir)) {
      mkdirSync(storeDir, { recursive: true });
    }

    this.storePath = path.join(storeDir, 'projects.json');
    this.data = this.load();
  }

  /**
   * Load store from disk
   */
  private load(): StoreData {
    if (existsSync(this.storePath)) {
      try {
        const content = readFileSync(this.storePath, 'utf-8');
        const data = JSON.parse(content);
        // Convert date strings back to Date objects and normalize paths to absolute
        data.projects = data.projects.map((p: Project) => ({
          ...p,
          // Ensure project.path is always absolute (critical for dev mode path resolution)
          // Do NOT use decodeURIComponent: filesystem paths may contain literal %20
          // (e.g., directory named "MeCa%20Web") which is a valid filename, not URL encoding
          path: ensureAbsolutePath(p.path),
          createdAt: new Date(p.createdAt),
          updatedAt: new Date(p.updatedAt)
        }));
        return data;
      } catch {
        return { projects: [], settings: {} };
      }
    }
    return { projects: [], settings: {} };
  }

  /**
   * Save store to disk
   */
  private save(): void {
    writeFileSync(this.storePath, JSON.stringify(this.data, null, 2), 'utf-8');
  }

  /**
   * Add a new project
   */
  addProject(projectPath: string, name?: string): Project {
    // CRITICAL: Normalize to absolute path for dev mode compatibility
    // This prevents path resolution issues after app restart
    // Do NOT use decodeURIComponent: filesystem paths may contain literal %20
    const absolutePath = ensureAbsolutePath(projectPath);

    // Check if project already exists (using absolute path for comparison)
    const existing = this.data.projects.find((p) => p.path === absolutePath);
    if (existing) {
      // Validate that .auto-claude folder still exists for existing project
      // If manually deleted, reset autoBuildPath so UI prompts for reinitialization
      if (existing.autoBuildPath && !isInitialized(existing.path)) {
        console.warn(`[ProjectStore] .auto-claude folder was deleted for project "${existing.name}" - resetting autoBuildPath`);
        existing.autoBuildPath = '';
        existing.updatedAt = new Date();
        this.save();
      }
      return existing;
    }

    // Derive name from path if not provided
    const projectName = name || path.basename(absolutePath);

    // Determine auto-claude path (supports both 'auto-claude' and '.auto-claude')
    const autoBuildPath = getAutoBuildPath(absolutePath) || '';

    const project: Project = {
      id: uuidv4(),
      name: projectName,
      path: absolutePath, // Store absolute path
      autoBuildPath,
      settings: { ...DEFAULT_PROJECT_SETTINGS },
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.data.projects.push(project);
    this.save();

    return project;
  }

  /**
   * Update project's autoBuildPath after initialization
   */
  updateAutoBuildPath(projectId: string, autoBuildPath: string): Project | undefined {
    const project = this.data.projects.find((p) => p.id === projectId);
    if (project) {
      project.autoBuildPath = autoBuildPath;
      project.updatedAt = new Date();
      this.save();
    }
    return project;
  }

  /**
   * Remove a project
   */
  removeProject(projectId: string): boolean {
    const index = this.data.projects.findIndex((p) => p.id === projectId);
    if (index !== -1) {
      this.data.projects.splice(index, 1);
      // Clean up kanban preferences to avoid orphaned data
      if (this.data.kanbanPreferences?.[projectId]) {
        delete this.data.kanbanPreferences[projectId];
      }
      this.save();
      return true;
    }
    return false;
  }

  /**
   * Get all projects
   */
  getProjects(): Project[] {
    return this.data.projects;
  }

  /**
   * Get tab state
   */
  getTabState(): TabState {
    return this.data.tabState || {
      openProjectIds: [],
      activeProjectId: null,
      tabOrder: []
    };
  }

  /**
   * Save tab state
   */
  saveTabState(tabState: TabState): void {
    // Filter out any project IDs that no longer exist
    const validProjectIds = new Set(this.data.projects.map(p => p.id));
    this.data.tabState = {
      openProjectIds: tabState.openProjectIds.filter(id => validProjectIds.has(id)),
      activeProjectId: tabState.activeProjectId && validProjectIds.has(tabState.activeProjectId)
        ? tabState.activeProjectId
        : null,
      tabOrder: tabState.tabOrder.filter(id => validProjectIds.has(id))
    };
    this.save();
  }

  /**
   * Get kanban column preferences for a specific project
   */
  getKanbanPreferences(projectId: string): KanbanPreferences | null {
    return this.data.kanbanPreferences?.[projectId] ?? null;
  }

  /**
   * Save kanban column preferences for a specific project
   */
  saveKanbanPreferences(projectId: string, preferences: KanbanPreferences): void {
    this.data.kanbanPreferences ??= {};
    this.data.kanbanPreferences[projectId] = preferences;
    this.save();
  }

  /**
   * Validate all projects to ensure their .auto-claude folders still exist.
   * If a project has autoBuildPath set but the folder was deleted,
   * reset autoBuildPath to empty string so the UI prompts for reinitialization.
   *
   * @returns Array of project IDs that were reset due to missing .auto-claude folder
   */
  validateProjects(): string[] {
    const resetProjectIds: string[] = [];
    let hasChanges = false;

    for (const project of this.data.projects) {
      // Skip projects that aren't initialized (autoBuildPath is empty)
      if (!project.autoBuildPath) {
        continue;
      }

      // Check if the project path still exists
      if (!existsSync(project.path)) {
        console.warn(`[ProjectStore] Project path no longer exists: ${project.path}`);
        continue; // Don't reset - let user handle this case
      }

      // Check if .auto-claude folder still exists
      if (!isInitialized(project.path)) {
        console.warn(`[ProjectStore] .auto-claude folder missing for project "${project.name}" at ${project.path}`);
        project.autoBuildPath = '';
        project.updatedAt = new Date();
        resetProjectIds.push(project.id);
        hasChanges = true;
      }
    }

    if (hasChanges) {
      this.save();
      console.warn(`[ProjectStore] Reset ${resetProjectIds.length} project(s) due to missing .auto-claude folder`);
    }

    return resetProjectIds;
  }

  /**
   * Get a project by ID
   */
  getProject(projectId: string): Project | undefined {
    return this.data.projects.find((p) => p.id === projectId);
  }

  /**
   * Update project settings
   */
  updateProjectSettings(
    projectId: string,
    settings: Partial<ProjectSettings>
  ): Project | undefined {
    const project = this.data.projects.find((p) => p.id === projectId);
    if (project) {
      project.settings = { ...project.settings, ...settings };
      project.updatedAt = new Date();
      this.save();
    }
    return project;
  }

  /**
   * Rename a project (display name only — path is never changed)
   */
  renameProject(projectId: string, name: string): Project | undefined {
    const project = this.data.projects.find((p) => p.id === projectId);
    if (project) {
      project.name = name.trim();
      project.updatedAt = new Date();
      this.save();
    }
    return project;
  }

  /**
   * Get tasks for a project by scanning specs directory
   * Implements caching with 3-second TTL to prevent excessive worktree scanning
   */
  getTasks(projectId: string): Task[] {
    // Check cache first
    const cached = this.getCachedTasks(projectId);
    if (cached) {
      return cached;
    }

    const project = this.getProject(projectId);
    if (!project) {
      return [];
    }

    const allTasks = this.loadAllTasks(project);
    const deduplicatedTasks = this.deduplicateTasks(allTasks);
    
    // Update cache
    this.cacheTasks(projectId, deduplicatedTasks);

    return deduplicatedTasks;
  }

  /**
   * Get cached tasks if valid
   * @param projectId - Project ID
   * @returns Cached tasks or null if expired/not found
   */
  private getCachedTasks(projectId: string): Task[] | null {
    const cached = this.tasksCache.get(projectId);
    const now = Date.now();

    if (cached && (now - cached.timestamp) < this.CACHE_TTL_MS) {
      return cached.tasks;
    }

    return null;
  }

  /**
   * Load all tasks from main project and worktrees
   * @param project - Project object
   * @returns Array of all tasks (potentially duplicated)
   */
  private loadAllTasks(project: Project): Task[] {
    const allTasks: Task[] = [];
    const specsBaseDir = getSpecsDir(project.autoBuildPath);

    // Load main project tasks
    const mainTasks = this.loadMainProjectTasks(project, specsBaseDir);
    allTasks.push(...mainTasks);

    // Load worktree tasks (only if spec exists in main)
    const worktreeTasks = this.loadWorktreeTasks(project, specsBaseDir, mainTasks);
    allTasks.push(...worktreeTasks);

    return allTasks;
  }

  /**
   * Load tasks from main project specs directory
   * @param project - Project object
   * @param specsBaseDir - Base specs directory
   * @returns Array of main project tasks
   */
  private loadMainProjectTasks(project: Project, specsBaseDir: string): Task[] {
    const mainSpecsDir = path.join(project.path, specsBaseDir);
    
    if (!existsSync(mainSpecsDir)) {
      return [];
    }

    return this.loadTasksFromSpecsDir(mainSpecsDir, project.path, 'main', project.id, specsBaseDir);
  }

  /**
   * Load tasks from worktree directories
   * @param project - Project object
   * @param specsBaseDir - Base specs directory
   * @param mainTasks - Main project tasks for validation
   * @returns Array of valid worktree tasks
   */
  private loadWorktreeTasks(project: Project, specsBaseDir: string, mainTasks: Task[]): Task[] {
    const worktreesDir = getTaskWorktreeDir(project.path);
    
    if (!existsSync(worktreesDir)) {
      return [];
    }

    const mainSpecIds = new Set(mainTasks.map(t => t.specId));
    
    try {
      return this.scanWorktreesForTasks(worktreesDir, specsBaseDir, project.id, mainSpecIds);
    } catch (error) {
      console.error('[ProjectStore] Error scanning worktrees:', error);
      return [];
    }
  }

  /**
   * Scan worktree directories for tasks
   * @param worktreesDir - Worktrees directory path
   * @param specsBaseDir - Base specs directory
   * @param projectId - Project ID
   * @param mainSpecIds - Set of valid spec IDs from main project
   * @returns Array of valid worktree tasks
   */
  private scanWorktreesForTasks(
    worktreesDir: string, 
    specsBaseDir: string, 
    projectId: string, 
    mainSpecIds: Set<string>
  ): Task[] {
    const allWorktreeTasks: Task[] = [];
    const worktrees = readdirSync(worktreesDir, { withFileTypes: true });

    for (const worktree of worktrees) {
      if (!worktree.isDirectory()) {
        continue;
      }

      const worktreeTasks = this.loadSingleWorktreeTasks(
        worktreesDir, 
        worktree.name, 
        specsBaseDir, 
        projectId, 
        mainSpecIds
      );
      allWorktreeTasks.push(...worktreeTasks);
    }

    return allWorktreeTasks;
  }

  /**
   * Load tasks from a single worktree
   * @param worktreesDir - Worktrees directory path
   * @param worktreeName - Worktree name
   * @param specsBaseDir - Base specs directory
   * @param projectId - Project ID
   * @param mainSpecIds - Set of valid spec IDs from main project
   * @returns Array of valid worktree tasks
   */
  private loadSingleWorktreeTasks(
    worktreesDir: string,
    worktreeName: string,
    specsBaseDir: string,
    projectId: string,
    mainSpecIds: Set<string>
  ): Task[] {
    const worktreeSpecsDir = path.join(worktreesDir, worktreeName, specsBaseDir);
    
    if (!existsSync(worktreeSpecsDir)) {
      return [];
    }

    const worktreePath = path.join(worktreesDir, worktreeName);
    const worktreeTasks = this.loadTasksFromSpecsDir(
      worktreeSpecsDir,
      worktreePath,
      'worktree',
      projectId,
      specsBaseDir
    );

    // Only include worktree tasks if the spec exists in main project
    return worktreeTasks.filter(t => mainSpecIds.has(t.specId));
  }

  /**
   * Deduplicate tasks by ID with proper priority logic
   * @param allTasks - All tasks (potentially duplicated)
   * @returns Deduplicated array of tasks
   */
  private deduplicateTasks(allTasks: Task[]): Task[] {
    const taskMap = new Map<string, Task>();

    for (const task of allTasks) {
      this.mergeTaskIntoMap(taskMap, task);
    }

    return Array.from(taskMap.values());
  }

  /**
   * Merge a task into the task map with proper deduplication logic
   * @param taskMap - Map of tasks by ID
   * @param task - Task to merge
   */
  private mergeTaskIntoMap(taskMap: Map<string, Task>, task: Task): void {
    const existing = taskMap.get(task.id);
    
    if (!existing) {
      // First occurrence wins
      taskMap.set(task.id, task);
      return;
    }

    const shouldReplace = this.shouldReplaceTask(existing, task);
    
    if (shouldReplace) {
      taskMap.set(task.id, task);
    }
  }

  /**
   * Determine if a new task should replace an existing one
   * @param existing - Existing task
   * @param newTask - New task to consider
   * @returns true if new task should replace existing
   */
  private shouldReplaceTask(existing: Task, newTask: Task): boolean {
    const existingIsMain = existing.location === 'main';
    const newIsMain = newTask.location === 'main';

    if (!existingIsMain && newIsMain) {
      // New is main, replace existing worktree
      return true;
    }

    if (existingIsMain === newIsMain) {
      // Same location - use status priority to determine which is more complete
      return this.hasHigherStatusPriority(newTask, existing);
    }

    // If existing is main and new is worktree, keep existing
    return false;
  }

  /**
   * Check if a task has higher status priority than another
   * @param task1 - First task
   * @param task2 - Second task
   * @returns true if task1 has higher priority
   */
  private hasHigherStatusPriority(task1: Task, task2: Task): boolean {
    const priority1 = TASK_STATUS_PRIORITY[task1.status] || 0;
    const priority2 = TASK_STATUS_PRIORITY[task2.status] || 0;
    return priority1 > priority2;
  }

  /**
   * Cache tasks for a project
   * @param projectId - Project ID
   * @param tasks - Tasks to cache
   */
  private cacheTasks(projectId: string, tasks: Task[]): void {
    this.tasksCache.set(projectId, { tasks, timestamp: Date.now() });
  }

  /**
   * Invalidate the tasks cache for a specific project
   * Call this when tasks are modified (created, deleted, status changed, etc.)
   */
  invalidateTasksCache(projectId: string): void {
    this.tasksCache.delete(projectId);
  }

  /**
   * Clear all tasks cache entries
   * Useful for global refresh scenarios
   */
  clearTasksCache(): void {
    this.tasksCache.clear();
  }

  /**
   * Load tasks from a specs directory (helper method for main project and worktrees)
   */
  private loadTasksFromSpecsDir(
    specsDir: string,
    _basePath: string,
    location: 'main' | 'worktree',
    projectId: string,
    _specsBaseDir: string
  ): Task[] {
    const specDirs = this.getSpecDirectories(specsDir);
    const tasks: Task[] = [];

    for (const dir of specDirs) {
      const task = this.createTaskFromSpec(dir, specsDir, location, projectId);
      if (task) {
        tasks.push(task);
      }
    }

    return tasks;
  }

  /**
   * Get all spec directories from the specs directory
   */
  private getSpecDirectories(specsDir: string): Dirent[] {
    try {
      return readdirSync(specsDir, { withFileTypes: true })
        .filter(dir => dir.isDirectory() && dir.name !== '.gitkeep');
    } catch (error) {
      console.error('[ProjectStore] Error reading specs directory:', error);
      return [];
    }
  }

  /**
   * Create a task from a spec directory
   */
  private createTaskFromSpec(
    dir: Dirent, 
    specsDir: string, 
    location: 'main' | 'worktree', 
    projectId: string
  ): Task | null {
    try {
      const specPath = path.join(specsDir, dir.name);
      const plan = this.loadImplementationPlan(specPath, dir.name);
      const { hasJsonError, jsonErrorMessage } = this.getJsonErrorInfo(plan, dir.name);
      
      const description = this.extractDescription(specPath, plan, hasJsonError);
      const metadata = this.loadTaskMetadata(specPath);
      const { status: finalStatus, reviewReason: finalReviewReason } = this.determineFinalStatus(plan, hasJsonError);
      const subtasks = this.extractSubtasks(plan);
      const { status: correctedStatus, reviewReason: correctedReviewReason } = this.correctStaleTaskStatus(
        subtasks, hasJsonError, finalStatus, finalReviewReason, plan, path.join(specPath, AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN), dir.name
      );
      
      const title = this.extractTitle(dir.name, plan, hasJsonError, specPath);
      const executionProgress = this.calculateExecutionProgress(plan);
      const { stagedInMainProject, stagedAt } = this.extractStagedInfo(plan);

      return {
        id: dir.name,
        specId: dir.name,
        projectId,
        title,
        description: hasJsonError ? `${JSON_ERROR_PREFIX}${jsonErrorMessage}` : description,
        status: correctedStatus,
        subtasks,
        logs: [],
        metadata,
        ...(correctedReviewReason !== undefined && { reviewReason: correctedReviewReason }),
        ...(executionProgress && { executionProgress }),
        stagedInMainProject,
        stagedAt,
        location,
        specsPath: specPath,
        createdAt: new Date(plan?.created_at || Date.now()),
        updatedAt: new Date(plan?.updated_at || Date.now())
      };
    } catch (error) {
      console.error(`[ProjectStore] Error loading spec ${dir.name}:`, error);
      return null;
    }
  }

  /**
   * Load implementation plan from spec directory
   */
  private loadImplementationPlan(specPath: string, specName: string): ImplementationPlan | null {
    const planPath = path.join(specPath, AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN);
    
    if (!existsSync(planPath)) {
      return null;
    }

    try {
      const content = readFileSync(planPath, 'utf-8');
      return JSON.parse(content);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      console.error(`[ProjectStore] JSON parse error for spec ${specName}:`, errorMessage);
      return null;
    }
  }

  /**
   * Get JSON error information
   */
  private getJsonErrorInfo(plan: ImplementationPlan | null, _specName: string): { hasJsonError: boolean; jsonErrorMessage: string } {
    if (plan !== null) {
      return { hasJsonError: false, jsonErrorMessage: '' };
    }
    
    // This indicates a JSON parse error occurred during loading
    return { hasJsonError: true, jsonErrorMessage: 'JSON parse error' };
  }

  /**
   * Extract description from various sources in priority order
   */
  private extractDescription(specPath: string, plan: ImplementationPlan | null, hasJsonError: boolean): string {
    if (hasJsonError) {
      return '';
    }

    // PRIORITY 1: From implementation plan
    if (plan?.description) {
      return plan.description;
    }

    // PRIORITY 2: From requirements.json
    const requirementsDescription = this.getRequirementsDescription(specPath);
    if (requirementsDescription) {
      return requirementsDescription;
    }

    // PRIORITY 3: From spec.md Overview
    return this.getSpecOverview(specPath);
  }

  /**
   * Get description from requirements.json
   */
  private getRequirementsDescription(specPath: string): string {
    const requirementsPath = path.join(specPath, AUTO_BUILD_PATHS.REQUIREMENTS);
    
    if (!existsSync(requirementsPath)) {
      return '';
    }

    try {
      const reqContent = readFileSync(requirementsPath, 'utf-8');
      const requirements = JSON.parse(reqContent);
      return requirements.task_description || '';
    } catch {
      return '';
    }
  }

  /**
   * Get overview from spec.md file
   */
  private getSpecOverview(specPath: string): string {
    const specFilePath = path.join(specPath, AUTO_BUILD_PATHS.SPEC_FILE);
    
    if (!existsSync(specFilePath)) {
      return '';
    }

    try {
      const content = readFileSync(specFilePath, 'utf-8');
      const overviewRegex = /## Overview\s*\n+([\s\S]*?)(?=\n#{1,6}\s|$)/;
      const overviewMatch = overviewRegex.exec(content);
      return overviewMatch?.[1]?.trim() || '';
    } catch {
      return '';
    }
  }

  /**
   * Load task metadata
   */
  private loadTaskMetadata(specPath: string): TaskMetadata | undefined {
    const metadataPath = path.join(specPath, 'task_metadata.json');
    
    if (!existsSync(metadataPath)) {
      return undefined;
    }

    try {
      const content = readFileSync(metadataPath, 'utf-8');
      return JSON.parse(content);
    } catch {
      return undefined;
    }
  }

  /**
   * Determine final task status
   */
  private determineFinalStatus(plan: ImplementationPlan | null, hasJsonError: boolean): { status: TaskStatus; reviewReason?: ReviewReason } {
    if (hasJsonError) {
      return { status: 'human_review' as TaskStatus, reviewReason: 'errors' as ReviewReason };
    }
    
    return this.determineTaskStatusAndReason(plan);
  }

  /**
   * Extract subtasks from plan
   */
  private extractSubtasks(plan: ImplementationPlan | null): Subtask[] {
    return plan?.phases?.flatMap((phase) => {
      const items = phase.subtasks || (phase as { chunks?: PlanSubtask[] }).chunks || [];
      return items.map((subtask) => ({
        id: subtask.id,
        title: subtask.description,
        description: subtask.description,
        status: subtask.status,
        files: []
      }));
    }) || [];
  }

  /**
   * Extract title from plan or spec file
   */
  private extractTitle(dirName: string, plan: ImplementationPlan | null, hasJsonError: boolean, specPath: string): string {
    // For JSON error tasks, use directory name with marker
    if (hasJsonError) {
      return `${dirName}${JSON_ERROR_TITLE_SUFFIX}`;
    }

    // Get title from plan
    let title = plan?.feature || plan?.title || dirName;
    
    // If it looks like a spec ID, try to extract title from spec file
    const looksLikeSpecId = /^\d{3}-/.test(title);
    if (looksLikeSpecId && existsSync(path.join(specPath, AUTO_BUILD_PATHS.SPEC_FILE))) {
      title = this.extractTitleFromSpec(specPath) || title;
    }

    return title;
  }

  /**
   * Extract title from spec file
   */
  private extractTitleFromSpec(specPath: string): string | null {
    const specFilePath = path.join(specPath, AUTO_BUILD_PATHS.SPEC_FILE);
    
    try {
      const specContent = readFileSync(specFilePath, 'utf-8');
      const titleRegex = /^#\s+(?:Quick Spec:|Specification:)?\s*(.+)$/m;
      const titleMatch = titleRegex.exec(specContent);
      return titleMatch?.[1]?.trim() || null;
    } catch {
      return null;
    }
  }

  /**
   * Calculate execution progress
   */
  private calculateExecutionProgress(plan: ImplementationPlan | null): { phase: ExecutionPhase; phaseProgress: number; overallProgress: number } | undefined {
    const persistedPhase = (plan as { executionPhase?: string } | null)?.executionPhase as ExecutionPhase | undefined;
    const xstateState = (plan as { xstateState?: string } | null)?.xstateState;
    
    if (persistedPhase) {
      return { phase: persistedPhase, phaseProgress: 50, overallProgress: 50 };
    }
    
    if (xstateState) {
      return this.inferExecutionProgressFromXState(xstateState);
    }
    
    return this.inferExecutionProgress(plan?.status);
  }

  /**
   * Extract staged information from plan
   */
  private extractStagedInfo(plan: ImplementationPlan | null): { stagedInMainProject?: boolean; stagedAt?: string } {
    const planWithStaged = plan as unknown as { stagedInMainProject?: boolean; stagedAt?: string } | null;
    return {
      stagedInMainProject: planWithStaged?.stagedInMainProject,
      stagedAt: planWithStaged?.stagedAt
    };
  }

  /**
   * Correct stale task status when all subtasks are completed but status wasn't persisted.
   * Extracted from loadTasksFromSpecsDir to keep read/write separation clear.
   *
   * NOTE: This method intentionally writes to implementation_plan.json to persist the
   * correction and prevent repeated auto-corrections on every getTasks() call. The plan
   * object is NOT mutated unless the write succeeds, preserving memory/disk consistency.
   */
  private correctStaleTaskStatus(
    subtasks: { status: string }[],
    hasJsonError: boolean,
    finalStatus: TaskStatus,
    finalReviewReason: ReviewReason | undefined,
    plan: ImplementationPlan | null,
    planPath: string,
    taskName: string
  ): { status: TaskStatus; reviewReason: ReviewReason | undefined } {
    if (subtasks.length === 0 || hasJsonError) {
      return { status: finalStatus, reviewReason: finalReviewReason };
    }

    const completedCount = subtasks.filter(s => s.status === 'completed').length;
    const allCompleted = completedCount === subtasks.length;

    // Only auto-correct if all subtasks are done and status is in a stale state.
    // Preserve in_progress (task is actively running — auto-correction would race with XState),
    // ai_review (QA in progress), error (needs investigation), human_review, done, pr_created.
    if (!allCompleted || finalStatus === 'in_progress' || finalStatus === 'human_review' || finalStatus === 'done' || finalStatus === 'pr_created' || finalStatus === 'ai_review' || finalStatus === 'error') {
      return { status: finalStatus, reviewReason: finalReviewReason };
    }

    // Skip auto-correction if plan was recently updated (backend may still be writing)
    if (plan?.updated_at) {
      const updatedAt = new Date(plan.updated_at).getTime();
      const ageMs = Date.now() - updatedAt;
      if (ageMs < 30_000) {
        return { status: finalStatus, reviewReason: finalReviewReason };
      }
    }

    console.warn(`[ProjectStore] Auto-correcting task ${taskName}: all ${subtasks.length} subtasks completed but status was ${finalStatus}. Setting to human_review.`);

    if (plan) {
      // Clone before mutation — only apply to the original plan object if the write succeeds
      const correctedPlan = {
        ...plan,
        status: 'human_review' as const,
        planStatus: 'review',
        reviewReason: 'completed' as ReviewReason,
        updated_at: new Date().toISOString(),
        xstateState: 'human_review',
        executionPhase: 'complete'
      };
      try {
        writeFileSync(planPath, JSON.stringify(correctedPlan, null, 2), 'utf-8');
        // Write succeeded — apply mutations to the in-memory plan so the rest of
        // loadTasksFromSpecsDir sees the corrected values (e.g., executionProgress)
        Object.assign(plan, correctedPlan);
        console.warn(`[ProjectStore] Persisted corrected status for task ${taskName}`);
      } catch (writeError) {
        // Write failed — leave the plan object unchanged and return the original status
        // so there's no memory/disk inconsistency
        console.error(`[ProjectStore] Failed to persist corrected status for task ${taskName}:`, writeError);
        return { status: finalStatus, reviewReason: finalReviewReason };
      }
    }

    return { status: 'human_review', reviewReason: 'completed' };
  }

  /**
   * Determine task status and review reason from the plan file.
   *
   * With the XState refactor, status and reviewReason are authoritative fields
   * written by the TaskStateManager. The renderer should not recompute status
   * from subtasks or QA files.
   */
  private determineTaskStatusAndReason(
    plan: ImplementationPlan | null
  ): { status: TaskStatus; reviewReason?: ReviewReason } {
    if (!plan?.status) {
      return { status: 'backlog' };
    }

    const statusMap: Record<string, TaskStatus> = {
      'pending': 'backlog',
      'planning': 'in_progress',
      'in_progress': 'in_progress',
      'coding': 'in_progress',
      'review': 'ai_review',
      'completed': 'done',
      'done': 'done',
      'human_review': 'human_review',
      'ai_review': 'ai_review',
      'pr_created': 'pr_created',
      'backlog': 'backlog',
      'error': 'error',
      'queue': 'queue',
      'queued': 'queue'
    };

    const storedStatus = statusMap[plan.status] || 'backlog';
    const reviewReason = storedStatus === 'human_review' ? plan.reviewReason : undefined;

    return { status: storedStatus, reviewReason };
  }

  /**
   * Infer execution progress from plan status for XState snapshot restoration.
   * Maps plan status values to ExecutionPhase so buildSnapshotFromTask can
   * correctly determine the XState state (planning vs coding vs qa_review, etc.).
   */
  private inferExecutionProgress(planStatus: string | undefined): { phase: ExecutionPhase; phaseProgress: number; overallProgress: number } | undefined {
    if (!planStatus) return undefined;

    // Map plan status to execution phase
    const phaseMap: Record<string, ExecutionPhase> = {
      'pending': 'idle',
      'backlog': 'idle',
      'queue': 'idle',
      'queued': 'idle',
      'planning': 'planning',
      'coding': 'coding',
      'in_progress': 'coding', // Default in_progress to coding
      'review': 'qa_review',
      'ai_review': 'qa_review',
      'qa_review': 'qa_review',
      'qa_fixing': 'qa_fixing',
      'human_review': 'complete',
      'completed': 'complete',
      'done': 'complete',
      'error': 'failed'
    };

    const phase = phaseMap[planStatus];
    if (!phase) return undefined;

    return {
      phase,
      phaseProgress: 50,
      overallProgress: 50
    };
  }

  /**
   * Infer execution progress from persisted XState state.
   * This is more precise than inferring from plan status since it uses the exact machine state.
   */
  private inferExecutionProgressFromXState(xstateState: string): { phase: ExecutionPhase; phaseProgress: number; overallProgress: number } | undefined {
    // Map XState state directly to execution phase
    const phaseMap: Record<string, ExecutionPhase> = {
      'backlog': 'idle',
      'planning': 'planning',
      'plan_review': 'planning',
      'coding': 'coding',
      'qa_review': 'qa_review',
      'qa_fixing': 'qa_fixing',
      'human_review': 'complete',
      'error': 'failed',
      'creating_pr': 'complete',
      'pr_created': 'complete',
      'done': 'complete'
    };

    const phase = phaseMap[xstateState];
    if (!phase) return undefined;

    return {
      phase,
      phaseProgress: phase === 'complete' ? 100 : 50,
      overallProgress: phase === 'complete' ? 100 : 50
    };
  }

  /**
   * Archive tasks by writing archivedAt to their metadata
   * @param projectId - Project ID
   * @param taskIds - IDs of tasks to archive
   * @param version - Version they were archived in (optional)
   */
  archiveTasks(projectId: string, taskIds: string[], version?: string): boolean {
    const project = this.getProject(projectId);
    if (!project) {
      console.error('[ProjectStore] archiveTasks: Project not found:', projectId);
      return false;
    }

    const specsBaseDir = getSpecsDir(project.autoBuildPath);
    const archivedAt = new Date().toISOString();
    
    const hasErrors = this.archiveMultipleTasks(taskIds, project.path, specsBaseDir, archivedAt, version);
    
    // Invalidate cache since task metadata changed
    this.invalidateTasksCache(projectId);

    return !hasErrors;
  }

  /**
   * Archive multiple tasks and track errors
   * @param taskIds - Task IDs to archive
   * @param projectPath - Project root path
   * @param specsBaseDir - Base directory for specs
   * @param archivedAt - Archive timestamp
   * @param version - Optional version
   * @returns true if there were errors
   */
  private archiveMultipleTasks(
    taskIds: string[], 
    projectPath: string, 
    specsBaseDir: string, 
    archivedAt: string, 
    version?: string
  ): boolean {
    let hasErrors = false;

    for (const taskId of taskIds) {
      if (this.archiveSingleTask(taskId, projectPath, specsBaseDir, archivedAt, version)) {
        hasErrors = true;
      }
    }

    return hasErrors;
  }

  /**
   * Archive a single task across all its spec locations
   * @param taskId - Task ID to archive
   * @param projectPath - Project root path
   * @param specsBaseDir - Base directory for specs
   * @param archivedAt - Archive timestamp
   * @param version - Optional version
   * @returns true if there were errors
   */
  private archiveSingleTask(
    taskId: string, 
    projectPath: string, 
    specsBaseDir: string, 
    archivedAt: string, 
    version?: string
  ): boolean {
    const specPaths = findAllSpecPaths(projectPath, specsBaseDir, taskId);

    // If spec directory doesn't exist anywhere, skip gracefully
    if (specPaths.length === 0) {
      return false;
    }

    let hasErrors = false;
    for (const specPath of specPaths) {
      if (this.archiveTaskAtLocation(taskId, specPath, archivedAt, version)) {
        hasErrors = true;
      }
    }

    return hasErrors;
  }

  /**
   * Archive task at a specific location
   * @param taskId - Task ID
   * @param specPath - Path to the spec directory
   * @param archivedAt - Archive timestamp
   * @param version - Optional version
   * @returns true if there was an error
   */
  private archiveTaskAtLocation(
    taskId: string, 
    specPath: string, 
    archivedAt: string, 
    version?: string
  ): boolean {
    try {
      const metadataPath = path.join(specPath, 'task_metadata.json');
      const metadata = this.readOrCreateMetadata(metadataPath);

      // Add archive info
      metadata.archivedAt = archivedAt;
      if (version) {
        metadata.archivedInVersion = version;
      }

      writeFileSync(metadataPath, JSON.stringify(metadata, null, 2), 'utf-8');
      return false;
    } catch (error) {
      console.error(`[ProjectStore] archiveTasks: Failed to archive task ${taskId} at ${specPath}:`, error);
      return true;
    }
  }

  /**
   * Read existing metadata or create new if file doesn't exist
   * @param metadataPath - Path to metadata file
   * @returns TaskMetadata object
   */
  private readOrCreateMetadata(metadataPath: string): TaskMetadata {
    try {
      return JSON.parse(readFileSync(metadataPath, 'utf-8'));
    } catch (readErr: unknown) {
      // File doesn't exist yet - start with empty metadata
      if ((readErr as NodeJS.ErrnoException).code !== 'ENOENT') {
        throw readErr;
      }
      return {};
    }
  }

  /**
   * Unarchive tasks by removing archivedAt from their metadata
   * @param projectId - Project ID
   * @param taskIds - IDs of tasks to unarchive
   */
  unarchiveTasks(projectId: string, taskIds: string[]): boolean {
    const project = this.getProject(projectId);
    if (!project) {
      console.error('[ProjectStore] unarchiveTasks: Project not found:', projectId);
      return false;
    }

    const specsBaseDir = getSpecsDir(project.autoBuildPath);
    let hasErrors = false;

    for (const taskId of taskIds) {
      if (this.unarchiveSingleTask(taskId, project.path, specsBaseDir)) {
        hasErrors = true;
      }
    }

    // Invalidate cache since task metadata changed
    this.invalidateTasksCache(projectId);

    return !hasErrors;
  }

  /**
   * Unarchive a single task across all its spec locations
   * @param taskId - Task ID to unarchive
   * @param projectPath - Project root path
   * @param specsBaseDir - Base directory for specs
   * @returns true if there were errors, false otherwise
   */
  private unarchiveSingleTask(taskId: string, projectPath: string, specsBaseDir: string): boolean {
    const specPaths = findAllSpecPaths(projectPath, specsBaseDir, taskId);

    if (specPaths.length === 0) {
      console.warn(`[ProjectStore] unarchiveTasks: Spec directory not found for task ${taskId}`);
      return false;
    }

    let hasErrors = false;
    for (const specPath of specPaths) {
      if (this.unarchiveTaskAtLocation(taskId, specPath)) {
        hasErrors = true;
      }
    }

    return hasErrors;
  }

  /**
   * Unarchive task at a specific location
   * @param taskId - Task ID
   * @param specPath - Path to the spec directory
   * @returns true if there was an error, false otherwise
   */
  private unarchiveTaskAtLocation(taskId: string, specPath: string): boolean {
    try {
      const metadataPath = path.join(specPath, 'task_metadata.json');
      const metadata = this.readTaskMetadata(metadataPath, taskId, specPath);
      
      if (!metadata) {
        return false;
      }

      delete metadata.archivedAt;
      delete metadata.archivedInVersion;
      writeFileSync(metadataPath, JSON.stringify(metadata, null, 2), 'utf-8');
      return false;
    } catch (error) {
      console.error(`[ProjectStore] unarchiveTasks: Failed to unarchive task ${taskId} at ${specPath}:`, error);
      return true;
    }
  }

  /**
   * Read task metadata with error handling
   * @param metadataPath - Path to metadata file
   * @param taskId - Task ID for logging
   * @param specPath - Spec path for logging
   * @returns TaskMetadata or null if file not found
   */
  private readTaskMetadata(metadataPath: string, taskId: string, specPath: string): TaskMetadata | null {
    try {
      return JSON.parse(readFileSync(metadataPath, 'utf-8'));
    } catch (readErr: unknown) {
      if ((readErr as NodeJS.ErrnoException).code === 'ENOENT') {
        console.warn(`[ProjectStore] unarchiveTasks: Metadata file not found for task ${taskId} at ${specPath}`);
        return null;
      }
      throw readErr;
    }
  }
}

// Singleton instance
export const projectStore = new ProjectStore();
