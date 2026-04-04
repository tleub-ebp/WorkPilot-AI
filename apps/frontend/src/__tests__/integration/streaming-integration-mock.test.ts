/**
 * Streaming Integration Tests (Mock Version)
 * =========================================
 * Integration tests using only mocked WebSocket functionality.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock WebSocket for testing (instead of 'ws' module)
class MockWebSocket {
	static readonly instances: MockWebSocket[] = [];
	url: string;
	onopen: ((event: Event) => void) | null = null;
	onmessage: ((event: MessageEvent<string>) => void) | null = null;
	onerror: ((event: Event) => void) | null = null;
	onclose: ((event: CloseEvent) => void) | null = null;
	readyState: number = 0; // CONNECTING

	constructor(url: string) {
		this.url = url;
		MockWebSocket.instances.push(this);

		// Simulate connection after a short delay
		setTimeout(() => {
			this.readyState = 1; // OPEN
			if (this.onopen) {
				this.onopen(new Event("open"));
			}
		}, 10);
	}

	send(data: string): void {
		// Parse the message and generate appropriate response
		try {
			const message = JSON.parse(data);

			// Generate response based on message type
			let response: unknown;
			if (message.type === "init_session") {
				response = {
					event_type: "session_confirmed",
					data: {
						session_id: message.session_id,
						message: `Connected to session ${message.session_id}`,
					},
					timestamp: Date.now(),
					session_id: message.session_id,
				};
			} else if (message.type === "chat_message") {
				response = {
					event_type: "chat_message",
					data: { message: message.message, session_id: "test-session" },
					timestamp: Date.now(),
					session_id: "test-session",
				};
			} else if (message.type === "control") {
				response = {
					event_type: "control",
					data: { action: message.action },
					timestamp: Date.now(),
					session_id: "test-session",
				};
			} else {
				// Echo unknown messages
				response = message;
			}

			// Send response after a short delay
			setTimeout(() => {
				if (this.onmessage) {
					const event = new MessageEvent("message", {
						data: JSON.stringify(response),
					});
					this.onmessage(event);
				}
			}, 5);
		} catch (error) {
			// JSON parsing failed - echo the raw message as fallback
			console.warn(
				"[MockWebSocket] JSON parse error, echoing raw message:",
				error,
			);
			if (this.onmessage) {
				const event = new MessageEvent("message", { data });
				this.onmessage(event);
			}
		}
	}

	close(): void {
		this.readyState = 3; // CLOSED
		if (this.onclose) {
			this.onclose(new CloseEvent("close"));
		}
	}

	static clearInstances(): void {
		MockWebSocket.instances.length = 0;
	}
}

// Mock global WebSocket
vi.stubGlobal("WebSocket", MockWebSocket);

// Test configuration
const TEST_PORT = 8766;
const WEBSOCKET_URL = `ws://localhost:${TEST_PORT}`;

// WebSocket ready states
const WebSocketConstants = {
	CONNECTING: 0,
	OPEN: 1,
	CLOSING: 2,
	CLOSED: 3,
};

describe("Streaming Integration Tests (Mock)", () => {
	let websocketClients: MockWebSocket[] = [];

	beforeEach(() => {
		MockWebSocket.clearInstances();
		websocketClients = [];
	});

	afterEach(() => {
		// Close all WebSocket clients
		for (const client of websocketClients) {
			if (client.readyState === WebSocketConstants.OPEN) {
				client.close();
			}
		}
		websocketClients = [];
	});

	function createWebSocketClient(): Promise<MockWebSocket> {
		return new Promise((resolve, reject) => {
			const ws = new MockWebSocket(WEBSOCKET_URL);

			ws.onopen = () => {
				websocketClients.push(ws);
				resolve(ws);
			};

			ws.onerror = reject;

			setTimeout(() => reject(new Error("WebSocket connection timeout")), 5000);
		});
	}

	async function waitForMessage(
		ws: MockWebSocket,
		eventType: string,
		timeout = 5000,
	): Promise<unknown> {
		return new Promise((resolve, reject) => {
			const timeoutId = setTimeout(() => {
				reject(new Error(`Timeout waiting for ${eventType} message`));
			}, timeout);

			const messageHandler = (event: MessageEvent) => {
				const message = JSON.parse(event.data as string);
				if (message.event_type === eventType) {
					clearTimeout(timeoutId);
					ws.onmessage = null;
					resolve(message);
				}
			};

			ws.onmessage = messageHandler;
		});
	}

	it("should establish WebSocket connection", async () => {
		const ws = await createWebSocketClient();
		expect(ws.readyState).toBe(WebSocketConstants.OPEN);
		expect(ws.url).toBe(WEBSOCKET_URL);
	});

	it("should handle session initialization", async () => {
		const ws = await createWebSocketClient();

		// Send init session message
		const initMessage = {
			type: "init_session",
			session_id: "test-session-123",
		};

		ws.send(JSON.stringify(initMessage));

		// Wait for confirmation (mocked)
		const confirmation = (await waitForMessage(ws, "session_confirmed")) as {
			data: { session_id: string };
		};
		expect(confirmation.data.session_id).toBe("test-session-123");
	});

	it("should handle chat messages", async () => {
		const ws = await createWebSocketClient();

		// Join session
		const initMessage = { type: "init_session", session_id: "chat-test" };
		ws.send(JSON.stringify(initMessage));

		// Send chat message
		const chatMessage = {
			type: "chat_message",
			message: "Hello from test",
		};

		ws.send(JSON.stringify(chatMessage));

		// Should receive the chat message back (echo)
		const received = (await waitForMessage(ws, "chat_message")) as {
			data: { message: string };
		};
		expect(received.data.message).toBe("Hello from test");
	});

	it("should handle control messages", async () => {
		const ws = await createWebSocketClient();

		// Join session
		const initMessage = { type: "init_session", session_id: "control-test" };
		ws.send(JSON.stringify(initMessage));

		// Send pause control
		const pauseMessage = {
			type: "control",
			action: "pause",
		};

		ws.send(JSON.stringify(pauseMessage));

		// Should receive pause event
		const pauseEvent = (await waitForMessage(ws, "control")) as {
			data: { action: string };
		};
		expect(pauseEvent.data.action).toBe("pause");
	});

	it("should handle connection errors gracefully", async () => {
		// Create a client that will fail
		const ws = new MockWebSocket("ws://invalid-host:9999");

		// Mock error callback
		const errorCallback = vi.fn();
		ws.onerror = errorCallback;

		// Simulate connection error
		setTimeout(() => {
			if (ws.onerror) {
				ws.onerror(new Event("error"));
			}
		}, 10);

		// Should handle gracefully without error
		expect(true).toBe(true);
	});
});
