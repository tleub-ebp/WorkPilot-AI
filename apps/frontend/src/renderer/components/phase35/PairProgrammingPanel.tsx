/**
 * #3.5 Real-time Pair Programming panel.
 *
 * Create or join a room, see the live participant list, send chat
 * messages and watch operations stream in via SSE.
 */

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	setupPairRealtimeListeners,
	usePairRealtimeStore,
} from "../../stores/phase35-stores";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { PanelShell } from "./_panel-shell";

const ROLES = ["driver", "navigator", "ai"] as const;

export function PairProgrammingPanel() {
	const { t } = useTranslation("phase35");
	const {
		phase,
		error,
		currentRoom,
		ops,
		isStreaming,
		createOrJoin,
		leave,
		sendChat,
		subscribe,
		unsubscribe,
	} = usePairRealtimeStore();
	const [roomId, setRoomId] = useState("demo-room");
	const [userId, setUserId] = useState("you");
	const [displayName, setDisplayName] = useState("You");
	const [role, setRole] = useState<"driver" | "navigator" | "ai">("driver");
	const [chatText, setChatText] = useState("");
	const opsScrollRef = useRef<HTMLDivElement>(null);

	// Wire SSE → store on mount.
	useEffect(() => {
		const teardown = setupPairRealtimeListeners();
		return teardown;
	}, []);

	// Auto-subscribe when joining a room; auto-unsubscribe on leave/unmount.
	useEffect(() => {
		if (currentRoom && !isStreaming) {
			void subscribe();
		}
		return () => {
			if (isStreaming) void unsubscribe();
		};
	}, [currentRoom, isStreaming, subscribe, unsubscribe]);

	// Auto-scroll the ops feed to the bottom.
	useEffect(() => {
		if (opsScrollRef.current) {
			opsScrollRef.current.scrollTop = opsScrollRef.current.scrollHeight;
		}
	}, []);

	const isRunning = phase === "running";

	return (
		<PanelShell
			title={t("pair.title")}
			subtitle={t("pair.subtitle")}
			error={error}
			actions={
				currentRoom ? (
					<Button size="sm" variant="outline" onClick={() => leave()}>
						{t("pair.leave")}
					</Button>
				) : (
					<Button
						size="sm"
						onClick={() => createOrJoin(roomId, userId, displayName, role)}
						disabled={isRunning || !roomId || !userId}
					>
						{t("pair.joinRoom")}
					</Button>
				)
			}
		>
			{!currentRoom ? (
				<div className="grid grid-cols-2 gap-3 text-sm">
					<div>
						<label className="block font-medium mb-1">{t("pair.roomId")}</label>
						<input
							value={roomId}
							onChange={(e) => setRoomId(e.target.value)}
							className="w-full rounded border bg-background p-2 text-sm"
						/>
					</div>
					<div>
						<label className="block font-medium mb-1">{t("pair.yourName")}</label>
						<input
							value={displayName}
							onChange={(e) => {
								setDisplayName(e.target.value);
								setUserId(e.target.value.toLowerCase().replace(/\s+/g, "-") || "you");
							}}
							className="w-full rounded border bg-background p-2 text-sm"
						/>
					</div>
					<div>
						<label className="block font-medium mb-1">{t("pair.role")}</label>
						<select
							value={role}
							onChange={(e) => setRole(e.target.value as typeof role)}
							className="w-full rounded border bg-background p-2 text-sm"
						>
							{ROLES.map((r) => (
								<option key={r} value={r}>
									{r}
								</option>
							))}
						</select>
					</div>
				</div>
			) : (
				<div className="space-y-3 text-sm">
					<div className="flex items-center gap-3">
						<Badge variant="outline">room: {currentRoom.room_id}</Badge>
						<Badge
							className={
								isStreaming
									? "bg-green-500/20 text-green-700 border-green-500/40"
									: "bg-muted"
							}
						>
							{isStreaming ? `● ${t("pair.streaming")}` : "○"}
						</Badge>
					</div>

					<div>
						<div className="font-medium mb-1">
							{t("pair.participants")} ({currentRoom.participants.length})
						</div>
						<ul className="flex flex-wrap gap-2">
							{currentRoom.participants.map((p) => (
								<li key={p.user_id} className="rounded border px-2 py-1 text-xs">
									{p.display_name}{" "}
									<span className="text-muted-foreground">({p.role})</span>
								</li>
							))}
						</ul>
					</div>

					<div>
						<div className="font-medium mb-1">{t("pair.recentOps")}</div>
						<div
							ref={opsScrollRef}
							className="rounded border p-2 max-h-64 overflow-auto space-y-1 text-xs font-mono bg-muted/20"
						>
							{ops.length === 0 ? (
								<p className="text-muted-foreground">—</p>
							) : (
								ops.map((op) => (
									<div key={op.op_id}>
										<span className="text-muted-foreground">
											#{op.sequence}
										</span>{" "}
										<Badge variant="outline" className="text-[10px]">
											{op.kind}
										</Badge>{" "}
										<span>{op.actor}</span>
										{op.kind === "chat" && (
											<span className="ml-2">{String(op.payload.text ?? "")}</span>
										)}
										{op.kind === "edit" && (
											<span className="ml-2">
												{String(op.payload.file_path ?? "")}:
												{String(op.payload.start_line ?? 0)}
											</span>
										)}
									</div>
								))
							)}
						</div>
					</div>

					<form
						className="flex gap-2"
						onSubmit={(e) => {
							e.preventDefault();
							if (!chatText.trim()) return;
							void sendChat(chatText);
							setChatText("");
						}}
					>
						<input
							value={chatText}
							onChange={(e) => setChatText(e.target.value)}
							placeholder={t("pair.chatPlaceholder")}
							className="flex-1 rounded border bg-background p-2 text-sm"
						/>
						<Button type="submit" size="sm">
							{t("pair.send")}
						</Button>
					</form>
				</div>
			)}
		</PanelShell>
	);
}
