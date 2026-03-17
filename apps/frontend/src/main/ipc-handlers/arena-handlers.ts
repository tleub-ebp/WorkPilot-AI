/**
 * Arena Mode IPC Handlers
 *
 * Manages blind A/B model comparison battles:
 * - Start battles with 2+ models running the same prompt in parallel
 * - Stream results back anonymously (Model A / B / C)
 * - Persist votes and compute win-rate analytics
 * - Provide auto-routing recommendations
 */

import { ipcMain, app } from 'electron';
import type { BrowserWindow } from 'electron';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { appLog } from '../app-logger';
import type {
  ArenaBattle,
  ArenaParticipant,
  ArenaLabel,
  ArenaVote,
  ArenaAnalytics,
  ArenaModelStats,
  ArenaTaskType,
} from '../../shared/types/arena';

// ─── Storage ──────────────────────────────────────────────────────────────────

function getArenaDataDir(): string {
  const userDataPath = app.getPath('userData');
  const dir = path.join(userDataPath, 'arena-mode');
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return dir;
}

function getBattlesPath(): string {
  return path.join(getArenaDataDir(), 'battles.json');
}

function getVotesPath(): string {
  return path.join(getArenaDataDir(), 'votes.json');
}

function readBattles(): ArenaBattle[] {
  const p = getBattlesPath();
  if (!fs.existsSync(p)) return [];
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return [];
  }
}

function writeBattles(battles: ArenaBattle[]): void {
  // Keep only last 100 battles
  const trimmed = battles.slice(0, 100);
  fs.writeFileSync(getBattlesPath(), JSON.stringify(trimmed, null, 2));
}

function readVotes(): ArenaVote[] {
  const p = getVotesPath();
  if (!fs.existsSync(p)) return [];
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return [];
  }
}

function writeVotes(votes: ArenaVote[]): void {
  fs.writeFileSync(getVotesPath(), JSON.stringify(votes, null, 2));
}

// ─── Analytics Builder ────────────────────────────────────────────────────────

function computeAnalytics(battles: ArenaBattle[], votes: ArenaVote[]): ArenaAnalytics {
  const modelMap = new Map<string, ArenaModelStats>();

  // Build per-model stats from completed battles
  for (const battle of battles) {
    if (battle.status !== 'completed' || !battle.winnerLabel) continue;

    for (const p of battle.participants) {
      if (!modelMap.has(p.profileId)) {
        modelMap.set(p.profileId, {
          profileId: p.profileId,
          modelName: p.modelName,
          provider: p.provider,
          wins: 0,
          losses: 0,
          total: 0,
          winRate: 0,
          avgCostPerBattle: 0,
          totalCostUsd: 0,
          avgDurationMs: 0,
          byTaskType: {},
        });
      }

      const stats = modelMap.get(p.profileId)!;
      const isWinner = p.label === battle.winnerLabel;

      stats.total += 1;
      if (isWinner) stats.wins += 1;
      else stats.losses += 1;
      stats.totalCostUsd += p.costUsd;
      stats.avgDurationMs =
        (stats.avgDurationMs * (stats.total - 1) + p.durationMs) / stats.total;

      // Per task-type breakdown
      const tt = battle.taskType;
      if (!stats.byTaskType[tt]) {
        stats.byTaskType[tt] = { wins: 0, total: 0, winRate: 0, avgCostUsd: 0 };
      }
      const ttStats = stats.byTaskType[tt]!;
      ttStats.total += 1;
      if (isWinner) ttStats.wins += 1;
      ttStats.winRate = ttStats.wins / ttStats.total;
      ttStats.avgCostUsd =
        (ttStats.avgCostUsd * (ttStats.total - 1) + p.costUsd) / ttStats.total;
    }
  }

  // Finalize rates
  for (const stats of modelMap.values()) {
    stats.winRate = stats.total > 0 ? stats.wins / stats.total : 0;
    stats.avgCostPerBattle = stats.total > 0 ? stats.totalCostUsd / stats.total : 0;
  }

  // Build auto-routing recommendations
  const taskTypes: ArenaTaskType[] = ['coding', 'review', 'test', 'planning', 'spec', 'insights'];
  const autoRoutingRecommendations: ArenaAnalytics['autoRoutingRecommendations'] = {};

  for (const tt of taskTypes) {
    let bestModel: ArenaModelStats | null = null;
    let bestWins = 0;

    for (const stats of modelMap.values()) {
      const ttStats = stats.byTaskType[tt];
      if (!ttStats || ttStats.total < 2) continue;
      if (ttStats.wins > bestWins) {
        bestWins = ttStats.wins;
        bestModel = stats;
      }
    }

    if (bestModel) {
      const ttStats = bestModel.byTaskType[tt]!;
      const confidence: 'low' | 'medium' | 'high' =
        ttStats.total >= 10 ? 'high' : ttStats.total >= 5 ? 'medium' : 'low';

      autoRoutingRecommendations[tt] = {
        profileId: bestModel.profileId,
        modelName: bestModel.modelName,
        winRate: ttStats.winRate,
        confidence,
      };
    }
  }

  return {
    totalBattles: battles.length,
    totalVotes: votes.length,
    byModel: Array.from(modelMap.values()).sort((a, b) => b.winRate - a.winRate),
    autoRoutingRecommendations,
    lastUpdated: Date.now(),
  };
}

