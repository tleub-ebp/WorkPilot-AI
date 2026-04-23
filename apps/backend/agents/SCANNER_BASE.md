# Scanner base — migration guide

`agents/scanner_base.py` provides a shared skeleton for "scanner-style"
agents: a module that reads source artifacts, runs rules, and emits a
report of findings grouped by severity. It is intentionally small — one
generic report class (`BaseScanReport`) and one optional scanner base
(`BaseScanner`) — because the ~40 agent modules in the backend do **not**
share a single shape.

## The three buckets

A deliberate audit of every `*_agent` / `*_detector` / `*_detective` /
`*_scanner` / `*_analyzer` module yielded three distinct patterns.
`BaseScanner` only fits the first.

### Bucket 1 — per-file scanners (3 agents, 3 migrated)

Shape: `scan_file(path: str, content: str) -> Report`. The agent walks
the file tree or receives a `{path: content}` map from a runner.

| Agent | File | Status |
|---|---|---|
| `accessibility_agent` | `accessibility_scanner.py` | ✅ migrated |
| `i18n_agent` | `i18n_scanner.py` | ✅ migrated |
| `security.scan_secrets` | `scan_secrets.py` | ⚪ function-based, not class-based — kept as-is (direct `scan_content(content, path)` API) |

`security/injection_scanner.py` has a `scan(text, source)` signature
(scans arbitrary strings, not files). Doesn't fit `BaseScanner`.

### Bucket 2 — batch analyzers (report rides on `BaseScanReport` only)

Shape: `analyze(batch_of_items) -> Report`. The input isn't a file map —
it's runs, events, a git history, a coverage report, etc. The analyzer
class is kept bespoke, but the *report* can still reuse
`BaseScanReport[Finding]` as long as `Finding` exposes `severity` and
`file` (or a `@property` that returns them).

| Agent | File | Status |
|---|---|---|
| `flaky_test_detective` | `flaky_analyzer.py` | ✅ report migrated |
| `git_surgeon` | `history_analyzer.py` | ⚪ candidate |
| `prediction` | `risk_analyzer.py` | ⚪ candidate |
| `review.test_coverage` | — | ⚪ candidate |
| `spec.complexity` | `complexity_analyzer.py` | ⚪ candidate |

### Bucket 3 — stateful monitors / orchestrators (no base fits)

These either hold long-lived state (sessions, incidents) or orchestrate
multiple sub-components (parser + detector + generator). Forcing any
`BaseScanner` / `BaseScanReport` inheritance would be speculative
architecture — the useful reuse is at the report level at most, not the
agent level.

| Agent | Why it doesn't fit |
|---|---|
| `security.anomaly_detector` | per-session state (`start_session`, `record_event`, `get_anomalies`), not a one-shot analyze |
| `api_watcher` | pipeline: `contract_parser` + `breaking_change_detector` + `migration_guide_generator` |
| `regression_guardian` | pipeline: `incident_parser` + `fixture_builder` + `test_generator` + `dedup_checker` |
| `compliance_collector` | evidence-gathering orchestrator, not per-file |
| `tech_debt.scanner` | function-based multi-signal scanner (TODOs + long funcs + deps + coverage) |
| `browser_agent`, `database_agent`, `mission_control`, `self_healing`, … | orchestrators with their own domain-specific APIs |

## Migration recipe (Bucket 1 — scanner)

1. Add the import:
   ```python
   from agents.scanner_base import BaseScanner, BaseScanReport
   ```
2. Rename your report's findings list to `findings` (a `list[Finding]`),
   or expose `findings` as an alias via `@property` + `@setter` that
   returns the *same list object* (not a copy). The base expects
   `.findings` to be the source of truth.
3. Make your `Report` extend `BaseScanReport[Finding]`. Drop custom
   `passed` / `summary` / by-severity properties — the base provides
   them. If your severity vocabulary doesn't match the default, override
   `blocking_severities`. If your summary groups by *type* or *cause*
   rather than severity, override `summary` (see `I18nReport`,
   `FlakyReport`).
4. Make your `Scanner` extend `BaseScanner[Finding, Report]`, set
   `report_cls = Report`, and implement only `scan_file(path, content)`.
   `scan_files(files: dict[str, str])` comes for free and swallows
   per-file exceptions so one bad file doesn't abort the whole run.

## Migration recipe (Bucket 2 — analyzer with shared report)

1. Add `from agents.scanner_base import BaseScanReport`.
2. Your `Finding` dataclass must expose `severity` (str or Enum with
   `.value`) and `file` (str). If it doesn't, add them as `@property`
   that derives from existing fields — don't change the on-disk shape.
   See `FlakyTest.file` (aliases `file_path`) and `FlakyTest.severity`
   (derives from `confidence`).
3. Extend `BaseScanReport[Finding]`. Keep your domain-specific fields
   (`total_tests_analysed`, `coverage`, …) as extra dataclass attributes.
4. Keep back-compat aliases for the old attribute name (`flaky_tests` →
   `findings`, `violations` → `findings`, `issues` → `findings`) with
   both getter and setter so downstream code that assigns or mutates
   the list keeps working.
5. Override `summary` if the UI displays a grouping that isn't
   per-severity (flaky groups by cause, i18n groups by issue type).

## Back-compat rule

Rename in place, keep old attribute names as `@property` aliases
pointing at `findings`. **Same list object, not a copy.** This lets
you migrate without breaking any caller — and the
`test_*_alias_is_same_object` regression test in
`tests/backend/test_scanner_base_migrations.py` locks that invariant.

## What NOT to do

- **Don't create a `BaseAgent` covering all ~40 modules.** We tried; the
  shapes are too different. A base that abstracts nothing adds cost
  without reducing duplication.
- **Don't force `scan_file` onto analyzers.** `FlakyAnalyzer.analyze(runs)`
  is the natural API — wrapping it in a `scan_file` that takes `(path,
  content)` and ignores both would be dishonest.
- **Don't extend `BaseScanReport` when your report has no findings list.**
  If your agent produces a fundamentally different output (e.g. a single
  `HealthStatus` dataclass, a `ComplianceGrade` scalar), just use a
  bespoke report class.
