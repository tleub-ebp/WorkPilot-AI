/**
 * IPC handlers for the 12 Phase 3-5 backend feature modules.
 *
 * Each handler is a thin wrapper around `backendFetch` that translates the
 * camelCase IPC payload into the snake_case backend payload and returns
 * the JSON response verbatim.
 */

import { ipcMain, type BrowserWindow } from "electron";
import { IPC_CHANNELS } from "../../shared/constants";
import { backendFetch, getBackendUrl } from "./_backend-fetch";

// ---------------------------------------------------------------------------
// Subscriptions for the SSE stream of #3.5 Pair Realtime

interface PairSubscription {
	subscriptionId: string;
	roomId: string;
	abortController: AbortController;
}

const _pairSubs = new Map<string, PairSubscription>();

function _broadcast(getMainWindow: () => BrowserWindow | null, channel: string, payload: unknown) {
	const win = getMainWindow();
	if (win && !win.isDestroyed()) {
		win.webContents.send(channel, payload);
	}
}

async function _runPairStream(
	getMainWindow: () => BrowserWindow | null,
	sub: PairSubscription,
	sinceSequence: number,
): Promise<void> {
	const url = `${getBackendUrl()}/api/pair-realtime/rooms/${encodeURIComponent(
		sub.roomId,
	)}/stream?since_sequence=${sinceSequence}`;
	try {
		const res = await fetch(url, {
			signal: sub.abortController.signal,
			headers: { Accept: "text/event-stream" },
		});
		if (!res.ok || !res.body) {
			_broadcast(getMainWindow, IPC_CHANNELS.PAIR_RT_STREAM_ERROR, {
				subscriptionId: sub.subscriptionId,
				error: `HTTP ${res.status}`,
			});
			return;
		}
		const reader = res.body.getReader();
		const decoder = new TextDecoder();
		let buffer = "";
		while (true) {
			const { value, done } = await reader.read();
			if (done) break;
			buffer += decoder.decode(value, { stream: true });
			let newlineIdx = buffer.indexOf("\n\n");
			while (newlineIdx >= 0) {
				const block = buffer.slice(0, newlineIdx).trim();
				buffer = buffer.slice(newlineIdx + 2);
				newlineIdx = buffer.indexOf("\n\n");
				if (!block) continue;
				// SSE block: each non-empty line either `event: foo` or `data: bar`.
				const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
				if (!dataLine) continue;
				try {
					const op = JSON.parse(dataLine.slice(6));
					_broadcast(getMainWindow, IPC_CHANNELS.PAIR_RT_OP_EVENT, {
						subscriptionId: sub.subscriptionId,
						op,
					});
				} catch {
					/* malformed payload — skip */
				}
			}
		}
	} catch (err) {
		if (sub.abortController.signal.aborted) return;
		_broadcast(getMainWindow, IPC_CHANNELS.PAIR_RT_STREAM_ERROR, {
			subscriptionId: sub.subscriptionId,
			error: err instanceof Error ? err.message : String(err),
		});
	} finally {
		_pairSubs.delete(sub.subscriptionId);
	}
}

// ---------------------------------------------------------------------------
// Registration

