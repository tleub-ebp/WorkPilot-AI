/**
 * Cost Estimator Preload API
 * Exposes cost summary and budget IPC calls to the renderer process.
 */

import { ipcRenderer } from 'electron';

export interface CostSummary {
  total_cost: number;
  cost_by_provider: Record<string, number>;
  cost_by_model: Record<string, number>;
  total_tokens: number;
  tokens_input: number;
  tokens_output: number;
  period_days: number;
  daily_avg: number;
  trend_pct: number;
}

export interface BudgetInfo {
  monthly_budget: number;
  spent_this_month: number;
  remaining: number;
  utilization_pct: number;
  alerts: string[];
  forecast_end_of_month: number;
}

export interface CostAPI {
  getCostSummary(projectPath: string): Promise<{ success: boolean; summary?: CostSummary; error?: string }>;
  getCostBudget(projectPath: string): Promise<{ success: boolean; budget?: BudgetInfo; error?: string }>;
  setCostBudget(projectPath: string, limit: number, period?: string): Promise<{ success: boolean; error?: string }>;
}

export const createCostAPI = (): CostAPI => ({
  getCostSummary: (projectPath: string) =>
    ipcRenderer.invoke('costs:getSummary', projectPath),

  getCostBudget: (projectPath: string) =>
    ipcRenderer.invoke('costs:getBudget', projectPath),

  setCostBudget: (projectPath: string, limit: number, period = 'monthly') =>
    ipcRenderer.invoke('costs:setBudget', projectPath, limit, period),
});
