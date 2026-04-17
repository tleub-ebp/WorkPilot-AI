import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { ipcMain, net } from "electron";
import { IPC_CHANNELS } from "../../shared/constants";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DetectedRoute {
	path: string;
	methods: string[];
	summary?: string;
	tag: string;
	file: string;
	framework: string;
	requiresAuth: boolean;
}

// ── Directory walker ──────────────────────────────────────────────────────────

const EXCLUDED_DIRS = new Set([
	"node_modules",
	".git",
	"__pycache__",
	"dist",
	"build",
	".next",
	".nuxt",
	"coverage",
	".cache",
	".venv",
	"venv",
	"out",
	".turbo",
	".worktrees",
	"vendor",
	"target",
	".gradle",
	".maven",
	"obj",
	"bin",
	".vs",
]);

function walkFiles(
	dir: string,
	extensions: string[],
	maxDepth = 12,
	depth = 0,
): string[] {
	if (depth > maxDepth) return [];
	let results: string[] = [];
	let entries: string[];
	try {
		entries = readdirSync(dir);
	} catch {
		return [];
	}
	for (const entry of entries) {
		if (EXCLUDED_DIRS.has(entry)) continue;
		const full = path.join(dir, entry);
		// biome-ignore lint/suspicious/noImplicitAnyLet: type inferred from assignment
		let stat;
		try {
			stat = statSync(full);
		} catch {
			continue;
		}
		if (stat.isDirectory()) {
			results = results.concat(
				walkFiles(full, extensions, maxDepth, depth + 1),
			);
		} else if (extensions.some((ext) => full.endsWith(ext))) {
			results.push(full);
		}
	}
	return results;
}

function readFile(filePath: string): string | null {
	try {
		return readFileSync(filePath, "utf8");
	} catch {
		return null;
	}
}

// ── Language detectors ────────────────────────────────────────────────────────

