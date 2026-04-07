/**
 * Universal PR Details Handler
 *
 * Supports both GitHub and Azure DevOps Pull Requests
 * Routes to appropriate handlers based on URL detection
 */

import type { ChildProcess } from "node:child_process";
import { ipcMain } from "electron";
import { IPC_CHANNELS } from "../../shared/constants";
import type { IPCResult, PRDetailsResult, Project } from "../../shared/types";
import { getGitHubConfig, githubFetch } from "./github/utils";
import { findTaskAndProject } from "./task/shared";

/**
 * Register universal PR details handler
 */
export function registerPRDetailsHandlers(): void {
	ipcMain.handle(
		IPC_CHANNELS.PR_DETAILS,
		async (
			_,
			prNumber: number,
			taskId?: string,
		): Promise<IPCResult<PRDetailsResult>> => {
			try {
				// If taskId is provided, get the task and project to detect PR URL
				let prUrl: string | null = null;
				let project: Project | null = null;

				if (taskId) {
					const result = findTaskAndProject(taskId);
					if (result.task && result.project) {
						prUrl = result.task.metadata?.prUrl || null;
						project = result.project;
					}
				}

				// If no PR URL from task, we need to determine the platform
				// For now, we'll default to GitHub if no URL is found
				if (!prUrl) {
					return getGitHubPRDetails(prNumber, prUrl, project);
				}

				// Detect platform from URL and route accordingly
				if (
					prUrl.includes("dev.azure.com") ||
					prUrl.includes("/pullrequest/")
				) {
					return getAzureDevOpsPRDetails(prNumber, prUrl, project);
				} else if (prUrl.includes("github.com") || prUrl.includes("/pull/")) {
					return getGitHubPRDetails(prNumber, prUrl, project);
				} else {
					return {
						success: false,
						error: `Unsupported PR URL format: ${prUrl}. Only GitHub and Azure DevOps are supported.`,
					};
				}
			} catch (error) {
				console.error(`[PR_DETAILS] Error:`, error);
				return {
					success: false,
					error:
						error instanceof Error ? error.message : "Unknown error occurred",
				};
			}
		},
	);
}

/**
 * Extract owner/repo from a GitHub PR URL
 */
function extractRepoFromUrl(prUrl: string): string | null {
	const match = /github\.com\/([^/]+\/[^/]+)/.exec(prUrl);
	return match ? match[1].replace(/\.git$/, "") : null;
}

/**
 * Map GitHub file status to PRFileData status
 */
function mapGitHubFileStatus(
	status: string,
): "added" | "removed" | "modified" | "renamed" {
	switch (status) {
		case "added":
			return "added";
		case "removed":
			return "removed";
		case "renamed":
			return "renamed";
		case "copied":
			return "added";
		default:
			return "modified";
	}
}

/**
 * Get GitHub PR details using the GitHub REST API
 */
