#!/usr/bin/env python3
"""
CI/CD Deployment Triggers Runner (Feature 44)

Triggers deployment pipelines on GitHub Actions, GitLab CI, Azure DevOps,
and Jenkins after an agent creates a pull request.

Usage:
    python cicd_triggers_runner.py --action trigger --provider github --project /path --pr-url https://... [options]
    python cicd_triggers_runner.py --action status --run-id <id> --project /path
    python cicd_triggers_runner.py --action cancel --run-id <id> --project /path
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_env(project_dir: str) -> dict:
    env = dict(os.environ)
    env_path = Path(project_dir) / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            eq = line.find("=")
            if eq < 0:
                continue
            key = line[:eq].strip()
            val = line[eq + 1:].strip().strip('"\'')
            env[key] = val
    return env


def http_request(url: str, method: str = "GET", headers: dict | None = None, body: bytes | None = None) -> dict:
    """Simple HTTP request wrapper using only stdlib."""
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")
            try:
                return {"status": resp.status, "body": json.loads(content)}
            except Exception:
                return {"status": resp.status, "body": content}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return {"status": e.code, "error": content}
    except Exception as e:
        return {"status": 0, "error": str(e)}


# ── GitHub Actions ────────────────────────────────────────────────────────────

def trigger_github(env: dict, branch: str, workflow: str | None = None, pr_url: str | None = None) -> dict:
    token = env.get("CICD_GITHUB_TOKEN", "")
    workflow_file = workflow or env.get("CICD_GITHUB_WORKFLOW", "")
    ref = env.get("CICD_GITHUB_REF", branch or "main")

    if not token:
        return {"error": "CICD_GITHUB_TOKEN not configured"}

    # Derive repo from pr_url or environment
    repo = env.get("CICD_GITHUB_REPO", "")
    if not repo and pr_url:
        # Extract owner/repo from https://github.com/owner/repo/pull/N
        parts = pr_url.replace("https://github.com/", "").split("/")
        if len(parts) >= 2:
            repo = f"{parts[0]}/{parts[1]}"

    if not repo:
        return {"error": "Could not determine GitHub repo (set CICD_GITHUB_REPO or pass --pr-url)"}

    if not workflow_file:
        return {"error": "CICD_GITHUB_WORKFLOW not configured (e.g. 'deploy.yml')"}

    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/dispatches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    body = json.dumps({"ref": ref, "inputs": {"pr_url": pr_url or "", "branch": branch or ""}}).encode()
    resp = http_request(url, method="POST", headers=headers, body=body)

    if resp["status"] in (204, 201, 200):
        return {"provider": "github", "status": "triggered", "workflow": workflow_file, "ref": ref, "repo": repo}
    return {"provider": "github", "error": resp.get("error") or str(resp.get("body", "")), "status_code": resp["status"]}


# ── GitLab CI ─────────────────────────────────────────────────────────────────

def trigger_gitlab(env: dict, branch: str, pr_url: str | None = None) -> dict:
    token = env.get("CICD_GITLAB_TOKEN", "")
    project_id = env.get("CICD_GITLAB_PROJECT_ID", "")
    ref = env.get("CICD_GITLAB_REF", branch or "main")
    gitlab_host = env.get("CICD_GITLAB_HOST", "https://gitlab.com")

    if not token:
        return {"error": "CICD_GITLAB_TOKEN not configured"}
    if not project_id:
        return {"error": "CICD_GITLAB_PROJECT_ID not configured"}

    url = f"{gitlab_host}/api/v4/projects/{project_id}/pipeline"
    headers = {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}
    body = json.dumps({"ref": ref}).encode()
    resp = http_request(url, method="POST", headers=headers, body=body)

    if resp["status"] in (201, 200):
        pipeline = resp.get("body", {})
        return {
            "provider": "gitlab",
            "status": "triggered",
            "pipeline_id": pipeline.get("id") if isinstance(pipeline, dict) else None,
            "ref": ref,
            "web_url": pipeline.get("web_url") if isinstance(pipeline, dict) else None,
        }
    return {"provider": "gitlab", "error": resp.get("error") or str(resp.get("body", "")), "status_code": resp["status"]}


# ── Azure DevOps ──────────────────────────────────────────────────────────────

def trigger_azure(env: dict, branch: str, pr_url: str | None = None) -> dict:
    token = env.get("CICD_AZURE_TOKEN", "")
    org = env.get("CICD_AZURE_ORG", "")
    project = env.get("CICD_AZURE_PROJECT", "")
    pipeline_id = env.get("CICD_AZURE_PIPELINE_ID", "")
    ref = env.get("CICD_AZURE_REF", branch or "main")

    if not token or not org or not project or not pipeline_id:
        return {"error": "Azure DevOps config incomplete (need CICD_AZURE_TOKEN, CICD_AZURE_ORG, CICD_AZURE_PROJECT, CICD_AZURE_PIPELINE_ID)"}

    import base64
    encoded = base64.b64encode(f":{token}".encode()).decode()
    url = f"https://dev.azure.com/{org}/{project}/_apis/pipelines/{pipeline_id}/runs?api-version=7.0"
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
    }
    body = json.dumps({"resources": {"repositories": {"self": {"refName": f"refs/heads/{ref}"}}}}).encode()
    resp = http_request(url, method="POST", headers=headers, body=body)

    if resp["status"] in (200, 201):
        run = resp.get("body", {})
        return {
            "provider": "azure",
            "status": "triggered",
            "run_id": run.get("id") if isinstance(run, dict) else None,
            "pipeline_id": pipeline_id,
            "web_url": run.get("_links", {}).get("web", {}).get("href") if isinstance(run, dict) else None,
        }
    return {"provider": "azure", "error": resp.get("error") or str(resp.get("body", "")), "status_code": resp["status"]}


# ── Jenkins ───────────────────────────────────────────────────────────────────

def trigger_jenkins(env: dict, branch: str, pr_url: str | None = None) -> dict:
    jenkins_url = env.get("CICD_JENKINS_URL", "").rstrip("/")
    token = env.get("CICD_JENKINS_TOKEN", "")
    job = env.get("CICD_JENKINS_JOB", "")
    user = env.get("CICD_JENKINS_USER", "")

    if not jenkins_url or not job:
        return {"error": "Jenkins config incomplete (need CICD_JENKINS_URL, CICD_JENKINS_JOB)"}

    url = f"{jenkins_url}/job/{job}/buildWithParameters?BRANCH={branch or 'main'}&PR_URL={pr_url or ''}"
    headers: dict = {}
    if user and token:
        import base64
        encoded = base64.b64encode(f"{user}:{token}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    elif token:
        headers["Authorization"] = f"Bearer {token}"

    resp = http_request(url, method="POST", headers=headers)
    if resp["status"] in (200, 201, 302):
        return {"provider": "jenkins", "status": "triggered", "job": job, "branch": branch}
    return {"provider": "jenkins", "error": resp.get("error") or str(resp.get("body", "")), "status_code": resp["status"]}


# ── Dispatch ──────────────────────────────────────────────────────────────────

def action_trigger(env: dict, provider: str, branch: str, workflow: str | None, pr_url: str | None) -> dict:
    p = provider.lower()
    if p in ("github", "github_actions"):
        return trigger_github(env, branch, workflow, pr_url)
    elif p in ("gitlab", "gitlab_ci"):
        return trigger_gitlab(env, branch, pr_url)
    elif p in ("azure", "azuredevops", "azure_devops"):
        return trigger_azure(env, branch, pr_url)
    elif p == "jenkins":
        return trigger_jenkins(env, branch, pr_url)
    else:
        return {"error": f"Unknown CI/CD provider: {provider}. Supported: github, gitlab, azure, jenkins"}


def action_status(env: dict, provider: str, run_id: str) -> dict:
    """Get pipeline run status (provider-specific)."""
    p = provider.lower()
    token = env.get(f"CICD_{p.upper()}_TOKEN", "")

    if p in ("github", "github_actions"):
        repo = env.get("CICD_GITHUB_REPO", "")
        if not repo or not token:
            return {"error": "Missing CICD_GITHUB_REPO or CICD_GITHUB_TOKEN"}
        url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        resp = http_request(url, headers=headers)
        if resp["status"] == 200:
            run = resp["body"]
            return {"run_id": run_id, "status": run.get("status"), "conclusion": run.get("conclusion"), "url": run.get("html_url")}
        return {"error": resp.get("error") or str(resp.get("body", ""))}

    return {"status": "unknown", "note": f"Status polling not implemented for provider: {provider}"}


def action_cancel(env: dict, provider: str, run_id: str) -> dict:
    """Cancel a running pipeline."""
    p = provider.lower()
    token = env.get(f"CICD_{p.upper()}_TOKEN", "")

    if p in ("github", "github_actions"):
        repo = env.get("CICD_GITHUB_REPO", "")
        if not repo or not token:
            return {"error": "Missing CICD_GITHUB_REPO or CICD_GITHUB_TOKEN"}
        url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/cancel"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        resp = http_request(url, method="POST", headers=headers)
        return {"cancelled": resp["status"] == 202}

    return {"cancelled": False, "note": f"Cancel not implemented for provider: {provider}"}


def main():
    parser = argparse.ArgumentParser(description="CI/CD Triggers Runner")
    parser.add_argument("--action", choices=["trigger", "status", "cancel"], required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--provider", default="")
    parser.add_argument("--pr-url", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--workflow", default=None)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-json", action="store_true")
    args = parser.parse_args()

    env = load_env(args.project)
    provider = args.provider or env.get("CICD_PROVIDER", "")

    try:
        if args.action == "trigger":
            result = action_trigger(env, provider, args.branch, args.workflow, args.pr_url)
        elif args.action == "status":
            result = action_status(env, provider, args.run_id)
        elif args.action == "cancel":
            result = action_cancel(env, provider, args.run_id)
        else:
            result = {"error": f"Unknown action: {args.action}"}

        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if "error" not in result else 1)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
