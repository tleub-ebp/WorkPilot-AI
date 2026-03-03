/**
 * Shared Sentry Privacy Utilities
 *
 * Provides path masking functions for both main and renderer processes
 * to ensure user privacy in error reports.
 *
 * Privacy approach:
 * - Usernames are masked from all file paths
 * - Project paths remain visible (this is expected for debugging)
 * - All event fields are processed: stack traces, breadcrumbs, messages,
 *   tags, contexts, extra data, and user info
 */

// Using a generic event type to work with both main and renderer Sentry SDKs
// The actual type is Sentry.ErrorEvent but we define a compatible interface
// to avoid importing @sentry/electron which has different exports per process
export interface SentryErrorEvent {
  exception?: {
    values?: Array<{
      stacktrace?: {
        frames?: Array<{
          filename?: string;
          abs_path?: string;
        }>;
      };
      value?: string;
    }>;
  };
  breadcrumbs?: Array<{
    message?: string;
    data?: Record<string, unknown>;
  }>;
  message?: string;
  tags?: Record<string, string>;
  contexts?: Record<string, Record<string, unknown> | null>;
  extra?: Record<string, unknown>;
  user?: Record<string, unknown>;
  request?: {
    url?: string;
    headers?: Record<string, string>;
    data?: unknown;
  };
}

/**
 * Mask user-specific paths for privacy
 *
 * Replaces usernames in common OS path patterns:
 * - macOS: /Users/username/... becomes /Users/.../
 * - Windows: C:\Users\username\... becomes C:\Users\...\
 * - Linux: /home/username/... becomes /home/.../
 *
 * Note: Project paths remain visible for debugging purposes.
 * This is intentional - we need to know which file caused the error.
 */
export function maskUserPaths(text: string): string {
  if (!text) return text;

  // macOS: /Users/username/... or /Users/username (at end of string)
  // Uses lookahead to match with or without trailing slash
  text = text.replaceAll(/\/Users\/[^/]+(?=\/|$)/g, '/Users/***');

  // Windows: C:\Users\username\... or C:\Users\username (at end of string)
  // Uses lookahead to match with or without trailing backslash
  text = text.replaceAll(/[A-Z]:\\Users\\[^\\]+(?=\\|$)/gi, (match: string) => {
    const drive = match[0];
    return String.raw`${drive}:\Users\***`;
  });

  // Linux: /home/username/... or /home/username (at end of string)
  // Uses lookahead to match with or without trailing slash
  text = text.replaceAll(/\/home\/[^/]+(?=\/|$)/g, '/home/***');

  return text;
}

/**
 * Recursively mask paths in an object
 * Handles nested objects and arrays
 */
function maskObjectPaths(obj: unknown): unknown {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (typeof obj === 'string') {
    return maskUserPaths(obj);
  }

  if (Array.isArray(obj)) {
    return obj.map(maskObjectPaths);
  }

  if (typeof obj === 'object') {
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(obj as Record<string, unknown>)) {
      result[key] = maskObjectPaths((obj as Record<string, unknown>)[key]);
    }
    return result;
  }

  return obj;
}

/**
 * Process Sentry event to mask sensitive paths
 *
 * Comprehensive masking covers:
 * - Exception stack traces (filename, abs_path)
 * - Exception values (error messages)
 * - Breadcrumbs (messages and data)
 * - Top-level message
 * - Tags (custom tags might contain paths)
 * - Contexts (additional context data)
 * - Extra data (arbitrary data attached to events)
 * - User info (cleared entirely for privacy)
 * - Request data (URLs, headers)
 */
export function processEvent<T extends SentryErrorEvent>(event: T): T {
  processExceptionPaths(event);
  processBreadcrumbs(event);
  processMessage(event);
  processTags(event);
  processContexts(event);
  processExtraData(event);
  processUserInfo(event);
  processRequestData(event);
  
  return event;
}

/**
 * Process exception stack traces and values
 */
function processExceptionPaths<T extends SentryErrorEvent>(event: T): void {
  if (!event.exception?.values) return;
  
  for (const exception of event.exception.values) {
    processStacktraceFrames(exception);
    processExceptionValue(exception);
  }
}

/**
 * Process stacktrace frames for an exception
 */
function processStacktraceFrames(exception: { stacktrace?: { frames?: Array<{ filename?: string; abs_path?: string }> } }): void {
  if (!exception.stacktrace?.frames) return;
  
  for (const frame of exception.stacktrace.frames) {
    if (frame.filename) {
      frame.filename = maskUserPaths(frame.filename);
    }
    if (frame.abs_path) {
      frame.abs_path = maskUserPaths(frame.abs_path);
    }
  }
}

/**
 * Process exception value
 */
function processExceptionValue(exception: { value?: string }): void {
  if (exception.value) {
    exception.value = maskUserPaths(exception.value);
  }
}

/**
 * Process breadcrumb messages and data
 */
function processBreadcrumbs<T extends SentryErrorEvent>(event: T): void {
  if (!event.breadcrumbs) return;
  
  for (const breadcrumb of event.breadcrumbs) {
    if (breadcrumb.message) {
      breadcrumb.message = maskUserPaths(breadcrumb.message);
    }
    if (breadcrumb.data) {
      breadcrumb.data = maskObjectPaths(breadcrumb.data) as Record<string, unknown>;
    }
  }
}

/**
 * Process top-level message
 */
function processMessage<T extends SentryErrorEvent>(event: T): void {
  if (event.message) {
    event.message = maskUserPaths(event.message);
  }
}

/**
 * Process tag values
 */
function processTags<T extends SentryErrorEvent>(event: T): void {
  if (!event.tags) return;
  
  for (const key of Object.keys(event.tags)) {
    if (typeof event.tags[key] === 'string') {
      event.tags[key] = maskUserPaths(event.tags[key]);
    }
  }
}

/**
 * Process context objects recursively
 */
function processContexts<T extends SentryErrorEvent>(event: T): void {
  if (!event.contexts) return;
  
  for (const contextKey of Object.keys(event.contexts)) {
    const context = event.contexts[contextKey];
    if (context && typeof context === 'object') {
      event.contexts[contextKey] = maskObjectPaths(context) as Record<string, unknown>;
    }
  }
}

/**
 * Process extra data recursively
 */
function processExtraData<T extends SentryErrorEvent>(event: T): void {
  if (event.extra) {
    event.extra = maskObjectPaths(event.extra) as Record<string, unknown>;
  }
}

/**
 * Clear user info entirely for privacy
 */
function processUserInfo<T extends SentryErrorEvent>(event: T): void {
  if (event.user) {
    event.user = {};
  }
}

/**
 * Process request data (URLs, headers, and data)
 */
function processRequestData<T extends SentryErrorEvent>(event: T): void {
  if (!event.request) return;
  
  if (event.request.url) {
    event.request.url = maskUserPaths(event.request.url);
  }
  
  processRequestHeaders(event.request);
  
  if (event.request.data) {
    event.request.data = maskObjectPaths(event.request.data);
  }
}

/**
 * Process request headers
 */
function processRequestHeaders(request: { headers?: Record<string, string> }): void {
  if (!request.headers) return;
  
  for (const key of Object.keys(request.headers)) {
    if (typeof request.headers[key] === 'string') {
      request.headers[key] = maskUserPaths(request.headers[key]);
    }
  }
}

/**
 * Production trace sample rate
 * 10% of transactions are sampled for performance monitoring
 */
export const PRODUCTION_TRACE_SAMPLE_RATE = 0.1;
