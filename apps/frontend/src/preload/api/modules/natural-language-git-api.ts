export interface NaturalLanguageGitRequest {
	projectPath: string;
	command: string;
	model?: string;
	thinkingLevel?: string;
}

export interface NaturalLanguageGitAPI {
	executeNaturalLanguageGit: (
		request: NaturalLanguageGitRequest,
	) => Promise<void>;
	cancelNaturalLanguageGit: () => Promise<boolean>;
	onNaturalLanguageGitStatus: (
		callback: (status: string) => void,
	) => () => void;
	onNaturalLanguageGitStreamChunk: (
		callback: (chunk: string) => void,
	) => () => void;
	onNaturalLanguageGitError: (callback: (error: string) => void) => () => void;
	onNaturalLanguageGitComplete: (
		callback: (result: {
			generatedCommand: string;
			explanation: string;
			executionOutput: string;
			success: boolean;
		}) => void,
	) => () => void;
	removeNaturalLanguageGitStatusListener: (
		callback: (status: string) => void,
	) => void;
	removeNaturalLanguageGitStreamChunkListener: (
		callback: (chunk: string) => void,
	) => void;
	removeNaturalLanguageGitErrorListener: (
		callback: (error: string) => void,
	) => void;
	removeNaturalLanguageGitCompleteListener: (
		callback: (result: {
			generatedCommand: string;
			explanation: string;
			executionOutput: string;
			success: boolean;
		}) => void,
	) => void;
}
