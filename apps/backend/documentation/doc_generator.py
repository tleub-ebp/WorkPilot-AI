"""Documentation Generator - Generates documentation from code analysis."""

import json
import uuid
from pathlib import Path

from .models import DocSection, DocStatus, DocType


class DocumentationGenerator:
    """Generates documentation files from codebase analysis."""

    def __init__(self, project_dir: str, output_dir: str | None = None):
        self.project_dir = Path(project_dir)
        self.output_dir = Path(output_dir) if output_dir else self.project_dir / "docs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_readme(self, project_context: dict) -> DocSection:
        """Generate a comprehensive README.md."""
        info = self._detect_project_info()
        name = info.get("name", self.project_dir.name)
        description = project_context.get("description", info.get("description", ""))
        tech_stack = project_context.get("tech_stack", info.get("tech_stack", []))
        scripts = info.get("scripts", {})

        content = f"""# {name}

{description or "A software project."}

## Tech Stack

{chr(10).join(f"- {t}" for t in tech_stack) if tech_stack else "- See package.json / requirements.txt"}

## Getting Started

### Prerequisites

See the project configuration files for required dependencies.

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd {self.project_dir.name}
```

"""
        if scripts.get("install"):
            content += f"```bash\n# Install dependencies\n{scripts['install']}\n```\n\n"

        content += "## Usage\n\n"
        if scripts.get("dev") or scripts.get("start"):
            cmd = scripts.get("dev") or scripts.get("start")
            content += f"```bash\n{cmd}\n```\n\n"

        content += "## Scripts\n\n"
        for script_name, script_cmd in scripts.items():
            content += f"- `{script_name}`: `{script_cmd}`\n"

        content += "\n## Contributing\n\nSee [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.\n"
        content += "\n## License\n\nSee [LICENSE](LICENSE) for details.\n"

        section = DocSection(
            section_id=str(uuid.uuid4())[:8],
            file_path="README.md",
            doc_type=DocType.README,
            title="README",
            content=content,
            status=DocStatus.UP_TO_DATE,
        )
        self._write_section(section)
        return section

    def generate_api_docs(self, api_endpoints: list[dict]) -> list[DocSection]:
        """Generate API documentation in Markdown."""
        if not api_endpoints:
            return []

        content = "# API Documentation\n\n"
        content += "Auto-generated API reference.\n\n"
        content += "---\n\n"

        for endpoint in api_endpoints:
            method = endpoint.get("method", "GET").upper()
            path = endpoint.get("path", "/")
            description = endpoint.get("description", "")
            params = endpoint.get("params", [])

            content += f"## `{method} {path}`\n\n"
            if description:
                content += f"{description}\n\n"
            if params:
                content += "### Parameters\n\n"
                content += "| Name | Type | Required | Description |\n"
                content += "|------|------|----------|-------------|\n"
                for p in params:
                    required = "✓" if p.get("required") else ""
                    content += f"| `{p.get('name')}` | `{p.get('type', 'any')}` | {required} | {p.get('desc', '')} |\n"
                content += "\n"
            content += "---\n\n"

        section = DocSection(
            section_id=str(uuid.uuid4())[:8],
            file_path="docs/api.md",
            doc_type=DocType.API_DOCS,
            title="API Documentation",
            content=content,
            status=DocStatus.UP_TO_DATE,
        )
        self._write_section(section)
        return [section]

    def generate_contribution_guide(self) -> DocSection:
        """Generate CONTRIBUTING.md."""
        content = """# Contributing Guide

Thank you for contributing! Please read this guide before submitting changes.

## Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dependencies (see README.md)
4. Make your changes
5. Run tests and linting
6. Submit a pull request

## Code Style

- Follow the existing code style and conventions
- Run the linter before committing
- Write meaningful commit messages

## Pull Request Guidelines

- Keep PRs focused on a single concern
- Include tests for new functionality
- Update documentation when needed
- Ensure all CI checks pass

## Reporting Issues

Please use the issue tracker with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, versions)

## Questions

Open a discussion or reach out to the maintainers.
"""
        section = DocSection(
            section_id=str(uuid.uuid4())[:8],
            file_path="CONTRIBUTING.md",
            doc_type=DocType.CONTRIBUTION_GUIDE,
            title="Contributing Guide",
            content=content,
            status=DocStatus.UP_TO_DATE,
        )
        self._write_section(section)
        return section

    def generate_docstrings(
        self, symbols: list[dict], language: str
    ) -> list[DocSection]:
        """Generate docstring templates for undocumented symbols."""
        sections = []
        for symbol in symbols[:50]:  # Limit to avoid overwhelming output
            if symbol.get("has_doc"):
                continue
            name = symbol.get("name", "unknown")
            kind = symbol.get("kind", "function")
            file_path = symbol.get("file_path", "")

            if language == "python":
                doc = self._generate_python_docstring(name, kind)
            else:
                doc = self._generate_jsdoc(name, kind)

            sections.append(
                DocSection(
                    section_id=str(uuid.uuid4())[:8],
                    file_path=file_path,
                    doc_type=DocType.INLINE_DOCSTRINGS,
                    title=f"{kind}: {name}",
                    content=doc,
                    status=DocStatus.MISSING,
                    related_code_file=file_path,
                )
            )
        return sections

    def generate_sequence_diagrams(self, workflows: list[dict]) -> list[DocSection]:
        """Generate Mermaid sequence diagrams for key workflows."""
        sections = []
        for workflow in workflows:
            title = workflow.get("title", "Workflow")
            steps = workflow.get("steps", [])

            mermaid = "```mermaid\nsequenceDiagram\n"
            mermaid += f"    title: {title}\n"
            for step in steps:
                actor_a = step.get("from", "Client")
                actor_b = step.get("to", "Server")
                message = step.get("message", "request")
                arrow = "->>" if step.get("async") else "->>"
                mermaid += f"    {actor_a}{arrow}{actor_b}: {message}\n"
                if step.get("response"):
                    mermaid += f"    {actor_b}-->>{actor_a}: {step['response']}\n"
            mermaid += "```\n"

            content = f"# {title}\n\n{mermaid}\n"
            slug = title.lower().replace(" ", "_")
            section = DocSection(
                section_id=str(uuid.uuid4())[:8],
                file_path=f"docs/diagrams/{slug}.md",
                doc_type=DocType.SEQUENCE_DIAGRAMS,
                title=title,
                content=content,
                status=DocStatus.UP_TO_DATE,
            )
            self._write_section(section)
            sections.append(section)
        return sections

    def _write_section(self, section: DocSection) -> str:
        """Write a DocSection to a file. Returns the path written."""
        target = self.project_dir / section.file_path
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(section.content, encoding="utf-8")
            return str(target)
        except Exception as e:
            print(f"[DocGen] Warning: could not write {target}: {e}")
            return ""

    def _detect_project_info(self) -> dict:
        """Read package.json / pyproject.toml for project metadata."""
        info: dict = {}

        package_json = self.project_dir / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                info["name"] = data.get("name", "")
                info["description"] = data.get("description", "")
                info["version"] = data.get("version", "")
                scripts = data.get("scripts", {})
                info["scripts"] = {
                    k: v
                    for k, v in scripts.items()
                    if k in ("dev", "start", "build", "test", "lint", "install")
                }
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                tech = []
                for pkg, tier in [
                    ("react", "React"),
                    ("vue", "Vue"),
                    ("angular", "@angular"),
                    ("next", "Next.js"),
                    ("electron", "Electron"),
                    ("typescript", "TypeScript"),
                    ("tailwindcss", "Tailwind CSS"),
                ]:
                    if any(pkg in d for d in deps):
                        tech.append(tier)
                info["tech_stack"] = tech
                return info
            except Exception:
                pass

        pyproject = self.project_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            name_m = re.search(r'name\s*=\s*["\']([^"\']+)', content)
            desc_m = re.search(r'description\s*=\s*["\']([^"\']+)', content)
            if name_m:
                info["name"] = name_m.group(1)
            if desc_m:
                info["description"] = desc_m.group(1)

        return info


import re
