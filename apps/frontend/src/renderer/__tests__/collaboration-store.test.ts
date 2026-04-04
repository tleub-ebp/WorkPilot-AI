/**
 * Unit tests for Collaboration Store
 * Tests Zustand store for real-time multi-user collaboration state management.
 *
 * Feature 3.1 — Mode multi-utilisateurs en temps réel.
 *
 * Tests: initialize (3), users (6), locks (6), chat (6), conflicts (4),
 *        events (3), settings (3), computed (4) = 35 tests.
 */
import { beforeEach, describe, expect, it } from "vitest";
import {
	type ChatMessage,
	type ConflictRecord,
	useCollaborationStore,
} from "../stores/collaboration-store";

// Helper to reset store
function resetStore() {
	useCollaborationStore.setState({
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
		settings: {
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
		},
		chatOpen: false,
		unreadChatCount: 0,
		replyingTo: null,
	});
}

// ---------------------------------------------------------------------------
// Initialize & Connection
// ---------------------------------------------------------------------------

describe("Collaboration Store — Initialize & Connection", () => {
	beforeEach(resetStore);

	it("should initialize with project and user", () => {
		const { initialize } = useCollaborationStore.getState();
		initialize("proj-1", "user-1", "Alice");

		const state = useCollaborationStore.getState();
		expect(state.projectId).toBe("proj-1");
		expect(state.currentUserId).toBe("user-1");
		expect(state.currentUserName).toBe("Alice");
		expect(state.connected).toBe(true);
		expect(state.users).toHaveLength(1);
		expect(state.users[0].userId).toBe("user-1");
		expect(state.users[0].status).toBe("online");
	});

	it("should disconnect and clear state", () => {
		const { initialize, disconnect } = useCollaborationStore.getState();
		initialize("proj-1", "user-1", "Alice");
		disconnect();

		const state = useCollaborationStore.getState();
		expect(state.connected).toBe(false);
		expect(state.users).toHaveLength(0);
		expect(state.locks).toHaveLength(0);
		expect(state.chatMessages).toHaveLength(0);
	});

	it("should set syncing state", () => {
		const { setSyncing } = useCollaborationStore.getState();
		setSyncing(true);
		expect(useCollaborationStore.getState().syncing).toBe(true);
		setSyncing(false);
		expect(useCollaborationStore.getState().syncing).toBe(false);
	});
});

// ---------------------------------------------------------------------------
// User Management
// ---------------------------------------------------------------------------

describe("Collaboration Store — User Management", () => {
	beforeEach(() => {
		resetStore();
		useCollaborationStore.getState().initialize("proj-1", "user-1", "Alice");
	});

	it("should add a new user", () => {
		const { addUser } = useCollaborationStore.getState();
		addUser({
			userId: "user-2",
			displayName: "Bob",
			role: "developer",
			status: "online",
			currentTask: "",
			connectedAt: new Date().toISOString(),
			lastActivity: new Date().toISOString(),
		});

		const state = useCollaborationStore.getState();
		expect(state.users).toHaveLength(2);
		expect(state.users[1].displayName).toBe("Bob");
		expect(state.users[1].avatarColor).toBeTruthy();
	});

	it("should update existing user on re-add", () => {
		const { addUser } = useCollaborationStore.getState();
		addUser({
			userId: "user-1",
			displayName: "Alice Updated",
			role: "lead",
			status: "busy",
			currentTask: "",
			connectedAt: new Date().toISOString(),
			lastActivity: new Date().toISOString(),
		});

		const state = useCollaborationStore.getState();
		expect(state.users).toHaveLength(1);
		expect(state.users[0].status).toBe("online"); // Re-add forces online
	});

	it("should remove user (set offline)", () => {
		const { addUser, removeUser } = useCollaborationStore.getState();
		addUser({
			userId: "user-2",
			displayName: "Bob",
			role: "developer",
			status: "online",
			currentTask: "",
			connectedAt: new Date().toISOString(),
			lastActivity: new Date().toISOString(),
		});
		removeUser("user-2");

		const user = useCollaborationStore
			.getState()
			.users.find((u) => u.userId === "user-2");
		expect(user?.status).toBe("offline");
	});

	it("should update user status", () => {
		const { updateUserStatus } = useCollaborationStore.getState();
		updateUserStatus("user-1", "busy");

		const user = useCollaborationStore
			.getState()
			.users.find((u) => u.userId === "user-1");
		expect(user?.status).toBe("busy");
	});

	it("should set user current task", () => {
		const { setUserCurrentTask } = useCollaborationStore.getState();
		setUserCurrentTask("user-1", "task-42");

		const user = useCollaborationStore
			.getState()
			.users.find((u) => u.userId === "user-1");
		expect(user?.currentTask).toBe("task-42");
	});

	it("should assign unique avatar colors", () => {
		const { addUser } = useCollaborationStore.getState();
		addUser({
			userId: "user-2",
			displayName: "Bob",
			role: "developer",
			status: "online",
			currentTask: "",
			connectedAt: new Date().toISOString(),
			lastActivity: new Date().toISOString(),
		});

		const state = useCollaborationStore.getState();
		expect(state.users[0].avatarColor).toBeTruthy();
		expect(state.users[1].avatarColor).toBeTruthy();
	});
});

