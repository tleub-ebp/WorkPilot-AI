﻿# 🔄 Auto-Migration Engine

The Auto-Migration Engine enables **automatic technology stack migration** while preserving business logic. It can migrate between frameworks (React ↔ Vue), databases (MySQL ↔ PostgreSQL), languages (Python 2 → 3), and APIs (REST → GraphQL).

## Features

### ✨ Core Capabilities

- **Automatic Stack Detection**: Detects current framework, language, dependencies
- **Migration Planning**: Generates step-by-step migration plans with risk assessment
- **Code Transformation**: Automatically transforms code between stacks
- **🤖 LLM Enhancement**: Uses Claude to improve transformation quality and handle complex patterns
- **⚡ Performance Optimized**: Caching, parallel processing, and incremental migrations
- **Validation**: Runs tests and validates transformations
- **Rollback Support**: Full rollback to any checkpoint
- **Comprehensive Reporting**: Detailed migration reports with metrics
- **Auto-Fix Integration**: Automatically fixes failing tests after migration

### 🎯 Supported Migrations (MVP)

| From | To | Complexity | Status |
|------|----|----|--------|
| React | Vue | Medium | ✅ MVP |
| MySQL | PostgreSQL | Medium | ✅ MVP |
| Python 2 | Python 3 | Medium | ✅ MVP |
| JavaScript | TypeScript | Low | ✅ MVP |
| REST API | GraphQL | High | ⏳ Future |

### 🛡️ Safety Features

- **Git-based checkpoints**: Save state after each phase
- **Incremental rollback**: Revert to any checkpoint
- **Risk assessment**: Automatic complexity scoring
- **Approval workflows**: High-risk migrations require approval
- **Dry-run mode**: Preview changes without applying

## Installation

The migration engine is part of Auto-Claude. No additional installation needed.

## Quick Start

### 1. List Supported Migrations

```bash
python -m apps.backend.migration list-migrations
```

Output:
```
✨ Supported Migrations:

  REACT → VUE
    Complexity: MEDIUM
    Estimated: 40h

  MYSQL → POSTGRESQL
    Complexity: MEDIUM
    Estimated: 30h

  PYTHON2 → PYTHON3
    Complexity: MEDIUM
    Estimated: 20h
```

### 2. Analyze Your Project

```bash
python -m apps.backend.migration analyze --to vue --project-dir ./src --verbose
```

Output:
```
🔍 Analyzing project at ./src...

✅ Analysis complete!

Complexity Assessment:
  Supported: True
  Affected Files: 125
  Risk Level: medium
  Estimated Effort: 40h
```

### 3. Start Migration

```bash
python -m apps.backend.migration migrate --to vue --project-dir ./src
```

Output:
```
🚀 Starting migration to vue...

✅ Migration initialized!
  Migration ID: 550e8400-e29b-41d4-a716-446655440000
  Source: react
  Target: vue
  Status: planning
  Total Steps: 12
  Risk Level: medium

⚠️  Review the migration plan before proceeding.
   Run: python -m apps.backend.migration report --migration-id <id>
```

### 4. Review Migration Plan

```bash
python -m apps.backend.migration report --migration-id 550e8400-e29b-41d4-a716-446655440000
```

Generates detailed Markdown report with:
- Source/target stack details
- Risk assessment
- Phase-by-phase migration plan
- Estimated timeline
- Recommendations

### 5. Execute Migration (with Auto-fix)

The migration uses the Auto-Fix loop to automatically fix test failures:

```bash
# Start transformation phase
python -m apps.backend.migration migrate --to vue --auto
```

The system will:
1. ✅ Analyze source code
2. ✅ Create backup checkpoint
3. 🔄 Transform code files
4. 🧪 Run test suite
5. 🔧 Auto-fix failures (max 3 attempts)
6. 📋 Generate report

### 6. Rollback if Needed

```bash
# Rollback to specific checkpoint
python -m apps.backend.migration rollback \
  --migration-id 550e8400-e29b-41d4-a716-446655440000 \
  --to-phase backup

# Or rollback to beginning
python -m apps.backend.migration rollback \
  --migration-id 550e8400-e29b-41d4-a716-446655440000
```

### 7. Resume Interrupted Migration

```bash
python -m apps.backend.migration resume \
  --migration-id 550e8400-e29b-41d4-a716-446655440000
```

## Architecture

### Module Structure

