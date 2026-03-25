import { describe, it, expect } from 'vitest';
import { parseTaskEvent } from '../task-event-parser';

describe('task-event-parser', () => {
  it('should handle malformed JSON gracefully', () => {
    const malformedInput = '__TASK_EVENT__:{ invalid json }';
    const result = parseTaskEvent(malformedInput);
    expect(result).toBeNull();
  });

  it('should handle non-existent JSON structure', () => {
    const noBracesInput = '__TASK_EVENT__:no braces here';
    const result = parseTaskEvent(noBracesInput);
    expect(result).toBeNull();
  });

  it('should return null for empty JSON string', () => {
    const emptyInput = '__TASK_EVENT__:';
    const result = parseTaskEvent(emptyInput);
    expect(result).toBeNull();
  });

  it('should extract JSON with escaped quotes correctly', () => {
    const input = '__TASK_EVENT__:{"message": "Hello \\"world\\"", "type": "log"}some trailing text';
    const result = parseTaskEvent(input);
    expect(result).not.toBeNull();
    expect(result?.message).toBe('Hello "world"');
  });

  it('should extract JSON with nested objects correctly', () => {
    const input = '__TASK_EVENT__:{"data": {"nested": {"value": 42}}, "type": "result"}';
    const result = parseTaskEvent(input);
    expect(result).not.toBeNull();
    expect(result?.data).toEqual({"nested": {"value": 42}});
  });

  it('should handle JSON with escaped backslashes correctly', () => {
    const input = '__TASK_EVENT__:{"path": "C:\\\\Users\\\\test", "type": "file"}';
    const result = parseTaskEvent(input);
    expect(result).not.toBeNull();
    expect(result?.path).toBe('C:\\Users\\test');
  });

  it('should return null for input without task event prefix', () => {
    const input = '{"message": "no prefix here"}';
    const result = parseTaskEvent(input);
    expect(result).toBeNull();
  });

  it('should handle complex nested JSON with strings and escapes', () => {
    const input = '__TASK_EVENT__:{"config": {"path": "C:\\\\temp\\\\file.txt", "description": "A \\"special\\" file"}, "status": "ready"}extra garbage';
    const result = parseTaskEvent(input);
    expect(result).not.toBeNull();
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    expect((result as any)?.config?.path).toBe('C:\\temp\\file.txt');
    // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
    expect((result as any)?.config?.description).toBe('A "special" file');
  });
});
