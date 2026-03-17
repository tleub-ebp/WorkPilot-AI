"""Performance Optimizer - Generates and applies optimization suggestions."""
import uuid
from typing import Dict, List

from .models import (
    Bottleneck,
    BottleneckType,
    OptimizationEffort,
    OptimizationSuggestion,
    PerformanceReport,
    Severity,
)


class PerformanceOptimizer:
    """Generates optimization suggestions for detected bottlenecks."""

    def __init__(self, project_dir: str, report: PerformanceReport):
        self.project_dir = project_dir
        self.report = report

    def generate_suggestions(self) -> List[OptimizationSuggestion]:
        """Generate optimization suggestions for all bottlenecks in the report."""
        suggestions = []
        dispatch = {
            BottleneckType.ALGORITHM_COMPLEXITY: self._suggest_for_algorithm,
            BottleneckType.MEMORY_LEAK: self._suggest_for_memory,
            BottleneckType.UNNECESSARY_RENDERS: self._suggest_for_react,
            BottleneckType.N_PLUS_ONE_QUERY: self._suggest_for_query,
            BottleneckType.MISSING_INDEX: self._suggest_for_index,
            BottleneckType.SYNCHRONOUS_IO: self._suggest_for_io,
            BottleneckType.MISSING_CACHE: self._suggest_for_caching,
            BottleneckType.LARGE_BUNDLE: self._suggest_for_bundle,
        }
        for bottleneck in self.report.bottlenecks:
            handler = dispatch.get(bottleneck.type)
            if handler:
                suggestion = handler(bottleneck)
                if suggestion:
                    suggestions.append(suggestion)
        return suggestions

    def _suggest_for_algorithm(self, b: Bottleneck) -> OptimizationSuggestion:
        return OptimizationSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            bottleneck_id=b.bottleneck_id,
            title="Replace nested loops with hashmap lookup",
            description=(
                "Convert the inner loop into a dictionary/set lookup to reduce "
                "complexity from O(n²) to O(n)."
            ),
            implementation=(
                "# Before: O(n²)\n"
                "for item in list_a:\n"
                "    for other in list_b:\n"
                "        if item.id == other.id:\n"
                "            ...\n\n"
                "# After: O(n) with dict\n"
                "lookup = {item.id: item for item in list_b}\n"
                "for item in list_a:\n"
                "    if item.id in lookup:\n"
                "        ..."
            ),
            estimated_improvement="Up to 100x faster for n > 1000",
            effort=OptimizationEffort.MEDIUM,
            auto_implementable=False,
        )

    def _suggest_for_memory(self, b: Bottleneck) -> OptimizationSuggestion:
        if "addEventListener" in b.description:
            return OptimizationSuggestion(
                suggestion_id=str(uuid.uuid4())[:8],
                bottleneck_id=b.bottleneck_id,
                title="Add removeEventListener in cleanup",
                description="Remove event listeners in useEffect cleanup or component unmount.",
                implementation=(
                    "useEffect(() => {\n"
                    "  const handler = (e) => { /* ... */ };\n"
                    "  element.addEventListener('event', handler);\n"
                    "  return () => element.removeEventListener('event', handler);  // cleanup\n"
                    "}, []);"
                ),
                estimated_improvement="Eliminates memory leak on component unmount",
                effort=OptimizationEffort.LOW,
                auto_implementable=False,
            )
        if "setInterval" in b.description:
            return OptimizationSuggestion(
                suggestion_id=str(uuid.uuid4())[:8],
                bottleneck_id=b.bottleneck_id,
                title="Clear interval on unmount",
                description="Store interval ID and clear it in useEffect cleanup.",
                implementation=(
                    "useEffect(() => {\n"
                    "  const id = setInterval(fn, delay);\n"
                    "  return () => clearInterval(id);  // cleanup\n"
                    "}, []);"
                ),
                estimated_improvement="Stops timers leaking after component unmount",
                effort=OptimizationEffort.LOW,
                auto_implementable=True,
            )
        return OptimizationSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            bottleneck_id=b.bottleneck_id,
            title="Fix memory leak pattern",
            description=b.description,
            implementation="Add proper cleanup/disposal in component unmount or destructor.",
            estimated_improvement="Prevents memory growth over time",
            effort=OptimizationEffort.MEDIUM,
            auto_implementable=False,
        )

    def _suggest_for_react(self, b: Bottleneck) -> OptimizationSuggestion:
        if "inline arrow" in b.description:
            return OptimizationSuggestion(
                suggestion_id=str(uuid.uuid4())[:8],
                bottleneck_id=b.bottleneck_id,
                title="Extract handler with useCallback",
                description="Move inline functions out of JSX props and wrap with useCallback.",
                implementation=(
                    "// Before:\n"
                    "<Button onClick={(e) => handleClick(e, item)} />\n\n"
                    "// After:\n"
                    "const handleItemClick = useCallback((e) => handleClick(e, item), [item]);\n"
                    "<Button onClick={handleItemClick} />"
                ),
                estimated_improvement="Prevents unnecessary child re-renders",
                effort=OptimizationEffort.LOW,
                auto_implementable=False,
            )
        return OptimizationSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            bottleneck_id=b.bottleneck_id,
            title="Add stable key prop in list rendering",
            description="Provide unique, stable key props to list items.",
            implementation=(
                "// Before:\n"
                "{items.map(item => <Item {...item} />)}\n\n"
                "// After:\n"
                "{items.map(item => <Item key={item.id} {...item} />)}"
            ),
            estimated_improvement="React can skip re-renders when keys are stable",
            effort=OptimizationEffort.LOW,
            auto_implementable=False,
        )

    def _suggest_for_query(self, b: Bottleneck) -> OptimizationSuggestion:
        return OptimizationSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            bottleneck_id=b.bottleneck_id,
            title="Batch queries with eager loading",
            description="Use JOIN/eager loading or a single batch query instead of querying in a loop.",
            implementation=(
                "# Before (N+1):\n"
                "for user in users:\n"
                "    posts = Post.query.filter_by(user_id=user.id).all()\n\n"
                "# After (1 query):\n"
                "users_with_posts = User.query.options(joinedload(User.posts)).all()"
            ),
            estimated_improvement="Reduces N database queries to 1",
            effort=OptimizationEffort.MEDIUM,
            auto_implementable=False,
        )

    def _suggest_for_index(self, b: Bottleneck) -> OptimizationSuggestion:
        return OptimizationSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            bottleneck_id=b.bottleneck_id,
            title="Select specific columns instead of SELECT *",
            description="Fetch only the columns you need to reduce data transfer.",
            implementation=(
                "-- Before:\nSELECT * FROM users WHERE id = ?;\n\n"
                "-- After:\nSELECT id, name, email FROM users WHERE id = ?;"
            ),
            estimated_improvement="Reduces data transfer and memory usage",
            effort=OptimizationEffort.LOW,
            auto_implementable=False,
        )

    def _suggest_for_io(self, b: Bottleneck) -> OptimizationSuggestion:
        if ".py" in b.file_path:
            return OptimizationSuggestion(
                suggestion_id=str(uuid.uuid4())[:8],
                bottleneck_id=b.bottleneck_id,
                title="Use aiofiles for async file I/O",
                description="Replace blocking open() with aiofiles in async functions.",
                implementation=(
                    "# Before (blocking):\n"
                    "async def read_file(path):\n"
                    "    with open(path) as f:  # blocks event loop!\n"
                    "        return f.read()\n\n"
                    "# After (non-blocking):\n"
                    "import aiofiles\n"
                    "async def read_file(path):\n"
                    "    async with aiofiles.open(path) as f:\n"
                    "        return await f.read()"
                ),
                estimated_improvement="Non-blocking I/O allows concurrent operations",
                effort=OptimizationEffort.LOW,
                auto_implementable=False,
            )
        return OptimizationSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            bottleneck_id=b.bottleneck_id,
            title="Replace synchronous fs operations with async alternatives",
            description="Use fs.promises or fs/promises module for async file operations.",
            implementation=(
                "// Before:\nconst data = fs.readFileSync(path);\n\n"
                "// After:\nconst data = await fs.promises.readFile(path);"
            ),
            estimated_improvement="Unblocks Node.js event loop during I/O",
            effort=OptimizationEffort.LOW,
            auto_implementable=False,
        )

    def _suggest_for_caching(self, b: Bottleneck) -> OptimizationSuggestion:
        return OptimizationSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            bottleneck_id=b.bottleneck_id,
            title="Cache expensive operations outside the loop",
            description="Move network calls and expensive serialization outside hot loops.",
            implementation=(
                "# Before:\nfor item in items:\n"
                "    data = json.loads(expensive_api_call())\n\n"
                "# After:\ncached_data = json.loads(expensive_api_call())  # once\n"
                "for item in items:\n"
                "    process(cached_data, item)"
            ),
            estimated_improvement="Reduces repeated computation by N times",
            effort=OptimizationEffort.LOW,
            auto_implementable=False,
        )

    def _suggest_for_bundle(self, b: Bottleneck) -> OptimizationSuggestion:
        return OptimizationSuggestion(
            suggestion_id=str(uuid.uuid4())[:8],
            bottleneck_id=b.bottleneck_id,
            title="Implement code splitting with dynamic imports",
            description="Use React.lazy() or dynamic import() to split large bundles.",
            implementation=(
                "// Before:\nimport HeavyComponent from './HeavyComponent';\n\n"
                "// After:\nconst HeavyComponent = React.lazy(() => import('./HeavyComponent'));\n"
                "// Wrap with: <Suspense fallback={<Loading />}><HeavyComponent /></Suspense>"
            ),
            estimated_improvement="Reduces initial bundle size and load time",
            effort=OptimizationEffort.MEDIUM,
            auto_implementable=False,
        )

    def implement_suggestion(
        self, suggestion: OptimizationSuggestion, dry_run: bool = True
    ) -> Dict:
        """Attempt to auto-implement a suggestion if it's marked auto_implementable."""
        if not suggestion.auto_implementable:
            return {
                "status": "skipped",
                "reason": "Suggestion requires manual implementation",
                "suggestion_id": suggestion.suggestion_id,
            }
        # Auto-implementation is deferred to the AI agent
        return {
            "status": "queued",
            "suggestion_id": suggestion.suggestion_id,
            "dry_run": dry_run,
            "note": "Will be implemented by the coding agent in a worktree",
        }
