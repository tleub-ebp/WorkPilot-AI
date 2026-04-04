// Initialize browser mock before anything else (no-op in Electron)
import "./lib/browser-mock";

// Initialize i18n before React
import "../shared/i18n";

// Initialize Sentry for error tracking (respects user's sentryEnabled setting)
// Fire-and-forget: React rendering proceeds immediately while Sentry initializes async
import { initSentryRenderer } from "./lib/sentry";

try {
	await initSentryRenderer();
} catch (err) {
	console.warn("[Sentry] Failed to initialize renderer:", err);
}

import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles/globals.css";

// biome-ignore lint/style/noNonNullAssertion: value is guaranteed by context
ReactDOM.createRoot(document.getElementById("root")!).render(
	<React.StrictMode>
		<App />
	</React.StrictMode>,
);
