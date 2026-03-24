"""
App Emulator Runner — Detects project type and start command for preview.

Analyzes the project directory to determine the application type,
framework, start command, and default port. No LLM required.

Output: __APP_EMULATOR_RESULT__:{json}
"""

import argparse
import json
import os
import sys
from pathlib import Path


class AppEmulatorRunner:
    """Analyzes a project to detect type, start command, and port."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)

    def detect_project_type(self) -> dict:
        """Analyze the project and return detection result."""
        # Try detection strategies in priority order
        strategies = [
            self._detect_from_package_json,
            self._detect_from_python,
            self._detect_from_go,
            self._detect_from_rust,
            self._detect_from_docker,
        ]

        for strategy in strategies:
            result = strategy()
            if result:
                return {
                    "success": True,
                    **result,
                }

        return {
            "success": False,
            "error": "Could not detect project type. No package.json, requirements.txt, pyproject.toml, go.mod, or Cargo.toml found.",
            "type": "unknown",
            "framework": "unknown",
            "startCommand": "",
            "port": 3000,
            "isWeb": False,
        }

    def _detect_from_package_json(self) -> dict | None:
        """Detect Node.js / frontend project from package.json."""
        pkg_path = self.project_dir / "package.json"
        if not pkg_path.exists():
            return None

        try:
            with open(pkg_path, encoding="utf-8") as f:
                pkg = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        scripts = pkg.get("scripts", {})
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        # Detect framework
        framework = "node"
        app_type = "web"
        port = 3000

        if "next" in deps:
            framework = "next"
            port = 3000
        elif "nuxt" in deps or "nuxt3" in deps:
            framework = "nuxt"
            port = 3000
        elif "react-scripts" in deps:
            framework = "create-react-app"
            port = 3000
        elif "vite" in deps:
            framework = "vite"
            port = 5173
        elif "@angular/core" in deps:
            framework = "angular"
            port = 4200
        elif "vue" in deps and "vite" not in deps:
            framework = "vue-cli"
            port = 8080
        elif "svelte" in deps or "@sveltejs/kit" in deps:
            framework = "svelte"
            port = 5173
        elif "electron" in deps:
            framework = "electron"
            app_type = "desktop"
            port = 0

        # Detect start command
        start_command = ""
        # Prefer dev scripts for preview
        dev_script_names = ["dev", "start:dev", "serve", "start"]
        for script_name in dev_script_names:
            if script_name in scripts:
                # Detect package manager
                pm = self._detect_package_manager()
                start_command = (
                    f"{pm} run {script_name}"
                    if script_name != "start"
                    else f"{pm} start"
                )
                break

        if not start_command and scripts:
            # Fallback: use first available script
            pm = self._detect_package_manager()
            first_script = next(iter(scripts))
            start_command = f"{pm} run {first_script}"

        return {
            "type": app_type,
            "framework": framework,
            "startCommand": start_command,
            "port": port,
            "isWeb": app_type == "web",
        }

    def _detect_package_manager(self) -> str:
        """Detect which package manager to use."""
        if (self.project_dir / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (self.project_dir / "yarn.lock").exists():
            return "yarn"
        if (self.project_dir / "bun.lockb").exists() or (
            self.project_dir / "bun.lock"
        ).exists():
            return "bun"
        return "npm"

    def _detect_from_python(self) -> dict | None:
        """Detect Python project from various config files."""
        # Check pyproject.toml
        pyproject = self.project_dir / "pyproject.toml"
        requirements = self.project_dir / "requirements.txt"
        manage_py = self.project_dir / "manage.py"
        app_py = self.project_dir / "app.py"
        main_py = self.project_dir / "main.py"

        if not (
            pyproject.exists()
            or requirements.exists()
            or manage_py.exists()
            or app_py.exists()
            or main_py.exists()
        ):
            return None

        # Read all dependency sources to detect framework
        deps_text = ""
        if requirements.exists():
            try:
                deps_text = requirements.read_text(encoding="utf-8").lower()
            except OSError:
                pass
        if pyproject.exists():
            try:
                deps_text += "\n" + pyproject.read_text(encoding="utf-8").lower()
            except OSError:
                pass

        # Django
        if manage_py.exists() or "django" in deps_text:
            return {
                "type": "web",
                "framework": "django",
                "startCommand": "python manage.py runserver",
                "port": 8000,
                "isWeb": True,
            }

        # FastAPI
        if "fastapi" in deps_text:
            # Try to find the main module
            main_module = "main:app"
            if app_py.exists():
                main_module = "app:app"
            return {
                "type": "web",
                "framework": "fastapi",
                "startCommand": f"uvicorn {main_module} --reload --port 8000",
                "port": 8000,
                "isWeb": True,
            }

        # Flask
        if "flask" in deps_text:
            entry = "app.py" if app_py.exists() else "main.py"
            return {
                "type": "web",
                "framework": "flask",
                "startCommand": f"python {entry}",
                "port": 5000,
                "isWeb": True,
            }

        # Streamlit
        if "streamlit" in deps_text:
            entry = "app.py" if app_py.exists() else "main.py"
            return {
                "type": "web",
                "framework": "streamlit",
                "startCommand": f"streamlit run {entry}",
                "port": 8501,
                "isWeb": True,
            }

        # Generic Python
        entry = "main.py" if main_py.exists() else ("app.py" if app_py.exists() else "")
        if entry:
            return {
                "type": "cli",
                "framework": "python",
                "startCommand": f"python {entry}",
                "port": 0,
                "isWeb": False,
            }

        return None

    def _detect_from_go(self) -> dict | None:
        """Detect Go project from go.mod."""
        go_mod = self.project_dir / "go.mod"
        if not go_mod.exists():
            return None

        try:
            content = go_mod.read_text(encoding="utf-8").lower()
        except OSError:
            content = ""

        framework = "go"
        port = 8080

        if "gin-gonic" in content:
            framework = "gin"
        elif "gorilla/mux" in content:
            framework = "gorilla"
        elif "labstack/echo" in content:
            framework = "echo"
        elif "gofiber/fiber" in content:
            framework = "fiber"

        return {
            "type": "web",
            "framework": framework,
            "startCommand": "go run .",
            "port": port,
            "isWeb": True,
        }

    def _detect_from_rust(self) -> dict | None:
        """Detect Rust project from Cargo.toml."""
        cargo = self.project_dir / "Cargo.toml"
        if not cargo.exists():
            return None

        try:
            content = cargo.read_text(encoding="utf-8").lower()
        except OSError:
            content = ""

        is_web = (
            "actix" in content
            or "rocket" in content
            or "axum" in content
            or "warp" in content
        )

        return {
            "type": "web" if is_web else "cli",
            "framework": "rust",
            "startCommand": "cargo run",
            "port": 8080 if is_web else 0,
            "isWeb": is_web,
        }

    def _detect_from_docker(self) -> dict | None:
        """Detect project with Docker support."""
        compose = self.project_dir / "docker-compose.yml"
        compose_alt = self.project_dir / "docker-compose.yaml"
        dockerfile = self.project_dir / "Dockerfile"

        if not (compose.exists() or compose_alt.exists() or dockerfile.exists()):
            return None

        if compose.exists() or compose_alt.exists():
            return {
                "type": "web",
                "framework": "docker-compose",
                "startCommand": "docker-compose up",
                "port": 3000,
                "isWeb": True,
            }

        return {
            "type": "web",
            "framework": "docker",
            "startCommand": "docker build -t app . && docker run -p 3000:3000 app",
            "port": 3000,
            "isWeb": True,
        }


def main():
    parser = argparse.ArgumentParser(
        description="App Emulator — Detect project type and start command"
    )
    parser.add_argument(
        "--project-dir", required=True, help="Path to the project directory"
    )
    args = parser.parse_args()

    project_dir = args.project_dir
    if not os.path.isdir(project_dir):
        result = {"success": False, "error": f"Directory not found: {project_dir}"}
        print(f"__APP_EMULATOR_RESULT__:{json.dumps(result)}")
        sys.exit(1)

    runner = AppEmulatorRunner(project_dir)
    result = runner.detect_project_type()

    print(f"__APP_EMULATOR_RESULT__:{json.dumps(result)}")


if __name__ == "__main__":
    main()
