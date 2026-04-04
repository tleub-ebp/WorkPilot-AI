/**
 * PresenceIndicator — Shows connected users with their online status.
 *
 * Displays circular avatars in the top-right area, with color-coded status:
 * 🟢 Online, 🟡 Away, 🔴 Busy, ⚫ Offline.
 * Hover reveals the user's current task.
 *
 * Feature 3.1 — Mode multi-utilisateurs en temps réel.
 */

import { useTranslation } from "react-i18next";
import { cn } from "../../lib/utils";
import {
	type ConnectedUser,
	type UserStatus,
	useCollaborationStore,
} from "../../stores/collaboration-store";
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from "../ui/tooltip";

const STATUS_COLORS: Record<UserStatus, string> = {
	online: "bg-green-500",
	away: "bg-yellow-500",
	busy: "bg-red-500",
	offline: "bg-gray-400",
};

const STATUS_RING_COLORS: Record<UserStatus, string> = {
	online: "ring-green-500/30",
	away: "ring-yellow-500/30",
	busy: "ring-red-500/30",
	offline: "ring-gray-400/30",
};

function UserAvatar({
	user,
	isCurrentUser,
}: {
	user: ConnectedUser;
	isCurrentUser: boolean;
}) {
	const { t } = useTranslation("collaboration");
	const initials = user.displayName
		.split(" ")
		.map((n) => n[0])
		.join("")
		.toUpperCase()
		.slice(0, 2);

	const statusLabel = t(`presence.${user.status}`);
	const taskInfo = user.currentTask
		? t("presence.workingOn", { task: user.currentTask })
		: t("presence.idle");

	return (
		<TooltipProvider delayDuration={200}>
			<Tooltip>
				<TooltipTrigger asChild>
					<div className="relative">
						<div
							className={cn(
								"flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold text-white ring-2",
								STATUS_RING_COLORS[user.status],
								"cursor-default transition-transform hover:scale-110",
							)}
							style={{ backgroundColor: user.avatarColor }}
						>
							{initials}
						</div>
						<span
							className={cn(
								"absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background",
								STATUS_COLORS[user.status],
							)}
						/>
					</div>
				</TooltipTrigger>
				<TooltipContent side="bottom" className="max-w-52">
					<div className="space-y-1">
						<div className="flex items-center gap-1.5">
							<span className="font-medium">{user.displayName}</span>
							{isCurrentUser && (
								<span className="text-xs text-muted-foreground">
									{t("presence.you")}
								</span>
							)}
						</div>
						<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
							<span
								className={cn(
									"h-2 w-2 rounded-full",
									STATUS_COLORS[user.status],
								)}
							/>
							{statusLabel}
						</div>
						<div className="text-xs text-muted-foreground">{taskInfo}</div>
					</div>
				</TooltipContent>
			</Tooltip>
		</TooltipProvider>
	);
}

export function PresenceIndicator() {
	const { t } = useTranslation("collaboration");
	const users = useCollaborationStore((s) => s.users);
	const currentUserId = useCollaborationStore((s) => s.currentUserId);
	const showPresenceIndicator = useCollaborationStore(
		(s) => s.settings.showPresenceIndicator,
	);

	if (!showPresenceIndicator) return null;

	const onlineUsers = users.filter((u) => u.status !== "offline");
	const maxVisible = 5;
	const visibleUsers = onlineUsers.slice(0, maxVisible);
	const overflowCount = Math.max(0, onlineUsers.length - maxVisible);

	return (
		<div className="flex items-center gap-1">
			<div className="flex -space-x-2">
				{visibleUsers.map((user) => (
					<UserAvatar
						key={user.userId}
						user={user}
						isCurrentUser={user.userId === currentUserId}
					/>
				))}
				{overflowCount > 0 && (
					<div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground ring-2 ring-background">
						+{overflowCount}
					</div>
				)}
			</div>
			{onlineUsers.length > 0 && (
				<span className="ml-1.5 text-xs text-muted-foreground">
					{t("presence.usersOnline", { count: onlineUsers.length })}
				</span>
			)}
		</div>
	);
}