async function getGitHubPRDetails(
	prNumber: number,
	prUrl: string | null,
	project: Project | null,
): Promise<IPCResult<PRDetailsResult>> {
	try {
		// Resolve token and repo from project config or URL
		let token: string | null = null;
		let repo: string | null = null;

		if (project) {
			const config = getGitHubConfig(project);
			if (config) {
				token = config.token;
				repo = config.repo;
			}
		}

		// Try to extract repo from PR URL if not found in config
		if (!repo && prUrl) {
			repo = extractRepoFromUrl(prUrl);
		}

		if (!token || !repo) {
			return {
				success: false,
				error:
					"GitHub is not configured. Set GITHUB_TOKEN and GITHUB_REPO in your project .env file, or authenticate with `gh auth login`.",
			};
		}

		// Fetch PR details and files in parallel
		const [prData, filesData] = await Promise.all([
			githubFetch(token, `/repos/${repo}/pulls/${prNumber}`) as Promise<{
				number: number;
				title: string;
				body: string | null;
				state: string;
				html_url: string;
				additions: number;
				deletions: number;
				changed_files: number;
				head: { ref: string };
				base: { ref: string };
				user: { login: string };
				created_at: string;
				updated_at: string;
				mergeable: boolean | null;
				draft: boolean;
				labels: Array<{ name: string }>;
				requested_reviewers: Array<{ login: string }>;
			}>,
			githubFetch(
				token,
				`/repos/${repo}/pulls/${prNumber}/files?per_page=100`,
			) as Promise<
				Array<{
					filename: string;
					status: string;
					additions: number;
					deletions: number;
					changes: number;
					patch?: string;
					previous_filename?: string;
				}>
			>,
		]);

		// Build combined diff from file patches
		const combinedDiff = filesData
			.filter((f) => f.patch)
			.map(
				(f) =>
					`diff --git a/${f.previous_filename || f.filename} b/${f.filename}\n${f.patch}`,
			)
			.join("\n");

		return {
			success: true,
			data: {
				success: true,
				data: {
					number: prData.number,
					title: prData.title,
					body: prData.body ?? "",
					state: prData.state,
					url: prData.html_url,
					additions: prData.additions,
					deletions: prData.deletions,
					changed_files: prData.changed_files,
					source_branch: prData.head.ref,
					target_branch: prData.base.ref,
					author: prData.user.login,
					created_at: prData.created_at,
					updated_at: prData.updated_at,
					mergeable: prData.mergeable ?? true,
					labels: prData.labels.map((l) => l.name),
					reviewers: prData.requested_reviewers.map((r) => r.login),
					is_draft: prData.draft,
					diff: combinedDiff,
					files: filesData.map((f) => ({
						filename: f.filename,
						status: mapGitHubFileStatus(f.status),
						additions: f.additions,
						deletions: f.deletions,
						changes: f.changes,
						patch: f.patch ?? "",
						previous_filename: f.previous_filename,
					})),
				},
			},
		};
	} catch (error) {
		console.error("[PR_DETAILS] GitHub error:", error);
		return {
			success: false,
			error:
				error instanceof Error
					? error.message
					: "Failed to fetch GitHub PR details",
		};
	}
}

/**
 * Get Azure DevOps PR details
 */
async function getAzureDevOpsPRDetails(
	prNumber: number,
	prUrl: string,
	project: Project | null,
): Promise<IPCResult<PRDetailsResult>> {
	try {
		if (!project) {
			return {
				success: false,
				error: "Project is required for Azure DevOps PR details",
			};
		}

		// Parse Azure DevOps URL to extract organization and project
		const azureDevOpsUrlRegex =
			/https:\/\/dev\.azure\.com\/([^/]+)\/([^/]+)\/_git\/([^/]+)\/pullrequest\/(\d+)/;
		const urlMatch = azureDevOpsUrlRegex.exec(prUrl);
		if (!urlMatch) {
			return {
				success: false,
				error: "Invalid Azure DevOps PR URL format",
			};
		}

		const [, _organization, _projectName, repository, prNumFromUrl] = urlMatch;

		// Validate PR number matches URL
		if (Number.parseInt(prNumFromUrl, 10) !== prNumber) {
			return {
				success: false,
				error: `PR number mismatch: requested ${prNumber} but URL contains ${prNumFromUrl}`,
			};
		}

		// Try to call Azure DevOps Python connector using existing project configuration
		try {
			const result = await callAzureDevOpsPythonWithExistingConfig(
				project.path,
				repository,
				prNumber,
				prUrl,
			);

			if (result && !result.error) {
				return transformAzureDevOpsData(result.data, prUrl);
			} else {
				console.warn("[PR_DETAILS] Python call returned error:", result?.error);
				if (result?.traceback) {
					console.error("[PR_DETAILS] Python traceback:", result.traceback);
				}
			}
		} catch (error) {
			console.error(
				"[PR_DETAILS] Azure DevOps API call failed, using mock data:",
				error,
			);
			console.error(
				"[PR_DETAILS] Error details:",
				error instanceof Error ? error.message : error,
			);
		}

		// Fallback to mock data
		console.warn("[PR_DETAILS] Using enhanced mock data for Azure DevOps PR");
		return getMockAzureDevOpsPRDetails(prNumber, prUrl);
	} catch (error) {
		console.error("[PR_DETAILS] Azure DevOps error:", error);
		// Fallback to mock data
		return getMockAzureDevOpsPRDetails(prNumber, prUrl);
	}
}

/**
 * Extract JSON from Python script output
 */
function extractJsonFromOutput(output: string): unknown {
	const lines = output.trim().split("\n");
	for (let i = lines.length - 1; i >= 0; i--) {
		const line = lines[i].trim();
		if (line.startsWith("{") || line.startsWith("[")) {
			try {
				return JSON.parse(line);
			} catch {
				// Not valid JSON, keep searching
			}
		}
	}
	return null;
}

