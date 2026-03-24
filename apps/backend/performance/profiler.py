"""Performance Profiler - Scans codebase to detect bottlenecks and performance issues."""

import re
import uuid
from pathlib import Path

from .models import (
    Bottleneck,
    BottleneckType,
    PerformanceReport,
    Severity,
)

IGNORE_PATTERNS = {
    "node_modules",
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".venv",
    ".next",
    "out",
    "coverage",
}

PYTHON_EXTENSIONS = {".py"}
JS_EXTENSIONS = {".js", ".ts", ".jsx", ".tsx"}
ALL_EXTENSIONS = PYTHON_EXTENSIONS | JS_EXTENSIONS


class PerformanceProfiler:
    """Analyzes codebase for performance bottlenecks."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)

    def profile(self) -> PerformanceReport:
        """Run all profiling analyses and combine into a report."""
        print("🔍 Detecting algorithm complexity issues...")
        algo_bottlenecks = self.detect_algorithm_issues()

        print("💾 Detecting memory issues...")
        memory_bottlenecks = self.detect_memory_issues()

        print("⚛️  Detecting React performance issues...")
        react_bottlenecks = self.detect_react_issues()

        print("🗄️  Detecting query issues...")
        query_bottlenecks = self.detect_query_issues()

        print("📁 Detecting synchronous I/O issues...")
        io_bottlenecks = self.detect_io_issues()

        print("🔄 Detecting caching opportunities...")
        cache_bottlenecks = self.detect_caching_opportunities()

        all_bottlenecks = (
            algo_bottlenecks
            + memory_bottlenecks
            + react_bottlenecks
            + query_bottlenecks
            + io_bottlenecks
            + cache_bottlenecks
        )

        report = PerformanceReport(
            project_dir=str(self.project_dir),
            bottlenecks=all_bottlenecks,
        )
        report.compute_summary()
        return report

    def detect_algorithm_issues(self) -> list[Bottleneck]:
        """Detect O(n²) loops, recursive patterns without memoization."""
        bottlenecks = []
        nested_loop_py = re.compile(
            r"for\s+\w+\s+in\s+[^:]+:\s*\n(?:\s+.*\n)*?\s+for\s+\w+\s+in\s+[^:]+"
        )
        nested_loop_js = re.compile(r"for\s*\([^)]+\)\s*\{[^{}]*for\s*\([^)]+\)\s*\{")
        recursive_no_memo = re.compile(r"def\s+(\w+)\s*\([^)]*\):[^}]*\1\s*\([^)]*\)")

        for file_path in self._get_source_files(list(ALL_EXTENSIONS)):
            content = self._read_file_safe(file_path)
            if not content:
                continue
            rel_path = str(file_path.relative_to(self.project_dir))

            if file_path.suffix == ".py":
                for m in nested_loop_py.finditer(content):
                    line = content[: m.start()].count("\n") + 1
                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_id=str(uuid.uuid4())[:8],
                            file_path=rel_path,
                            line_start=line,
                            line_end=line + 3,
                            type=BottleneckType.ALGORITHM_COMPLEXITY,
                            severity=Severity.HIGH,
                            description="Nested loops detected — potential O(n²) complexity",
                            estimated_impact="Up to 10x slower for large datasets",
                            code_snippet=m.group(0)[:200],
                        )
                    )
                for m in recursive_no_memo.finditer(content):
                    line = content[: m.start()].count("\n") + 1
                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_id=str(uuid.uuid4())[:8],
                            file_path=rel_path,
                            line_start=line,
                            line_end=line + 5,
                            type=BottleneckType.ALGORITHM_COMPLEXITY,
                            severity=Severity.MEDIUM,
                            description=f"Recursive function '{m.group(1)}' without memoization",
                            estimated_impact="Exponential time complexity for recursive calls",
                            code_snippet=m.group(0)[:200],
                        )
                    )
            else:
                for m in nested_loop_js.finditer(content):
                    line = content[: m.start()].count("\n") + 1
                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_id=str(uuid.uuid4())[:8],
                            file_path=rel_path,
                            line_start=line,
                            line_end=line + 5,
                            type=BottleneckType.ALGORITHM_COMPLEXITY,
                            severity=Severity.HIGH,
                            description="Nested for loops detected — potential O(n²) complexity",
                            estimated_impact="Significant slowdown with large arrays",
                            code_snippet=m.group(0)[:200],
                        )
                    )

        return bottlenecks[:20]  # Cap per category

    def detect_memory_issues(self) -> list[Bottleneck]:
        """Detect potential memory leak patterns."""
        bottlenecks = []
        # addEventListener without removeEventListener
        add_listener = re.compile(r"addEventListener\s*\(")
        remove_listener = re.compile(r"removeEventListener\s*\(")
        # Large array allocation
        large_array = re.compile(r"new\s+Array\s*\(\s*(\d{6,})\s*\)")
        # setInterval without clearInterval
        set_interval = re.compile(r"setInterval\s*\(")
        clear_interval = re.compile(r"clearInterval\s*\(")

        for file_path in self._get_source_files([".js", ".ts", ".tsx", ".jsx"]):
            content = self._read_file_safe(file_path)
            if not content:
                continue
            rel_path = str(file_path.relative_to(self.project_dir))

            add_count = len(add_listener.findall(content))
            remove_count = len(remove_listener.findall(content))
            if add_count > 0 and remove_count < add_count:
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_id=str(uuid.uuid4())[:8],
                        file_path=rel_path,
                        line_start=1,
                        line_end=1,
                        type=BottleneckType.MEMORY_LEAK,
                        severity=Severity.HIGH,
                        description=f"addEventListener ({add_count}x) without matching removeEventListener ({remove_count}x)",
                        estimated_impact="Memory leak — event listeners accumulate on each render",
                    )
                )

            set_count = len(set_interval.findall(content))
            clear_count = len(clear_interval.findall(content))
            if set_count > 0 and clear_count < set_count:
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_id=str(uuid.uuid4())[:8],
                        file_path=rel_path,
                        line_start=1,
                        line_end=1,
                        type=BottleneckType.MEMORY_LEAK,
                        severity=Severity.MEDIUM,
                        description=f"setInterval ({set_count}x) without matching clearInterval ({clear_count}x)",
                        estimated_impact="Timer leak — intervals continue running after component unmount",
                    )
                )

            for m in large_array.finditer(content):
                line = content[: m.start()].count("\n") + 1
                size = int(m.group(1))
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_id=str(uuid.uuid4())[:8],
                        file_path=rel_path,
                        line_start=line,
                        line_end=line,
                        type=BottleneckType.MEMORY_LEAK,
                        severity=Severity.MEDIUM,
                        description=f"Large array allocation: new Array({size:,})",
                        estimated_impact=f"~{size * 8 // 1024} KB pre-allocated memory",
                        code_snippet=m.group(0),
                    )
                )

        return bottlenecks[:20]

    def detect_react_issues(self) -> list[Bottleneck]:
        """Detect React-specific performance issues."""
        bottlenecks = []
        inline_func_in_jsx = re.compile(r"on\w+=\{(?:\s*)\((?:[^)]*)\)\s*=>")
        missing_key = re.compile(r"\.map\s*\([^)]+\)\s*=>\s*(?:<\w+|(?:\(\s*<\w+))")
        has_key = re.compile(r'key\s*=\s*\{|key\s*=\s*"')

        for file_path in self._get_source_files([".tsx", ".jsx"]):
            content = self._read_file_safe(file_path)
            if not content:
                continue
            rel_path = str(file_path.relative_to(self.project_dir))

            for m in inline_func_in_jsx.finditer(content):
                line = content[: m.start()].count("\n") + 1
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_id=str(uuid.uuid4())[:8],
                        file_path=rel_path,
                        line_start=line,
                        line_end=line,
                        type=BottleneckType.UNNECESSARY_RENDERS,
                        severity=Severity.MEDIUM,
                        description="Inline arrow function in JSX prop — new function created on every render",
                        estimated_impact="Unnecessary re-renders of child components",
                        code_snippet=m.group(0)[:100],
                    )
                )

            for m in missing_key.finditer(content):
                surrounding = content[m.start() : m.start() + 200]
                if not has_key.search(surrounding):
                    line = content[: m.start()].count("\n") + 1
                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_id=str(uuid.uuid4())[:8],
                            file_path=rel_path,
                            line_start=line,
                            line_end=line,
                            type=BottleneckType.UNNECESSARY_RENDERS,
                            severity=Severity.MEDIUM,
                            description=".map() rendering elements without 'key' prop",
                            estimated_impact="React cannot optimize re-renders without stable keys",
                            code_snippet=surrounding[:100],
                        )
                    )

        return bottlenecks[:20]

    def detect_query_issues(self) -> list[Bottleneck]:
        """Detect N+1 query patterns and missing indexes."""
        bottlenecks = []
        # Queries inside loops
        loop_with_query_py = re.compile(
            r"for\s+\w+\s+in\s+[^:]+:.*?(?:\.query\(|\.filter\(|\.get\(|\.all\()",
            re.DOTALL,
        )
        select_star = re.compile(r"SELECT\s+\*\s+FROM", re.IGNORECASE)

        for file_path in self._get_source_files([".py"]):
            content = self._read_file_safe(file_path)
            if not content:
                continue
            rel_path = str(file_path.relative_to(self.project_dir))

            for m in loop_with_query_py.finditer(content):
                line = content[: m.start()].count("\n") + 1
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_id=str(uuid.uuid4())[:8],
                        file_path=rel_path,
                        line_start=line,
                        line_end=line + 5,
                        type=BottleneckType.N_PLUS_ONE_QUERY,
                        severity=Severity.CRITICAL,
                        description="Database query inside a loop — classic N+1 problem",
                        estimated_impact="N database queries instead of 1 — can be 100x slower",
                        code_snippet=m.group(0)[:200],
                    )
                )

            for m in select_star.finditer(content):
                line = content[: m.start()].count("\n") + 1
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_id=str(uuid.uuid4())[:8],
                        file_path=rel_path,
                        line_start=line,
                        line_end=line,
                        type=BottleneckType.MISSING_INDEX,
                        severity=Severity.LOW,
                        description="SELECT * fetches all columns — use explicit column names",
                        estimated_impact="Fetches unnecessary data, increases memory and network usage",
                        code_snippet=m.group(0),
                    )
                )

        return bottlenecks[:20]

    def detect_io_issues(self) -> list[Bottleneck]:
        """Detect synchronous I/O in async contexts."""
        bottlenecks = []
        sync_read_in_async = re.compile(
            r"async\s+def\s+\w+[^:]*:.*?(?:open\(|readFileSync\(|writeFileSync\()",
            re.DOTALL,
        )
        sync_fs_js = re.compile(
            r"(?:readFileSync|writeFileSync|existsSync|readdirSync)\s*\("
        )

        for file_path in self._get_source_files(list(ALL_EXTENSIONS)):
            content = self._read_file_safe(file_path)
            if not content:
                continue
            rel_path = str(file_path.relative_to(self.project_dir))

            if file_path.suffix == ".py":
                for m in sync_read_in_async.finditer(content):
                    line = content[: m.start()].count("\n") + 1
                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_id=str(uuid.uuid4())[:8],
                            file_path=rel_path,
                            line_start=line,
                            line_end=line + 5,
                            type=BottleneckType.SYNCHRONOUS_IO,
                            severity=Severity.HIGH,
                            description="Synchronous file I/O inside async function blocks the event loop",
                            estimated_impact="Blocks all other async operations during I/O",
                            code_snippet=m.group(0)[:200],
                        )
                    )
            else:
                for m in sync_fs_js.finditer(content):
                    line = content[: m.start()].count("\n") + 1
                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_id=str(uuid.uuid4())[:8],
                            file_path=rel_path,
                            line_start=line,
                            line_end=line,
                            type=BottleneckType.SYNCHRONOUS_IO,
                            severity=Severity.MEDIUM,
                            description=f"Synchronous filesystem operation: {m.group(0)[:50]}",
                            estimated_impact="Blocks Node.js event loop — use async alternatives",
                            code_snippet=m.group(0),
                        )
                    )

        return bottlenecks[:20]

    def detect_caching_opportunities(self) -> list[Bottleneck]:
        """Detect expensive computations that could benefit from caching."""
        bottlenecks = []
        expensive_ops = re.compile(
            r"(?:json\.loads|json\.dumps|hashlib\.\w+\(|base64\.|subprocess\.run|"
            r"requests\.get|requests\.post|fetch\s*\(|axios\.\w+\s*\()"
        )
        in_loop_pattern = re.compile(
            r"for\s+.*?:.*?(?:json\.|hashlib\.|base64\.|subprocess\.|requests\.|fetch\(|axios\.)",
            re.DOTALL,
        )

        for file_path in self._get_source_files(list(ALL_EXTENSIONS)):
            content = self._read_file_safe(file_path)
            if not content:
                continue
            rel_path = str(file_path.relative_to(self.project_dir))

            for m in in_loop_pattern.finditer(content):
                line = content[: m.start()].count("\n") + 1
                bottlenecks.append(
                    Bottleneck(
                        bottleneck_id=str(uuid.uuid4())[:8],
                        file_path=rel_path,
                        line_start=line,
                        line_end=line + 3,
                        type=BottleneckType.MISSING_CACHE,
                        severity=Severity.HIGH,
                        description="Expensive operation (network/serialization) repeated in a loop",
                        estimated_impact="Cache results to avoid repeated computation/network calls",
                        code_snippet=m.group(0)[:200],
                    )
                )

        return bottlenecks[:10]

    def _read_file_safe(self, path: Path) -> str:
        """Read a file safely, returning empty string on error."""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _is_ignoreable_path(self, path: Path) -> bool:
        """Check if path should be skipped."""
        return any(part in IGNORE_PATTERNS for part in path.parts)

    def _get_source_files(self, extensions: list[str]) -> list[Path]:
        """Return source files matching extensions, excluding ignored paths."""
        files = []
        ext_set = set(extensions)
        for file_path in self.project_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in ext_set:
                continue
            if self._is_ignoreable_path(file_path):
                continue
            files.append(file_path)
        return files
