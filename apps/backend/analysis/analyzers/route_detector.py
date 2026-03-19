"""
Route Detector Module
=====================

Detects API routes and endpoints across different frameworks:
- Python: FastAPI, Flask, Django
- Node.js: Express, Next.js
- Go: Gin, Echo, Chi, Fiber
- Rust: Axum, Actix
- C#: ASP.NET Core (controllers + minimal API)
- Java: Spring Boot (RestController, RequestMapping)
- Ruby: Rails routes.rb
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import BaseAnalyzer


class RouteDetector(BaseAnalyzer):
    """Detects API routes across multiple web frameworks."""

    # Directories to exclude from route detection
    EXCLUDED_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git"}

    def __init__(self, path: Path):
        super().__init__(path)

    def _should_include_file(self, file_path: Path) -> bool:
        """Check if file should be included (not in excluded directories)."""
        return not any(part in self.EXCLUDED_DIRS for part in file_path.parts)

    def detect_all_routes(self) -> list[dict]:
        """Detect all API routes across different frameworks."""
        routes = []

        # Python FastAPI
        routes.extend(self._detect_fastapi_routes())

        # Python Flask
        routes.extend(self._detect_flask_routes())

        # Python Django
        routes.extend(self._detect_django_routes())

        # Node.js Express/Fastify/Koa
        routes.extend(self._detect_express_routes())

        # Next.js (file-based routing)
        routes.extend(self._detect_nextjs_routes())

        # Go Gin/Echo/Chi
        routes.extend(self._detect_go_routes())

        # Rust Axum/Actix
        routes.extend(self._detect_rust_routes())

        # C# ASP.NET Core
        routes.extend(self._detect_dotnet_routes())

        # Java Spring Boot
        routes.extend(self._detect_spring_routes())

        # Ruby on Rails
        routes.extend(self._detect_rails_routes())

        return routes

    def _detect_fastapi_routes(self) -> list[dict]:
        """Detect FastAPI routes."""
        routes = []
        files_to_check = [
            f for f in self.path.glob("**/*.py") if self._should_include_file(f)
        ]

        for file_path in files_to_check:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Pattern: @app.get("/path") or @router.post("/path", dependencies=[...])
            patterns = [
                (
                    r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                    "decorator",
                ),
                (
                    r'@(?:app|router)\.api_route\(["\']([^"\']+)["\'][^)]*methods\s*=\s*\[([^\]]+)\]',
                    "api_route",
                ),
            ]

            for pattern, pattern_type in patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    if pattern_type == "decorator":
                        method = match.group(1).upper()
                        path = match.group(2)
                        methods = [method]
                    else:
                        path = match.group(1)
                        methods_str = match.group(2)
                        methods = [
                            m.strip().strip('"').strip("'").upper()
                            for m in methods_str.split(",")
                        ]

                    # Check if route requires auth (has Depends in the decorator)
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    line_end = content.find("\n", match.end())
                    route_definition = content[
                        line_start : line_end if line_end != -1 else len(content)
                    ]

                    requires_auth = (
                        "Depends" in route_definition
                        or "require" in route_definition.lower()
                    )

                    routes.append(
                        {
                            "path": path,
                            "methods": methods,
                            "file": str(file_path.relative_to(self.path)),
                            "framework": "FastAPI",
                            "requires_auth": requires_auth,
                        }
                    )

        return routes

    def _detect_flask_routes(self) -> list[dict]:
        """Detect Flask routes."""
        routes = []
        files_to_check = [
            f for f in self.path.glob("**/*.py") if self._should_include_file(f)
        ]

        for file_path in files_to_check:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Pattern: @app.route("/path", methods=["GET", "POST"])
            pattern = r'@(?:app|bp|blueprint)\.route\(["\']([^"\']+)["\'](?:[^)]*methods\s*=\s*\[([^\]]+)\])?'
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                path = match.group(1)
                methods_str = match.group(2)

                if methods_str:
                    methods = [
                        m.strip().strip('"').strip("'").upper()
                        for m in methods_str.split(",")
                    ]
                else:
                    methods = ["GET"]  # Flask default

                # Check for @login_required decorator
                decorator_start = content.rfind("@", 0, match.start())
                decorator_section = content[decorator_start : match.end()]
                requires_auth = (
                    "login_required" in decorator_section
                    or "require" in decorator_section.lower()
                )

                routes.append(
                    {
                        "path": path,
                        "methods": methods,
                        "file": str(file_path.relative_to(self.path)),
                        "framework": "Flask",
                        "requires_auth": requires_auth,
                    }
                )

        return routes

    def _detect_django_routes(self) -> list[dict]:
        """Detect Django routes from urls.py files."""
        routes = []
        url_files = [
            f for f in self.path.glob("**/urls.py") if self._should_include_file(f)
        ]

        for file_path in url_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Pattern: path('users/<int:id>/', views.user_detail)
            patterns = [
                r'path\(["\']([^"\']+)["\']',
                r're_path\([r]?["\']([^"\']+)["\']',
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    path = match.group(1)

                    routes.append(
                        {
                            "path": f"/{path}" if not path.startswith("/") else path,
                            "methods": ["GET", "POST"],  # Django allows both by default
                            "file": str(file_path.relative_to(self.path)),
                            "framework": "Django",
                            "requires_auth": False,  # Can't easily detect without middleware analysis
                        }
                    )

        return routes

    def _detect_express_routes(self) -> list[dict]:
        """Detect Express/Fastify/Koa routes."""
        routes = []
        js_files = [
            f for f in self.path.glob("**/*.js") if self._should_include_file(f)
        ]
        ts_files = [
            f for f in self.path.glob("**/*.ts") if self._should_include_file(f)
        ]
        files_to_check = js_files + ts_files
        for file_path in files_to_check:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Pattern: app.get('/path', handler) or router.post('/path', middleware, handler)
            pattern = (
                r'(?:app|router)\.(get|post|put|delete|patch|use)\(["\']([^"\']+)["\']'
            )
            matches = re.finditer(pattern, content)

            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)

                if method == "USE":
                    # .use() is middleware, might be a route prefix
                    continue

                # Check for auth middleware in the route definition
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.end())
                route_line = content[
                    line_start : line_end if line_end != -1 else len(content)
                ]

                requires_auth = any(
                    keyword in route_line.lower()
                    for keyword in ["auth", "authenticate", "protect", "require"]
                )

                routes.append(
                    {
                        "path": path,
                        "methods": [method],
                        "file": str(file_path.relative_to(self.path)),
                        "framework": "Express",
                        "requires_auth": requires_auth,
                    }
                )

        return routes

    def _detect_nextjs_routes(self) -> list[dict]:
        """Detect Next.js file-based routes."""
        routes = []

        # Next.js App Router (app directory)
        app_dir = self.path / "app"
        if app_dir.exists():
            # Find all route.ts/js files
            route_files = [
                f
                for f in app_dir.glob("**/route.{ts,js,tsx,jsx}")
                if self._should_include_file(f)
            ]
            for route_file in route_files:
                # Convert file path to route path
                # app/api/users/[id]/route.ts -> /api/users/:id
                relative_path = route_file.parent.relative_to(app_dir)
                route_path = "/" + str(relative_path).replace("\\", "/")

                # Convert [id] to :id
                route_path = re.sub(r"\[([^\]]+)\]", r":\1", route_path)

                try:
                    content = route_file.read_text(encoding="utf-8")
                    # Detect exported methods: export async function GET(request)
                    methods = re.findall(
                        r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)",
                        content,
                    )

                    if methods:
                        routes.append(
                            {
                                "path": route_path,
                                "methods": methods,
                                "file": str(route_file.relative_to(self.path)),
                                "framework": "Next.js",
                                "requires_auth": "auth" in content.lower(),
                            }
                        )
                except (OSError, UnicodeDecodeError):
                    continue

        # Next.js Pages Router (pages/api directory)
        pages_api = self.path / "pages" / "api"
        if pages_api.exists():
            api_files = [
                f
                for f in pages_api.glob("**/*.{ts,js,tsx,jsx}")
                if self._should_include_file(f)
            ]
            for api_file in api_files:
                if api_file.name.startswith("_"):
                    continue

                # Convert file path to route
                relative_path = api_file.relative_to(pages_api)
                route_path = "/api/" + str(relative_path.with_suffix("")).replace(
                    "\\", "/"
                )

                # Convert [id] to :id
                route_path = re.sub(r"\[([^\]]+)\]", r":\1", route_path)

                routes.append(
                    {
                        "path": route_path,
                        "methods": [
                            "GET",
                            "POST",
                        ],  # Next.js API routes handle all methods
                        "file": str(api_file.relative_to(self.path)),
                        "framework": "Next.js",
                        "requires_auth": False,
                    }
                )

        return routes

    def _detect_go_routes(self) -> list[dict]:
        """Detect Go framework routes (Gin, Echo, Chi, Fiber)."""
        routes = []
        go_files = [
            f for f in self.path.glob("**/*.go") if self._should_include_file(f)
        ]

        for file_path in go_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Gin: r.GET("/path", handler)
            # Echo: e.POST("/path", handler)
            # Chi: r.Get("/path", handler)
            # Fiber: app.Get("/path", handler)
            pattern = r'(?:r|e|app|router)\.(GET|POST|PUT|DELETE|PATCH|Get|Post|Put|Delete|Patch)\(["\']([^"\']+)["\']'
            matches = re.finditer(pattern, content)

            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)

                routes.append(
                    {
                        "path": path,
                        "methods": [method],
                        "file": str(file_path.relative_to(self.path)),
                        "framework": "Go",
                        "requires_auth": False,
                    }
                )

        return routes

    def _detect_rust_routes(self) -> list[dict]:
        """Detect Rust framework routes (Axum, Actix)."""
        routes = []
        rust_files = [
            f for f in self.path.glob("**/*.rs") if self._should_include_file(f)
        ]

        for file_path in rust_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Axum: .route("/path", get(handler))
            # Actix: web::get().to(handler)
            patterns = [
                r'\.route\(["\']([^"\']+)["\'],\s*(get|post|put|delete|patch)',
                r"web::(get|post|put|delete|patch)\(\)",
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    if len(match.groups()) == 2:
                        path = match.group(1)
                        method = match.group(2).upper()
                    else:
                        path = "/"  # Can't determine path from web:: syntax
                        method = match.group(1).upper()

                    routes.append(
                        {
                            "path": path,
                            "methods": [method],
                            "file": str(file_path.relative_to(self.path)),
                            "framework": "Rust",
                            "requires_auth": False,
                        }
                    )

        return routes

    def _detect_dotnet_routes(self) -> list[dict]:
        """Detect ASP.NET Core routes from C# controller files."""
        routes = []
        cs_files = [
            f for f in self.path.glob("**/*.cs") if self._should_include_file(f)
        ]

        http_verbs = {
            "Get": "GET",
            "Post": "POST",
            "Put": "PUT",
            "Delete": "DELETE",
            "Patch": "PATCH",
        }

        for file_path in cs_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue

            # Must be a Controller class
            if not re.search(r"class\s+\w+Controller", content):
                continue

            # Extract class-level [Route("...")] and controller name
            class_match = re.search(
                r'\[Route\(["\']([^"\']*)["\'].*?\)\][\s\S]{0,300}?class\s+(\w+)Controller',
                content,
            )
            if class_match:
                route_template = class_match.group(1)
                controller_name = class_match.group(2)
                # Resolve [controller] token → lowercase controller name
                class_base = route_template.replace(
                    "[controller]", controller_name.lower()
                )
            else:
                cn_match = re.search(r"class\s+(\w+)Controller", content)
                if not cn_match:
                    continue
                controller_name = cn_match.group(1)
                class_base = f"/{controller_name.lower()}s"

            if not class_base.startswith("/"):
                class_base = f"/{class_base}"

            # Extract XML doc <summary> + [HttpVerb] pairs
            # Walk through file looking for method-level attributes
            method_pattern = re.compile(
                r'(?:///\s*<summary>\s*((?:///[^\n]*\n?)*?)///\s*</summary>[\s\S]{0,500}?)?'
                r'\[Http(Get|Post|Put|Delete|Patch)(?:\(["\']?([^"\')\]]*)["\']?\))?\]',
                re.MULTILINE,
            )

            for m in method_pattern.finditer(content):
                raw_summary = m.group(1) or ""
                # Strip leading /// and whitespace from each summary line
                summary = " ".join(
                    line.lstrip("/ ").strip()
                    for line in raw_summary.splitlines()
                    if line.strip().lstrip("/ ")
                ) or None

                verb = m.group(2)
                sub_path = (m.group(3) or "").strip().strip('"').strip("'")
                method = http_verbs.get(verb, verb.upper())

                full_path = (
                    f"{class_base}/{sub_path}".replace("//", "/")
                    if sub_path
                    else class_base
                )

                # Auth detection: [Authorize] within 300 chars before the attribute
                ctx = content[max(0, m.start() - 300) : m.start()]
                requires_auth = bool(re.search(r"\[Authorize\b", ctx)) and not bool(
                    re.search(r"\[AllowAnonymous\]", ctx)
                )

                routes.append(
                    {
                        "path": full_path,
                        "methods": [method],
                        "file": str(file_path.relative_to(self.path)),
                        "framework": "ASP.NET Core",
                        "requires_auth": requires_auth,
                        "summary": summary,
                    }
                )

        return routes

    def _detect_spring_routes(self) -> list[dict]:
        """Detect Spring Boot routes from Java files."""
        routes = []
        java_files = [
            f for f in self.path.glob("**/*.java") if self._should_include_file(f)
        ]

        verb_map = {
            "GetMapping": "GET",
            "PostMapping": "POST",
            "PutMapping": "PUT",
            "DeleteMapping": "DELETE",
            "PatchMapping": "PATCH",
        }

        for file_path in java_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Only process controller files
            if not re.search(
                r"@(?:Rest)?Controller|@RequestMapping", content
            ):
                continue

            # Class-level @RequestMapping
            class_mapping = re.search(
                r'@RequestMapping\(["\']?([^"\')\s]+)["\']?\)', content
            )
            class_base = class_mapping.group(1) if class_mapping else ""
            if class_base and not class_base.startswith("/"):
                class_base = f"/{class_base}"

            # Method-level mappings
            method_pattern = (
                r'@(?:(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)'
                r'(?:\((?:value\s*=\s*)?["\']?([^"\')\s]*)["\']?\))?'
                r'|RequestMapping\([^)]*method\s*=\s*RequestMethod\.(\w+)[^)]*'
                r'(?:value|path)\s*=\s*["\']?([^"\')\s]+)["\']?[^)]*\))'
            )
            for m in re.finditer(method_pattern, content):
                if m.group(1):
                    method = verb_map.get(m.group(1), "GET")
                    sub = (m.group(2) or "").strip()
                else:
                    method = (m.group(3) or "GET").upper()
                    sub = (m.group(4) or "").strip()

                full_path = f"{class_base}/{sub}".replace("//", "/") if sub else (class_base or "/")
                if not full_path.startswith("/"):
                    full_path = f"/{full_path}"

                ctx = content[max(0, m.start() - 300) : m.start()]
                requires_auth = bool(
                    re.search(r"@(?:Secured|PreAuthorize|RolesAllowed)", ctx)
                )

                routes.append(
                    {
                        "path": full_path,
                        "methods": [method],
                        "file": str(file_path.relative_to(self.path)),
                        "framework": "Spring Boot",
                        "requires_auth": requires_auth,
                    }
                )

        return routes

    def _detect_rails_routes(self) -> list[dict]:
        """Detect Ruby on Rails routes from routes.rb."""
        routes = []
        route_files = [
            f
            for f in self.path.glob("**/config/routes.rb")
            if self._should_include_file(f)
        ]

        verb_map = {
            "get": "GET",
            "post": "POST",
            "put": "PUT",
            "patch": "PATCH",
            "delete": "DELETE",
        }

        for file_path in route_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Explicit verb routes: get '/path', to: 'controller#action'
            explicit = re.finditer(
                r"(get|post|put|patch|delete)\s+['\"]([^'\"]+)['\"]",
                content,
                re.IGNORECASE,
            )
            for m in explicit:
                method = verb_map.get(m.group(1).lower(), m.group(1).upper())
                path = m.group(2)
                if not path.startswith("/"):
                    path = f"/{path}"
                routes.append(
                    {
                        "path": path,
                        "methods": [method],
                        "file": str(file_path.relative_to(self.path)),
                        "framework": "Rails",
                        "requires_auth": False,
                    }
                )

            # resources :users → standard CRUD routes
            for m in re.finditer(r"resources\s+:(\w+)", content):
                resource = m.group(1)
                base = f"/{resource}"
                for path, method in [
                    (base, "GET"),
                    (base, "POST"),
                    (f"{base}/{{id}}", "GET"),
                    (f"{base}/{{id}}", "PUT"),
                    (f"{base}/{{id}}", "DELETE"),
                ]:
                    routes.append(
                        {
                            "path": path,
                            "methods": [method],
                            "file": str(file_path.relative_to(self.path)),
                            "framework": "Rails",
                            "requires_auth": False,
                        }
                    )

        return routes
