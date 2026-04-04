import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { Terminal as XTerminal } from "@xterm/xterm";
import { useCallback, useEffect, useRef, useState } from "react";
import "@xterm/xterm/css/xterm.css";
import { AlertCircle, CheckCircle2, Loader2, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";

// Debug logging - only active when DEBUG=true (npm run dev:debug)
const DEBUG = typeof process !== "undefined" && process.env?.DEBUG === "true";
const debugLog = (...args: unknown[]) => {
	if (DEBUG) console.warn("[CopilotAuthTerminal:DEBUG]", ...args);
};

interface CopilotAuthTerminalProps {
	/** Terminal ID for this auth session */
	terminalId: string;
	/** Profile name being authenticated */
	profileName: string;
	/** Callback when terminal is closed */
	onClose: () => void;
	/** Callback when authentication succeeds */
	onAuthSuccess?: (username?: string) => void;
	/** Callback when authentication fails */
	onAuthError?: (error: string) => void;
}

/**
 * Embedded terminal component for GitHub Copilot authentication.
 * Shows a minimal terminal where users can run `gh auth login` to authenticate.
 * Automatically detects authentication success via terminal output monitoring.
 */
export function CopilotAuthTerminal({
	terminalId,
	profileName,
	onClose,
	onAuthSuccess,
	onAuthError,
}: CopilotAuthTerminalProps) {
	const { t } = useTranslation("common");
	const terminalRef = useRef<HTMLDivElement>(null);
	const xtermRef = useRef<XTerminal | null>(null);
	const fitAddonRef = useRef<FitAddon | null>(null);
	const isCreatedRef = useRef(false);
	const cleanupFnsRef = useRef<(() => void)[]>([]);

	const [status, setStatus] = useState<
		"loading" | "running" | "success" | "error"
	>("loading");
	const [statusMessage, setStatusMessage] = useState<string>("");
	const [canClose, setCanClose] = useState(false);

	/**
	 * Clean up terminal and event listeners
	 */
	const cleanup = useCallback(() => {
		debugLog("Cleaning up terminal");

		// Call all cleanup functions
		cleanupFnsRef.current.forEach((cleanup) => {
			try {
				cleanup();
			} catch (error) {
				console.warn("[CopilotAuthTerminal] Cleanup error:", error);
			}
		});
		cleanupFnsRef.current = [];

		// Dispose terminal
		if (xtermRef.current) {
			try {
				xtermRef.current.dispose();
			} catch (error) {
				console.warn("[CopilotAuthTerminal] Terminal dispose error:", error);
			}
			xtermRef.current = null;
		}

		isCreatedRef.current = false;
	}, []);

	/**
	 * Handle terminal output and detect authentication success
	 */
	const handleTerminalData = useCallback(
		(data: string) => {
			debugLog("Terminal data received:", data);

			// Check for authentication success indicators
			if (
				data.includes("Logged in to") ||
				data.includes("Authentication complete")
			) {
				setStatus("success");
				setStatusMessage(t("githubCopilot.authSuccess"));
				setCanClose(true);

				// Extract username if available
				const usernameMatch = data.match(/as\s+(\S+)/);
				const username = usernameMatch ? usernameMatch[1] : undefined;

				setTimeout(() => {
					onAuthSuccess?.(username);
				}, 1000);
			}

			// Check for authentication failure indicators
			if (data.includes("Authentication failed") || data.includes("Error:")) {
				setStatus("error");
				setStatusMessage(t("githubCopilot.errors.authFailed"));
				setCanClose(true);

				setTimeout(() => {
					onAuthError?.(data);
				}, 1000);
			}
		},
		[t, onAuthSuccess, onAuthError],
	);

	/**
	 * Create and initialize terminal
	 */
	const createTerminal = useCallback(async () => {
		if (!terminalRef.current || isCreatedRef.current) {
			return;
		}

		debugLog("Creating terminal with ID:", terminalId);

		try {
			// Create terminal instance
			const terminal = new XTerminal({
				cursorBlink: true,
				cursorStyle: "block",
				fontSize: 12,
				fontFamily: 'Consolas, "Courier New", monospace',
				theme: {
					background: "#1a1a1a",
					foreground: "#ffffff",
					cursor: "#ffffff",
					// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
				} as any,
				rows: 20,
				cols: 80,
			});

			// Create addons
			const fitAddon = new FitAddon();
			const webLinksAddon = new WebLinksAddon();

			// Load addons
			terminal.loadAddon(fitAddon);
			terminal.loadAddon(webLinksAddon);

			// Store references
			xtermRef.current = terminal;
			fitAddonRef.current = fitAddon;

			// Open terminal in DOM
			terminal.open(terminalRef.current);
			fitAddon.fit();

			// Set up terminal data handler
			terminal.onData((data: string) => {
				// Send data to terminal process
				window.electronAPI?.sendTerminalInput?.(terminalId, data);
			});

			// Set up terminal output listener
			const removeOutputListener = window.electronAPI?.onTerminalOutput?.(
				(id: string, data: string) => {
					if (id === terminalId) {
						terminal.write(data);
						handleTerminalData(data);
					}
				},
			);

			// Set up terminal exit listener
			const removeExitListener = window.electronAPI?.onTerminalExit?.(
				(id: string, code: number) => {
					if (id === terminalId) {
						debugLog("Terminal exited with code:", code);
						if (code !== 0 && status !== "success" && status !== "error") {
							setStatus("error");
							setStatusMessage(t("githubCopilot.errors.authFailed"));
							setCanClose(true);
							onAuthError?.(`Terminal exited with code ${code}`);
						}
					}
				},
			);

			// Store cleanup functions
			if (removeOutputListener) {
				cleanupFnsRef.current.push(removeOutputListener);
			}
			if (removeExitListener) {
				cleanupFnsRef.current.push(removeExitListener);
			}

			// Send initial authentication command
			setTimeout(() => {
				terminal.writeln("\x1b[36mGitHub Copilot Authentication\x1b[0m");
				terminal.writeln("\x1b[90mPlease run: gh auth login\x1b[0m");
				terminal.writeln("");

				// Start the authentication process
				window.electronAPI?.sendTerminalInput?.(terminalId, "gh auth login\r");
			}, 500);

			isCreatedRef.current = true;
			setStatus("running");
			setStatusMessage(t("githubCopilot.instructions.authentication.title"));

			debugLog("Terminal created successfully");
		} catch (error) {
			console.error("[CopilotAuthTerminal] Failed to create terminal:", error);
			setStatus("error");
			setStatusMessage(t("githubCopilot.errors.authFailed"));
			setCanClose(true);
			onAuthError?.(error instanceof Error ? error.message : "Unknown error");
		}
	}, [terminalId, handleTerminalData, status, t, onAuthError]);

	/**
	 * Handle close button click
	 */
	const handleClose = useCallback(() => {
		if (!canClose && status === "running") {
			// Allow closing but warn user
			if (confirm(t("githubCopilot.authCloseWarning"))) {
				cleanup();
				onClose();
			}
			return;
		}

		cleanup();
		onClose();
	}, [canClose, status, cleanup, onClose, t]);

	/**
	 * Handle window resize
	 */
	const handleResize = useCallback(() => {
		if (fitAddonRef.current && xtermRef.current) {
			try {
				fitAddonRef.current.fit();
			} catch (error) {
				console.warn("[CopilotAuthTerminal] Resize fit error:", error);
			}
		}
	}, []);

	// Set up terminal on mount
	useEffect(() => {
		createTerminal();

		// Set up resize listener
		window.addEventListener("resize", handleResize);

		return () => {
			window.removeEventListener("resize", handleResize);
			cleanup();
		};
	}, [createTerminal, cleanup, handleResize]);

	// Get status icon and color
	const getStatusIcon = () => {
		switch (status) {
			case "loading":
				return <Loader2 className="w-4 h-4 animate-spin" />;
			case "success":
				return <CheckCircle2 className="w-4 h-4 text-green-500" />;
			case "error":
				return <AlertCircle className="w-4 h-4 text-red-500" />;
			default:
				return null;
		}
	};

	const getStatusColor = () => {
		switch (status) {
			case "loading":
				return "text-blue-500";
			case "success":
				return "text-green-500";
			case "error":
				return "text-red-500";
			default:
				return "text-gray-500";
		}
	};

	return (
		<div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
			{/* Header */}
			<div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
				<div className="flex items-center space-x-2">
					<div className={cn("flex items-center space-x-1", getStatusColor())}>
						{getStatusIcon()}
						<span className="text-sm font-medium">
							{t("githubCopilot.authTerminalTitle")}
						</span>
					</div>
					<span className="text-xs text-gray-400">{profileName}</span>
				</div>

				<Button
					variant="ghost"
					size="sm"
					onClick={handleClose}
					className="h-6 w-6 p-0 text-gray-400 hover:text-white hover:bg-gray-700"
				>
					<X className="w-4 h-4" />
				</Button>
			</div>

			{/* Status message */}
			{statusMessage && (
				<div
					className={cn(
						"px-3 py-1 text-xs border-b",
						status === "success"
							? "bg-green-900/20 text-green-400 border-green-800"
							: status === "error"
								? "bg-red-900/20 text-red-400 border-red-800"
								: "bg-blue-900/20 text-blue-400 border-blue-800",
					)}
				>
					{statusMessage}
				</div>
			)}

			{/* Terminal */}
			<div
				ref={terminalRef}
				className="flex-1 overflow-hidden"
				style={{ minHeight: "200px" }}
			/>
		</div>
	);
}