export function registerPhase35FeatureHandlers(getMainWindow: () => BrowserWindow | null): void {
	// === #3.8 Longevity ===
	ipcMain.handle(IPC_CHANNELS.LONGEVITY_SCORE, async (_e, { projectPath }: { projectPath: string }) => {
		if (!projectPath) return { success: false, error: "projectPath is required" };
		return backendFetch("/api/longevity/score", {
			method: "POST",
			body: JSON.stringify({ project_path: projectPath }),
		});
	});

	// === #3.11 Agent Health ===
	ipcMain.handle(IPC_CHANNELS.AGENT_HEALTH_RECORD, async (_e, run: Record<string, unknown>) =>
		backendFetch("/api/agent-health/record", { method: "POST", body: JSON.stringify(run) }),
	);
	ipcMain.handle(IPC_CHANNELS.AGENT_HEALTH_RECORD_BATCH, async (_e, { runs }: { runs: unknown[] }) =>
		backendFetch("/api/agent-health/record-batch", { method: "POST", body: JSON.stringify({ runs }) }),
	);
	ipcMain.handle(IPC_CHANNELS.AGENT_HEALTH_SCORE, async (_e, { agentName }: { agentName: string }) =>
		backendFetch(`/api/agent-health/score/${encodeURIComponent(agentName)}`),
	);
	ipcMain.handle(IPC_CHANNELS.AGENT_HEALTH_SCORES, async () =>
		backendFetch("/api/agent-health/scores"),
	);
	ipcMain.handle(IPC_CHANNELS.AGENT_HEALTH_RESET, async (_e, { agentName }: { agentName?: string }) =>
		backendFetch("/api/agent-health/reset", {
			method: "POST",
			body: JSON.stringify({ agent_name: agentName ?? null }),
		}),
	);

	// === #3.1 Model Router ===
	ipcMain.handle(IPC_CHANNELS.MODEL_ROUTER_ROUTE, async (_e, req: Record<string, unknown>) =>
		backendFetch("/api/model-router/route", { method: "POST", body: JSON.stringify(req) }),
	);
	ipcMain.handle(IPC_CHANNELS.MODEL_ROUTER_COMPARE, async (_e, req: Record<string, unknown>) =>
		backendFetch("/api/model-router/compare", { method: "POST", body: JSON.stringify(req) }),
	);

	// === #3.6 Domain Agents ===
	ipcMain.handle(IPC_CHANNELS.DOMAIN_AGENTS_LIST, async () => backendFetch("/api/domain-agents/domains"));
	ipcMain.handle(IPC_CHANNELS.DOMAIN_AGENTS_PROFILE, async (_e, { domain }: { domain: string }) =>
		backendFetch(`/api/domain-agents/profile/${encodeURIComponent(domain)}`),
	);
	ipcMain.handle(
		IPC_CHANNELS.DOMAIN_AGENTS_BUILD,
		async (_e, { domain, role }: { domain: string; role: string }) =>
			backendFetch("/api/domain-agents/build", {
				method: "POST",
				body: JSON.stringify({ domain, role }),
			}),
	);

	// === #3.4 CI/CD Anomaly ===
	ipcMain.handle(IPC_CHANNELS.CICD_ANOMALY_SCAN, async (_e, { log, label }: { log: string; label?: string }) =>
		backendFetch("/api/cicd-anomaly/scan", {
			method: "POST",
			body: JSON.stringify({ log, label: label ?? "" }),
		}),
	);
	ipcMain.handle(
		IPC_CHANNELS.CICD_ANOMALY_ANALYSE,
		async (_e, { samples }: { samples: { label: string; text: string }[] }) =>
			backendFetch("/api/cicd-anomaly/analyse", {
				method: "POST",
				body: JSON.stringify({ samples }),
			}),
	);

	// === #3.7 License Governance ===
	ipcMain.handle(
		IPC_CHANNELS.LICENSE_GOV_SCAN,
		async (
			_e,
			{
				projectPath,
				policy,
				licenseOverrides,
			}: {
				projectPath: string;
				policy?: string;
				licenseOverrides?: { name: string; license: string | null }[];
			},
		) =>
			backendFetch("/api/license-governance/scan", {
				method: "POST",
				body: JSON.stringify({
					project_path: projectPath,
					policy: policy ?? "permissive_only",
					license_overrides: licenseOverrides ?? null,
				}),
			}),
	);
	ipcMain.handle(IPC_CHANNELS.LICENSE_GOV_CLASSIFY, async (_e, { license }: { license: string }) =>
		backendFetch("/api/license-governance/classify", {
			method: "POST",
			body: JSON.stringify({ license }),
		}),
	);

	// === #3.9 Architecture Drift ===
	ipcMain.handle(IPC_CHANNELS.ARCH_DRIFT_SCAN, async (_e, { projectPath }: { projectPath: string }) =>
		backendFetch("/api/architecture/drift/scan", {
			method: "POST",
			body: JSON.stringify({ project_path: projectPath }),
		}),
	);
	ipcMain.handle(IPC_CHANNELS.ARCH_DRIFT_SAVE_BASELINE, async (_e, { projectPath }: { projectPath: string }) =>
		backendFetch("/api/architecture/drift/save-baseline", {
			method: "POST",
			body: JSON.stringify({ project_path: projectPath }),
		}),
	);
	ipcMain.handle(IPC_CHANNELS.ARCH_DRIFT_COMPARE, async (_e, { projectPath }: { projectPath: string }) =>
		backendFetch("/api/architecture/drift/compare", {
			method: "POST",
			body: JSON.stringify({ project_path: projectPath }),
		}),
	);

	// === #3.10 Generational Tests ===
	ipcMain.handle(IPC_CHANNELS.GEN_TESTS_LIST, async (_e, { projectPath }: { projectPath: string }) =>
		backendFetch(`/api/generational-tests/list?project_path=${encodeURIComponent(projectPath)}`),
	);
	ipcMain.handle(
		IPC_CHANNELS.GEN_TESTS_CAPTURE,
		async (_e, { projectPath, label, junitXml }: { projectPath: string; label: string; junitXml: string }) =>
			backendFetch("/api/generational-tests/capture", {
				method: "POST",
				body: JSON.stringify({ project_path: projectPath, label, junit_xml: junitXml }),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.GEN_TESTS_COMPARE,
		async (
			_e,
			{
				projectPath,
				baselineLabel,
				currentJunitXml,
			}: { projectPath: string; baselineLabel: string; currentJunitXml: string },
		) =>
			backendFetch("/api/generational-tests/compare", {
				method: "POST",
				body: JSON.stringify({
					project_path: projectPath,
					baseline_label: baselineLabel,
					current_junit_xml: currentJunitXml,
				}),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.GEN_TESTS_DELETE,
		async (_e, { projectPath, label }: { projectPath: string; label: string }) =>
			backendFetch(
				`/api/generational-tests/${encodeURIComponent(label)}?project_path=${encodeURIComponent(projectPath)}`,
				{ method: "DELETE" },
			),
	);

	// === #3.12 i18n Scaler ===
	ipcMain.handle(
		IPC_CHANNELS.I18N_SCALER_DIFF,
		async (
			_e,
			{
				source,
				target,
				sourceLocale,
				targetLocale,
			}: { source: unknown; target: unknown; sourceLocale?: string; targetLocale?: string },
		) =>
			backendFetch("/api/i18n-scaler/diff", {
				method: "POST",
				body: JSON.stringify({
					source,
					target,
					source_locale: sourceLocale ?? "en",
					target_locale: targetLocale ?? "fr",
				}),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.I18N_SCALER_SKELETON,
		async (
			_e,
			{
				source,
				targetLocale,
				existingTarget,
				strategy,
			}: { source: unknown; targetLocale: string; existingTarget?: unknown; strategy?: string },
		) =>
			backendFetch("/api/i18n-scaler/skeleton", {
				method: "POST",
				body: JSON.stringify({
					source,
					target_locale: targetLocale,
					existing_target: existingTarget ?? null,
					placeholder_strategy: strategy ?? null,
				}),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.I18N_SCALER_REPORT_FROM_DIR,
		async (
			_e,
			{
				localesDir,
				sourceLocale,
				strategy,
			}: { localesDir: string; sourceLocale?: string; strategy?: string },
		) =>
			backendFetch("/api/i18n-scaler/report-from-dir", {
				method: "POST",
				body: JSON.stringify({
					locales_dir: localesDir,
					source_locale: sourceLocale ?? "en",
					placeholder_strategy: strategy ?? null,
				}),
			}),
	);

	// === #3.2 Cognitive Context ===
	ipcMain.handle(
		IPC_CHANNELS.COGNITIVE_CONTEXT_OPTIMIZE,
		async (
			_e,
			{
				prompt,
				candidateFiles,
				tokenBudget,
				projectDir,
				explicitMentions,
				recentFiles,
			}: {
				prompt: string;
				candidateFiles: string[];
				tokenBudget: number;
				projectDir?: string;
				explicitMentions?: string[];
				recentFiles?: string[];
			},
		) =>
			backendFetch("/api/cognitive-context/optimize", {
				method: "POST",
				body: JSON.stringify({
					prompt,
					candidate_files: candidateFiles,
					token_budget: tokenBudget,
					project_dir: projectDir ?? null,
					explicit_mentions: explicitMentions ?? null,
					recent_files: recentFiles ?? null,
				}),
			}),
	);

	// === #3.3 Audit Trail ===
	ipcMain.handle(
		IPC_CHANNELS.AUDIT_TRAIL_APPEND,
		async (
			_e,
			input: {
				storageDir: string;
				trailName?: string;
				kind: string;
				actor: string;
				correlationId: string;
				summary?: string;
				payload?: Record<string, unknown>;
			},
		) =>
			backendFetch("/api/audit-trail/append", {
				method: "POST",
				body: JSON.stringify({
					storage_dir: input.storageDir,
					trail_name: input.trailName ?? "default",
					kind: input.kind,
					actor: input.actor,
					correlation_id: input.correlationId,
					summary: input.summary ?? "",
					payload: input.payload ?? null,
				}),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.AUDIT_TRAIL_APPEND_DECISION,
		async (
			_e,
			input: {
				storageDir: string;
				trailName?: string;
				actor: string;
				correlationId: string;
				decisionId: string;
				title: string;
				chosenOption: string;
				rejectedOptions?: string[];
				rationale?: string;
				riskScore?: number;
			},
		) =>
			backendFetch("/api/audit-trail/append-decision", {
				method: "POST",
				body: JSON.stringify({
					storage_dir: input.storageDir,
					trail_name: input.trailName ?? "default",
					actor: input.actor,
					correlation_id: input.correlationId,
					decision_id: input.decisionId,
					title: input.title,
					chosen_option: input.chosenOption,
					rejected_options: input.rejectedOptions ?? null,
					rationale: input.rationale ?? "",
					risk_score: input.riskScore ?? 0,
				}),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.AUDIT_TRAIL_EVENTS,
		async (
			_e,
			input: {
				storageDir: string;
				trailName?: string;
				actor?: string;
				kind?: string;
				since?: number;
				until?: number;
			},
		) => {
			const params = new URLSearchParams({
				storage_dir: input.storageDir,
				trail_name: input.trailName ?? "default",
			});
			if (input.actor) params.set("actor", input.actor);
			if (input.kind) params.set("kind", input.kind);
			if (input.since !== undefined) params.set("since", String(input.since));
			if (input.until !== undefined) params.set("until", String(input.until));
			return backendFetch(`/api/audit-trail/events?${params.toString()}`);
		},
	);
	ipcMain.handle(
		IPC_CHANNELS.AUDIT_TRAIL_REPLAY,
		async (
			_e,
			{
				correlationId,
				storageDir,
				trailName,
			}: { correlationId: string; storageDir: string; trailName?: string },
		) => {
			const params = new URLSearchParams({
				storage_dir: storageDir,
				trail_name: trailName ?? "default",
			});
			return backendFetch(
				`/api/audit-trail/replay/${encodeURIComponent(correlationId)}?${params.toString()}`,
			);
		},
	);
	ipcMain.handle(
		IPC_CHANNELS.AUDIT_TRAIL_VERIFY,
		async (_e, { storageDir, trailName }: { storageDir: string; trailName?: string }) => {
			const params = new URLSearchParams({
				storage_dir: storageDir,
				trail_name: trailName ?? "default",
			});
			return backendFetch(`/api/audit-trail/verify?${params.toString()}`);
		},
	);
	ipcMain.handle(IPC_CHANNELS.AUDIT_TRAIL_LIST, async (_e, { storageDir }: { storageDir: string }) => {
		const params = new URLSearchParams({ storage_dir: storageDir });
		return backendFetch(`/api/audit-trail/trails?${params.toString()}`);
	});

	// === #3.5 Pair Realtime ===
	ipcMain.handle(IPC_CHANNELS.PAIR_RT_CREATE_ROOM, async (_e, { roomId }: { roomId: string }) =>
		backendFetch("/api/pair-realtime/rooms", {
			method: "POST",
			body: JSON.stringify({ room_id: roomId }),
		}),
	);
	ipcMain.handle(IPC_CHANNELS.PAIR_RT_LIST_ROOMS, async () => backendFetch("/api/pair-realtime/rooms"));
	ipcMain.handle(IPC_CHANNELS.PAIR_RT_GET_ROOM, async (_e, { roomId }: { roomId: string }) =>
		backendFetch(`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}`),
	);
	ipcMain.handle(IPC_CHANNELS.PAIR_RT_CLOSE_ROOM, async (_e, { roomId }: { roomId: string }) =>
		backendFetch(`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}`, { method: "DELETE" }),
	);
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_JOIN,
		async (
			_e,
			{
				roomId,
				userId,
				displayName,
				role,
			}: { roomId: string; userId: string; displayName: string; role?: string },
		) =>
			backendFetch(`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}/join`, {
				method: "POST",
				body: JSON.stringify({
					user_id: userId,
					display_name: displayName,
					role: role ?? "navigator",
				}),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_LEAVE,
		async (_e, { roomId, userId }: { roomId: string; userId: string }) =>
			backendFetch(`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}/leave`, {
				method: "POST",
				body: JSON.stringify({ user_id: userId }),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_CHAT,
		async (_e, { roomId, actor, text }: { roomId: string; actor: string; text: string }) =>
			backendFetch(`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}/chat`, {
				method: "POST",
				body: JSON.stringify({ actor, text }),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_CURSOR,
		async (
			_e,
			{
				roomId,
				actor,
				filePath,
				line,
				column,
			}: { roomId: string; actor: string; filePath: string; line: number; column: number },
		) =>
			backendFetch(`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}/cursor`, {
				method: "POST",
				body: JSON.stringify({ actor, file_path: filePath, line, column }),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_EDIT,
		async (
			_e,
			{
				roomId,
				actor,
				filePath,
				startLine,
				endLine,
				newText,
			}: {
				roomId: string;
				actor: string;
				filePath: string;
				startLine: number;
				endLine: number;
				newText: string;
			},
		) =>
			backendFetch(`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}/edit`, {
				method: "POST",
				body: JSON.stringify({
					actor,
					file_path: filePath,
					start_line: startLine,
					end_line: endLine,
					new_text: newText,
				}),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_SUGGESTION,
		async (
			_e,
			{
				roomId,
				actor,
				filePath,
				suggestion,
				rationale,
			}: { roomId: string; actor: string; filePath: string; suggestion: string; rationale?: string },
		) =>
			backendFetch(`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}/suggestion`, {
				method: "POST",
				body: JSON.stringify({
					actor,
					file_path: filePath,
					suggestion,
					rationale: rationale ?? "",
				}),
			}),
	);
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_OPS,
		async (_e, { roomId, sinceSequence }: { roomId: string; sinceSequence?: number }) =>
			backendFetch(
				`/api/pair-realtime/rooms/${encodeURIComponent(roomId)}/ops?since_sequence=${sinceSequence ?? 0}`,
			),
	);

	// SSE subscribe / unsubscribe
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_SUBSCRIBE,
		async (_e, { roomId, sinceSequence }: { roomId: string; sinceSequence?: number }) => {
			const subscriptionId = `${roomId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
			const sub: PairSubscription = {
				subscriptionId,
				roomId,
				abortController: new AbortController(),
			};
			_pairSubs.set(subscriptionId, sub);
			// Run in background — don't await.
			void _runPairStream(getMainWindow, sub, sinceSequence ?? 0);
			return { success: true, subscriptionId };
		},
	);
	ipcMain.handle(
		IPC_CHANNELS.PAIR_RT_UNSUBSCRIBE,
		async (_e, { subscriptionId }: { subscriptionId: string }) => {
			const sub = _pairSubs.get(subscriptionId);
			if (!sub) return { success: true, closed: false };
			sub.abortController.abort();
			_pairSubs.delete(subscriptionId);
			return { success: true, closed: true };
		},
	);
}
