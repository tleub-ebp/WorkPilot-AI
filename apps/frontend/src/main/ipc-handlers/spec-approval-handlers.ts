/**
 * Spec Approval Workflow IPC Handlers (Feature 42)
 *
 * Exposes channels for the human-in-the-loop spec review and approval step:
 *   specApproval:getPendingSpecs — List specs awaiting human approval
 *   specApproval:getSpec         — Get full spec content for review
 *   specApproval:approve         — Approve a spec (with optional amendments)
 *   specApproval:reject          — Reject a spec with feedback
 *   specApproval:requestChanges  — Request specific changes before approval
 *   specApproval:getHistory      — List past approval decisions
 */

import * as fs from "node:fs";
import * as path from "node:path";
import type { BrowserWindow } from "electron";
import { ipcMain } from "electron";

type ApprovalStatus = "pending" | "approved" | "rejected" | "changes_requested";

interface SpecApprovalRecord {
	specNumber: string;
	specName: string;
	specDir: string;
	status: ApprovalStatus;
	reviewedAt?: string;
	feedback?: string;
	amendments?: string;
	autoApproveThreshold?: number;
}

function getApprovalDbPath(projectDir: string): string {
	return path.join(projectDir, ".workpilot", "spec_approvals.json");
}

function loadApprovals(projectDir: string): SpecApprovalRecord[] {
	const p = getApprovalDbPath(projectDir);
	if (!fs.existsSync(p)) return [];
	try {
		return JSON.parse(fs.readFileSync(p, "utf-8"));
	} catch {
		return [];
	}
}

function saveApprovals(
	projectDir: string,
	records: SpecApprovalRecord[],
): void {
	const p = getApprovalDbPath(projectDir);
	fs.mkdirSync(path.dirname(p), { recursive: true });
	fs.writeFileSync(p, JSON.stringify(records, null, 2), "utf-8");
}

function upsertApproval(projectDir: string, record: SpecApprovalRecord): void {
	const records = loadApprovals(projectDir);
	const idx = records.findIndex((r) => r.specNumber === record.specNumber);
	if (idx >= 0) {
		records[idx] = record;
	} else {
		records.unshift(record);
	}
	saveApprovals(projectDir, records.slice(0, 500));
}

/** Scan .workpilot/specs/ for specs with status file showing 'awaiting_approval' */
function scanPendingSpecs(projectDir: string): SpecApprovalRecord[] {
	const specsDir = path.join(projectDir, ".workpilot", "specs");
	if (!fs.existsSync(specsDir)) return [];

	const pending: SpecApprovalRecord[] = [];
	const existing = loadApprovals(projectDir);

	try {
		for (const entry of fs.readdirSync(specsDir)) {
			const specDir = path.join(specsDir, entry);
			if (!fs.statSync(specDir).isDirectory()) continue;

			// Check for approval_pending marker file
			const pendingMarker = path.join(specDir, "APPROVAL_PENDING");
			const specMd = path.join(specDir, "spec.md");

			if (fs.existsSync(pendingMarker) && fs.existsSync(specMd)) {
				const match = entry.match(/^(\d+)-(.+)$/);
				const specNumber = match?.[1] ?? entry;
				const specName = match?.[2]?.replace(/-/g, " ") ?? entry;

				const alreadyDecided = existing.find(
					(r) => r.specNumber === specNumber,
				);
				if (!alreadyDecided || alreadyDecided.status === "pending") {
					pending.push({
						specNumber,
						specName,
						specDir,
						status: "pending",
					});
				}
			}
		}
	} catch {
		/* ignore */
	}

	return pending;
}

