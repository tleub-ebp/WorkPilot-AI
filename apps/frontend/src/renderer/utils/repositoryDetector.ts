/**
 * Repository Detection Utilities
 * 
 * Utilities for automatically detecting repository types (GitHub, Azure DevOps, etc.)
 * from existing git repositories.
 */

import type { Project } from '@shared/types';

export interface RepositoryDetectionResult {
  provider: 'github' | 'azure_devops' | 'unknown';
  remoteUrl?: string;
  detectedAt: Date;
}

/**
 * Detect repository provider by reading the .git/config file directly
 * This is more reliable than using git commands as it analyzes the local configuration
 */
export async function detectRepositoryProvider(projectPath: string): Promise<RepositoryDetectionResult> {
  
  try {
    // First try to read the .git/config file directly for more reliable detection
    const gitConfigPath = `${projectPath}/.git/config`;
    
    try {
      const result = await window.electronAPI.invoke('fileExplorer:read', gitConfigPath);
      if (result.success && result.data) {
        const configContent = result.data;

        // Parse the git config file to find remote URLs
        const urlMatches = configContent.match(/url\s*=\s*(.+)/g);
        
        if (urlMatches) {
          for (const match of urlMatches) {
            const url = match.split('=', 2)[1].trim();
            
            // Check for Azure DevOps patterns
            if (url.includes('dev.azure.com') || url.includes('visualstudio.com')) {
              return {
                provider: 'azure_devops',
                remoteUrl: url,
                detectedAt: new Date()
              };
            }
            
            // Check for GitHub patterns
            if (url.includes('github.com')) {
              return {
                provider: 'github',
                remoteUrl: url,
                detectedAt: new Date()
              };
            }
          }
        }
      }
    } catch (_configError) {
    }

    // Fallback to the existing git command approach
    const gitResult = await window.electronAPI.detectRepoProvider(projectPath);

    if (gitResult.success && gitResult.data) {
      return {
        provider: gitResult.data.provider,
        remoteUrl: gitResult.data.remoteUrl,
        detectedAt: new Date()
      };
    }
  } catch (error) {
    console.error('❌ Failed to detect repository provider:', error);
  }
  
  return {
    provider: 'unknown',
    detectedAt: new Date()
  };
}

/**
 * Auto-detect repository type for a project and update its environment configuration
 */
export async function autoDetectAndUpdateProject(project: Project): Promise<{
  success: boolean;
  detection?: RepositoryDetectionResult;
  error?: string;
}> {
  try {
    if (!project.path) {
      return { success: false, error: 'Project path is missing' };
    }

    // First check if it's a git repository
    const gitStatus = await window.electronAPI.checkGitStatus(project.path);
    if (!gitStatus.success || !gitStatus.data?.isGitRepo) {
      return { success: false, error: 'Not a git repository' };
    }

    // Detect the repository provider
    const detection = await detectRepositoryProvider(project.path);
    
    if (detection.provider === 'unknown') {
      return { success: false, error: 'Unknown repository provider' };
    }

    // Update project environment based on detection
    const updates: any = {};
    
    if (detection.provider === 'github') {
      updates.githubEnabled = true;
      updates.azureDevOpsEnabled = false;
      updates.jiraEnabled = false;
    } else if (detection.provider === 'azure_devops') {
      updates.githubEnabled = false;
      updates.azureDevOpsEnabled = true;
      updates.jiraEnabled = false;
    }

    // Store the detection result in environment
    updates.detectedRepositoryProvider = detection;

    // Update the project environment
    const updateResult = await window.electronAPI.updateProjectEnv(project.id, updates);
    
    if (updateResult.success) {
      return { success: true, detection };
    } else {
      return { success: false, error: updateResult.error, detection };
    }
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

/**
 * Check if a project has already been auto-detected
 */
export function hasBeenAutoDetected(project: Project): boolean {
  return !!(project.settings?.provider);
}
