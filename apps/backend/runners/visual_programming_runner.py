"""Visual Programming Runner

CLI entry point for visual programming actions. Spawned by the Electron frontend
as a child process. Prints structured output lines for IPC parsing.

Output protocol:
  - Lines NOT starting with __ are status/progress messages forwarded to UI.
  - __VIS_PROG_RESULT__:<json>   — success payload
  - __VIS_PROG_ERROR__:<message> — error payload

Actions:
  generate-code   — Convert a ReactFlow diagram (nodes + edges) into source code
                    using Claude AI.
  code-to-visual  — Parse a source file and return diagram nodes + edges that
                    represent its structure.

Usage:
  python runners/visual_programming_runner.py \
      --action generate-code \
      --diagram-json '{"nodes":[...],"edges":[...],"diagramType":"flowchart"}' \
      --framework React

  python runners/visual_programming_runner.py \
      --action code-to-visual \
      --file-path /path/to/component.tsx \
      --project-path /path/to/project
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure the backend root is on sys.path
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)


def _print_result(payload: dict) -> None:
    print(f"__VIS_PROG_RESULT__:{json.dumps(payload)}", flush=True)


def _print_error(message: str) -> None:
    print(f"__VIS_PROG_ERROR__:{message}", flush=True)


def _status(message: str) -> None:
    print(message, flush=True)


# ── Prompt builders ──────────────────────────────────────────────────


def _build_generate_code_prompt(diagram: dict, framework: str) -> str:
    """Build a prompt asking Claude to generate code from a diagram."""
    nodes = diagram.get("nodes", [])
    edges = diagram.get("edges", [])
    diagram_type = diagram.get("diagramType", "flowchart")

    nodes_desc = "\n".join(
        f"  - [{n.get('id', '?')}] {n.get('data', {}).get('label', 'Unnamed')} "
        f"(type: {n.get('data', {}).get('type', 'default')}, "
        f"framework: {n.get('data', {}).get('framework', '')})"
        for n in nodes
    )
    edges_desc = "\n".join(
        f"  - {e.get('source', '?')} → {e.get('target', '?')}"
        + (
            f" [{e.get('data', {}).get('label', '')}]"
            if e.get("data", {}).get("label")
            else ""
        )
        for e in edges
    )

    return f"""You are an expert software architect and developer.

The user has designed a {diagram_type} diagram using a visual no-code editor.
Your task is to generate production-ready source code that implements the architecture shown.

## Diagram Nodes
{nodes_desc or "  (no nodes)"}

## Connections (Edges)
{edges_desc or "  (no connections)"}

## Target Framework / Technology
{framework or "Auto-detect from node labels"}

## Instructions
1. Analyse the diagram structure carefully.
2. Generate well-structured, commented source code implementing the described architecture.
3. For each node, create the corresponding file/module/component.
4. Respect the connections (edges) as dependencies or data flows between modules.
5. Return a JSON object with this exact structure:

{{
  "files": [
    {{
      "filename": "relative/path/to/File.ext",
      "language": "typescript",
      "content": "// full file content here"
    }}
  ],
  "summary": "Brief description of what was generated",
  "instructions": "How to run / integrate the generated code"
}}

Respond with ONLY the JSON object, no markdown fences, no explanation outside the JSON.
"""


def _build_code_to_visual_prompt(source_code: str, file_name: str) -> str:
    """Build a prompt asking Claude to convert source code into diagram nodes/edges."""
    return f"""You are an expert software architect.

Analyse the following source file and extract its structure as a visual diagram
(nodes and edges compatible with ReactFlow).

## File: {file_name}
```
{source_code[:8000]}
```

## Instructions
Return a JSON object with this exact structure:

{{
  "nodes": [
    {{
      "id": "unique-string",
      "label": "Human-readable name",
      "type": "component|function|class|module|service|database|api|custom",
      "framework": "React|Angular|Python|etc (or empty string)"
    }}
  ],
  "edges": [
    {{
      "source": "node-id",
      "target": "node-id",
      "label": "optional relationship label"
    }}
  ],
  "summary": "One-sentence description of what this file does"
}}

