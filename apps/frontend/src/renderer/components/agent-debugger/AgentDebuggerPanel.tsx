import { Bug, Check, ChevronRight, Pause, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAgentDebuggerStore } from "../../stores/agent-debugger-store";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

const SELECT_CLASS =
	"h-9 rounded-md border border-border bg-card px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring";

const TOOLS = ["*", "Write", "Edit", "Bash"];

interface Props {
	readonly sessionId?: string;
}

export function AgentDebuggerPanel({ sessionId }: Props) {
	const { t } = useTranslation(["agentDebugger", "common"]);
	const {
		sessionId: attachedSession,
		breakpoints,
		frames,
		loading,
		error,
		attach,
		detach,
		addBreakpoint,
		removeBreakpoint,
		resume,
		refresh,
	} = useAgentDebuggerStore();

	const [newId, setNewId] = useState("");
	const [newTool, setNewTool] = useState("*");
	const [newPath, setNewPath] = useState("");
	const [newCommand, setNewCommand] = useState("");

	const handleAdd = async () => {
		if (!newId.trim()) return;
		await addBreakpoint({
			id: newId.trim(),
			tool: newTool,
			path_pattern: newPath || undefined,
			command_pattern: newCommand || undefined,
			enabled: true,
		});
		setNewId("");
		setNewPath("");
		setNewCommand("");
	};

	return (
		<div className="flex flex-col gap-3 p-4">
			<div className="flex items-center justify-between">
				<h3 className="text-base font-semibold flex items-center gap-2">
					<Bug className="w-4 h-4" />
					{t("agentDebugger:title", "Agent Debugger")}
				</h3>
				<div className="flex items-center gap-2">
					{attachedSession ? (
						<>
							<span className="text-xs text-muted-foreground">
								{t("agentDebugger:attachedTo", "Attached to")}{" "}
								<code className="bg-muted px-1 py-0.5 rounded">
									{attachedSession}
								</code>
							</span>
							<Button size="sm" variant="outline" onClick={refresh}>
								{t("common:refresh", "Refresh")}
							</Button>
							<Button size="sm" variant="outline" onClick={detach}>
								<X className="w-3 h-3 mr-1" />
								{t("agentDebugger:detach", "Detach")}
							</Button>
						</>
					) : (
						<Button
							size="sm"
							disabled={!sessionId || loading}
							onClick={() => sessionId && attach(sessionId)}
						>
							<Bug className="w-3 h-3 mr-1" />
							{t("agentDebugger:attach", "Attach")}
						</Button>
					)}
				</div>
			</div>

			{error && <p className="text-sm text-destructive">{error}</p>}

			{attachedSession && (
				<>
					<section className="border rounded-md p-3 bg-card">
						<h4 className="text-sm font-medium mb-2">
							{t("agentDebugger:breakpoints", "Breakpoints")} (
							{breakpoints.length})
						</h4>
						<div className="grid grid-cols-6 gap-2 mb-2 items-end">
							<div className="col-span-2">
								<Label className="text-xs">
									{t("agentDebugger:ruleId", "Id")}
								</Label>
								<Input
									value={newId}
									onChange={(e) => setNewId(e.target.value)}
									placeholder="no-writes-to-secrets"
								/>
							</div>
							<div>
								<Label className="text-xs">
									{t("agentDebugger:tool", "Tool")}
								</Label>
								<select
									className={SELECT_CLASS}
									value={newTool}
									onChange={(e) => setNewTool(e.target.value)}
								>
									{TOOLS.map((t0) => (
										<option key={t0} value={t0}>
											{t0}
										</option>
									))}
								</select>
							</div>
							<div className="col-span-2">
								<Label className="text-xs">
									{newTool === "Bash"
										? t("agentDebugger:commandPattern", "Command pattern")
										: t("agentDebugger:pathPattern", "Path pattern")}
								</Label>
								<Input
									value={newTool === "Bash" ? newCommand : newPath}
									onChange={(e) =>
										newTool === "Bash"
											? setNewCommand(e.target.value)
											: setNewPath(e.target.value)
									}
									placeholder={newTool === "Bash" ? "rm -rf" : "secrets/"}
								/>
							</div>
							<Button size="sm" onClick={handleAdd} disabled={!newId.trim()}>
								<Plus className="w-3 h-3 mr-1" />
								{t("common:add", "Add")}
							</Button>
						</div>
						<div className="space-y-1">
							{breakpoints.map((bp) => (
								<div
									key={bp.id}
									className="flex items-center justify-between text-sm border rounded p-2 bg-muted/20"
								>
									<div className="flex-1 truncate">
										<code className="font-mono">{bp.id}</code>{" "}
										<span className="text-muted-foreground">({bp.tool})</span>
										{bp.path_pattern && (
											<span className="ml-2 text-xs">
												path≈<code>{bp.path_pattern}</code>
											</span>
										)}
										{bp.command_pattern && (
											<span className="ml-2 text-xs">
												cmd≈<code>{bp.command_pattern}</code>
											</span>
										)}
									</div>
									<Button
										size="icon"
										variant="ghost"
										onClick={() => removeBreakpoint(bp.id)}
									>
										<Trash2 className="w-3 h-3" />
									</Button>
								</div>
							))}
							{breakpoints.length === 0 && (
								<p className="text-xs text-muted-foreground">
									{t("agentDebugger:noBreakpoints", "No breakpoints yet.")}
								</p>
							)}
						</div>
					</section>

					<section className="border rounded-md p-3 bg-card">
						<h4 className="text-sm font-medium mb-2 flex items-center gap-2">
							<Pause className="w-4 h-4" />
							{t("agentDebugger:pausedFrames", "Paused frames")} (
							{frames.length})
						</h4>
						{frames.length === 0 ? (
							<p className="text-xs text-muted-foreground">
								{t("agentDebugger:noFrames", "No paused frames.")}
							</p>
						) : (
							<div className="space-y-2">
								{frames.map((f) => (
									<div
										key={f.frame_id}
										className="border rounded p-2 space-y-1 bg-muted/20"
									>
										<div className="text-sm">
											<span className="font-medium">{f.tool_name}</span>
											<span className="text-muted-foreground">
												{" "}
												@ {f.breakpoint_id}
											</span>
										</div>
										<pre className="text-xs font-mono whitespace-pre-wrap bg-background p-2 rounded">
											{JSON.stringify(f.tool_input, null, 2)}
										</pre>
										<div className="flex gap-2">
											<Button
												size="sm"
												onClick={() => resume(f.frame_id, "continue")}
											>
												<Check className="w-3 h-3 mr-1" />
												{t("agentDebugger:continue", "Continue")}
											</Button>
											<Button
												size="sm"
												variant="outline"
												onClick={() =>
													resume(f.frame_id, "skip", { reason: "skipped" })
												}
											>
												<ChevronRight className="w-3 h-3 mr-1" />
												{t("agentDebugger:skip", "Skip")}
											</Button>
										</div>
									</div>
								))}
							</div>
						)}
					</section>
				</>
			)}
		</div>
	);
}