```
apps/backend/migration/
├── __init__.py           # Package exports
├── __main__.py           # CLI entry point
├── config.py             # Configuration & constants
├── models.py             # Data models (350 LOC)
├── analyzer.py           # Stack detection (650 LOC)
├── planner.py            # Plan generation (850 LOC)
├── transformer.py        # Code transformation (1400 LOC)
├── orchestrator.py       # Pipeline orchestration (750 LOC)
├── reporter.py           # Report generation (550 LOC)
├── validator.py          # Validation (350 LOC)
├── rollback.py           # Rollback management (350 LOC)
├── transformers/         # Specific transformation modules
│   ├── react_to_vue.py
│   ├── database.py
│   ├── python.py
│   ├── rest_to_graphql.py
│   └── js_to_ts.py
├── prompts/              # LLM prompts
│   ├── analyzer.md
│   ├── planner.md
│   ├── transformer.md
│   └── validator.md
└── README.md             # This file
```

### Data Models

**StackInfo**: Information about a technology stack
- framework, language, version
- database, package manager
- dependencies, additional tools

**MigrationPlan**: Complete migration plan
- source/target stacks
- phases with steps
- risk assessment, effort estimation
- timeline and approvals

**MigrationContext**: State during migration
- plan and transformations
- checkpoints and rollback info
- test results and status

**MigrationPhase**: Logical group of steps
- Analysis, Planning, Backup
- Transformation phases (by migration type)
- Validation, Auto-fix, Reporting

**MigrationStep**: Atomic migration action
- Category (component, database, config, etc.)
- Transformation type
- Files affected
- Validation checks, rollback procedure

**TransformationResult**: Result of code transformation
- Before/after content
- Confidence score
- Errors and warnings
- Diff representation

### Execution Pipeline

```
┌──────────────────────────────────────────────────────────┐
│ 1. START MIGRATION                                       │
│    - User selects target stack                          │
│    - Create migration ID                                │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│ 2. ANALYSIS PHASE                                        │
│    - Detect source stack (StackAnalyzer)               │
│    - Assess complexity and risk                         │
│    - Count affected files                               │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│ 3. PLANNING PHASE                                        │
│    - Generate migration plan (MigrationPlanner)         │
│    - Create phases and steps                            │
│    - Estimate effort and timeline                       │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│ 4. BACKUP & CHECKPOINT                                  │
│    - Create git branch for migration                    │
│    - Save state checkpoint                              │
│    - Prepare rollback capability                        │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│ 5. TRANSFORMATION PHASE                                 │
│    - Run type-specific transformers                     │
│    - Apply code transformations (TransformationEngine)  │
│    - Create checkpoint after each phase                 │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│ 6. VALIDATION PHASE                                     │
│    - Run test suite (MigrationValidator)               │
│    - Check build, lint, types                          │
│    - Detect regressions                                │
└────────────────────────┬─────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
   ✅ PASS                           ❌ FAIL
        │                                 │
        │                   ┌─────────────▼──────────────────┐
        │                   │ 7. AUTO-FIX ISSUES            │
        │                   │    - Use Auto-Fix Loop        │
        │                   │    - Max 3 attempts           │
        │                   │    - Re-validate after fix    │
        │                   └─────────────┬──────────────────┘
        │                                 │
        │        ┌────────────────────────┘
        │        │
        └────────┬──────────────────────────────────────────┐
                 │                                           │
        ┌────────▼─────────────────────────────────────────┐
        │ 8. REPORTING PHASE                              │
        │    - Generate migration report                  │
        │    - Document transformations & changes        │
        │    - Create rollback guide                      │
        │    - Update CHANGELOG                           │
        └────────┬─────────────────────────────────────────┘
                 │
        ┌────────▼─────────────────────────────────────────┐
        │ 9. COMPLETE                                      │
        │    - Migration finished                         │
        │    - Checkpoints available for rollback         │
        │    - Report generated and saved                 │
        └────────────────────────────────────────────────────┘
```

## Configuration

### Risk Levels

- **Low**: Auto-proceed, minimal manual review needed
- **Medium**: Requires review of migration plan
- **High**: Requires explicit approval before proceeding
- **Critical**: Team discussion and approval required

### Timeouts (seconds)

- Analysis: 300s (5 min)
- Planning: 300s (5 min)
- Transformation: 1800s (30 min)
- Test execution: 1200s (20 min)
- Validation: 600s (10 min)

### Auto-Fix Configuration

- Max 3 attempts per failure
- 300s timeout per attempt
- Escalate to Teams if all attempts fail
- Run before validation to catch early errors

## Advanced Usage

### Dry-Run Mode

Preview changes without applying:

```bash
python -m apps.backend.migration migrate --to vue --dry-run
```

### Custom Migration

Extend the engine for custom stacks:

```python
from apps.backend.migration import StackAnalyzer, MigrationOrchestrator

# Analyze
analyzer = StackAnalyzer("./project")
source = analyzer.detect_stack()

# Plan
orchestrator = MigrationOrchestrator("./project")
context = orchestrator.start_migration("custom_target", "custom_lang")

# Transform, validate, report...
```

