"""
Transformation Engine: Applies code transformations for migrations.
"""

from pathlib import Path

from .models import TransformationResult
from .performance import (
    IncrementalMigration,
    MigrationCache,
    ParallelTransformer,
    ProgressTracker,
)
from .transformers import (
    CSharpToPythonTransformer,
    DatabaseTransformer,
    JSToCSharpTransformer,
    JSToTypeScriptTransformer,
    PythonToCSharpTransformer,
    PythonTransformer,
    ReactToAngularTransformer,
    ReactToVueTransformer,
    RestToGraphQLTransformer,
)


class TransformationEngine:
    """Main transformation orchestrator."""

    def __init__(
        self,
        project_dir: str,
        source_framework: str,
        target_framework: str,
        enable_cache: bool = True,
        enable_parallel: bool = True,
        max_workers: int = 4,
    ):
        self.project_dir = Path(project_dir)
        self.source_framework = source_framework
        self.target_framework = target_framework
        self.transformations: list[TransformationResult] = []

        # Performance optimizations
        self.enable_cache = enable_cache
        self.enable_parallel = enable_parallel

        # Initialize cache
        cache_dir = self.project_dir / ".auto-claude" / "migration" / "cache"
        self.cache = MigrationCache(str(cache_dir)) if enable_cache else None

        # Initialize parallel processor
        self.parallel = (
            ParallelTransformer(max_workers=max_workers) if enable_parallel else None
        )

        # Initialize incremental migration
        self.incremental = IncrementalMigration(str(self.project_dir))

        # Initialize progress tracker
        self.progress = ProgressTracker()

    def transform_code(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Execute code transformations."""
        results = []

        if (self.source_framework, self.target_framework) == ("react", "vue"):
            results = self._transform_react_to_vue(file_paths)
        elif (self.source_framework, self.target_framework) == ("react", "angular"):
            results = self._transform_react_to_angular(file_paths)
        elif (self.source_framework, self.target_framework) == ("mysql", "postgresql"):
            results = self._transform_database(file_paths)
        elif (self.source_framework, self.target_framework) == ("python2", "python3"):
            results = self._transform_python(file_paths)
        elif (self.source_framework, self.target_framework) == ("rest", "graphql"):
            results = self._transform_rest_to_graphql(file_paths)
        elif (self.source_framework, self.target_framework) == (
            "javascript",
            "typescript",
        ):
            results = self._transform_js_to_ts(file_paths)
        elif (self.source_framework, self.target_framework) == ("javascript", "csharp"):
            results = self._transform_js_to_csharp(file_paths)
        elif (self.source_framework, self.target_framework) == ("typescript", "csharp"):
            results = self._transform_ts_to_csharp(file_paths)
        elif (self.source_framework, self.target_framework) == ("csharp", "python"):
            results = self._transform_csharp_to_python(file_paths)
        elif (self.source_framework, self.target_framework) == ("python", "csharp"):
            results = self._transform_python_to_csharp(file_paths)

        self.transformations = results
        return results

    def _transform_react_to_vue(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform React code to Vue."""
        transformer = ReactToVueTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect React files
            file_paths = []
            for ext in ["*.jsx", "*.tsx"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        return transformer.transform_files(file_paths)

    def _transform_react_to_angular(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform React code to Angular."""
        transformer = ReactToAngularTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect React files
            file_paths = []
            for ext in ["*.jsx", "*.tsx"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        return transformer.transform_files(file_paths)

    def _transform_database(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform database schema and code."""
        transformer = DatabaseTransformer(str(self.project_dir))

        results = []

        if not file_paths:
            # Auto-detect SQL and application files
            file_paths = []
            for ext in ["*.sql"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        # Transform SQL files
        results.extend(transformer.transform_sql_files(file_paths))

        # Transform application code
        app_files = []
        for ext in ["*.js", "*.ts", "*.py"]:
            app_files.extend(
                str(p.relative_to(self.project_dir))
                for p in self.project_dir.rglob(ext)
            )

        results.extend(transformer.transform_application_code(app_files))

        return results

    def _transform_python(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform Python 2 to Python 3."""
        transformer = PythonTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect Python files
            file_paths = []
            file_paths.extend(
                str(p.relative_to(self.project_dir))
                for p in self.project_dir.rglob("*.py")
            )

        return transformer.transform_files(file_paths)

    def _transform_rest_to_graphql(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform REST API to GraphQL."""
        transformer = RestToGraphQLTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect REST route files
            file_paths = []
            for ext in ["*.js", "*.ts"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        return transformer.transform_files(file_paths)

    def _transform_js_to_ts(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform JavaScript to TypeScript."""
        transformer = JSToTypeScriptTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect JavaScript files
            file_paths = []
            for ext in ["*.js", "*.jsx"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        return transformer.transform_files(file_paths)

    def _transform_js_to_csharp(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform JavaScript to C#."""
        transformer = JSToCSharpTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect JavaScript files
            file_paths = []
            for ext in ["*.js", "*.jsx"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        return transformer.transform_files(file_paths)

    def _transform_ts_to_csharp(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform TypeScript to C#."""
        transformer = JSToCSharpTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect TypeScript files
            file_paths = []
            for ext in ["*.ts", "*.tsx"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        return transformer.transform_files(file_paths)

    def _transform_csharp_to_python(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform C# to Python."""
        transformer = CSharpToPythonTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect C# files
            file_paths = []
            for ext in ["*.cs"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        return transformer.transform_files(file_paths)

    def _transform_python_to_csharp(
        self, file_paths: list[str] | None = None
    ) -> list[TransformationResult]:
        """Transform Python to C#."""
        transformer = PythonToCSharpTransformer(str(self.project_dir))

        if not file_paths:
            # Auto-detect Python files
            file_paths = []
            for ext in ["*.py"]:
                file_paths.extend(
                    str(p.relative_to(self.project_dir))
                    for p in self.project_dir.rglob(ext)
                )

        return transformer.transform_files(file_paths)

    def apply_transformations(self, dry_run: bool = False) -> dict:
        """Apply transformations to files."""
        applied = 0
        skipped = 0
        errors = []

        for result in self.transformations:
            try:
                if not dry_run:
                    target_file = self.project_dir / result.file_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_text(result.after)
                    result.applied = True
                applied += 1
            except Exception as e:
                result.errors.append(str(e))
                skipped += 1
                errors.append(f"{result.file_path}: {str(e)}")

        return {
            "applied": applied,
            "skipped": skipped,
            "errors": errors,
            "dry_run": dry_run,
            "total": len(self.transformations),
        }

    def get_transformations(self) -> list[TransformationResult]:
        """Get all transformations."""
        return self.transformations
