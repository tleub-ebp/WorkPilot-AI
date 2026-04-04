/**
 * Collaboration Store — Zustand store for real-time multi-user collaboration state.
 *
 * Manages:
 * - Connected users and presence indicators
 * - Task locks (user and agent)
 * - Team chat messages
 * - Conflict detection and resolution
 * - Real-time event stream
 * - Collaboration settings
 *
 * Feature 3.1 — Mode multi-utilisateurs en temps réel.
 */

import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type UserStatus = "online" | "away" | "busy" | "offline";
export type LockType = "user" | "agent";
export type ConflictResolution =
	| "last_write_wins"
	| "first_write_wins"
	| "manual"
	| "merge";
export type EventType =
	| "user_joined"
	| "user_left"
	| "user_status_changed"
	| "task_updated"
	| "task_locked"
	| "task_unlocked"
	| "task_created"
	| "task_deleted"
	| "task_moved"
	| "chat_message"
	| "agent_started"
	| "agent_completed"
	| "notification"
	| "conflict_detected"
	| "sync_request"
	| "sync_response";

export interface ConnectedUser {
	userId: string;
	displayName: string;
	role: string;
	status: UserStatus;
	currentTask: string;
	connectedAt: string;
	lastActivity: string;
	avatarColor: string;
}

export interface TaskLock {
	taskId: string;
	lockedBy: string;
	lockType: LockType;
	lockedAt: string;
	reason: string;
}

export interface ChatMessage {
	messageId: string;
	senderId: string;
	senderName: string;
	content: string;
	timestamp: string;
	replyTo: string;
	mentions: string[];
}

export interface ConflictRecord {
	conflictId: string;
	taskId: string;
	userA: string;
	userB: string;
	fieldName: string;
	valueA: unknown;
	valueB: unknown;
	resolution: ConflictResolution;
	resolved: boolean;
	resolvedValue: unknown;
	timestamp: string;
}

export interface RealtimeEvent {
	eventId: string;
	eventType: EventType;
	senderId: string;
	data: Record<string, unknown>;
	timestamp: string;
	targetUsers: string[];
}

export interface CollaborationSettings {
	conflictStrategy: ConflictResolution;
	showPresenceIndicator: boolean;
	chatEnabled: boolean;
	chatSoundNotifications: boolean;
	chatDesktopNotifications: boolean;
	notifyUserJoinLeave: boolean;
	notifyTaskLocks: boolean;
	notifyAgentActivity: boolean;
	notifyChatMentions: boolean;
	notifyConflicts: boolean;
}

export interface CollaborationStats {
	totalUsers: number;
	onlineUsers: number;
	activeLocks: number;
	agentLocks: number;
	totalEvents: number;
	chatMessages: number;
	totalConflicts: number;
	unresolvedConflicts: number;
}

// ---------------------------------------------------------------------------
// Avatar color palette
// ---------------------------------------------------------------------------

const AVATAR_COLORS = [
	"#ef4444",
	"#f97316",
	"#eab308",
	"#22c55e",
	"#14b8a6",
	"#3b82f6",
	"#6366f1",
	"#a855f7",
	"#ec4899",
	"#f43f5e",
];

