#!/usr/bin/env python3
"""
Cross-Language Translation Runner (Feature 41)

AI-powered code translation between programming languages using the Claude Agent SDK.
Translates source files or code snippets from one language to another while
preserving logic, structure, and optionally comments.

Usage:
    python cross_language_translation_runner.py --action translate \
        --source-lang python --target-lang typescript \
        --file /path/to/source.py --output /path/to/output.ts \
        --project /path/to/project [--preserve-comments] [--generate-tests]
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

SUPPORTED_LANGUAGES = {
    "python": {"ext": ".py", "label": "Python"},
    "typescript": {"ext": ".ts", "label": "TypeScript"},
    "javascript": {"ext": ".js", "label": "JavaScript"},
    "go": {"ext": ".go", "label": "Go"},
    "java": {"ext": ".java", "label": "Java"},
    "csharp": {"ext": ".cs", "label": "C#"},
    "rust": {"ext": ".rs", "label": "Rust"},
    "kotlin": {"ext": ".kt", "label": "Kotlin"},
    "swift": {"ext": ".swift", "label": "Swift"},
    "php": {"ext": ".php", "label": "PHP"},
}


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


def build_translation_prompt(
    source_lang: str,
    target_lang: str,
    source_code: str,
    source_file: str,
    preserve_comments: bool,
    generate_tests: bool,
) -> str:
    src_label = SUPPORTED_LANGUAGES.get(source_lang, {}).get("label", source_lang)
    tgt_label = SUPPORTED_LANGUAGES.get(target_lang, {}).get("label", target_lang)

    prompt = f"""You are an expert software engineer specializing in code translation between programming languages.

Translate the following {src_label} code to idiomatic {tgt_label}.

**Source file:** `{source_file}`
**Source language:** {src_label}
**Target language:** {tgt_label}

**Translation requirements:**
- Preserve all business logic and functionality exactly
- Use idiomatic {tgt_label} patterns and conventions
- Adapt standard library calls to {tgt_label} equivalents
- Handle type system differences appropriately
{"- Preserve all comments (translate them to the target language if needed)" if preserve_comments else "- You may omit inline comments but keep critical documentation"}
{"- After the translation, also generate a basic unit test file" if generate_tests else ""}

**Source code:**
```{source_lang}
{source_code}
```