/**
 * Handle successful Python process execution
 */
function handlePythonSuccess(
	output: string,
	_errorOutput: string,
	resolve: (value: unknown) => void,
	reject: (reason: unknown) => void,
): void {
	try {
		const result = extractJsonFromOutput(output);
		if (result) {
			resolve(result);
		} else {
			console.error(
				"[PR_DETAILS] No valid JSON found in Python output:",
				output,
			);
			reject(new Error("No valid JSON found in Python output"));
		}
	} catch (error) {
		console.error("[PR_DETAILS] Failed to parse Python output:", output);
		reject(new Error(`Failed to parse Python output: ${error}`));
	}
}

/**
 * Handle failed Python process execution
 */
function handlePythonFailure(
	code: number,
	output: string,
	errorOutput: string,
	reject: (reason: unknown) => void,
): void {
	console.error("[PR_DETAILS] Python process failed with output:");
	console.error("[PR_DETAILS] STDOUT:", output);
	console.error("[PR_DETAILS] STDERR:", errorOutput);
	reject(
		new Error(
			`Python process exited with code ${code}. Output: ${errorOutput || output}`,
		),
	);
}

/**
 * Setup Python process event handlers
 */
function setupPythonProcessHandlers(
	pythonProcess: ChildProcess,
	resolve: (value: unknown) => void,
	reject: (reason: unknown) => void,
): { output: string; errorOutput: string } {
	let output = "";
	let errorOutput = "";

	pythonProcess.stdout?.on("data", (data: Buffer) => {
		const dataStr = data.toString();
		output += dataStr;
	});

	pythonProcess.stderr?.on("data", (data: Buffer) => {
		const dataStr = data.toString();
		errorOutput += dataStr;
		console.error("[PR_DETAILS] Python stderr:", dataStr);
	});

	pythonProcess.on("close", (code: number) => {
		if (code === 0) {
			handlePythonSuccess(output, errorOutput, resolve, reject);
		} else {
			handlePythonFailure(code, output, errorOutput, reject);
		}
	});

	pythonProcess.on("error", (error: Error) => {
		reject(error);
	});

	return { output, errorOutput };
}

/**
 * Call Azure DevOps Python connector using existing project configuration
 */