Rules:
- Every import, class, function, or component becomes a node.
- Dependencies (imports, calls) become directed edges.
- Keep node labels short and human-readable.
- Use meaningful edge labels (imports, extends, calls, renders, etc.).
- Respond with ONLY the JSON object, no markdown fences.
"""


# ── Action: generate-code ─────────────────────────────────────────────


async def action_generate_code(diagram_json: str, framework: str) -> None:
    """Convert a ReactFlow diagram to source code using Claude."""
    try:
        diagram = json.loads(diagram_json)
    except json.JSONDecodeError as exc:
        _print_error(f"Invalid diagram JSON: {exc}")
        return

    _status("Analysing diagram structure…")

    prompt = _build_generate_code_prompt(diagram, framework)

    _status("Calling Claude to generate code…")

    try:
        from core.simple_client import create_simple_client

        client = create_simple_client(
            agent_type="merge_resolver",  # text-only, no tools needed
            model="claude-sonnet-4-6",
            system_prompt=(
                "You are an expert software architect that converts visual diagrams "
                "into production-ready source code. Always respond with valid JSON only."
            ),
            max_turns=1,
        )

        raw_response = ""
        async with client:
            async for message in client.process_query(prompt):
                text = getattr(message, "content", None)
                if isinstance(text, str) and text.strip():
                    raw_response += text
                elif isinstance(text, list):
                    for block in text:
                        if hasattr(block, "text"):
                            raw_response += block.text

        _status("Parsing Claude response…")

        # Try to extract JSON from the response
        raw_response = raw_response.strip()
        if raw_response.startswith("```"):
            # Strip markdown fences if present
            lines = raw_response.split("\n")
            raw_response = "\n".join(line for line in lines if not line.startswith("```"))

        result = json.loads(raw_response)
        _print_result({"action": "generate-code", "data": result})

    except Exception as exc:
        _print_error(f"Code generation failed: {exc}")


# ── Action: code-to-visual ────────────────────────────────────────────


async def action_code_to_visual(file_path: str) -> None:
    """Parse a source file and return diagram nodes + edges."""
    path = Path(file_path)
    if not path.exists():
        _print_error(f"File not found: {file_path}")
        return

    try:
        source_code = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        _print_error(f"Cannot read file: {exc}")
        return

    _status(f"Analysing {path.name}…")

    prompt = _build_code_to_visual_prompt(source_code, path.name)

    _status("Calling Claude to extract structure…")

    try:
        from core.simple_client import create_simple_client

        client = create_simple_client(
            agent_type="merge_resolver",
            model="claude-sonnet-4-6",
            system_prompt=(
                "You are an expert software architect that extracts visual diagram "
                "structures from source code. Always respond with valid JSON only."
            ),
            max_turns=1,
        )

        raw_response = ""
        async with client:
            async for message in client.process_query(prompt):
                text = getattr(message, "content", None)
                if isinstance(text, str) and text.strip():
                    raw_response += text
                elif isinstance(text, list):
                    for block in text:
                        if hasattr(block, "text"):
                            raw_response += block.text

        _status("Parsing Claude response…")

        raw_response = raw_response.strip()
        if raw_response.startswith("```"):
            lines = raw_response.split("\n")
            raw_response = "\n".join(line for line in lines if not line.startswith("```"))

        result = json.loads(raw_response)
        _print_result({"action": "code-to-visual", "data": result})

    except Exception as exc:
        _print_error(f"Code-to-visual conversion failed: {exc}")


# ── Entry point ───────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Visual Programming Runner")
    parser.add_argument(
        "--action",
        required=True,
        choices=["generate-code", "code-to-visual"],
        help="Action to perform",
    )
    # generate-code args
    parser.add_argument(
        "--diagram-json", help="JSON string of the diagram (nodes + edges)"
    )
    parser.add_argument("--framework", default="", help="Target framework/technology")
    # code-to-visual args
    parser.add_argument("--file-path", help="Path to the source file to analyse")
    parser.add_argument("--project-path", help="Root project path (optional)")

    args = parser.parse_args()

    if args.action == "generate-code":
        if not args.diagram_json:
            _print_error("--diagram-json is required for generate-code action")
            sys.exit(1)
        asyncio.run(action_generate_code(args.diagram_json, args.framework or ""))

    elif args.action == "code-to-visual":
        if not args.file_path:
            _print_error("--file-path is required for code-to-visual action")
            sys.exit(1)
        asyncio.run(action_code_to_visual(args.file_path))


if __name__ == "__main__":
    main()