Respond with ONLY the translated code in a code block, no explanations before it.
{"After the main translation code block, add a separate code block for the test file prefixed with '// TEST FILE' or '# TEST FILE'." if generate_tests else ""}
"""
    return prompt


def extract_code_blocks(response: str, target_lang: str) -> dict:
    """Extract code blocks from the LLM response."""
    import re

    # Find all fenced code blocks
    pattern = r"```(?:\w+)?\n(.*?)```"
    blocks = re.findall(pattern, response, re.DOTALL)

    if not blocks:
        # No fenced blocks, return the whole response
        return {"translated_code": response.strip(), "test_code": None}

    main_code = blocks[0].strip()
    test_code = None

    # Check if there's a test block
    if len(blocks) > 1:
        second_block = blocks[1].strip()
        if second_block.startswith(("// TEST FILE", "# TEST FILE")):
            test_code = second_block
        else:
            # Heuristic: if second block contains test keywords
            test_keywords = ["test", "spec", "assert", "expect", "describe", "it("]
            if any(kw in second_block.lower() for kw in test_keywords):
                test_code = second_block

    return {"translated_code": main_code, "test_code": test_code}


async def translate_with_claude(
    source_lang: str,
    target_lang: str,
    source_code: str,
    source_file: str,
    project_dir: str,
    preserve_comments: bool,
    generate_tests: bool,
) -> dict:
    """Use Claude Agent SDK for translation."""
    # Add backend to path
    backend_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_dir))

    try:
        from core.client import create_client  # type: ignore

        prompt = build_translation_prompt(
            source_lang, target_lang, source_code, source_file, preserve_comments, generate_tests
        )

        client = create_client(
            project_dir=project_dir,
            spec_dir=None,
            model="claude-sonnet-4-6",
            agent_type="coder",
            max_thinking_tokens=0,
        )

        full_response = []
        async with client:
            async for chunk in client.stream(prompt):
                full_response.append(chunk)
                print(chunk, end="", flush=True)  # Stream to stdout for IPC

        response_text = "".join(full_response)
        return extract_code_blocks(response_text, target_lang)

    except ImportError:
        # Fallback: use a simple rule-based approach for common cases
        return translate_fallback(source_lang, target_lang, source_code)


def translate_fallback(source_lang: str, target_lang: str, source_code: str) -> dict:
    """Very basic fallback translation hint when Claude SDK is unavailable."""
    src_label = SUPPORTED_LANGUAGES.get(source_lang, {}).get("label", source_lang)
    tgt_label = SUPPORTED_LANGUAGES.get(target_lang, {}).get("label", target_lang)

    comment_char = "//" if target_lang not in ("python",) else "#"
    note = (
        f"{comment_char} Auto-translation from {src_label} to {tgt_label}\n"
        f"{comment_char} Note: Claude SDK unavailable — manual review required\n\n"
        f"{comment_char} Original {src_label} source:\n"
    )
    commented = "\n".join(f"{comment_char} {line}" for line in source_code.splitlines())
    return {"translated_code": note + commented, "test_code": None}


def action_translate(args: argparse.Namespace, env: dict) -> dict:
    source_lang = args.source_lang.lower()
    target_lang = args.target_lang.lower()

    if source_lang not in SUPPORTED_LANGUAGES:
        return {"error": f"Unsupported source language: {source_lang}. Supported: {list(SUPPORTED_LANGUAGES)}"}
    if target_lang not in SUPPORTED_LANGUAGES:
        return {"error": f"Unsupported target language: {target_lang}. Supported: {list(SUPPORTED_LANGUAGES)}"}

    # Load source code
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            return {"error": f"Source file not found: {args.file}"}
        source_code = file_path.read_text(encoding="utf-8")
        source_file = str(file_path)
    else:
        return {"error": "--file is required"}

    # Run translation
    result = asyncio.run(translate_with_claude(
        source_lang=source_lang,
        target_lang=target_lang,
        source_code=source_code,
        source_file=source_file,
        project_dir=args.project,
        preserve_comments=args.preserve_comments,
        generate_tests=args.generate_tests,
    ))

    if "error" in result:
        return result

    translated_code = result["translated_code"]
    test_code = result.get("test_code")

    # Write output
    if args.output:
        out_path = Path(args.output)
    else:
        tgt_ext = SUPPORTED_LANGUAGES[target_lang]["ext"]
        src_path = Path(source_file)
        out_path = src_path.parent / f"{src_path.stem}_translated{tgt_ext}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(translated_code, encoding="utf-8")

    response = {
        "source_lang": source_lang,
        "target_lang": target_lang,
        "source_file": source_file,
        "output_file": str(out_path),
        "lines_translated": len(source_code.splitlines()),
        "lines_output": len(translated_code.splitlines()),
    }

    if test_code:
        tgt_ext = SUPPORTED_LANGUAGES[target_lang]["ext"]
        test_path = out_path.parent / f"{out_path.stem}_test{tgt_ext}"
        test_path.write_text(test_code, encoding="utf-8")
        response["test_file"] = str(test_path)

    return response


def main():
    parser = argparse.ArgumentParser(description="Cross-Language Translation Runner")
    parser.add_argument("--action", choices=["translate", "list-languages"], default="translate")
    parser.add_argument("--project", required=False, default=".")
    parser.add_argument("--source-lang", default="")
    parser.add_argument("--target-lang", default="")
    parser.add_argument("--file", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--preserve-comments", action="store_true")
    parser.add_argument("--generate-tests", action="store_true")
    parser.add_argument("--output-json", action="store_true")
    args = parser.parse_args()

    if args.action == "list-languages":
        print(json.dumps(list(SUPPORTED_LANGUAGES.values()), ensure_ascii=False))
        sys.exit(0)

    env = load_env(args.project)

    try:
        result = action_translate(args, env)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if "error" not in result else 1)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