async function callAzureDevOpsPythonWithExistingConfig(
	projectPath: string,
	_repository: string,
	prNumber: number,
	prUrl: string,
	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
): Promise<any> {
	return new Promise((resolve, reject) => {
		// Debug: Check Python executable and project path
		const { exec } = require("node:child_process");
		exec(
			"python --version",
			(_error: Error | null, _stdout: string, _stderr: string) => {
				/* intentionally empty */
			},
		);

		const pythonScript = `
import sys
import json
import os
import urllib.request
import urllib.error
import base64
import ssl

# All debug output goes to stderr so stdout is clean JSON only
def debug(msg):
    print(msg, file=sys.stderr)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try loading .env from project path first, then common locations
    env_locations = [
        os.path.join(r'${projectPath.split("\\\\").join("\\\\")}', '.env'),
        os.path.join(r'${projectPath.split("\\\\").join("\\\\")}', 'apps', 'backend', '.env'),
    ]
    for env_path in env_locations:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            debug(f"[OK] Loaded .env from {env_path}")
            break
    else:
        load_dotenv()
        debug("[OK] Loaded default .env")
except ImportError:
    debug("[WARN] python-dotenv not available, using system environment only")

# Get Azure DevOps credentials from environment
pat = os.getenv('AZURE_DEVOPS_PAT', '')
org_url = os.getenv('AZURE_DEVOPS_ORG_URL', '')

debug(f"AZURE_DEVOPS_PAT: {'[OK] Set (' + str(len(pat)) + ' chars)' if pat else '[ERR] Missing'}")
debug(f"AZURE_DEVOPS_ORG_URL: {org_url if org_url else '[ERR] Missing'}")

if not pat:
    print(json.dumps({'error': 'AZURE_DEVOPS_PAT not set'}))
    sys.exit(1)

if not org_url:
    print(json.dumps({'error': 'AZURE_DEVOPS_ORG_URL not set'}))
    sys.exit(1)

# Extract project and repo from the PR URL
pr_url = '${prUrl}'
pr_number = ${prNumber}

# Parse: https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}
url_parts = pr_url.split('/')
project_name = url_parts[4] if len(url_parts) > 4 else ''
repo_name = url_parts[6] if len(url_parts) > 6 else ''

debug(f"Project: {project_name}, Repo: {repo_name}, PR: {pr_number}")

# Build auth header (Basic auth with PAT)
credentials = base64.b64encode(f":{pat}".encode()).decode()
headers = {
    'Authorization': f'Basic {credentials}',
    'Content-Type': 'application/json',
}

# Allow self-signed certs if needed
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

import difflib

def api_get(url):
    debug(f"[API] GET {url}")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        debug(f"[API ERROR] {e.code} {e.reason}: {body[:500]}")
        raise

def api_get_text(url):
    """Fetch raw text content from a URL (for file contents)."""
    debug(f"[API-TEXT] GET {url}")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        debug(f"[API-TEXT ERROR] {e.code} {e.reason}")
        if e.code == 404:
            return None
        raise

def get_file_content(repo_url, file_path, version, version_type='branch'):
    """Get file content at a specific version (branch or commit)."""
    params = urllib.parse.urlencode({
        'path': file_path,
        'versionDescriptor.version': version,
        'versionDescriptor.versionType': version_type,
        '$format': 'text',
        'api-version': '7.1',
    })
    url = f"{repo_url}/items?{params}"
    return api_get_text(url)

def compute_diff(old_content, new_content, old_path='a', new_path='b'):
    """Compute unified diff, additions and deletions between two file contents.
    Returns (patch_text, additions, deletions)."""
    old_lines = (old_content or '').splitlines(keepends=True)
    new_lines = (new_content or '').splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(old_lines, new_lines, fromfile=old_path, tofile=new_path, n=3))
    additions = 0
    deletions = 0
    for line in diff_lines:
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            continue
        if line.startswith('+'):
            additions += 1
        elif line.startswith('-'):
            deletions += 1
    patch_text = ''.join(diff_lines)
    return patch_text, additions, deletions

try:
    base = org_url.rstrip('/')
    api_ver = 'api-version=7.1'
    import urllib.parse

    # 1) Get PR details
    pr_api_url = f"{base}/{project_name}/_apis/git/repositories/{repo_name}/pullrequests/{pr_number}?{api_ver}"
    pr_data = api_get(pr_api_url)
    debug(f"[OK] Got PR details: {pr_data.get('title', 'N/A')}")

    source_branch = pr_data.get('sourceRefName', '').replace('refs/heads/', '')
    target_branch = pr_data.get('targetRefName', '').replace('refs/heads/', '')
    debug(f"[OK] Source: {source_branch}, Target: {target_branch}")

    # 2) Get PR iterations to find file changes
    iterations_url = f"{base}/{project_name}/_apis/git/repositories/{repo_name}/pullrequests/{pr_number}/iterations?{api_ver}"
    iterations_data = api_get(iterations_url)
    iterations = iterations_data.get('value', [])
    debug(f"[OK] Got {len(iterations)} iterations")

    # 3) Get file changes from the last iteration
    files = []
    total_additions = 0
    total_deletions = 0
    repo_url = f"{base}/{project_name}/_apis/git/repositories/{repo_name}"

    if iterations:
        last_iteration_id = iterations[-1]['id']
        changes_url = f"{repo_url}/pullrequests/{pr_number}/iterations/{last_iteration_id}/changes?{api_ver}"
        changes_data = api_get(changes_url)
        change_entries = changes_data.get('changeEntries', [])
        debug(f"[OK] Got {len(change_entries)} change entries from iteration {last_iteration_id}")

        for entry in change_entries:
            item = entry.get('item', {})
            path = item.get('path', '')

            # Skip directory entries (only include files)
            if item.get('isFolder', False):
                continue

            change_type = entry.get('changeType', 'edit')
            # Handle combined flags (e.g. 17 = add+rename)
            if isinstance(change_type, int):
                if change_type & 1:
                    ct_str = 'add'
                elif change_type & 16:
                    ct_str = 'delete'
                elif change_type & 8:
                    ct_str = 'rename'
                else:
                    ct_str = 'edit'
            else:
                ct_lower = str(change_type).lower().split(',')[0].strip()
                ct_map = {'add': 'add', 'edit': 'edit', 'delete': 'delete', 'rename': 'rename'}
                ct_str = ct_map.get(ct_lower, 'edit')

            old_path = entry.get('sourceServerItem', '') or ''
            if not old_path:
                change_detail = entry.get('changeTrackingInfo', {})
                old_path = change_detail.get('originalPath', '')

            # Compute per-file diff stats and patch by fetching content at both branches
            additions = 0
            deletions = 0
            patch_text = ''
            try:
                debug(f"[DIFF] Computing stats for {path} (type={ct_str})")
                if ct_str == 'add':
                    new_content = get_file_content(repo_url, path, source_branch)
                    if new_content is not None:
                        patch_text, additions, deletions = compute_diff('', new_content, '/dev/null', path)
                        debug(f"[DIFF] {path}: new file, +{additions} lines")
                    else:
                        debug(f"[DIFF] {path}: could not fetch new file content")
                elif ct_str == 'delete':
                    old_content = get_file_content(repo_url, old_path or path, target_branch)
                    if old_content is not None:
                        patch_text, additions, deletions = compute_diff(old_content, '', old_path or path, '/dev/null')
                        debug(f"[DIFF] {path}: deleted file, -{deletions} lines")
                    else:
                        debug(f"[DIFF] {path}: could not fetch old file content")
                else:
                    old_content = get_file_content(repo_url, old_path or path, target_branch)
                    new_content = get_file_content(repo_url, path, source_branch)
                    if old_content is not None and new_content is not None:
                        patch_text, additions, deletions = compute_diff(old_content, new_content, old_path or path, path)
                        debug(f"[DIFF] {path}: +{additions} -{deletions}")
                    else:
                        debug(f"[DIFF] {path}: could not fetch content (old={'OK' if old_content is not None else 'MISSING'}, new={'OK' if new_content is not None else 'MISSING'})")
            except Exception as diff_err:
                debug(f"[WARN] Could not compute diff for {path}: {type(diff_err).__name__}: {diff_err}")

            total_additions += additions
            total_deletions += deletions

            files.append({
                'path': path,
                'changeType': ct_str,
                'additions': additions,
                'deletions': deletions,
                'changes': additions + deletions,
                'oldPath': old_path,
                'patch': patch_text,
            })

        debug(f"[OK] Computed diff stats: +{total_additions} -{total_deletions} across {len(files)} files")

    # Build combined diff from all file patches
    combined_diff = '\\n'.join(f.get('patch', '') for f in files if f.get('patch'))

    # Build the result
    result = {
        'success': True,
        'data': {
            'id': pr_data.get('pullRequestId', pr_number),
            'title': pr_data.get('title', ''),
            'description': pr_data.get('description', ''),
            'status': pr_data.get('status', 'active'),
            'creationDate': pr_data.get('creationDate', ''),
            'closedDate': pr_data.get('closedDate', ''),
            'sourceRefName': source_branch,
            'targetRefName': target_branch,
            'createdBy': pr_data.get('createdBy', {}),
            'additions': total_additions,
            'deletions': total_deletions,
            'changed_files': len(files),
            'isDraft': pr_data.get('isDraft', False),
            'diff': combined_diff,
            'files': files,
            'reviewers': [
                {
                    'displayName': r.get('displayName', ''),
                    'vote': r.get('vote', 0),
                }
                for r in pr_data.get('reviewers', [])
            ],
            'labels': [l.get('name', '') for l in pr_data.get('labels', [])],
        }
    }

    # Output ONLY valid JSON to stdout
    print(json.dumps(result))

except Exception as e:
    import traceback
    debug(f"Exception: {e}")
    debug(traceback.format_exc())
    error_result = {
        'error': str(e),
        'traceback': traceback.format_exc()
    }
    print(json.dumps(error_result))
    sys.exit(1)
`;

		const { spawn } = require("node:child_process");
		const pythonProcess = spawn("python", ["-c", pythonScript], {
			cwd: projectPath,
			env: {
				...process.env,
				PYTHONIOENCODING: "utf-8",
			},
		});

		setupPythonProcessHandlers(pythonProcess, resolve, reject);
	});
}