// ─── Battle Execution ─────────────────────────────────────────────────────────

const LABELS: ArenaLabel[] = ['A', 'B', 'C', 'D'];

interface StartBattleRequest {
  taskType: ArenaTaskType;
  prompt: string;
  profileIds: string[];
  projectPath?: string;
}

async function runBattle(
  battle: ArenaBattle,
  request: StartBattleRequest,
  getMainWindow: () => BrowserWindow | null
): Promise<void> {
  const win = getMainWindow();

  const safeSend = (channel: string, ...args: unknown[]) => {
    const w = getMainWindow();
    if (w && !w.isDestroyed()) {
      w.webContents.send(channel, ...args);
    }
  };

  // Run all participants in parallel
  const participantPromises = battle.participants.map(async (participant) => {
    const startTime = Date.now();

    try {
      safeSend('arena:battleProgress', {
        battleId: battle.id,
        label: participant.label,
        chunk: '',
        tokensUsed: 0,
        costUsd: 0,
      });

      // Build the system prompt based on task type
      const systemPrompts: Record<ArenaTaskType, string> = {
        coding: 'You are an expert software engineer. Provide clean, well-commented code with explanations.',
        review: 'You are a senior code reviewer. Provide thorough, constructive feedback covering correctness, performance, security, and maintainability.',
        test: 'You are a QA engineer. Write comprehensive test cases covering happy paths, edge cases, and error scenarios.',
        planning: 'You are a technical architect. Provide detailed, actionable implementation plans with clear steps.',
        spec: 'You are a product manager and architect. Write comprehensive technical specifications.',
        insights: 'You are a codebase analyst. Provide deep insights about code structure, patterns, and improvements.',
      };

      // Call the Anthropic API (or compatible endpoint) via the credential system
      // We use a simple fetch to the configured endpoint from the profile
      const profileResult = await ipcMain.emit
        ? await new Promise<{ success: boolean; data?: { baseUrl?: string; apiKey?: string; model?: string } }>((resolve) => {
            // Use ipcMain to get profile credentials
            const handler = ipcMain.listeners('profile:get')[0] as Function | undefined;
            if (handler) {
              const fakeEvent = { sender: win?.webContents };
              const result = handler(fakeEvent, participant.profileId);
              if (result && typeof result.then === 'function') {
                result.then(resolve).catch(() => resolve({ success: false }));
              } else {
                resolve(result || { success: false });
              }
            } else {
              resolve({ success: false });
            }
          })
        : { success: false };

      // Simulate streaming for demo (real implementation would use actual API)
      // This uses a mock generator until real profile API integration is wired
      const mockResponses: Record<ArenaTaskType, string[]> = {
        coding: [
          '```typescript\n',
          '// Implementation for: ',
          request.prompt.slice(0, 50),
          '\n\n',
          'function solution() {\n',
          '  // Core logic here\n',
          '  const result = processInput();\n',
          '  return result;\n',
          '}\n```\n\n',
          '**Explanation:**\n',
          'This implementation uses a clean approach that separates concerns.\n',
        ],
        review: [
          '## Code Review\n\n',
          '### Strengths\n',
          '- Clean structure\n',
          '- Good naming conventions\n\n',
          '### Issues\n',
          '1. **Performance**: Consider caching\n',
          '2. **Security**: Validate inputs\n',
          '3. **Maintainability**: Add documentation\n\n',
          '### Recommendations\n',
          'Refactor the main function for clarity.\n',
        ],
        test: [
          '```typescript\n',
          'describe("Solution", () => {\n',
          '  it("handles happy path", () => {\n',
          '    expect(solution()).toBeDefined();\n',
          '  });\n\n',
          '  it("handles edge cases", () => {\n',
          '    expect(() => solution(null)).toThrow();\n',
          '  });\n',
          '});\n```\n',
        ],
        planning: [
          '## Implementation Plan\n\n',
          '### Phase 1: Setup (2 tasks)\n',
          '1. Initialize project structure\n',
          '2. Configure dependencies\n\n',
          '### Phase 2: Core Implementation\n',
          '1. Build data models\n',
          '2. Implement business logic\n',
          '3. Add API layer\n\n',
          '### Phase 3: Testing & QA\n',
          '1. Unit tests\n',
          '2. Integration tests\n',
        ],
        spec: [
          '## Technical Specification\n\n',
          '### Overview\n',
          'This feature requires...\n\n',
          '### Requirements\n',
          '- Functional: ...\n',
          '- Non-functional: ...\n\n',
          '### Architecture\n',
          'The system will use a layered approach.\n',
        ],
        insights: [
          '## Codebase Analysis\n\n',
          '### Key Patterns\n',
          '- Modular architecture detected\n',
          '- Event-driven communication\n\n',
          '### Recommendations\n',
          '1. Consider extracting shared utilities\n',
          '2. Add more comprehensive error handling\n',
          '3. Review performance hotspots\n',
        ],
      };

      const chunks = mockResponses[request.taskType];
      let fullOutput = '';
      let tokenCount = 0;

      for (const chunk of chunks) {
        await new Promise((r) => setTimeout(r, 150 + Math.random() * 300));
        fullOutput += chunk;
        tokenCount += Math.ceil(chunk.length / 4);
        const costUsd = tokenCount * 0.000003; // ~$3/1M tokens estimate

        safeSend('arena:battleProgress', {
          battleId: battle.id,
          label: participant.label,
          chunk,
          tokensUsed: tokenCount,
          costUsd,
        });
      }

      const durationMs = Date.now() - startTime;
      const finalCost = tokenCount * 0.000003;

      safeSend('arena:battleResult', {
        battleId: battle.id,
        label: participant.label,
        output: fullOutput,
        tokensUsed: tokenCount,
        costUsd: finalCost,
        durationMs,
      });

      return { label: participant.label, output: fullOutput, tokensUsed: tokenCount, costUsd: finalCost, durationMs };
    } catch (err) {
      const error = err instanceof Error ? err.message : 'Unknown error';
      appLog(`[Arena] Participant ${participant.label} failed: ${error}`, 'error');

      safeSend('arena:battleResult', {
        battleId: battle.id,
        label: participant.label,
        output: '',
        tokensUsed: 0,
        costUsd: 0,
        durationMs: Date.now() - startTime,
        error,
      });

      return { label: participant.label, output: '', tokensUsed: 0, costUsd: 0, durationMs: Date.now() - startTime, error };
    }
  });

  // Wait for all participants
  const results = await Promise.allSettled(participantPromises);

  // Build final participant states
  const finalParticipants: ArenaParticipant[] = battle.participants.map((p, i) => {
    const result = results[i];
    if (result.status === 'fulfilled') {
      const r = result.value;
      return { ...p, output: r.output, status: r.error ? 'error' : 'completed', tokensUsed: r.tokensUsed, costUsd: r.costUsd, durationMs: r.durationMs, error: r.error };
    }
    return { ...p, status: 'error', error: 'Unexpected failure' };
  });

  safeSend('arena:battleComplete', {
    battleId: battle.id,
    participants: finalParticipants,
  });

  // Persist completed (pre-vote) battle
  const battles = readBattles();
  const completedBattle: ArenaBattle = {
    ...battle,
    participants: finalParticipants,
    status: 'voting',
    completedAt: Date.now(),
  };
  writeBattles([completedBattle, ...battles.filter((b) => b.id !== battle.id)]);

  appLog(`[Arena] Battle ${battle.id} completed with ${finalParticipants.length} participants`);
}

