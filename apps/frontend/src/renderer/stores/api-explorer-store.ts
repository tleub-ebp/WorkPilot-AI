import { create } from "zustand";
import { persist } from "zustand/middleware";

// ── Minimal OpenAPI types ────────────────────────────────────────────────────

export interface OpenApiSchema {
	type?: string;
	format?: string;
	description?: string;
	example?: unknown;
	enum?: unknown[];
	properties?: Record<string, OpenApiSchema>;
	items?: OpenApiSchema;
	required?: string[];
	$ref?: string;
	allOf?: OpenApiSchema[];
	anyOf?: OpenApiSchema[];
	oneOf?: OpenApiSchema[];
	nullable?: boolean;
	default?: unknown;
	additionalProperties?: boolean | OpenApiSchema;
}

export interface OpenApiParameter {
	name: string;
	in: "query" | "path" | "header" | "cookie";
	required?: boolean;
	description?: string;
	schema?: OpenApiSchema;
	example?: unknown;
}

export interface OpenApiRequestBody {
	description?: string;
	required?: boolean;
	content: Record<string, { schema?: OpenApiSchema; example?: unknown }>;
}

export interface OpenApiResponse {
	description?: string;
	content?: Record<string, { schema?: OpenApiSchema; example?: unknown }>;
}

export interface OpenApiOperation {
	operationId?: string;
	summary?: string;
	description?: string;
	tags?: string[];
	parameters?: OpenApiParameter[];
	requestBody?: OpenApiRequestBody;
	responses?: Record<string, OpenApiResponse>;
	deprecated?: boolean;
}

export interface OpenApiSpec {
	openapi: string;
	info: { title: string; version: string; description?: string };
	paths: Record<string, Record<string, OpenApiOperation>>;
	tags?: Array<{ name: string; description?: string }>;
	components?: {
		schemas?: Record<string, OpenApiSchema>;
		parameters?: Record<string, OpenApiParameter>;
	};
	servers?: Array<{ url: string; description?: string }>;
}

// ── Environment ──────────────────────────────────────────────────────────────

export interface ApiEnvironment {
	id: string;
	name: string;
	baseUrl: string;
	headers: Record<string, string>;
	/** Bearer token — auto-injected as Authorization: Bearer <token> if set */
	token?: string;
	isDefault?: boolean;
}

// ── Endpoint key helper ──────────────────────────────────────────────────────

export function makeEndpointKey(method: string, path: string): string {
	return `${method.toUpperCase()}:${path}`;
}

// ── Request Auth ─────────────────────────────────────────────────────────────

export type AuthType =
	| "inherited"
	| "none"
	| "bearer"
	| "basic"
	| "apikey"
	| "oauth2";
export type OAuth2GrantType =
	| "client_credentials"
	| "authorization_code"
	| "password";

export interface RequestAuth {
	type: AuthType;
	bearer: string;
	username: string;
	password: string;
	keyName: string;
	keyValue: string;
	keyLocation: "header" | "query";
	// OAuth 2.0
	oauth2GrantType: OAuth2GrantType;
	oauth2TokenUrl: string;
	oauth2AuthUrl: string;
	oauth2ClientId: string;
	oauth2ClientSecret: string;
	oauth2Scope: string;
	oauth2AccessToken: string;
	oauth2HeaderPrefix: string;
}

export const DEFAULT_REQUEST_AUTH: RequestAuth = {
	type: "inherited",
	bearer: "",
	username: "",
	password: "",
	keyName: "X-API-Key",
	keyValue: "",
	keyLocation: "header",
	oauth2GrantType: "client_credentials",
	oauth2TokenUrl: "",
	oauth2AuthUrl: "",
	oauth2ClientId: "",
	oauth2ClientSecret: "",
	oauth2Scope: "",
	oauth2AccessToken: "",
	oauth2HeaderPrefix: "Bearer",
};

// ── Store ────────────────────────────────────────────────────────────────────

export type SpecSource = "url" | "scan" | null;

interface ApiExplorerState {
	// Spec
	spec: OpenApiSpec | null;
	specUrl: string;
	isLoadingSpec: boolean;
	specError: string | null;
	/** Where the current spec came from: 'url' = loaded via URL, 'scan' = scanned from source code */
	specSource: SpecSource;

	// Background project scan state (not persisted)
	isProjectScanning: boolean;
	projectScanError: string | null;
	/** ID of the project that was last scanned */
	scannedProjectId: string | null;
	/** Timestamp of last successful scan */
	lastProjectScanAt: number | null;

	// Environments (persisted)
	environments: ApiEnvironment[];
	activeEnvironmentId: string;

	// Navigation
	selectedEndpointKey: string | null;
	searchQuery: string;
	collapsedTags: string[];

	// Request builder state (per-session, not persisted)
	requestPathParams: Record<string, string>;
	requestQueryParams: Record<string, string>;
	requestHeaders: Record<string, string>;
	requestBody: string;
	requestAuth: RequestAuth;

	// Response state
	responseStatus: number | null;
	responseStatusText: string;
	responseHeaders: Record<string, string>;
	responseBody: string;
	responseTime: number | null;
	isSendingRequest: boolean;

	// Actions
	setSpec: (spec: OpenApiSpec | null) => void;
	setSpecUrl: (url: string) => void;
	setIsLoadingSpec: (loading: boolean) => void;
	setSpecError: (error: string | null) => void;
	setSpecSource: (source: SpecSource) => void;
	setIsProjectScanning: (scanning: boolean) => void;
	setProjectScanError: (error: string | null) => void;
	setScannedProjectId: (projectId: string | null) => void;
	setLastProjectScanAt: (ts: number | null) => void;

