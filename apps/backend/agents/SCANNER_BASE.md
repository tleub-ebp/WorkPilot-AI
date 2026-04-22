# Scanner base — migration guide

`agents/scanner_base.py` provides a shared skeleton for "scanner-style"
agents: a module that reads files, runs regex/AST rules, and emits a
report of findings grouped by severity.

## When to use it

Use it when your agent matches **all three** of:

1. It scans one or more files.
2. It emits a list of findings, each with at least a `severity` and a
   `file` field.
3. A single findings-list plus per-severity counts + a one-line summary
   is enough for downstream consumers (runners, tests, CLI).

It's a good fit for modules like `accessibility_agent`, some of the
security scanners, `tech_debt/scanner.py`, and any "lint-y" agent.

## When NOT to use it

Skip it for:

- **Event/run aggregators** (`flaky_test_detective`, `anomaly_detector`)
  — they aggregate over time-series, not files.
- **Multi-step pipelines** (`api_watcher`, `regression_guardian`) — these
  orchestrate several sub-components (parser + detector + generator).
  Each sub-component can individually be a scanner, but the pipeline
  itself is not.
- Scanners with a fundamentally different entry point, e.g. `DriftScanner`
  which takes `(doc_files, source_symbols)` rather than a single
  `(path, content)` pair. In that case, extend `BaseScanReport` alone
  for the report shape and keep your own `scan()` signature.

## Migration recipe (see `accessibility_agent` for a worked example)

1. Add the import:
   ```python
   from agents.scanner_base import BaseScanner, BaseScanReport
   ```
2. Rename your report's findings list to `findings` (a `list[Finding]`),
   or expose `findings` as an alias via `@property`. The base expects
   `.findings` to be the source of truth.
3. Make your `Report` extend `BaseScanReport[Finding]`. Drop custom
   `passed` / `summary` / `by-severity` properties — the base provides
   them. If your severity vocabulary doesn't match the default, override
   `blocking_severities`.
4. Make your `Scanner` extend `BaseScanner[Finding, Report]`, set
   `report_cls = Report`, and implement only `scan_file(path, content)`.
   `scan_files(files: dict[str, str])` comes for free and swallows
   per-file exceptions so one bad file doesn't abort the whole run.

## Back-compat

Rename in place, keep old attribute names as `@property` aliases
pointing at `findings`. See `A11yReport.violations` for the pattern.
This lets you migrate without a breaking change to runner code.
