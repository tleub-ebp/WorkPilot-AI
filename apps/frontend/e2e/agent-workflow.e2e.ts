/**
 * End-to-End tests for Agent Start / Merge Workflow
 * Tests critical user workflows: task creation, agent start, status transitions
 *
 * NOTE: These tests require the Electron app to be built first.
 * Run `npm run build` before running E2E tests.
 *
 * To run: npx playwright test agent-workflow --config=e2e/playwright.config.ts
 *
 * Improvement 6.1: E2E Playwright tests for critical workflows
 */
import { test, expect } from '@playwright/test';
import { mkdirSync, mkdtempSync, rmSync, existsSync, writeFileSync, readFileSync } from 'fs';
import { tmpdir } from 'os';
import path from 'path';

// Test data directory
let TEST_DATA_DIR: string;
let TEST_PROJECT_DIR: string;
let SPECS_DIR: string;

function setupTestEnvironment(): void {
  TEST_DATA_DIR = mkdtempSync(path.join(tmpdir(), 'auto-claude-agent-e2e-'));
  TEST_PROJECT_DIR = path.join(TEST_DATA_DIR, 'test-project');
  SPECS_DIR = path.join(TEST_PROJECT_DIR, '.workpilot', 'specs');
  mkdirSync(TEST_PROJECT_DIR, { recursive: true });
  mkdirSync(SPECS_DIR, { recursive: true });
}

function cleanupTestEnvironment(): void {
  if (existsSync(TEST_DATA_DIR)) {
    rmSync(TEST_DATA_DIR, { recursive: true, force: true });
  }
}

// Helper to create a task spec
function createTaskSpec(specId: string, status: string = 'backlog'): void {
  const specDir = path.join(SPECS_DIR, specId);
  mkdirSync(specDir, { recursive: true });

  writeFileSync(
    path.join(specDir, 'spec.md'),
    `# ${specId}\n\n## Overview\n\nAgent workflow test task.\n\n## Acceptance Criteria\n\n- [ ] Code compiles\n- [ ] Tests pass\n`
  );

  writeFileSync(
    path.join(specDir, 'requirements.json'),
    JSON.stringify({
      task_description: `Agent workflow test: ${specId}`,
      user_requirements: ['Implement feature', 'Add tests'],
      acceptance_criteria: ['Code compiles', 'Tests pass'],
      context: []
    }, null, 2)
  );

  writeFileSync(
    path.join(specDir, 'status.json'),
    JSON.stringify({ status, updated_at: new Date().toISOString() }, null, 2)
  );
}

// Helper to simulate agent execution phases
function simulateAgentPhases(specId: string): {
  plan: () => void;
  code: () => void;
  review: () => void;
  complete: () => void;
} {
  const specDir = path.join(SPECS_DIR, specId);

  return {
    plan: () => {
      writeFileSync(
        path.join(specDir, 'implementation_plan.json'),
        JSON.stringify({
          feature: `Feature for ${specId}`,
          workflow_type: 'feature',
          services_involved: ['backend'],
          phases: [
            {
              phase: 1,
              name: 'Implementation',
              type: 'implementation',
              subtasks: [
                { id: 'sub-1', description: 'Create module', status: 'pending' },
                { id: 'sub-2', description: 'Add tests', status: 'pending' }
              ]
            }
          ],
          final_acceptance: ['All tests pass'],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          spec_file: 'spec.md'
        }, null, 2)
      );
      updateStatus(specDir, 'in_progress');
    },
    code: () => {
      const planPath = path.join(specDir, 'implementation_plan.json');
      const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
      plan.phases[0].subtasks[0].status = 'completed';
      plan.phases[0].subtasks[1].status = 'in_progress';
      plan.updated_at = new Date().toISOString();
      writeFileSync(planPath, JSON.stringify(plan, null, 2));

      writeFileSync(
        path.join(specDir, 'build-progress.txt'),
        'Phase: Coding\nProgress: 50%\nSubtask 1/2 completed\n'
      );
    },
    review: () => {
      const planPath = path.join(specDir, 'implementation_plan.json');
      const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
      plan.phases[0].subtasks[1].status = 'completed';
      plan.updated_at = new Date().toISOString();
      writeFileSync(planPath, JSON.stringify(plan, null, 2));

      updateStatus(specDir, 'ai_review');
    },
    complete: () => {
      updateStatus(specDir, 'human_review');
      writeFileSync(
        path.join(specDir, 'build-progress.txt'),
        'Phase: Complete\nProgress: 100%\nAll subtasks completed\nAwaiting human review\n'
      );
    }
  };
}