/** ASP.NET Core — C# controllers */
function detectDotnet(projectPath: string): DetectedRoute[] {
	const routes: DetectedRoute[] = [];
	const files = walkFiles(projectPath, [".cs"]);
	const verbMap: Record<string, string> = {
		Get: "GET",
		Post: "POST",
		Put: "PUT",
		Delete: "DELETE",
		Patch: "PATCH",
	};

	for (const filePath of files) {
		const content = readFile(filePath);
		if (!content || !/class\s+\w+Controller/.test(content)) continue;

		// Class-level [Route("...")] + controller name
		const classMatch = content.match(
			/\[Route\(["']([^"']*)["'].*?\)\][\s\S]{0,300}?class\s+(\w+)Controller/,
		);
		let classBase: string;
		let controllerName: string;

		if (classMatch) {
			controllerName = classMatch[2];
			classBase = classMatch[1].replace(
				"[controller]",
				controllerName.toLowerCase(),
			);
		} else {
			const cn = content.match(/class\s+(\w+)Controller/);
			if (!cn) continue;
			controllerName = cn[1];
			classBase = `/${controllerName.toLowerCase()}s`;
		}
		if (!classBase.startsWith("/")) classBase = `/${classBase}`;

		const tag = controllerName.toLowerCase();

		// Method-level [HttpVerb] attributes with optional sub-path + XML doc summary
		// Two-pass approach to avoid ReDoS from nested quantifiers
		const methodRe =
			/\[Http(Get|Post|Put|Delete|Patch)(?:\(["']?([^"')\]]*?)["']?\))?\]/g;

		let m: RegExpExecArray | null;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = methodRe.exec(content)) !== null) {
			// Extract XML doc summary from the preceding context (separate pass to avoid ReDoS)
			const preceding = content.slice(Math.max(0, m.index - 600), m.index);
			const summaryMatch = preceding.match(
				/<summary>\s*([\s\S]*?)<\/summary>/,
			);
			const summary = summaryMatch
				? summaryMatch[1]
						.split("\n")
						.map((l) => l.replace(/^\s*\/\/\/\s*/, "").trim())
						.filter(Boolean)
						.join(" ") || undefined
				: undefined;

			const verb = m[1];
			const subPath = (m[2] ?? "").trim().replace(/^["']|["']$/g, "");
			const method = verbMap[verb] ?? verb.toUpperCase();

			const fullPath = subPath
				? `${classBase}/${subPath}`.replace(/\/+/g, "/")
				: classBase;

			const ctx = content.slice(Math.max(0, m.index - 300), m.index);
			const requiresAuth =
				/\[Authorize\b/.test(ctx) && !/\[AllowAnonymous\]/.test(ctx);

			routes.push({
				path: fullPath,
				methods: [method],
				summary,
				tag,
				file: path.relative(projectPath, filePath),
				framework: "ASP.NET Core",
				requiresAuth,
			});
		}
	}
	return routes;
}

/** FastAPI / Flask / Django — Python */
function detectPython(projectPath: string): DetectedRoute[] {
	const routes: DetectedRoute[] = [];
	const files = walkFiles(projectPath, [".py"]);

	for (const filePath of files) {
		const content = readFile(filePath);
		if (!content) continue;
		const tag = path.basename(filePath, ".py");

		// FastAPI: @app.get("/path") @router.post("/path")
		const fastapiRe =
			/@(?:app|router)\.(get|post|put|delete|patch)\(["']([^"']+)["']/g;
		let m: RegExpExecArray | null;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = fastapiRe.exec(content)) !== null) {
			routes.push({
				path: m[2],
				methods: [m[1].toUpperCase()],
				tag,
				file: path.relative(projectPath, filePath),
				framework: "FastAPI",
				requiresAuth: /Depends/.test(content.slice(m.index, m.index + 120)),
			});
		}

		// Flask: @app.route("/path", methods=["GET","POST"])
		const flaskRe =
			/@(?:app|bp|blueprint)\.route\(["']([^"']+)["'](?:[^)]*methods\s*=\s*\[([^\]]+)\])?/g;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = flaskRe.exec(content)) !== null) {
			const methods = m[2]
				? m[2]
						.split(",")
						.map((x) => x.trim().replace(/["']/g, "").toUpperCase())
				: ["GET"];
			routes.push({
				path: m[1],
				methods,
				tag,
				file: path.relative(projectPath, filePath),
				framework: "Flask",
				requiresAuth: /login_required/.test(
					content.slice(Math.max(0, m.index - 100), m.index),
				),
			});
		}
	}
	return routes;
}

/** Express / Fastify / NestJS — TypeScript / JavaScript */
function detectExpress(projectPath: string): DetectedRoute[] {
	const routes: DetectedRoute[] = [];
	const files = walkFiles(projectPath, [".ts", ".js", ".mts", ".mjs"]);

	for (const filePath of files) {
		const content = readFile(filePath);
		if (!content) continue;
		const tag = path.basename(filePath).replace(/\.(ts|js|mts|mjs)$/, "");

		// Express/Fastify: router.get('/path', ...)  app.post('/path', ...)
		const expressRe =
			/(?:app|router|server)\.(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']/g;
		let m: RegExpExecArray | null;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = expressRe.exec(content)) !== null) {
			routes.push({
				path: m[2],
				methods: [m[1].toUpperCase()],
				tag,
				file: path.relative(projectPath, filePath),
				framework: "Express",
				requiresAuth: false,
			});
		}

		// NestJS decorators: @Get('/path') @Post('/path') etc.
		const nestRe =
			/@(Get|Post|Put|Delete|Patch)\s*\(\s*["']?([^"')\s]*)["']?\s*\)/g;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = nestRe.exec(content)) !== null) {
			const p = m[2] ? (m[2].startsWith("/") ? m[2] : `/${m[2]}`) : "/";
			routes.push({
				path: p,
				methods: [m[1].toUpperCase()],
				tag,
				file: path.relative(projectPath, filePath),
				framework: "NestJS",
				requiresAuth: false,
			});
		}
	}
	return routes;
}

