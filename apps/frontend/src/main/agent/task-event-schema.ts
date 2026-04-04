import { z } from "zod";

export const TaskEventSchema = z
	.object({
		type: z.string().optional(),
		taskId: z.string().optional(),
		specId: z.string().optional(),
		projectId: z.string().optional(),
		timestamp: z.string().optional(),
		eventId: z.string().optional(),
		sequence: z.number().int().min(0).optional(),
	})
	.passthrough();

export type TaskEventPayload = z.infer<typeof TaskEventSchema>;

export interface ValidationResult {
	success: true;
	data: TaskEventPayload;
}

export interface ValidationError {
	success: false;
	error: z.ZodError;
}

export type ParseResult = ValidationResult | ValidationError;

export function validateTaskEvent(data: unknown): ParseResult {
	const result = TaskEventSchema.safeParse(data);
	if (result.success) {
		return { success: true, data: result.data as TaskEventPayload };
	}
	return { success: false, error: result.error };
}
