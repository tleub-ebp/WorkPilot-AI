/**
 * Structured phase event parser for Python ↔ TypeScript protocol.
 * Protocol: __EXEC_PHASE__:{"phase":"coding","message":"Starting"}
 */

import { PHASE_MARKER_PREFIX } from '../../shared/constants/phase-protocol';
import { validatePhaseEvent, type PhaseEventPayload } from './phase-event-schema';

export { PHASE_MARKER_PREFIX };
export type { PhaseEventPayload as PhaseEvent };

const DEBUG = process.env.DEBUG?.toLowerCase() === 'true' || process.env.DEBUG === '1';

export function parsePhaseEvent(line: string): PhaseEventPayload | null {
  const markerIndex = line.indexOf(PHASE_MARKER_PREFIX);
  if (markerIndex === -1) {
    return null;
  }

  if (DEBUG) {
  }

  const rawJsonStr = line.slice(markerIndex + PHASE_MARKER_PREFIX.length).trim();
  if (!rawJsonStr) {
    if (DEBUG) {
    }
    return null;
  }

  const jsonStr = extractJsonObject(rawJsonStr);
  if (!jsonStr) {
    if (DEBUG) {
    }
    return null;
  }

  if (DEBUG) {
  }

  try {
    const rawPayload = JSON.parse(jsonStr) as unknown;
    const result = validatePhaseEvent(rawPayload);

    if (!result.success) {
      if (DEBUG) {
      }
      return null;
    }

    if (DEBUG) {
    }

    return result.data;
  } catch (_e) {
    if (DEBUG) {
    }
    return null;
  }
}

export function hasPhaseMarker(line: string): boolean {
  return line.includes(PHASE_MARKER_PREFIX);
}

/**
 * Extract a JSON object from a string that may have trailing garbage.
 * Finds the matching closing brace for the first opening brace.
 */
function extractJsonObject(str: string): string | null {
  const firstBrace = str.indexOf('{');
  if (firstBrace === -1) {
    return null;
  }

  let depth = 0;
  let inString = false;
  let isEscaped = false;

  for (let i = firstBrace; i < str.length; i++) {
    const char = str[i];

    if (isEscaped) {
      isEscaped = false;
      continue;
    }

    if (char === '\\' && inString) {
      isEscaped = true;
      continue;
    }

    if (char === '"') {
      inString = !inString;
      continue;
    }

    if (inString) {
      continue;
    }

    if (char === '{') {
      depth++;
    } else if (char === '}') {
      depth--;
      if (depth === 0) {
        return str.slice(firstBrace, i + 1);
      }
    }
  }

  return null;
}