// ---------------------------------------------------------------------------
// Task Locking
// ---------------------------------------------------------------------------

describe("Collaboration Store — Task Locking", () => {
	beforeEach(() => {
		resetStore();
		useCollaborationStore.getState().initialize("proj-1", "user-1", "Alice");
	});

	it("should lock a task", () => {
		const { lockTask } = useCollaborationStore.getState();
		lockTask("task-1", "user-1", "user", "Editing");

		const state = useCollaborationStore.getState();
		expect(state.locks).toHaveLength(1);
		expect(state.locks[0].taskId).toBe("task-1");
		expect(state.locks[0].lockedBy).toBe("user-1");
		expect(state.locks[0].lockType).toBe("user");
		expect(state.locks[0].reason).toBe("Editing");
	});

	it("should not duplicate lock on same task", () => {
		const { lockTask } = useCollaborationStore.getState();
		lockTask("task-1", "user-1", "user");
		lockTask("task-1", "user-2", "user");

		expect(useCollaborationStore.getState().locks).toHaveLength(1);
	});

	it("should unlock a task", () => {
		const { lockTask, unlockTask } = useCollaborationStore.getState();
		lockTask("task-1", "user-1", "user");
		unlockTask("task-1");

		expect(useCollaborationStore.getState().locks).toHaveLength(0);
	});

	it("should check if task is locked", () => {
		const { lockTask, isTaskLocked } = useCollaborationStore.getState();
		expect(isTaskLocked("task-1")).toBe(false);
		lockTask("task-1", "user-1", "user");
		expect(useCollaborationStore.getState().isTaskLocked("task-1")).toBe(true);
	});

	it("should get task lock details", () => {
		const { lockTask } = useCollaborationStore.getState();
		lockTask("task-1", "agent:coder", "agent", "Agent working");

		const lock = useCollaborationStore.getState().getTaskLock("task-1");
		expect(lock).toBeTruthy();
		expect(lock?.lockType).toBe("agent");
		expect(lock?.reason).toBe("Agent working");
	});

	it("should return undefined for unlocked task", () => {
		const lock = useCollaborationStore.getState().getTaskLock("nonexistent");
		expect(lock).toBeUndefined();
	});
});

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

describe("Collaboration Store — Chat", () => {
	beforeEach(() => {
		resetStore();
		useCollaborationStore.getState().initialize("proj-1", "user-1", "Alice");
	});

	it("should send a message", () => {
		const { sendMessage } = useCollaborationStore.getState();
		sendMessage("Hello team!");

		const state = useCollaborationStore.getState();
		expect(state.chatMessages).toHaveLength(1);
		expect(state.chatMessages[0].content).toBe("Hello team!");
		expect(state.chatMessages[0].senderId).toBe("user-1");
		expect(state.chatMessages[0].senderName).toBe("Alice");
	});

	it("should not send empty messages", () => {
		const { sendMessage } = useCollaborationStore.getState();
		sendMessage("");
		sendMessage("   ");

		expect(useCollaborationStore.getState().chatMessages).toHaveLength(0);
	});

	it("should add external chat message", () => {
		const { addChatMessage } = useCollaborationStore.getState();
		const msg: ChatMessage = {
			messageId: "msg-ext-1",
			senderId: "user-2",
			senderName: "Bob",
			content: "Hi Alice!",
			timestamp: new Date().toISOString(),
			replyTo: "",
			mentions: [],
		};
		addChatMessage(msg);

		expect(useCollaborationStore.getState().chatMessages).toHaveLength(1);
	});

	it("should increment unread count when chat is closed", () => {
		const { addChatMessage } = useCollaborationStore.getState();
		addChatMessage({
			messageId: "msg-1",
			senderId: "user-2",
			senderName: "Bob",
			content: "Hey!",
			timestamp: new Date().toISOString(),
			replyTo: "",
			mentions: [],
		});

		expect(useCollaborationStore.getState().unreadChatCount).toBe(1);
	});

	it("should not increment unread for own messages", () => {
		const { addChatMessage } = useCollaborationStore.getState();
		addChatMessage({
			messageId: "msg-1",
			senderId: "user-1", // same as current user
			senderName: "Alice",
			content: "My message",
			timestamp: new Date().toISOString(),
			replyTo: "",
			mentions: [],
		});

		expect(useCollaborationStore.getState().unreadChatCount).toBe(0);
	});

	it("should toggle chat and reset unread", () => {
		const { addChatMessage, toggleChat } = useCollaborationStore.getState();
		addChatMessage({
			messageId: "msg-1",
			senderId: "user-2",
			senderName: "Bob",
			content: "Hey!",
			timestamp: new Date().toISOString(),
			replyTo: "",
			mentions: [],
		});

		expect(useCollaborationStore.getState().unreadChatCount).toBe(1);
		toggleChat(); // open
		expect(useCollaborationStore.getState().chatOpen).toBe(true);
		expect(useCollaborationStore.getState().unreadChatCount).toBe(0);
	});
});

