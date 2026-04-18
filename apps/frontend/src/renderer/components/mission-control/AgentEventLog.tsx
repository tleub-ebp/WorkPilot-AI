/**
 * AgentEventLog — Scrollable live event feed for Mission Control.
 *
 * Shows recent orchestrator events with timestamps, types, and agent references.
 */

import {
	Activity,
	Pause,
	Play,
	Plus,
	RotateCcw,
	Settings2,
	Square,
	Trash2,
} from "lucide-react";
import { useMemo } from "react";
import { cn } from "../../lib/utils";
import type { AgentSlot, MCEvent } from "../../stores/mission-control-store";
import { Badge } from "../ui/badge";
import { ScrollArea } from "../ui/scroll-area";

interface AgentEventLogProps {
	readonly events: MCEvent[];
	readonly agents: AgentSlot[];
}

const EVENT_ICONS: Record<string, React.ElementType> = {
	agent_created: Plus,
	agent_removed: Trash2,
	agent_started: Play,
	agent_paused: Pause,
	agent_resumed: RotateCcw,
	agent_stopped: Square,
	agent_config_updated: Settings2,
};

const EVENT_COLORS: Record<string, string> = {
	agent_created: "text-green-500",
	agent_removed: "text-red-500",
	agent_started: "text-blue-500",
	agent_paused: "text-yellow-500",
	agent_resumed: "text-cyan-500",
	agent_stopped: "text-gray-500",
	agent_config_updated: "text-purple-500",
};

function formatTaskDisplay(task: unknown): string {
	if (typeof task === "string") {
		return task;
	}
	if (typeof task === "object" && task !== null) {
		return JSON.stringify(task);
	}
	if (typeof task === "number") {
		return task.toString();
	}
	if (typeof task === "boolean") {
		return task.toString();
	}
	// Handle symbol, bigint, undefined (though we check for null/undefined above)
	if (typeof task === "symbol" || typeof task === "bigint") {
		return task.toString();
	}
	// This should only be reached for function types or other edge cases
	return "Unsupported task type";
}

export function AgentEventLog({ events, agents }: AgentEventLogProps) {
	const agentMap = useMemo(() => {
		const map = new Map<string, string>();
		for (const a of agents) {
			map.set(a.id, a.name);
		}
		return map;
	}, [agents]);

	const reversedEvents = useMemo(() => [...events].reverse(), [events]);

	if (reversedEvents.length === 0) {
		return (
			<div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
				No events yet
			</div>
		);
	}

	return (
		<ScrollArea className="h-64">
			<div className="space-y-1 pr-2">
				{reversedEvents.map((event) => {
					const Icon = EVENT_ICONS[event.type] ?? Activity;
					const color = EVENT_COLORS[event.type] ?? "text-muted-foreground";
					const agentId = event.data?.agent_id as string | undefined;
					const agentName = agentId ? (agentMap.get(agentId) ?? agentId) : null;
					const ts = new Date(event.timestamp * 1000);
					const timeStr = ts.toLocaleTimeString([], {
						hour: "2-digit",
						minute: "2-digit",
						second: "2-digit",
					});

					return (
						<div
							key={`${event.timestamp}-${event.type}`}
							className="flex items-start gap-2 py-1 px-1.5 rounded text-xs hover:bg-muted/30 transition-colors"
						>
							<Icon className={cn("h-3.5 w-3.5 shrink-0 mt-0.5", color)} />
							<div className="flex-1 min-w-0">
								<div className="flex items-center gap-1.5">
									<span className="font-medium capitalize">
										{event.type.replaceAll("_", " ")}
									</span>
									{agentName && (
										<Badge variant="outline" className="text-[10px] px-1 py-0">
											{agentName}
										</Badge>
									)}
								</div>
								{(() => {
									const task = event.data?.task;
									if (task == null) return null;

									return (
										<p className="text-muted-foreground truncate mt-0.5">
											{formatTaskDisplay(task)}
										</p>
									);
								})()}
							</div>
							<span className="text-[10px] text-muted-foreground shrink-0 tabular-nums">
								{timeStr}
							</span>
						</div>
					);
				})}
			</div>
		</ScrollArea>
	);
}