/** Spring Boot — Java */
function detectSpring(projectPath: string): DetectedRoute[] {
	const routes: DetectedRoute[] = [];
	const files = walkFiles(projectPath, [".java"]);
	const verbMap: Record<string, string> = {
		GetMapping: "GET",
		PostMapping: "POST",
		PutMapping: "PUT",
		DeleteMapping: "DELETE",
		PatchMapping: "PATCH",
	};

	for (const filePath of files) {
		const content = readFile(filePath);
		if (!content || !/@(?:Rest)?Controller/.test(content)) continue;
		const tag = path
			.basename(filePath, ".java")
			.replace("Controller", "")
			.toLowerCase();

		// Class-level @RequestMapping
		const clsMatch = content.match(
			/@RequestMapping\(\s*["']?([^"')\s]+)["']?\s*\)/,
		);
		const classBase = clsMatch
			? clsMatch[1].startsWith("/")
				? clsMatch[1]
				: `/${clsMatch[1]}`
			: "";

		const methodRe =
			/@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*\(\s*(?:value\s*=\s*)?["']?([^"')\s]*)["']?\s*\)/g;
		let m: RegExpExecArray | null;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = methodRe.exec(content)) !== null) {
			const method = verbMap[m[1]] ?? "GET";
			const sub = m[2] ? (m[2].startsWith("/") ? m[2] : `/${m[2]}`) : "";
			const fullPath = `${classBase}${sub}`.replace(/\/+/g, "/") || "/";
			routes.push({
				path: fullPath,
				methods: [method],
				tag,
				file: path.relative(projectPath, filePath),
				framework: "Spring Boot",
				requiresAuth: false,
			});
		}
	}
	return routes;
}

/** Go — Gin / Echo / Chi / Fiber */
function detectGo(projectPath: string): DetectedRoute[] {
	const routes: DetectedRoute[] = [];
	const files = walkFiles(projectPath, [".go"]);

	for (const filePath of files) {
		const content = readFile(filePath);
		if (!content) continue;
		const tag = path.basename(filePath, ".go");

		const goRe =
			/(?:r|e|app|router)\.(GET|POST|PUT|DELETE|PATCH|Get|Post|Put|Delete|Patch)\s*\(\s*["']([^"']+)["']/g;
		let m: RegExpExecArray | null;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = goRe.exec(content)) !== null) {
			routes.push({
				path: m[2],
				methods: [m[1].toUpperCase()],
				tag,
				file: path.relative(projectPath, filePath),
				framework: "Go",
				requiresAuth: false,
			});
		}
	}
	return routes;
}

/** Rust — Axum / Actix */
function detectRust(projectPath: string): DetectedRoute[] {
	const routes: DetectedRoute[] = [];
	const files = walkFiles(projectPath, [".rs"]);

	for (const filePath of files) {
		const content = readFile(filePath);
		if (!content) continue;
		const tag = path.basename(filePath, ".rs");

		const axumRe =
			/\.route\s*\(\s*["']([^"']+)["']\s*,\s*(get|post|put|delete|patch)/g;
		let m: RegExpExecArray | null;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = axumRe.exec(content)) !== null) {
			routes.push({
				path: m[1],
				methods: [m[2].toUpperCase()],
				tag,
				file: path.relative(projectPath, filePath),
				framework: "Rust/Axum",
				requiresAuth: false,
			});
		}
	}
	return routes;
}

/** Rails — Ruby config/routes.rb */
function detectRails(projectPath: string): DetectedRoute[] {
	const routes: DetectedRoute[] = [];
	const files = walkFiles(projectPath, [".rb"]).filter((f) =>
		f.endsWith("routes.rb"),
	);

	for (const filePath of files) {
		const content = readFile(filePath);
		if (!content) continue;

		const verbRe = /(get|post|put|patch|delete)\s+['"]([^'"]+)['"]/gi;
		let m: RegExpExecArray | null;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = verbRe.exec(content)) !== null) {
			const p = m[2].startsWith("/") ? m[2] : `/${m[2]}`;
			routes.push({
				path: p,
				methods: [m[1].toUpperCase()],
				tag: "routes",
				file: path.relative(projectPath, filePath),
				framework: "Rails",
				requiresAuth: false,
			});
		}

		const resourcesRe = /resources\s+:(\w+)/g;
		// biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
		while ((m = resourcesRe.exec(content)) !== null) {
			const base = `/${m[1]}`;
			for (const [p, method] of [
				[base, "GET"],
				[base, "POST"],
				[`${base}/{id}`, "GET"],
				[`${base}/{id}`, "PUT"],
				[`${base}/{id}`, "DELETE"],
			] as [string, string][]) {
				routes.push({
					path: p,
					methods: [method],
					tag: m[1],
					file: path.relative(projectPath, filePath),
					framework: "Rails",
					requiresAuth: false,
				});
			}
		}
	}
	return routes;
}