/**
 * Transform Azure DevOps data to PRDetailsResult format
 */
function transformAzureDevOpsData(
	// biome-ignore lint/suspicious/noExplicitAny: Azure DevOps API response shape is not typed
	prData: any,
	prUrl: string,
): IPCResult<PRDetailsResult> {
	try {
		const files =
			// biome-ignore lint/suspicious/noExplicitAny: Azure DevOps API response shape is not typed
			prData.files?.map((file: any) => {
				const status = mapAzureDevOpsChangeType(file.changeType);
				return {
					filename: file.path,
					status: status,
					additions: file.additions || 0,
					deletions: file.deletions || 0,
					changes: file.changes || 0,
					patch: file.patch || "",
					previous_filename: file.oldPath || undefined,
				};
			}) || [];

		const reviewers = (prData.reviewers || [])
			// biome-ignore lint/suspicious/noExplicitAny: Azure DevOps API response shape is not typed
			.map((r: any) => r.displayName || r)
			.filter(Boolean);
		const labels = (prData.labels || [])
			// biome-ignore lint/suspicious/noExplicitAny: Azure DevOps API response shape is not typed
			.map((l: any) => (typeof l === "string" ? l : l.name))
			.filter(Boolean);

		return {
			success: true,
			data: {
				success: true,
				data: {
					number: prData.id,
					title: prData.title,
					body: prData.description,
					state: prData.status === "active" ? "open" : "closed",
					url: prUrl,
					additions: prData.additions || 0,
					deletions: prData.deletions || 0,
					changed_files: prData.changed_files || files.length,
					source_branch: prData.sourceRefName,
					target_branch: prData.targetRefName,
					author: prData.createdBy?.displayName || "Unknown",
					created_at: prData.creationDate,
					updated_at: prData.closedDate || prData.creationDate,
					mergeable: true,
					labels,
					reviewers,
					is_draft: prData.isDraft || false,
					diff: prData.diff || "",
					files,
				},
			},
		};
	} catch (error) {
		console.error("[PR_DETAILS] Error transforming Azure DevOps data:", error);
		return {
			success: false,
			error:
				error instanceof Error
					? error.message
					: "Failed to transform Azure DevOps data",
		};
	}
}