function getAvatarColor(userId: string): string {
	let hash = 0;
	for (let i = 0; i < userId.length; i++) {
		hash = ((hash << 5) - hash + userId.charCodeAt(i)) | 0;
	}
	return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

// ---------------------------------------------------------------------------
// Default settings
// ---------------------------------------------------------------------------

const DEFAULT_COLLABORATION_SETTINGS: CollaborationSettings = {
	conflictStrategy: "manual",
	showPresenceIndicator: true,
	chatEnabled: true,
	chatSoundNotifications: true,
	chatDesktopNotifications: true,
	notifyUserJoinLeave: true,
	notifyTaskLocks: true,
	notifyAgentActivity: true,
	notifyChatMentions: true,
	notifyConflicts: true,
};

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

interface CollaborationState {
	// State
	currentUserId: string;
	currentUserName: string;
	projectId: string;
	connected: boolean;
	syncing: boolean;
	users: ConnectedUser[];
	locks: TaskLock[];
	chatMessages: ChatMessage[];
	conflicts: ConflictRecord[];
	events: RealtimeEvent[];
	settings: CollaborationSettings;
	chatOpen: boolean;
	unreadChatCount: number;
	replyingTo: ChatMessage | null;

	// Actions — connection
	initialize: (projectId: string, userId: string, displayName: string) => void;
	disconnect: () => void;
	setConnected: (connected: boolean) => void;
	setSyncing: (syncing: boolean) => void;

	// Actions — users
	addUser: (user: Omit<ConnectedUser, "avatarColor">) => void;
	removeUser: (userId: string) => void;
	updateUserStatus: (userId: string, status: UserStatus) => void;
	setUserCurrentTask: (userId: string, taskId: string) => void;

	// Actions — locks
	lockTask: (
		taskId: string,
		lockedBy: string,
		lockType: LockType,
		reason?: string,
	) => void;
	unlockTask: (taskId: string) => void;
	isTaskLocked: (taskId: string) => boolean;
	getTaskLock: (taskId: string) => TaskLock | undefined;

	// Actions — chat
	addChatMessage: (message: ChatMessage) => void;
	sendMessage: (content: string) => void;
	setReplyingTo: (message: ChatMessage | null) => void;
	toggleChat: () => void;
	setChatOpen: (open: boolean) => void;
	markChatRead: () => void;

	// Actions — conflicts
	addConflict: (conflict: ConflictRecord) => void;
	resolveConflict: (conflictId: string, resolvedValue: unknown) => void;

	// Actions — events
	addEvent: (event: RealtimeEvent) => void;

	// Actions — settings
	updateSettings: (updates: Partial<CollaborationSettings>) => void;

	// Computed
	getOnlineUsers: () => ConnectedUser[];
	getStats: () => CollaborationStats;
	getUnresolvedConflicts: () => ConflictRecord[];
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

let _msgCounter = 0;
let _evtCounter = 0;

export const useCollaborationStore = create<CollaborationState>((set, get) => ({
	// Initial state
	currentUserId: "",
	currentUserName: "",
	projectId: "",
	connected: false,
	syncing: false,
	users: [],
	locks: [],
	chatMessages: [],
	conflicts: [],
	events: [],
	settings: { ...DEFAULT_COLLABORATION_SETTINGS },
	chatOpen: false,
	unreadChatCount: 0,
	replyingTo: null,

	// -- Connection ----------------------------------------------------------

	initialize: (projectId, userId, displayName) => {
		set({
			projectId,
			currentUserId: userId,
			currentUserName: displayName,
			connected: true,
			users: [
				{
					userId,
					displayName,
					role: "developer",
					status: "online",
					currentTask: "",
					connectedAt: new Date().toISOString(),
					lastActivity: new Date().toISOString(),
					avatarColor: getAvatarColor(userId),
				},
			],
		});
	},

	disconnect: () => {
		set({
			connected: false,
			users: [],
			locks: [],
			chatMessages: [],
			conflicts: [],
			events: [],
			unreadChatCount: 0,
		});
	},

	setConnected: (connected) => set({ connected }),
	setSyncing: (syncing) => set({ syncing }),

	// -- Users ---------------------------------------------------------------

	addUser: (user) => {
		set((state) => {
			const exists = state.users.find((u) => u.userId === user.userId);
			if (exists) {
				return {
					users: state.users.map((u) =>
						u.userId === user.userId
							? { ...u, ...user, status: "online" as UserStatus }
							: u,
					),
				};
			}
			return {
				users: [
					...state.users,
					{ ...user, avatarColor: getAvatarColor(user.userId) },
				],
			};
		});
	},

	removeUser: (userId) => {
		set((state) => ({
			users: state.users.map((u) =>
				u.userId === userId ? { ...u, status: "offline" as UserStatus } : u,
			),
		}));
	},

	updateUserStatus: (userId, status) => {
		set((state) => ({
			users: state.users.map((u) =>
				u.userId === userId
					? { ...u, status, lastActivity: new Date().toISOString() }
					: u,
			),
		}));
	},

	setUserCurrentTask: (userId, taskId) => {
		set((state) => ({
			users: state.users.map((u) =>
				u.userId === userId
					? {
							...u,
							currentTask: taskId,
							lastActivity: new Date().toISOString(),
						}
					: u,
			),
		}));
	},

	// -- Locks ---------------------------------------------------------------

	lockTask: (taskId, lockedBy, lockType, reason = "") => {
		set((state) => {
			const existing = state.locks.find((l) => l.taskId === taskId);
			if (existing) return state;
			return {
				locks: [
					...state.locks,
					{
						taskId,
						lockedBy,
						lockType,
						lockedAt: new Date().toISOString(),
						reason,
					},
				],
			};
		});
	},

	unlockTask: (taskId) => {
		set((state) => ({
			locks: state.locks.filter((l) => l.taskId !== taskId),
		}));
	},

	isTaskLocked: (taskId) => {
		return get().locks.some((l) => l.taskId === taskId);
	},

	getTaskLock: (taskId) => {
		return get().locks.find((l) => l.taskId === taskId);
	},

	// -- Chat ----------------------------------------------------------------

	addChatMessage: (message) => {
		set((state) => {
			const newState: Partial<CollaborationState> = {
				chatMessages: [...state.chatMessages, message],
			};
			if (!state.chatOpen && message.senderId !== state.currentUserId) {
				newState.unreadChatCount = state.unreadChatCount + 1;
			}
			return newState as CollaborationState;
		});
	},

	sendMessage: (content) => {
		const state = get();
		if (!content.trim() || !state.currentUserId) return;

		_msgCounter++;
		const message: ChatMessage = {
			messageId: `msg-${_msgCounter.toString().padStart(6, "0")}`,
			senderId: state.currentUserId,
			senderName: state.currentUserName,
			content: content.trim(),
			timestamp: new Date().toISOString(),
			replyTo: state.replyingTo?.messageId ?? "",
			mentions: [],
		};

		set((s) => ({
			chatMessages: [...s.chatMessages, message],
			replyingTo: null,
		}));
	},

	setReplyingTo: (message) => set({ replyingTo: message }),

	toggleChat: () =>
		set((state) => ({
			chatOpen: !state.chatOpen,
			unreadChatCount: !state.chatOpen ? 0 : state.unreadChatCount,
		})),

	setChatOpen: (open) =>
		set({
			chatOpen: open,
			unreadChatCount: open ? 0 : get().unreadChatCount,
		}),

	markChatRead: () => set({ unreadChatCount: 0 }),

	// -- Conflicts -----------------------------------------------------------

	addConflict: (conflict) => {
		set((state) => ({
			conflicts: [...state.conflicts, conflict],
		}));
	},

	resolveConflict: (conflictId, resolvedValue) => {
		set((state) => ({
			conflicts: state.conflicts.map((c) =>
				c.conflictId === conflictId
					? { ...c, resolved: true, resolvedValue }
					: c,
			),
		}));
	},

	// -- Events --------------------------------------------------------------

	addEvent: (event) => {
		_evtCounter++;
		set((state) => ({
			events: [
				...state.events.slice(-99),
				{
					...event,
					eventId:
						event.eventId || `evt-${_evtCounter.toString().padStart(6, "0")}`,
				},
			],
		}));
	},

	// -- Settings ------------------------------------------------------------

	updateSettings: (updates) => {
		set((state) => ({
			settings: { ...state.settings, ...updates },
		}));
	},

	// -- Computed ------------------------------------------------------------

	getOnlineUsers: () => {
		return get().users.filter((u) => u.status !== "offline");
	},

	getStats: () => {
		const state = get();
		const onlineUsers = state.users.filter((u) => u.status !== "offline");
		return {
			totalUsers: state.users.length,
			onlineUsers: onlineUsers.length,
			activeLocks: state.locks.length,
			agentLocks: state.locks.filter((l) => l.lockType === "agent").length,
			totalEvents: state.events.length,
			chatMessages: state.chatMessages.length,
			totalConflicts: state.conflicts.length,
			unresolvedConflicts: state.conflicts.filter((c) => !c.resolved).length,
		};
	},

	getUnresolvedConflicts: () => {
		return get().conflicts.filter((c) => !c.resolved);
	},
}));
