/**
 * Plugin Marketplace IPC Handlers
 *
 * Handles plugin catalog, installation, uninstallation, and management.
 */

import { ipcMain, app } from 'electron';
import { appLog } from '../app-logger';
import * as fs from 'node:fs';
import * as path from 'node:path';
import type { MarketplacePlugin, InstalledPlugin } from '../../shared/types/plugin-marketplace';

// ============================================
// Storage paths
// ============================================

function getPluginDataDir(): string {
  const userDataPath = app.getPath('userData');
  const dir = path.join(userDataPath, 'plugin-marketplace');
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return dir;
}

function getInstalledPluginsPath(): string {
  return path.join(getPluginDataDir(), 'installed-plugins.json');
}

function readInstalledPlugins(): InstalledPlugin[] {
  const filePath = getInstalledPluginsPath();
  if (!fs.existsSync(filePath)) return [];
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch {
    return [];
  }
}

function writeInstalledPlugins(plugins: InstalledPlugin[]): void {
  fs.writeFileSync(getInstalledPluginsPath(), JSON.stringify(plugins, null, 2));
}

// ============================================
// Built-in Plugin Catalog
// ============================================

function buildPluginCatalog(): MarketplacePlugin[] {
  return [
    // === AGENT PLUGINS ===
    {
      id: 'security-auditor-agent',
      name: 'Security Auditor Agent',
      tagline: 'Automated OWASP-compliant security analysis',
      description: 'A specialized AI agent that audits your codebase for OWASP Top 10 vulnerabilities, insecure dependencies, hardcoded secrets, and SQL injection risks. Generates detailed security reports with remediation steps.',
      author: 'WorkPilot Community',
      authorVerified: true,
      type: 'agent',
      icon: 'Shield',
      color: '#ef4444',
      version: '1.2.0',
      downloads: 12400,
      rating: 4.8,
      ratingCount: 312,
      verified: true,
      tags: ['security', 'owasp', 'audit', 'vulnerability', 'agent'],
      agentConfig: {
        systemPrompt: 'You are a security audit specialist. Analyze code for OWASP Top 10 vulnerabilities.',
        tools: ['read_file', 'search_files', 'run_command'],
        triggerKeywords: ['security audit', 'audit code', 'check vulnerabilities'],
      },
      addedAt: '2025-01-15T00:00:00Z',
      updatedAt: '2025-03-01T00:00:00Z',
    },
    {
      id: 'accessibility-agent',
      name: 'Accessibility Agent',
      tagline: 'WCAG 2.1 compliance checker and auto-fixer',
      description: 'Analyzes your UI components for WCAG 2.1 AA compliance. Detects missing ARIA labels, poor color contrast, keyboard navigation issues, and auto-generates fixes.',
      author: 'a11y-community',
      authorVerified: false,
      type: 'agent',
      icon: 'Eye',
      color: '#8b5cf6',
      version: '0.9.1',
      downloads: 5800,
      rating: 4.5,
      ratingCount: 128,
      verified: true,
      tags: ['accessibility', 'wcag', 'a11y', 'ui', 'agent'],
      agentConfig: {
        systemPrompt: 'You are an accessibility expert. Analyze UI code for WCAG 2.1 compliance.',
        tools: ['read_file', 'edit_file'],
        triggerKeywords: ['check accessibility', 'a11y audit', 'wcag check'],
      },
      addedAt: '2025-02-01T00:00:00Z',
      updatedAt: '2025-02-28T00:00:00Z',
    },
    {
      id: 'performance-optimizer-agent',
      name: 'Performance Optimizer Agent',
      tagline: 'Detect and fix performance bottlenecks automatically',
      description: 'Identifies N+1 queries, unnecessary re-renders, memory leaks, and bundle size issues. Provides actionable optimizations with benchmarks.',
      author: 'perf-guild',
      authorVerified: true,
      type: 'agent',
      icon: 'Zap',
      color: '#f59e0b',
      version: '1.0.3',
      downloads: 9200,
      rating: 4.7,
      ratingCount: 204,
      verified: true,
      tags: ['performance', 'optimization', 'profiling', 'agent'],
      agentConfig: {
        systemPrompt: 'You are a performance optimization expert. Find and fix performance issues.',
        tools: ['read_file', 'run_command', 'edit_file'],
        triggerKeywords: ['optimize performance', 'find bottlenecks', 'profile code'],
      },
      addedAt: '2025-01-20T00:00:00Z',
      updatedAt: '2025-03-05T00:00:00Z',
    },
    {
      id: 'i18n-agent',
      name: 'i18n Agent',
      tagline: 'Auto-detect and extract translatable strings',
      description: 'Scans your codebase for hardcoded UI strings, extracts them to i18n translation files, and replaces them with the appropriate translation function calls.',
      author: 'localize-dev',
      authorVerified: false,
      type: 'agent',
      icon: 'Globe',
      color: '#06b6d4',
      version: '1.1.0',
      downloads: 7600,
      rating: 4.6,
      ratingCount: 167,
      verified: false,
      tags: ['i18n', 'localization', 'translation', 'agent'],
      agentConfig: {
        systemPrompt: 'You are an internationalization expert. Extract hardcoded strings to i18n files.',
        tools: ['read_file', 'edit_file', 'create_file'],
        triggerKeywords: ['extract strings', 'i18n scan', 'localize codebase'],
      },
      addedAt: '2025-02-10T00:00:00Z',
      updatedAt: '2025-03-10T00:00:00Z',
    },

    // === INTEGRATION PLUGINS ===
    {
      id: 'slack-integration',
      name: 'Slack Integration',
      tagline: 'Send WorkPilot notifications to Slack channels',
      description: 'Automatically notify your team when tasks complete, QA passes, or builds fail. Configure per-project channels and notification filters.',
      author: 'WorkPilot Community',
      authorVerified: true,
      type: 'integration',
      icon: 'MessageSquare',
      color: '#4a154b',
      version: '2.0.1',
      downloads: 18900,
      rating: 4.9,
      ratingCount: 523,
      verified: true,
      tags: ['slack', 'notifications', 'team', 'integration'],
      integrationConfig: {
        authType: 'apikey',
        requiredEnvVars: [
          { name: 'SLACK_WEBHOOK_URL', label: 'Slack Webhook URL', description: 'Incoming webhook URL from your Slack app', secret: true },
        ],
      },
      addedAt: '2024-12-01T00:00:00Z',
      updatedAt: '2025-03-01T00:00:00Z',
    },
    {
      id: 'notion-integration',
      name: 'Notion Integration',
      tagline: 'Sync tasks and specs to Notion databases',
      description: 'Bi-directional sync between WorkPilot tasks and Notion databases. Automatically create Notion pages from specs and update them as work progresses.',
      author: 'notion-tools',
      authorVerified: false,
      type: 'integration',
      icon: 'FileText',
      color: '#000000',
      version: '1.3.0',
      downloads: 11200,
      rating: 4.4,
      ratingCount: 289,
      verified: true,
      tags: ['notion', 'sync', 'docs', 'integration'],
      integrationConfig: {
        authType: 'apikey',
        requiredEnvVars: [
          { name: 'NOTION_API_KEY', label: 'Notion API Key', description: 'Internal integration token from Notion', secret: true },
          { name: 'NOTION_DATABASE_ID', label: 'Database ID', description: 'The Notion database ID to sync to', secret: false },
        ],
      },
      addedAt: '2025-01-05T00:00:00Z',
      updatedAt: '2025-02-20T00:00:00Z',
    },
    {
      id: 'datadog-integration',
      name: 'Datadog Integration',
      tagline: 'Monitor deployments and track agent metrics',
      description: 'Send WorkPilot agent metrics, task durations, and error rates to Datadog dashboards. Track the ROI of your AI-assisted development.',
      author: 'devops-plugins',
      authorVerified: true,
      type: 'integration',
      icon: 'BarChart3',
      color: '#632ca6',
      version: '1.0.0',
      downloads: 4300,
      rating: 4.3,
      ratingCount: 87,
      verified: false,
      tags: ['datadog', 'monitoring', 'metrics', 'devops', 'integration'],
      integrationConfig: {
        authType: 'apikey',
        requiredEnvVars: [
          { name: 'DATADOG_API_KEY', label: 'Datadog API Key', description: 'Your Datadog API key', secret: true },
          { name: 'DATADOG_APP_KEY', label: 'Datadog App Key', description: 'Your Datadog application key', secret: true },
        ],
      },
      addedAt: '2025-02-15T00:00:00Z',
      updatedAt: '2025-03-08T00:00:00Z',
    },

    // === SPEC TEMPLATE PLUGINS ===
    {
      id: 'rest-api-spec-template',
      name: 'REST API Spec Template',
      tagline: 'Production-ready REST API specification template',
      description: 'Comprehensive spec template for building REST APIs with authentication, CRUD operations, error handling, validation, pagination, and OpenAPI documentation.',
      author: 'spec-masters',
      authorVerified: true,
      type: 'spec-template',
      icon: 'Code',
      color: '#10b981',
      version: '3.1.0',
      downloads: 22100,
      rating: 4.9,
      ratingCount: 678,
      verified: true,
      tags: ['rest', 'api', 'backend', 'openapi', 'spec'],
      templateContent: '# REST API Specification\n\n## Endpoints\n...',
      addedAt: '2024-11-15T00:00:00Z',
      updatedAt: '2025-03-01T00:00:00Z',
    },
    {
      id: 'react-component-spec-template',
      name: 'React Component Library Spec',
      tagline: 'Spec template for building React component libraries',
      description: 'Complete template for React component library development: design tokens, Storybook stories, accessibility requirements, unit tests, and documentation.',
      author: 'frontend-guild',
      authorVerified: false,
      type: 'spec-template',
      icon: 'Layers',
      color: '#61dafb',
      version: '2.0.0',
      downloads: 15400,
      rating: 4.7,
      ratingCount: 341,
      verified: true,
      tags: ['react', 'components', 'frontend', 'storybook', 'spec'],
      templateContent: '# React Component Library\n\n## Component Requirements\n...',
      addedAt: '2025-01-10T00:00:00Z',
      updatedAt: '2025-02-25T00:00:00Z',
    },
    {
      id: 'microservice-spec-template',
      name: 'Microservice Architecture Spec',
      tagline: 'Production-grade microservice spec with all the trimmings',
      description: 'Full-stack microservice spec covering Docker, Kubernetes manifests, health checks, distributed tracing, circuit breakers, and service mesh configuration.',
      author: 'cloud-native-devs',
      authorVerified: true,
      type: 'spec-template',
      icon: 'GitBranch',
      color: '#326ce5',
      version: '1.5.0',
      downloads: 8900,
      rating: 4.6,
      ratingCount: 195,
      verified: true,
      tags: ['microservice', 'docker', 'kubernetes', 'cloud', 'spec'],
      templateContent: '# Microservice Specification\n\n## Architecture\n...',
      addedAt: '2025-01-25T00:00:00Z',
      updatedAt: '2025-03-10T00:00:00Z',
    },

    // === THEME PLUGINS ===
    {
      id: 'cyberpunk-theme',
      name: 'Cyberpunk 2077',
      tagline: 'Neon-soaked cyberpunk aesthetic',
      description: "A vibrant cyberpunk theme with neon cyan and magenta accents, dark grid backgrounds, and futuristic UI elements. Perfect for late-night coding sessions.",
      author: 'theme-forge',
      authorVerified: false,
      type: 'theme',
      icon: 'Palette',
      color: '#00ffff',
      version: '1.0.0',
      downloads: 31200,
      rating: 4.8,
      ratingCount: 892,
      verified: false,
      tags: ['theme', 'cyberpunk', 'neon', 'dark'],
      themeData: {
        '--color-primary': '#00ffff',
        '--color-accent': '#ff00ff',
        '--color-background': '#0a0a1a',
      },
      addedAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-02-15T00:00:00Z',
    },
    {
      id: 'github-dark-theme',
      name: 'GitHub Dark Dimmed',
      tagline: "Faithful recreation of GitHub's dark dimmed theme",
      description: 'The beloved GitHub Dark Dimmed color scheme, faithfully recreated for WorkPilot AI. Easy on the eyes with muted blues and subtle contrasts.',
      author: 'github-fans',
      authorVerified: false,
      type: 'theme',
      icon: 'Moon',
      color: '#316dca',
      version: '1.2.0',
      downloads: 28400,
      rating: 4.9,
      ratingCount: 1124,
      verified: false,
      tags: ['theme', 'github', 'dark', 'dimmed'],
      themeData: {
        '--color-primary': '#316dca',
        '--color-background': '#22272e',
      },
      addedAt: '2024-12-15T00:00:00Z',
      updatedAt: '2025-03-01T00:00:00Z',
    },
    {
      id: 'solarized-light-theme',
      name: 'Solarized Light',
      tagline: 'The timeless Solarized Light color scheme',
      description: "Ethan Schoonover's iconic Solarized Light palette adapted for WorkPilot AI. Scientifically designed for reduced eye strain during day coding.",
      author: 'solarized-community',
      authorVerified: false,
      type: 'theme',
      icon: 'Sun',
      color: '#b58900',
      version: '1.1.0',
      downloads: 19700,
      rating: 4.6,
      ratingCount: 445,
      verified: false,
      tags: ['theme', 'solarized', 'light', 'classic'],
      themeData: {
        '--color-primary': '#b58900',
        '--color-background': '#fdf6e3',
      },
      addedAt: '2025-01-05T00:00:00Z',
      updatedAt: '2025-02-20T00:00:00Z',
    },

    // === CUSTOM PROMPT PLUGINS ===
    {
      id: 'senior-code-reviewer-prompt',
      name: 'Senior Code Reviewer',
      tagline: "Code review prompts from a 10x senior engineer",
      description: "A curated set of code review prompts that simulate a senior engineer's perspective: performance, maintainability, security, DRY principles, and architectural concerns.",
      author: 'prompt-labs',
      authorVerified: true,
      type: 'custom-prompt',
      icon: 'Search',
      color: '#f97316',
      version: '2.3.0',
      downloads: 25600,
      rating: 4.9,
      ratingCount: 734,
      verified: true,
      tags: ['code-review', 'prompts', 'senior', 'quality'],
      promptContent: 'Review this code as a senior engineer with 10+ years of experience...',
      addedAt: '2025-01-10T00:00:00Z',
      updatedAt: '2025-03-05T00:00:00Z',
    },
    {
      id: 'tdd-prompt-pack',
      name: 'TDD Prompt Pack',
      tagline: 'Drive development with Test-Driven Design prompts',
      description: 'A comprehensive prompt pack for practicing strict TDD: red-green-refactor cycles, property-based testing, boundary analysis, and mutation testing strategies.',
      author: 'tdd-zealots',
      authorVerified: false,
      type: 'custom-prompt',
      icon: 'TestTube',
      color: '#22c55e',
      version: '1.4.0',
      downloads: 13800,
      rating: 4.7,
      ratingCount: 312,
      verified: true,
      tags: ['tdd', 'testing', 'prompts', 'quality'],
      promptContent: 'Write failing tests first before implementing any code...',
      addedAt: '2025-01-20T00:00:00Z',
      updatedAt: '2025-02-28T00:00:00Z',
    },
    {
      id: 'ddd-architecture-prompt',
      name: 'DDD Architecture Advisor',
      tagline: 'Domain-Driven Design guidance and refactoring prompts',
      description: 'Expert prompts for applying Domain-Driven Design patterns: bounded contexts, aggregates, value objects, domain events, and CQRS. Includes refactoring from CRUD to DDD.',
      author: 'ddd-community',
      authorVerified: true,
      type: 'custom-prompt',
      icon: 'Layers',
      color: '#6366f1',
      version: '1.1.0',
      downloads: 9400,
      rating: 4.8,
      ratingCount: 198,
      verified: false,
      tags: ['ddd', 'architecture', 'prompts', 'patterns'],
      promptContent: 'Analyze this code through a Domain-Driven Design lens...',
      addedAt: '2025-02-05T00:00:00Z',
      updatedAt: '2025-03-08T00:00:00Z',
    },
  ];
}