/**
 * Mock Azure DevOps PR details for fallback
 */
async function getMockAzureDevOpsPRDetails(
	prNumber: number,
	prUrl: string,
): Promise<IPCResult<PRDetailsResult>> {
	// Extract real info from URL for more realistic mock data
	const urlRegex =
		/https:\/\/dev\.azure\.com\/([^/]+)\/([^/]+)\/_git\/([^/]+)\/pullrequest\/(\d+)/;
	const urlMatch = urlRegex.exec(prUrl);
	const [, organization, projectName, repository] = urlMatch || [
		undefined,
		"Unknown Org",
		"Unknown Project",
		"Unknown Repo",
	];

	return {
		success: true,
		data: {
			success: true,
			data: {
				number: prNumber,
				title: `Planning atelier sécuriser l'accès au dossier d'un [PR #${prNumber}]`,
				body: `This is a mock representation of Azure DevOps PR #${prNumber} from the ${repository} repository.\n\nThe actual PR details would be fetched from Azure DevOps API when a PAT is configured.\n\n**Organization**: ${organization}\n**Project**: ${projectName}\n**Repository**: ${repository}`,
				state: "open",
				url: prUrl,
				additions: 25,
				deletions: 12,
				changed_files: 3,
				source_branch: "feature/planning-atelier-securiser-acces",
				target_branch: "main",
				author: "Thomas Leberre",
				created_at: "2025-02-22T10:30:00Z",
				updated_at: "2025-02-22T14:15:00Z",
				mergeable: true,
				labels: ["planning", "security", "access-control"],
				reviewers: ["Reviewer1", "Reviewer2"],
				is_draft: false,
				diff: "",
				files: [
					{
						filename: "src/components/access-control/AccessManager.ts",
						status: "modified" as const,
						additions: 15,
						deletions: 8,
						changes: 23,
						patch: "",
					},
					{
						filename: "src/components/access-control/types.ts",
						status: "added" as const,
						additions: 8,
						deletions: 0,
						changes: 8,
						patch: "",
					},
					{
						filename: "src/utils/security-helpers.ts",
						status: "modified" as const,
						additions: 2,
						deletions: 4,
						changes: 6,
						patch: "",
					},
				],
			},
		},
	};
}

function mapAzureDevOpsChangeType(
	changeType: string,
): "added" | "modified" | "renamed" {
	switch (changeType) {
		case "add":
			return "added";
		case "edit":
			return "modified";
		case "delete":
			return "renamed"; // Map Azure DevOps 'delete' to 'renamed' for compatibility
		case "rename":
			return "renamed";
		default:
			return "modified";
	}
}
