/**
 * Tests for Bounty Board Store.
 */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { BountyResult } from "../../../preload/api/modules/bounty-board-api";

const mockStartBounty = vi.fn();
const mockListArchives = vi.fn();

beforeEach(() => {
	vi.clearAllMocks();
	Object.defineProperty(globalThis, "electronAPI", {
		value: {
			startBounty: mockStartBounty,
			listBountyArchives: mockListArchives,
		},
		writable: true,
		configurable: true,
	});
});

import { useBountyBoardStore } from "../bounty-board-store";

describe("bounty-board-store", () => {
	it("seeds three default contestants covering multiple providers", () => {
		const { result } = renderHook(() => useBountyBoardStore());
		const providers = result.current.contestants.map((c) => c.provider);
		expect(providers.length).toBeGreaterThanOrEqual(3);
		expect(new Set(providers).size).toBeGreaterThan(1);
	});

	it("adds, updates, and removes contestants", () => {
		const { result } = renderHook(() => useBountyBoardStore());
		act(() => result.current.resetContestants());
		const before = result.current.contestants.length;

		act(() =>
			result.current.addContestant({ provider: "grok", model: "grok-2" }),
		);
		expect(result.current.contestants.length).toBe(before + 1);

		act(() =>
			result.current.updateContestant(result.current.contestants.length - 1, {
				model: "grok-2-mini",
			}),
		);
		expect(
			result.current.contestants[result.current.contestants.length - 1].model,
		).toBe("grok-2-mini");

		act(() =>
			result.current.removeContestant(result.current.contestants.length - 1),
		);
		expect(result.current.contestants.length).toBe(before);
	});

	it("calls the IPC start bridge with current contestants and stores the result", async () => {
		const fakeResult: BountyResult = {
			id: "b1",
			specId: "001",
			projectPath: "/p",
			contestants: [],
			winnerId: null,
			judgeReport: "",
			judgeRationale: {},
			createdAt: 1,
			completedAt: 2,
			status: "completed",
		};
		mockStartBounty.mockResolvedValueOnce({ result: fakeResult });
		mockListArchives.mockResolvedValueOnce({ archives: [fakeResult] });

		const { result } = renderHook(() => useBountyBoardStore());
		await act(async () => {
			await result.current.startBounty("/p", "001");
		});

		expect(mockStartBounty).toHaveBeenCalledTimes(1);
		const call = mockStartBounty.mock.calls[0][0];
		expect(call.projectPath).toBe("/p");
		expect(call.specId).toBe("001");
		expect(Array.isArray(call.contestants)).toBe(true);
		expect(result.current.current).toEqual(fakeResult);
		expect(result.current.archives).toEqual([fakeResult]);
		expect(result.current.loading).toBe(false);
	});

	it("surfaces errors without leaving the store in loading state", async () => {
		mockStartBounty.mockRejectedValueOnce(new Error("network down"));
		const { result } = renderHook(() => useBountyBoardStore());
		await act(async () => {
			await result.current.startBounty("/p", "001");
		});
		expect(result.current.loading).toBe(false);
		expect(result.current.error).toContain("network down");
	});
});
