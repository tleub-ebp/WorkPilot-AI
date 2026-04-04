/**
 * Example usage of the new colored logging system
 *
 * This demonstrates how the scope-based coloring works with different log levels.
 */

import {
	formatFrontendLog,
	frontendDebugLog,
	frontendErrorLog,
	frontendInfoLog,
	frontendSuccessLog,
	frontendWarningLog,
	getColoredScope,
} from "../shared/utils/frontend-colored-logs";

// Enable debug mode for this example
process.env.DEBUG = "true";

// Example usage with different scopes
frontendDebugLog("[UsageMonitor:TRACE] Starting usage monitoring");
frontendInfoLog(
	"[UsageMonitor:PROVIDER_DETECTION] Detected provider: anthropic",
);
frontendSuccessLog("[UsageMonitor:FETCH] Successfully fetched usage data");
frontendWarningLog(
	"[UsageMonitor:CLI] CLI fallback - attempting to use claude usage command",
);
frontendErrorLog(
	"[UsageMonitor:API] API request failed: 429 Too Many Requests",
);

// Example with nested scopes
frontendDebugLog(
	"[UsageMonitor:PROVIDER_DETECTION:OAUTH] Checking OAuth token validity",
);
frontendInfoLog(
	"[UsageMonitor:PROVIDER_DETECTION:API_KEY] Using API key authentication",
);

// Example without scope (will show without scope coloring)
frontendDebugLog("This is a message without a scope");

// Example of using the formatter directly
const _formattedMessage = formatFrontendLog(
	"[CustomScope] This is a custom formatted message",
	"INFO",
	"custom-module",
);

// Example of getting just a colored scope
const _coloredScope = getColoredScope("MyScope");

// Demonstrate consistent color mapping
frontendDebugLog("[MyScope] First message with this scope");
frontendDebugLog("[MyScope] Second message - same color for consistency");
frontendDebugLog("[AnotherScope] Different scope gets different color");