export function registerSpecApprovalHandlers(): void {
	ipcMain.handle(
		"specApproval:getPendingSpecs",
		(_event, projectDir: string) => {
			try {
				const pending = scanPendingSpecs(projectDir);
				return { success: true, data: pending };
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);

	ipcMain.handle(
		"specApproval:getSpec",
		(_event, projectDir: string, specNumber: string) => {
			try {
				const specsDir = path.join(projectDir, ".workpilot", "specs");
				const entries = fs
					.readdirSync(specsDir)
					.filter((e) => e.startsWith(specNumber + "-") || e === specNumber);
				if (entries.length === 0)
					return { success: false, error: "Spec not found" };

				const specDir = path.join(specsDir, entries[0]);
				const result: Record<string, string> = { spec_number: specNumber };

				for (const fname of [
					"spec.md",
					"requirements.json",
					"context.json",
					"implementation_plan.json",
				]) {
					const fpath = path.join(specDir, fname);
					if (fs.existsSync(fpath)) {
						result[fname.replace(".", "_")] = fs.readFileSync(fpath, "utf-8");
					}
				}

				return { success: true, data: result };
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);

	ipcMain.handle(
		"specApproval:approve",
		(
			_event,
			projectDir: string,
			params: {
				specNumber: string;
				amendments?: string;
				autoApproveThreshold?: number;
			},
		) => {
			try {
				const specsDir = path.join(projectDir, ".workpilot", "specs");
				const entries = fs
					.readdirSync(specsDir)
					.filter(
						(e) =>
							e.startsWith(params.specNumber + "-") || e === params.specNumber,
					);
				if (entries.length === 0)
					return { success: false, error: "Spec not found" };

				const specDir = path.join(specsDir, entries[0]);
				const specName = entries[0].replace(/^\d+-/, "").replace(/-/g, " ");

				// Remove pending marker, write approval file
				const pendingMarker = path.join(specDir, "APPROVAL_PENDING");
				if (fs.existsSync(pendingMarker)) {
					fs.unlinkSync(pendingMarker);
				}
				fs.writeFileSync(
					path.join(specDir, "APPROVED"),
					JSON.stringify(
						{
							approved_at: new Date().toISOString(),
							amendments: params.amendments ?? "",
						},
						null,
						2,
					),
					"utf-8",
				);

				// If amendments provided, append to spec.md
				if (params.amendments?.trim()) {
					const specMd = path.join(specDir, "spec.md");
					if (fs.existsSync(specMd)) {
						const existing = fs.readFileSync(specMd, "utf-8");
						fs.writeFileSync(
							specMd,
							existing + "\n\n## Human Amendments\n\n" + params.amendments,
							"utf-8",
						);
					}
				}

				upsertApproval(projectDir, {
					specNumber: params.specNumber,
					specName,
					specDir,
					status: "approved",
					reviewedAt: new Date().toISOString(),
					amendments: params.amendments,
				});

				return { success: true };
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);

	ipcMain.handle(
		"specApproval:reject",
		(
			_event,
			projectDir: string,
			params: {
				specNumber: string;
				feedback: string;
			},
		) => {
			try {
				const specsDir = path.join(projectDir, ".workpilot", "specs");
				const entries = fs
					.readdirSync(specsDir)
					.filter(
						(e) =>
							e.startsWith(params.specNumber + "-") || e === params.specNumber,
					);
				if (entries.length === 0)
					return { success: false, error: "Spec not found" };

				const specDir = path.join(specsDir, entries[0]);
				const specName = entries[0].replace(/^\d+-/, "").replace(/-/g, " ");

				const pendingMarker = path.join(specDir, "APPROVAL_PENDING");
				if (fs.existsSync(pendingMarker)) {
					fs.unlinkSync(pendingMarker);
				}
				fs.writeFileSync(
					path.join(specDir, "REJECTED"),
					JSON.stringify(
						{
							rejected_at: new Date().toISOString(),
							feedback: params.feedback,
						},
						null,
						2,
					),
					"utf-8",
				);

				upsertApproval(projectDir, {
					specNumber: params.specNumber,
					specName,
					specDir,
					status: "rejected",
					reviewedAt: new Date().toISOString(),
					feedback: params.feedback,
				});

				return { success: true };
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);

	ipcMain.handle(
		"specApproval:requestChanges",
		(
			_event,
			projectDir: string,
			params: {
				specNumber: string;
				feedback: string;
			},
		) => {
			try {
				const specsDir = path.join(projectDir, ".workpilot", "specs");
				const entries = fs
					.readdirSync(specsDir)
					.filter(
						(e) =>
							e.startsWith(params.specNumber + "-") || e === params.specNumber,
					);
				if (entries.length === 0)
					return { success: false, error: "Spec not found" };

				const specDir = path.join(specsDir, entries[0]);
				const specName = entries[0].replace(/^\d+-/, "").replace(/-/g, " ");

				// Write change request file (keeps APPROVAL_PENDING so it stays in queue)
				fs.writeFileSync(
					path.join(specDir, "CHANGES_REQUESTED"),
					JSON.stringify(
						{
							requested_at: new Date().toISOString(),
							feedback: params.feedback,
						},
						null,
						2,
					),
					"utf-8",
				);

				upsertApproval(projectDir, {
					specNumber: params.specNumber,
					specName,
					specDir,
					status: "changes_requested",
					reviewedAt: new Date().toISOString(),
					feedback: params.feedback,
				});

				return { success: true };
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);

	ipcMain.handle(
		"specApproval:getHistory",
		(_event, projectDir: string, limit: number = 100) => {
			try {
				const history = loadApprovals(projectDir).slice(0, limit);
				return { success: true, data: history };
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);
}

export function setupSpecApprovalEventForwarding(
	_getMainWindow: () => BrowserWindow | null,
): void {
	// Spec approval is request-response. The agent marks specs by creating APPROVAL_PENDING files;
	// the renderer polls via specApproval:getPendingSpecs.
}