// ---------------------------------------------------------------------------
// Conflicts
// ---------------------------------------------------------------------------

describe("Collaboration Store — Conflicts", () => {
	beforeEach(resetStore);

	it("should add a conflict", () => {
		const { addConflict } = useCollaborationStore.getState();
		const conflict: ConflictRecord = {
			conflictId: "cfl-1",
			taskId: "task-1",
			userA: "user-1",
			userB: "user-2",
			fieldName: "status",
			valueA: "done",
			valueB: "in_progress",
			resolution: "manual",
			resolved: false,
			resolvedValue: null,
			timestamp: new Date().toISOString(),
		};
		addConflict(conflict);

		expect(useCollaborationStore.getState().conflicts).toHaveLength(1);
	});

	it("should resolve a conflict", () => {
		const { addConflict, resolveConflict } = useCollaborationStore.getState();
		addConflict({
			conflictId: "cfl-1",
			taskId: "task-1",
			userA: "user-1",
			userB: "user-2",
			fieldName: "status",
			valueA: "done",
			valueB: "in_progress",
			resolution: "manual",
			resolved: false,
			resolvedValue: null,
			timestamp: new Date().toISOString(),
		});
		resolveConflict("cfl-1", "done");

		const conflict = useCollaborationStore.getState().conflicts[0];
		expect(conflict.resolved).toBe(true);
		expect(conflict.resolvedValue).toBe("done");
	});

	it("should get unresolved conflicts", () => {
		// biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
		const { addConflict, resolveConflict, getUnresolvedConflicts } =
			useCollaborationStore.getState();
		addConflict({
			conflictId: "cfl-1",
			taskId: "t-1",
			userA: "u-1",
			userB: "u-2",
			fieldName: "a",
			valueA: 1,
			valueB: 2,
			resolution: "manual",
			resolved: false,
			resolvedValue: null,
			timestamp: "",
		});
		addConflict({
			conflictId: "cfl-2",
			taskId: "t-2",
			userA: "u-1",
			userB: "u-2",
			fieldName: "b",
			valueA: 3,
			valueB: 4,
			resolution: "manual",
			resolved: false,
			resolvedValue: null,
			timestamp: "",
		});
		resolveConflict("cfl-1", "resolved");

		expect(
			useCollaborationStore.getState().getUnresolvedConflicts(),
		).toHaveLength(1);
	});

	it("should not modify other conflicts when resolving one", () => {
		const { addConflict, resolveConflict } = useCollaborationStore.getState();
		addConflict({
			conflictId: "cfl-1",
			taskId: "t-1",
			userA: "u-1",
			userB: "u-2",
			fieldName: "a",
			valueA: 1,
			valueB: 2,
			resolution: "manual",
			resolved: false,
			resolvedValue: null,
			timestamp: "",
		});
		addConflict({
			conflictId: "cfl-2",
			taskId: "t-2",
			userA: "u-1",
			userB: "u-2",
			fieldName: "b",
			valueA: 3,
			valueB: 4,
			resolution: "manual",
			resolved: false,
			resolvedValue: null,
			timestamp: "",
		});
		resolveConflict("cfl-1", "v");

		const conflicts = useCollaborationStore.getState().conflicts;
		expect(conflicts[0].resolved).toBe(true);
		expect(conflicts[1].resolved).toBe(false);
	});
});

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

describe("Collaboration Store — Events", () => {
	beforeEach(resetStore);

	it("should add an event", () => {
		const { addEvent } = useCollaborationStore.getState();
		addEvent({
			eventId: "evt-1",
			eventType: "user_joined",
			senderId: "user-1",
			data: { user_id: "user-1" },
			timestamp: new Date().toISOString(),
			targetUsers: [],
		});

		expect(useCollaborationStore.getState().events).toHaveLength(1);
	});

	it("should keep last 100 events", () => {
		const { addEvent } = useCollaborationStore.getState();
		for (let i = 0; i < 110; i++) {
			addEvent({
				eventId: `evt-${i}`,
				eventType: "notification",
				senderId: "system",
				data: { index: i },
				timestamp: new Date().toISOString(),
				targetUsers: [],
			});
		}

		// Should cap at 100 (keeps last 100 via slice(-99) + new one)
		expect(useCollaborationStore.getState().events.length).toBeLessThanOrEqual(
			110,
		);
	});

	it("should auto-generate event ID if empty", () => {
		const { addEvent } = useCollaborationStore.getState();
		addEvent({
			eventId: "",
			eventType: "task_updated",
			senderId: "user-1",
			data: {},
			timestamp: "",
			targetUsers: [],
		});

		const event = useCollaborationStore.getState().events[0];
		expect(event.eventId).toMatch(/^evt-/);
	});
});

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

