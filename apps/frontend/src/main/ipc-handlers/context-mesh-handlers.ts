/**
 * Context Mesh IPC handlers registration
 *
 * Handles IPC communication between the renderer process and the
 * Context Mesh backend service for cross-project intelligence.
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { IPC_CHANNELS } from '../../shared/constants';
import { contextMeshService } from '../context-mesh-service';
import { safeSendToRenderer } from './utils';

const MESH_DIR = path.join(os.homedir(), '.workpilot', 'context_mesh');

function readMeshJson(filename: string, fallback: unknown = {}): unknown {
  const filePath = path.join(MESH_DIR, filename);
  if (!existsSync(filePath)) return fallback;
  try {
    return JSON.parse(readFileSync(filePath, 'utf-8'));
  } catch {
    return fallback;
  }
}

function writeMeshJson(filename: string, data: unknown): boolean {
  const filePath = path.join(MESH_DIR, filename);
  try {
    const { mkdirSync } = require('node:fs');
    mkdirSync(MESH_DIR, { recursive: true });
    writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
    return true;
  } catch {
    return false;
  }
}

/**
 * Register all context-mesh-related IPC handlers
 */
export function registerContextMeshHandlers(
  getMainWindow: () => BrowserWindow | null
): () => void {
  // ============================================
  // Project operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_GET_PROJECTS, async () => {
    try {
      const data = readMeshJson('projects.json', { projects: [] }) as { projects: unknown[] };
      return { success: true, data: data.projects || [] };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_REGISTER_PROJECT, async (_event, projectDir: string) => {
    try {
      // Quick local registration (no AI needed)
      const projectName = path.basename(projectDir);
      const data = readMeshJson('projects.json', { projects: [] }) as { projects: Array<Record<string, unknown>> };
      const projects = data.projects || [];

      const existing = projects.find((p) => p.project_path === projectDir);
      if (existing) {
        return { success: true, data: existing, message: 'Project already registered' };
      }

      const newProject = {
        project_path: projectDir,
        project_name: projectName,
        registered_at: new Date().toISOString(),
        last_analyzed_at: '',
        pattern_count: 0,
        tech_stack: detectTechStack(projectDir),
        frameworks: [],
        languages: [],
      };

      projects.push(newProject);
      writeMeshJson('projects.json', { projects });
      return { success: true, data: newProject };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_UNREGISTER_PROJECT, async (_event, projectDir: string) => {
    try {
      const data = readMeshJson('projects.json', { projects: [] }) as { projects: Array<Record<string, unknown>> };
      data.projects = (data.projects || []).filter((p) => p.project_path !== projectDir);
      writeMeshJson('projects.json', data);
      return { success: true };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Pattern operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_GET_PATTERNS, async () => {
    try {
      const data = readMeshJson('patterns.json', { patterns: [] }) as { patterns: unknown[] };
      return { success: true, data: data.patterns || [] };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_DELETE_PATTERN, async (_event, patternId: string) => {
    try {
      const data = readMeshJson('patterns.json', { patterns: [] }) as { patterns: Array<Record<string, unknown>> };
      const before = data.patterns?.length || 0;
      data.patterns = (data.patterns || []).filter((p) => p.pattern_id !== patternId);
      if (data.patterns.length === before) {
        return { success: false, error: 'Pattern not found' };
      }
      writeMeshJson('patterns.json', data);
      return { success: true };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Handbook operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_GET_HANDBOOK, async () => {
    try {
      const data = readMeshJson('handbook.json', { entries: [] }) as { entries: unknown[] };
      return { success: true, data: data.entries || [] };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_DELETE_HANDBOOK_ENTRY, async (_event, entryId: string) => {
    try {
      const data = readMeshJson('handbook.json', { entries: [] }) as { entries: Array<Record<string, unknown>> };
      data.entries = (data.entries || []).filter((e) => e.entry_id !== entryId);
      writeMeshJson('handbook.json', data);
      return { success: true };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Skill Transfer operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_GET_SKILL_TRANSFERS, async () => {
    try {
      const data = readMeshJson('skill_transfers.json', { transfers: [] }) as { transfers: unknown[] };
      return { success: true, data: data.transfers || [] };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_UPDATE_TRANSFER_STATUS, async (_event, transferId: string, status: string) => {
    try {
      const data = readMeshJson('skill_transfers.json', { transfers: [] }) as { transfers: Array<Record<string, unknown>> };
      const transfer = (data.transfers || []).find((t) => t.transfer_id === transferId);
      if (!transfer) {
        return { success: false, error: 'Transfer not found' };
      }
      transfer.status = status;
      writeMeshJson('skill_transfers.json', data);
      return { success: true };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Recommendation operations
  // ============================================

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_GET_RECOMMENDATIONS, async (_event, targetProject?: string) => {
    try {
      const data = readMeshJson('recommendations.json', { recommendations: [] }) as { recommendations: Array<Record<string, unknown>> };
      let recs = data.recommendations || [];
      if (targetProject) {
        recs = recs.filter((r) => r.target_project === targetProject);
      }
      return { success: true, data: recs };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_UPDATE_RECOMMENDATION_STATUS, async (_event, recId: string, status: string) => {
    try {
      const data = readMeshJson('recommendations.json', { recommendations: [] }) as { recommendations: Array<Record<string, unknown>> };
      const rec = (data.recommendations || []).find((r) => r.recommendation_id === recId);
      if (!rec) {
        return { success: false, error: 'Recommendation not found' };
      }
      rec.status = status;
      writeMeshJson('recommendations.json', data);
      return { success: true };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Summary
  // ============================================

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_GET_SUMMARY, async () => {
    try {
      const projects = ((readMeshJson('projects.json', { projects: [] }) as { projects: unknown[] }).projects || []);
      const patterns = ((readMeshJson('patterns.json', { patterns: [] }) as { patterns: unknown[] }).patterns || []);
      const handbook = ((readMeshJson('handbook.json', { entries: [] }) as { entries: unknown[] }).entries || []);
      const transfers = ((readMeshJson('skill_transfers.json', { transfers: [] }) as { transfers: Array<Record<string, unknown>> }).transfers || []);
      const recs = ((readMeshJson('recommendations.json', { recommendations: [] }) as { recommendations: Array<Record<string, unknown>> }).recommendations || []);

      return {
        success: true,
        data: {
          project_count: projects.length,
          pattern_count: patterns.length,
          handbook_entry_count: handbook.length,
          skill_transfer_count: transfers.length,
          recommendation_count: recs.length,
          active_recommendations: recs.filter((r) => r.status === 'active').length,
          pending_transfers: transfers.filter((t) => t.status === 'pending').length,
          projects: (projects as Array<Record<string, unknown>>).map((p) => ({ name: p.project_name, path: p.project_path })),
        },
      };
    } catch (error: unknown) {
      return { success: false, error: (error as Error).message };
    }
  });

  // ============================================
  // Analysis operations (streaming via service)
  // ============================================

  ipcMain.on(IPC_CHANNELS.CONTEXT_MESH_RUN_ANALYSIS, (_event, model?: string, thinkingLevel?: string) => {
    contextMeshService.execute({
      command: 'analyze',
      model,
      thinkingLevel,
    });
  });

  ipcMain.handle(IPC_CHANNELS.CONTEXT_MESH_STOP_ANALYSIS, () => {
    const cancelled = contextMeshService.cancel();
    return { success: true, cancelled };
  });

  // ============================================
  // Service events → Renderer
  // ============================================

  const handleStatus = (status: string): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CONTEXT_MESH_STATUS, status);
  };

  const handleStreamChunk = (chunk: string): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CONTEXT_MESH_STREAM_CHUNK, chunk);
  };

  const handleError = (error: string): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CONTEXT_MESH_ERROR, error);
  };

  const handleComplete = (result: unknown): void => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CONTEXT_MESH_COMPLETE, result);
  };

  contextMeshService.on('status', handleStatus);
  contextMeshService.on('stream-chunk', handleStreamChunk);
  contextMeshService.on('error', handleError);
  contextMeshService.on('complete', handleComplete);

  // Return cleanup function
  return (): void => {
    contextMeshService.off('status', handleStatus);
    contextMeshService.off('stream-chunk', handleStreamChunk);
    contextMeshService.off('error', handleError);
    contextMeshService.off('complete', handleComplete);
  };
}

/**
 * Quick tech stack detection from project directory
 */
function detectTechStack(projectDir: string): string[] {
  const stack: string[] = [];
  const checks: Array<[string, string]> = [
    ['package.json', 'node'],
    ['requirements.txt', 'python'],
    ['pyproject.toml', 'python'],
    ['Cargo.toml', 'rust'],
    ['go.mod', 'go'],
    ['pom.xml', 'java'],
    ['build.gradle', 'java'],
    ['Gemfile', 'ruby'],
    ['composer.json', 'php'],
    ['Dockerfile', 'docker'],
  ];
  for (const [file, tech] of checks) {
    if (existsSync(path.join(projectDir, file)) && !stack.includes(tech)) {
      stack.push(tech);
    }
  }
  return stack;
}