	addEnvironment: (env: Omit<ApiEnvironment, "id">) => void;
	updateEnvironment: (
		id: string,
		updates: Partial<Omit<ApiEnvironment, "id">>,
	) => void;
	removeEnvironment: (id: string) => void;
	setActiveEnvironment: (id: string) => void;

	setSelectedEndpointKey: (key: string | null) => void;
	setSearchQuery: (query: string) => void;
	toggleTag: (tag: string) => void;

	setRequestPathParams: (params: Record<string, string>) => void;
	setRequestQueryParams: (params: Record<string, string>) => void;
	setRequestHeaders: (headers: Record<string, string>) => void;
	setRequestBody: (body: string) => void;
	setRequestAuth: (auth: Partial<RequestAuth>) => void;
	clearRequestState: () => void;

	setResponse: (payload: {
		status: number;
		statusText: string;
		headers: Record<string, string>;
		body: string;
		time: number;
	}) => void;
	clearResponse: () => void;
	setIsSendingRequest: (sending: boolean) => void;
}

const DEFAULT_ENVIRONMENTS: ApiEnvironment[] = [
	{
		id: "local",
		name: "Local",
		baseUrl: "http://localhost:9000",
		headers: {},
		isDefault: true,
	},
];

export const useApiExplorerStore = create<ApiExplorerState>()(
	persist(
		(set) => ({
			// Spec
			spec: null,
			specUrl: "http://localhost:9000/openapi.json",
			isLoadingSpec: false,
			specError: null,
			specSource: null,

			// Project scan
			isProjectScanning: false,
			projectScanError: null,
			scannedProjectId: null,
			lastProjectScanAt: null,

			// Environments
			environments: DEFAULT_ENVIRONMENTS,
			activeEnvironmentId: "local",

			// Navigation
			selectedEndpointKey: null,
			searchQuery: "",
			collapsedTags: [],

			// Request
			requestPathParams: {},
			requestQueryParams: {},
			requestHeaders: {},
			requestBody: "",
			requestAuth: { ...DEFAULT_REQUEST_AUTH },

			// Response
			responseStatus: null,
			responseStatusText: "",
			responseHeaders: {},
			responseBody: "",
			responseTime: null,
			isSendingRequest: false,

			// Spec actions
			setSpec: (spec) => set({ spec }),
			setSpecUrl: (specUrl) => set({ specUrl }),
			setIsLoadingSpec: (isLoadingSpec) => set({ isLoadingSpec }),
			setSpecError: (specError) => set({ specError }),
			setSpecSource: (specSource) => set({ specSource }),
			setIsProjectScanning: (isProjectScanning) => set({ isProjectScanning }),
			setProjectScanError: (projectScanError) => set({ projectScanError }),
			setScannedProjectId: (scannedProjectId) => set({ scannedProjectId }),
			setLastProjectScanAt: (lastProjectScanAt) => set({ lastProjectScanAt }),

			// Environment actions
			addEnvironment: (env) =>
				set((state) => ({
					environments: [
						...state.environments,
						{ ...env, id: `env-${Date.now()}` },
					],
				})),
			updateEnvironment: (id, updates) =>
				set((state) => ({
					environments: state.environments.map((e) =>
						e.id === id ? { ...e, ...updates } : e,
					),
				})),
			removeEnvironment: (id) =>
				set((state) => ({
					environments: state.environments.filter((e) => e.id !== id),
					activeEnvironmentId:
						state.activeEnvironmentId === id
							? (state.environments[0]?.id ?? "local")
							: state.activeEnvironmentId,
				})),
			setActiveEnvironment: (activeEnvironmentId) =>
				set({ activeEnvironmentId }),

			// Navigation actions
			setSelectedEndpointKey: (selectedEndpointKey) =>
				set({
					selectedEndpointKey,
					responseStatus: null,
					responseBody: "",
					responseTime: null,
				}),
			setSearchQuery: (searchQuery) => set({ searchQuery }),
			toggleTag: (tag) =>
				set((state) => ({
					collapsedTags: state.collapsedTags.includes(tag)
						? state.collapsedTags.filter((t) => t !== tag)
						: [...state.collapsedTags, tag],
				})),

			// Request actions
			setRequestPathParams: (requestPathParams) => set({ requestPathParams }),
			setRequestQueryParams: (requestQueryParams) =>
				set({ requestQueryParams }),
			setRequestHeaders: (requestHeaders) => set({ requestHeaders }),
			setRequestBody: (requestBody) => set({ requestBody }),
			setRequestAuth: (auth) =>
				set((state) => ({ requestAuth: { ...state.requestAuth, ...auth } })),
			clearRequestState: () =>
				set({
					requestPathParams: {},
					requestQueryParams: {},
					requestHeaders: {},
					requestBody: "",
					requestAuth: { ...DEFAULT_REQUEST_AUTH },
				}),

			// Response actions
			setResponse: ({ status, statusText, headers, body, time }) =>
				set({
					responseStatus: status,
					responseStatusText: statusText,
					responseHeaders: headers,
					responseBody: body,
					responseTime: time,
					isSendingRequest: false,
				}),
			clearResponse: () =>
				set({
					responseStatus: null,
					responseStatusText: "",
					responseHeaders: {},
					responseBody: "",
					responseTime: null,
				}),
			setIsSendingRequest: (isSendingRequest) => set({ isSendingRequest }),
		}),
		{
			name: "api-explorer-store",
			partialize: (state) => ({
				specUrl: state.specUrl,
				environments: state.environments,
				activeEnvironmentId: state.activeEnvironmentId,
				collapsedTags: state.collapsedTags,
			}),
		},
	),
);