### Teams Collaboration

Migrations use Teams for:
- **Analyst**: Evaluates migration complexity
- **Architect**: Reviews migration plan
- **QA**: Oversees validation
- **Developer**: Executes transformations
- **Security**: Reviews for data safety

Example (auto-collaboration):

```python
from apps.backend.teams import ClaudeTeam, TeamMode

team = ClaudeTeam(mode=TeamMode.COLLABORATIVE)
debate_result = team.orchestrate({
    "task": f"Plan migration from {source.framework} to {target.framework}",
    "context": context.to_dict(),
})
```

### Integration with Auto-Fix Loop

When validation fails, Auto-Fix Loop is automatically triggered:

```python
from apps.backend.qa import AutoFixLoop

fix_loop = AutoFixLoop(
    max_attempts=3,
    timeout_per_attempt=300,
)

result = fix_loop.run_with_context(
    test_command="npm test",
    code_path=project_dir,
    context=migration_context,
)
```

## Prompts

The system uses specialized prompts for each phase:

### analyzer.md
Instructs Claude to analyze source code structure and identify:
- Framework patterns
- Dependency graph
- Business logic patterns
- Architectural decisions

### planner.md
Generates step-by-step migration plan with:
- Phase decomposition
- Dependency resolution
- Risk scoring
- Effort estimation

### transformer.md
Guides code transformation:
- Pattern matching
- Syntax conversion
- API mapping
- Logic preservation

### validator.md
Validates transformations:
- Correctness checks
- Regression detection
- Compatibility verification
- Performance impact

## Reporting

### Report Contents

1. **Summary**
   - Source/target stacks
   - Risk level and effort
   - Timeline and status

2. **Detailed Plan**
   - Phases and steps
   - Dependencies and ordering
   - Estimated times

3. **Transformations**
   - File-by-file changes
   - Confidence scores
   - Errors and warnings

4. **Validation Results**
   - Test results
   - Build status
   - Linting issues
   - Coverage changes

5. **Recommendations**
   - Manual review areas
   - Breaking changes
   - Deployment strategy

### Report Formats

- **Markdown** (.md): For documentation and version control
- **HTML** (.html): For easy viewing in browser
- **JSON**: For programmatic access

## Limitations & Future Work

### Current MVP Limitations

- ✅ React ↔ Vue, MySQL ↔ PostgreSQL, Python 2 → 3, JS → TS
- ⏳ No parallel transformation (future enhancement)
- ⏳ Limited data migration (schema only)
- ⏳ No custom transformer plugins (future)

### Future Enhancements

1. **Phase 2 (Q2 2026)**
   - Additional framework migrations
   - Parallel transformation support
   - Data migration enhancements

2. **Phase 3 (Q3 2026)**
   - Custom transformer plugins
   - Advanced analytics
   - Performance optimization

3. **Phase 4 (Q4 2026)**
   - AI-guided transformations
   - Community migration templates
   - Advanced rollback strategies

## Troubleshooting

### Migration Not Starting

```bash
# Check project structure
python -m apps.backend.migration analyze --to vue --verbose

# Verify git repository
git status
```

### Test Failures After Migration

The Auto-Fix loop will attempt to fix automatically (3 attempts). If that fails:

```bash
# Check test output
npm test  # or pytest, etc.

# Review migration plan for breaking changes
python -m apps.backend.migration report --migration-id <id>

# Rollback if needed
python -m apps.backend.migration rollback --migration-id <id>
```

### Rollback Issues

```bash
# Check available checkpoints
git log --oneline | grep "Migration checkpoint"

# View rollback plan
python -m apps.backend.migration status --migration-id <id>

# Manual rollback as last resort
git reset --hard <commit-hash>
```

## Performance

- **Analysis**: ~30 seconds for 100-file project
- **Planning**: ~20 seconds
- **Transformation**: ~1-5 seconds per file
- **Validation**: ~60 seconds (depends on test suite)
- **Full Migration**: ~30-60 minutes for typical project

## Security Considerations

- 🔐 All migrations tracked in git history
- 🔐 No credentials stored in migration files
- 🔐 Sensitive data excluded from reports
- 🔐 Rollback capability for safety net
- 🔐 Security review in Teams approval

## Contributing

To add support for new migrations:

1. Create transformer in `transformers/`
2. Register in `config.py`
3. Add prompts in `prompts/`
4. Add tests in `tests/`
5. Update documentation

## License

MIT - See LICENSE file

## Support

For issues and questions:
- 📖 Documentation: `docs/features/MIGRATION_ENGINE.md`
- 💬 GitHub Discussions
- 🐛 GitHub Issues
- 📧 Team Contact