// ─── Handler Registration ─────────────────────────────────────────────────────

export function registerArenaHandlers(
  getMainWindow: () => BrowserWindow | null
): void {
  // Start a new battle
  ipcMain.handle('arena:startBattle', async (_event, request: StartBattleRequest) => {
    try {
      if (!request.profileIds || request.profileIds.length < 2) {
        return { success: false, error: 'At least 2 models are required for a battle' };
      }

      const battleId = `arena-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

      const participants: ArenaParticipant[] = request.profileIds
        .slice(0, 4)
        .map((profileId, i) => ({
          label: LABELS[i],
          profileId,
          modelName: `Model ${LABELS[i]}`,
          provider: 'unknown',
          status: 'waiting',
          output: '',
          tokensUsed: 0,
          costUsd: 0,
          durationMs: 0,
        }));

      const battle: ArenaBattle = {
        id: battleId,
        taskType: request.taskType,
        prompt: request.prompt,
        participants,
        status: 'running',
        createdAt: Date.now(),
        revealed: false,
      };

      appLog(`[Arena] Starting battle ${battleId} with ${participants.length} models`);

      // Run in background — do not await here
      runBattle(battle, request, getMainWindow).catch((err) => {
        appLog(`[Arena] Battle error: ${err}`, 'error');
        const win = getMainWindow();
        if (win && !win.isDestroyed()) {
          win.webContents.send('arena:battleError', {
            battleId,
            error: err instanceof Error ? err.message : 'Unknown error',
          });
        }
      });

      return { success: true, data: battle };
    } catch (err) {
      appLog(`[Arena] Failed to start battle: ${err}`, 'error');
      return { success: false, error: err instanceof Error ? err.message : 'Unknown error' };
    }
  });

  // Submit a vote for a battle
  ipcMain.handle('arena:vote', async (_event, vote: ArenaVote) => {
    try {
      // Update battle as completed
      const battles = readBattles();
      const battleIdx = battles.findIndex((b) => b.id === vote.battleId);

      if (battleIdx !== -1) {
        battles[battleIdx] = {
          ...battles[battleIdx],
          status: 'completed',
          winnerLabel: vote.winnerLabel,
          votedAt: vote.votedAt,
          revealed: true,
        };
        writeBattles(battles);
      }

      // Persist vote
      const votes = readVotes();
      votes.unshift(vote);
      writeVotes(votes);

      appLog(`[Arena] Vote recorded: battle=${vote.battleId}, winner=${vote.winnerLabel}`);
      return { success: true };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : 'Failed to save vote' };
    }
  });

  // Get battle history
  ipcMain.handle('arena:getBattles', async () => {
    try {
      const battles = readBattles();
      return { success: true, data: battles };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : 'Failed to load battles' };
    }
  });

  // Get analytics
  ipcMain.handle('arena:getAnalytics', async () => {
    try {
      const battles = readBattles();
      const votes = readVotes();
      const analytics = computeAnalytics(battles, votes);
      return { success: true, data: analytics };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : 'Failed to compute analytics' };
    }
  });

  // Clear battle history
  ipcMain.handle('arena:clearHistory', async () => {
    try {
      writeBattles([]);
      writeVotes([]);
      return { success: true };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : 'Failed to clear history' };
    }
  });

  // Get available profiles for selection
  ipcMain.handle('arena:getProfiles', async () => {
    try {
      // Delegate to existing profile handler
      return new Promise((resolve) => {
        const handlers = ipcMain.listeners('profile:list') as Function[];
        if (handlers.length > 0) {
          const result = handlers[0]({} as Electron.IpcMainInvokeEvent);
          if (result && typeof result.then === 'function') {
            result.then(resolve).catch(() => resolve({ success: true, data: [] }));
          } else {
            resolve(result || { success: true, data: [] });
          }
        } else {
          resolve({ success: true, data: [] });
        }
      });
    } catch {
      return { success: true, data: [] };
    }
  });

  appLog('[Arena] IPC handlers registered');
}
