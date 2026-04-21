/**
 * Tests for Tech Debt Store.
 */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DebtReport } from "../../../preload/api/modules/tech-debt-api";

const mockScan = vi.fn();
const mockList = vi.fn();
const mockSpec = vi.fn();

beforeEach(() => {
	vi.clearAllMocks();
	Object.defineProperty(globalThis, "electronAPI", {
		value: {
			scanTechDebt: mockScan,
			listDebtItems: mockList,
			generateDebtSpec: mockSpec,
		},
		writable: true,
		configurable: true,
	});
});

import { useTechDebtStore } from "../tech-debt-store";

describe("tech-debt-store", () => {
	it("starts with empty state and default filters", () => {
		const { result } = renderHook(() => useTechDebtStore());
		act(() => result.current.clear());
		expect(result.current.items).toEqual([]);
		expect(result.current.filters.minScore).toBe(0);
		expect(result.current.filters.kind).toBeNull();
	});

	it("updates filters via setFilter", () => {
		const { result } = renderHook(() => useTechDebtStore());
		act(() => result.current.setFilter("minScore", 3));
		act(() => result.current.setFilter("kind", "duplication"));
		expect(result.current.filters.minScore).toBe(3);
		expect(result.current.filters.kind).toBe("duplication");
	});

	it("scans and stores the result", async () => {
		const report: DebtReport = {
			project_path: "/p",
			scanned_at: 123,
			items: [
				{
					id: "x",
					kind: "todo_fixme",
					file_path: "a.py",
					line: 1,
					message: "m",
					cost: 2,
					effort: 1,
					roi: 2,
					tags: [],
					context: "",
				},
			],
			trend: [
				{ timestamp: 123, total_items: 1, total_cost: 2, avg_roi: 2 },
			],
			summary: {
				total: 1,
				by_kind: { todo_fixme: 1 },
				total_cost: 2,
				total_effort: 1,
				avg_roi: 2,
			},
		};
		mockScan.mockResolvedValueOnce({ result: report });

		const { result } = renderHook(() => useTechDebtStore());
		await act(async () => {
			await result.current.scan("/p");
		});

		expect(mockScan).toHaveBeenCalledWith({ projectPath: "/p" });
		expect(result.current.items).toHaveLength(1);
		expect(result.current.summary?.total).toBe(1);
		expect(result.current.scanning).toBe(false);
		expect(result.current.lastScannedAt).toBe(123);
	});

	it("surfaces scan errors", async () => {
		mockScan.mockRejectedValueOnce(new Error("io failure"));
		const { result } = renderHook(() => useTechDebtStore());
		await act(async () => {
			await result.current.scan("/p");
		});
		expect(result.current.scanning).toBe(false);
		expect(result.current.error).toContain("io failure");
	});

	it("generateSpec returns the created path", async () => {
		mockSpec.mockResolvedValueOnce({ result: { spec_dir: "/p/.workpilot/specs/001-x" } });
		const { result } = renderHook(() => useTechDebtStore());
		let dir: string | null = null;
		await act(async () => {
			dir = await result.current.generateSpec("/p", "item-id");
		});
		expect(mockSpec).toHaveBeenCalledWith({
			projectPath: "/p",
			itemId: "item-id",
			llmHint: undefined,
		});
		expect(dir).toBe("/p/.workpilot/specs/001-x");
	});
});