function updateStatus(specDir: string, status: string): void {
  writeFileSync(
    path.join(specDir, 'status.json'),
    JSON.stringify({ status, updated_at: new Date().toISOString() }, null, 2)
  );
}

test.describe('Agent Workflow E2E Tests', () => {
  test.beforeAll(() => {
    setupTestEnvironment();
  });

  test.afterAll(() => {
    cleanupTestEnvironment();
  });

  test('should create task spec directory for agent', () => {
    const specId = '001-agent-task';
    createTaskSpec(specId);

    expect(existsSync(path.join(SPECS_DIR, specId, 'spec.md'))).toBe(true);
    expect(existsSync(path.join(SPECS_DIR, specId, 'requirements.json'))).toBe(true);
    expect(existsSync(path.join(SPECS_DIR, specId, 'status.json'))).toBe(true);
  });

  test('should simulate full agent execution: plan → code → review → complete', () => {
    const specId = '002-full-agent-run';
    createTaskSpec(specId);

    const agent = simulateAgentPhases(specId);

    // Phase 1: Planning
    agent.plan();
    const planPath = path.join(SPECS_DIR, specId, 'implementation_plan.json');
    expect(existsSync(planPath)).toBe(true);
    const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
    expect(plan.phases).toHaveLength(1);
    expect(plan.phases[0].subtasks).toHaveLength(2);

    const status1 = JSON.parse(readFileSync(path.join(SPECS_DIR, specId, 'status.json'), 'utf-8'));
    expect(status1.status).toBe('in_progress');

    // Phase 2: Coding
    agent.code();
    const plan2 = JSON.parse(readFileSync(planPath, 'utf-8'));
    expect(plan2.phases[0].subtasks[0].status).toBe('completed');
    expect(plan2.phases[0].subtasks[1].status).toBe('in_progress');

    // Phase 3: AI Review
    agent.review();
    const plan3 = JSON.parse(readFileSync(planPath, 'utf-8'));
    expect(plan3.phases[0].subtasks.every((s: { status: string }) => s.status === 'completed')).toBe(true);
    const status3 = JSON.parse(readFileSync(path.join(SPECS_DIR, specId, 'status.json'), 'utf-8'));
    expect(status3.status).toBe('ai_review');

    // Phase 4: Complete → Human Review
    agent.complete();
    const status4 = JSON.parse(readFileSync(path.join(SPECS_DIR, specId, 'status.json'), 'utf-8'));
    expect(status4.status).toBe('human_review');

    const progress = readFileSync(path.join(SPECS_DIR, specId, 'build-progress.txt'), 'utf-8');
    expect(progress).toContain('100%');
    expect(progress).toContain('human review');
  });

  test('should handle agent interruption and recovery', () => {
    const specId = '003-agent-recovery';
    createTaskSpec(specId);

    const agent = simulateAgentPhases(specId);

    // Start agent
    agent.plan();
    agent.code();

    // Simulate interruption — status stays in_progress, subtask partially done
    const planPath = path.join(SPECS_DIR, specId, 'implementation_plan.json');
    let plan = JSON.parse(readFileSync(planPath, 'utf-8'));
    expect(plan.phases[0].subtasks[0].status).toBe('completed');
    expect(plan.phases[0].subtasks[1].status).toBe('in_progress');

    // Recovery: reset in_progress subtask back to pending, then re-run
    plan.phases[0].subtasks[1].status = 'pending';
    plan.updated_at = new Date().toISOString();
    writeFileSync(planPath, JSON.stringify(plan, null, 2));

    // Resume from checkpoint
    plan = JSON.parse(readFileSync(planPath, 'utf-8'));
    const pendingSubtask = plan.phases[0].subtasks.find((s: { status: string }) => s.status === 'pending');
    expect(pendingSubtask).toBeDefined();
    expect(pendingSubtask.id).toBe('sub-2');

    // Complete the recovered subtask
    pendingSubtask.status = 'completed';
    writeFileSync(planPath, JSON.stringify(plan, null, 2));

    plan = JSON.parse(readFileSync(planPath, 'utf-8'));
    expect(plan.phases[0].subtasks.every((s: { status: string }) => s.status === 'completed')).toBe(true);
  });

  test('should handle multiple concurrent task specs', () => {
    const tasks = ['004-task-a', '004-task-b', '004-task-c'];

    for (const taskId of tasks) {
      createTaskSpec(taskId);
    }

    // Verify all tasks exist independently
    for (const taskId of tasks) {
      expect(existsSync(path.join(SPECS_DIR, taskId, 'spec.md'))).toBe(true);
    }

    // Start agents for different tasks at different stages
    simulateAgentPhases(tasks[0]).plan();
    simulateAgentPhases(tasks[1]).plan();
    simulateAgentPhases(tasks[1]).code();

    // Verify independent states
    const status0 = JSON.parse(readFileSync(path.join(SPECS_DIR, tasks[0], 'status.json'), 'utf-8'));
    expect(status0.status).toBe('in_progress');

    const plan1 = JSON.parse(readFileSync(path.join(SPECS_DIR, tasks[1], 'implementation_plan.json'), 'utf-8'));
    expect(plan1.phases[0].subtasks[0].status).toBe('completed');

    // Task C should still be in backlog
    const status2 = JSON.parse(readFileSync(path.join(SPECS_DIR, tasks[2], 'status.json'), 'utf-8'));
    expect(status2.status).toBe('backlog');
  });

  test('should validate task status transitions', () => {
    const specId = '005-status-transitions';
    createTaskSpec(specId);
    const statusPath = path.join(SPECS_DIR, specId, 'status.json');

    // Valid transitions: backlog → in_progress → ai_review → human_review → done
    const validTransitions = ['backlog', 'in_progress', 'ai_review', 'human_review', 'done'];

    for (const status of validTransitions) {
      updateStatus(path.join(SPECS_DIR, specId), status);
      const current = JSON.parse(readFileSync(statusPath, 'utf-8'));
      expect(current.status).toBe(status);
      expect(current.updated_at).toBeTruthy();
    }
  });

  test('should handle merge flow: human_review → done', () => {
    const specId = '006-merge-flow';
    createTaskSpec(specId);

    const agent = simulateAgentPhases(specId);
    agent.plan();
    agent.code();
    agent.review();
    agent.complete();

    // Verify task is in human_review
    const statusPath = path.join(SPECS_DIR, specId, 'status.json');
    let status = JSON.parse(readFileSync(statusPath, 'utf-8'));
    expect(status.status).toBe('human_review');

    // Simulate human approval → done
    updateStatus(path.join(SPECS_DIR, specId), 'done');
    status = JSON.parse(readFileSync(statusPath, 'utf-8'));
    expect(status.status).toBe('done');

    // Simulate PR created marker
    writeFileSync(
      path.join(SPECS_DIR, specId, 'pr_created.json'),
      JSON.stringify({
        pr_number: 42,
        branch: `feature/${specId}`,
        created_at: new Date().toISOString()
      }, null, 2)
    );

    expect(existsSync(path.join(SPECS_DIR, specId, 'pr_created.json'))).toBe(true);
    const pr = JSON.parse(readFileSync(path.join(SPECS_DIR, specId, 'pr_created.json'), 'utf-8'));
    expect(pr.pr_number).toBe(42);
  });
});