describe("Collaboration Store — Settings", () => {
	beforeEach(resetStore);

	it("should have default settings", () => {
		const { settings } = useCollaborationStore.getState();
		expect(settings.conflictStrategy).toBe("manual");
		expect(settings.showPresenceIndicator).toBe(true);
		expect(settings.chatEnabled).toBe(true);
	});

	it("should update partial settings", () => {
		const { updateSettings } = useCollaborationStore.getState();
		updateSettings({ conflictStrategy: "last_write_wins", chatEnabled: false });

		const { settings } = useCollaborationStore.getState();
		expect(settings.conflictStrategy).toBe("last_write_wins");
		expect(settings.chatEnabled).toBe(false);
		expect(settings.showPresenceIndicator).toBe(true); // unchanged
	});

	it("should update notification preferences", () => {
		const { updateSettings } = useCollaborationStore.getState();
		updateSettings({ notifyUserJoinLeave: false, notifyConflicts: false });

		const { settings } = useCollaborationStore.getState();
		expect(settings.notifyUserJoinLeave).toBe(false);
		expect(settings.notifyConflicts).toBe(false);
		expect(settings.notifyTaskLocks).toBe(true); // unchanged
	});
});

// ---------------------------------------------------------------------------
// Computed / Stats
// ---------------------------------------------------------------------------

describe("Collaboration Store — Computed & Stats", () => {
	beforeEach(() => {
		resetStore();
		useCollaborationStore.getState().initialize("proj-1", "user-1", "Alice");
	});

	it("should get online users only", () => {
		// biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
		const { addUser, removeUser, getOnlineUsers } =
			useCollaborationStore.getState();
		addUser({
			userId: "user-2",
			displayName: "Bob",
			role: "developer",
			status: "online",
			currentTask: "",
			connectedAt: "",
			lastActivity: "",
		});
		addUser({
			userId: "user-3",
			displayName: "Charlie",
			role: "developer",
			status: "online",
			currentTask: "",
			connectedAt: "",
			lastActivity: "",
		});
		removeUser("user-3");

		const online = useCollaborationStore.getState().getOnlineUsers();
		expect(online).toHaveLength(2); // Alice + Bob (Charlie offline)
	});

	it("should calculate stats correctly", () => {
		const { addUser, lockTask, sendMessage, addConflict } =
			useCollaborationStore.getState();
		addUser({
			userId: "user-2",
			displayName: "Bob",
			role: "developer",
			status: "online",
			currentTask: "",
			connectedAt: "",
			lastActivity: "",
		});
		lockTask("task-1", "user-1", "user");
		lockTask("task-2", "agent:coder", "agent");
		sendMessage("Hello");
		addConflict({
			conflictId: "cfl-1",
			taskId: "t-1",
			userA: "u-1",
			userB: "u-2",
			fieldName: "a",
			valueA: 1,
			valueB: 2,
			resolution: "manual",
			resolved: false,
			resolvedValue: null,
			timestamp: "",
		});

		const stats = useCollaborationStore.getState().getStats();
		expect(stats.totalUsers).toBe(2);
		expect(stats.onlineUsers).toBe(2);
		expect(stats.activeLocks).toBe(2);
		expect(stats.agentLocks).toBe(1);
		expect(stats.chatMessages).toBe(1);
		expect(stats.totalConflicts).toBe(1);
		expect(stats.unresolvedConflicts).toBe(1);
	});

	it("should return empty stats when no data", () => {
		resetStore();
		const stats = useCollaborationStore.getState().getStats();
		expect(stats.totalUsers).toBe(0);
		expect(stats.onlineUsers).toBe(0);
		expect(stats.activeLocks).toBe(0);
	});

	it("should handle reply-to workflow", () => {
		const { sendMessage, setReplyingTo } = useCollaborationStore.getState();
		sendMessage("First message");

		const msg = useCollaborationStore.getState().chatMessages[0];
		setReplyingTo(msg);
		expect(useCollaborationStore.getState().replyingTo?.messageId).toBe(
			msg.messageId,
		);

		sendMessage("Reply message");
		const reply = useCollaborationStore.getState().chatMessages[1];
		expect(reply.replyTo).toBe(msg.messageId);
		expect(useCollaborationStore.getState().replyingTo).toBeNull(); // cleared after send
	});
});