// ── OpenAPI spec builder ──────────────────────────────────────────────────────

function buildOpenApiSpec(
	routes: DetectedRoute[],
	projectName: string,
): Record<string, unknown> {
	const paths: Record<string, Record<string, unknown>> = {};
	const tags = new Set<string>();

	for (const route of routes) {
		// Convert {param} style (ASP.NET / Java) and [param] style to OpenAPI {param}
		const openApiPath = route.path
			.replace(/\[([^\]]+)\]/g, "{$1}")
			.replace(/\/+/g, "/");

		if (!paths[openApiPath]) paths[openApiPath] = {};

		for (const method of route.methods) {
			const op: Record<string, unknown> = {
				tags: [route.tag],
				summary: route.summary ?? `${method} ${openApiPath}`,
				operationId: `${method.toLowerCase()}_${openApiPath
					.replace(/[^a-zA-Z0-9]/g, "_")
					.replace(/_+/g, "_")
					.replace(/^_|_$/g, "")}`,
				responses: { "200": { description: "Success" } },
			};

			if (route.requiresAuth) {
				op.security = [{ bearerAuth: [] }];
			}

			// Extract path parameters from the path
			const pathParams = [...openApiPath.matchAll(/\{([^}]+)\}/g)].map(
				(pm) => ({
					name: pm[1],
					in: "path",
					required: true,
					schema: { type: "string" },
				}),
			);
			if (pathParams.length > 0) op.parameters = pathParams;

			paths[openApiPath][method.toLowerCase()] = op;
			tags.add(route.tag);
		}
	}

	return {
		openapi: "3.0.0",
		info: {
			title: projectName,
			version: "0.0.0",
			description: `API endpoints scanned from project source code (${routes.length} endpoints detected).`,
		},
		tags: [...tags].map((name) => ({ name })),
		paths,
		components: {
			securitySchemes: {
				bearerAuth: { type: "http", scheme: "bearer", bearerFormat: "JWT" },
			},
		},
	};
}

// ── IPC handler registration ──────────────────────────────────────────────────

interface ProxyRequestPayload {
	url: string;
	method: string;
	headers: Record<string, string>;
	body?: string;
}

interface ProxyResponse {
	success: boolean;
	status?: number;
	statusText?: string;
	headers?: Record<string, string>;
	body?: string;
	time?: number;
	error?: string;
}

export function registerApiExplorerHandlers(): void {
	ipcMain.handle(
		IPC_CHANNELS.API_EXPLORER_SCAN_ROUTES,
		(_event, projectPath: string, projectName: string) => {
			try {
				const routes: DetectedRoute[] = [
					...detectDotnet(projectPath),
					...detectPython(projectPath),
					...detectExpress(projectPath),
					...detectSpring(projectPath),
					...detectGo(projectPath),
					...detectRust(projectPath),
					...detectRails(projectPath),
				];

				const spec = buildOpenApiSpec(routes, projectName || "Project");
				return { success: true, data: spec, routeCount: routes.length };
			} catch (err) {
				return { success: false, error: String(err) };
			}
		},
	);

	// HTTP proxy — makes requests from main process to bypass renderer CSP
	ipcMain.handle(
		IPC_CHANNELS.API_EXPLORER_PROXY_REQUEST,
		async (_event, payload: ProxyRequestPayload): Promise<ProxyResponse> => {
			const start = Date.now();
			try {
				const res = await net.fetch(payload.url, {
					method: payload.method,
					headers: payload.headers,
					body: payload.body ?? undefined,
				});

				const resHeaders: Record<string, string> = {};
				res.headers.forEach((val: string, key: string) => {
					resHeaders[key] = val;
				});

				const contentType = res.headers.get("content-type") ?? "";
				let body: string;
				if (
					contentType.includes("application/json") ||
					contentType.includes("text/")
				) {
					body = await res.text();
				} else {
					body = `[Binary content: ${contentType}]`;
				}

				return {
					success: true,
					status: res.status,
					statusText: res.statusText,
					headers: resHeaders,
					body,
					time: Date.now() - start,
				};
			} catch (err) {
				return {
					success: false,
					status: 0,
					statusText: "Network Error",
					headers: {},
					body: String(err),
					time: Date.now() - start,
					error: String(err),
				};
			}
		},
	);
}