// ============================================
// IPC Handler Registration
// ============================================

export function registerPluginMarketplaceHandlers(): void {
  // Get full plugin catalog
  ipcMain.handle('pluginMarketplace:getCatalog', async () => {
    try {
      const catalog = buildPluginCatalog();
      return { success: true, data: catalog };
    } catch (error) {
      appLog.error('[Plugin Marketplace] Failed to get catalog');
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  // Get installed plugins
  ipcMain.handle('pluginMarketplace:getInstalled', async () => {
    try {
      const installed = readInstalledPlugins();
      return { success: true, data: installed };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  });

  // Install a plugin
  ipcMain.handle('pluginMarketplace:install', async (_event, { pluginId, config }: { pluginId: string; config?: Record<string, string> }) => {
    try {
      const catalog = buildPluginCatalog();
      const plugin = catalog.find(p => p.id === pluginId);
      if (!plugin) {
        return { success: false, error: `Plugin '${pluginId}' not found in catalog` };
      }

      const installed = readInstalledPlugins();
      const existing = installed.find(p => p.pluginId === pluginId);
      if (existing) {
        return { success: false, error: 'Plugin is already installed' };
      }

      const newInstall: InstalledPlugin = {
        pluginId: plugin.id,
        name: plugin.name,
        version: plugin.version,
        type: plugin.type,
        enabled: true,
        installedAt: new Date().toISOString(),
        config: config || {},
      };

      installed.push(newInstall);
      writeInstalledPlugins(installed);

      appLog.info(`[Plugin Marketplace] Installed plugin: ${plugin.name}`);
      return { success: true, data: newInstall };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Installation failed' };
    }
  });

  // Uninstall a plugin
  ipcMain.handle('pluginMarketplace:uninstall', async (_event, { pluginId }: { pluginId: string }) => {
    try {
      const installed = readInstalledPlugins();
      const filtered = installed.filter(p => p.pluginId !== pluginId);
      writeInstalledPlugins(filtered);
      appLog.info(`[Plugin Marketplace] Uninstalled plugin: ${pluginId}`);
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Uninstall failed' };
    }
  });

  // Toggle plugin enabled/disabled
  ipcMain.handle('pluginMarketplace:toggle', async (_event, { pluginId, enabled }: { pluginId: string; enabled: boolean }) => {
    try {
      const installed = readInstalledPlugins();
      const idx = installed.findIndex(p => p.pluginId === pluginId);
      if (idx === -1) {
        return { success: false, error: 'Plugin not found' };
      }
      installed[idx].enabled = enabled;
      writeInstalledPlugins(installed);
      return { success: true };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Toggle failed' };
    }
  });

  // Scaffold a new plugin on disk
  ipcMain.handle('pluginMarketplace:create', async (_event, data: {
    type: string;
    id: string;
    name: string;
    description: string;
    version: string;
    systemPrompt?: string;
    triggerKeywords?: string;
    authType?: string;
    apiEndpoint?: string;
    primaryColor?: string;
    backgroundColor?: string;
    templateContent?: string;
  }) => {
    try {
      const pluginsDir = path.join(getPluginDataDir(), 'local', data.id);
      if (fs.existsSync(pluginsDir)) {
        return { success: false, error: `A plugin with ID "${data.id}" already exists` };
      }
      fs.mkdirSync(pluginsDir, { recursive: true });

      // Build config object
      const config: Record<string, unknown> = {
        id: data.id,
        name: data.name,
        type: data.type,
        version: data.version,
        description: data.description,
      };

      if (data.type === 'agent') {
        config.systemPrompt = data.systemPrompt || '';
        if (data.triggerKeywords?.trim()) {
          config.triggers = data.triggerKeywords.split(',').map(k => k.trim()).filter(Boolean);
        }
      } else if (data.type === 'integration') {
        config.authType = data.authType || 'none';
        if (data.apiEndpoint) config.apiEndpoint = data.apiEndpoint;
      } else if (data.type === 'theme') {
        config.themeData = {
          '--color-primary': data.primaryColor || '#8b5cf6',
          '--color-background': data.backgroundColor || '#0a0a1a',
        };
      } else if (data.type === 'spec-template' || data.type === 'custom-prompt') {
        config.content = data.templateContent || '';
      }

      // Write plugin.config.json
      const configPath = path.join(pluginsDir, 'plugin.config.json');
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2));

      // Write a README
      const readme = `# ${data.name}\n\n${data.description}\n\n## Type\n\n\`${data.type}\`\n\n## Version\n\n\`${data.version}\`\n`;
      fs.writeFileSync(path.join(pluginsDir, 'README.md'), readme);

      // Register in local.json for auto-loading
      const localJsonPath = path.join(getPluginDataDir(), 'local.json');
      let localConfig: { localPlugins: Array<{ path: string; enabled: boolean }> } = { localPlugins: [] };
      if (fs.existsSync(localJsonPath)) {
        try {
          localConfig = JSON.parse(fs.readFileSync(localJsonPath, 'utf-8'));
        } catch { /* use default */ }
      }
      if (!localConfig.localPlugins.some(p => p.path === pluginsDir)) {
        localConfig.localPlugins.push({ path: pluginsDir, enabled: true });
      }
      fs.writeFileSync(localJsonPath, JSON.stringify(localConfig, null, 2));

      appLog.info(`[Plugin Marketplace] Created plugin: ${data.name} at ${pluginsDir}`);
      return { success: true, data: { path: pluginsDir } };
    } catch (error) {
      appLog.error(`[Plugin Marketplace] Failed to create plugin: ${error}`);
      return { success: false, error: error instanceof Error ? error.message : 'Failed to create plugin' };
    }
  });
}
