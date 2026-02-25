---
name: framework-migration
description: Automate framework and version upgrades with step-by-step plans, dependency resolution, and rollback support. Use when user mentions migration, upgrade, framework switch, version update, or technology stack changes.
triggers: ["migration", "upgrade", "framework switch", "version update", "technology change", "stack migration", "react upgrade", "express to fastify", "javascript to typescript"]
category: development
version: "1.0.0"
author: "Auto-Claude EBP Team"
---

# Framework Migration Skill

## Overview

Specialized skill for managing framework migrations (React 18→19, Express→Fastify, JS→TS, etc.). Analyzes codebase to detect current stack, proposes migration plans with per-file transformation steps, executes transformations with automatic dependency resolution, and generates regression tests.

## Quick Start

1. **Analyze current stack**: Use `scripts/analyze_stack.py` to detect current technology stack
2. **Create migration plan**: Generate step-by-step migration plan with breaking changes
3. **Execute migration**: Run transformations with automatic rollback support
4. **Validate results**: Run regression tests to ensure migration success

## Supported Migrations

### Version Upgrades
- **React 18→19**: ReactDOM.render → createRoot, automatic batching
- **Express 4→5**: req.query behavior changes, improved security
- **Major framework upgrades**: Breaking changes detection and automatic fixes

### Framework Switches
- **Express→Fastify**: Performance and type safety improvements
- **JavaScript→TypeScript**: Type safety migration with tsconfig generation
- **Build tool migrations**: Webpack→Vite, custom build systems

### Language Migrations
- **JavaScript→TypeScript**: Full type migration with interface generation
- **ES5→ES6+**: Modern JavaScript patterns and features

## Key Features

### Stack Analysis
- Automatic detection of current technology stack
- Dependency analysis with version tracking
- Configuration file identification
- Build tool detection

### Migration Planning
- Breaking changes database lookup
- Step-by-step transformation plans
- Risk assessment and time estimation
- Rollback strategy generation

### Execution Engine
- Automated code transformations
- Dependency updates with conflict resolution
- Configuration file migrations
- Progress tracking and error handling

### Quality Assurance
- Regression test generation
- Automated validation scripts
- Rollback capabilities
- Migration reporting

## Resources

### Scripts
- `scripts/analyze_stack.py` - Stack analysis and detection
- `scripts/execute_migration.py` - Migration execution engine
- `scripts/validate_migration.py` - Post-migration validation
- `scripts/generate_tests.py` - Regression test generation

### Data Files
- `data/breaking_changes.json` - Database of known breaking changes
- `data/migration_templates.json` - Common migration patterns
- `data/framework_configs.json` - Framework-specific configurations

### Templates
- `templates/migration_plan.md` - Migration plan template
- `templates/test_suite.py` - Regression test template
- `templates/rollback_script.sh` - Rollback script template

## Usage Examples

### Basic Migration
```python
# Analyze current stack
analysis = skill.execute_script("analyze_stack.py", {"project_root": "/path/to/project"})

# Create migration plan
plan = skill.create_migration_plan(
    source_framework="react",
    source_version="18.2",
    target_version="19.0"
)

# Execute migration
result = skill.execute_script("execute_migration.py", {
    "plan_id": plan.plan_id,
    "dry_run": False
})
```

### Complex Migration
```python
# Framework switch with custom steps
plan = skill.create_migration_plan(
    source_framework="express",
    target_framework="fastify",
    custom_steps=[
        {
            "title": "Update middleware configuration",
            "description": "Convert Express middleware to Fastify hooks",
            "step_type": "code_change",
            "risk": "medium"
        }
    ]
)
```

## Breaking Changes Database

The skill maintains a comprehensive database of breaking changes:

```json
{
  "react:18:19": {
    "breaking_changes": [
      {
        "change_type": "api_removed",
        "description": "ReactDOM.render removed — use createRoot instead",
        "old_api": "ReactDOM.render(<App />, document.getElementById('root'))",
        "new_api": "createRoot(document.getElementById('root')).render(<App />)",
        "auto_fixable": true
      }
    ],
    "dependency_updates": {"react": "^19.0.0", "react-dom": "^19.0.0"}
  }
}
```

## Error Handling

### Common Issues
- **Dependency conflicts**: Automatic resolution with fallback options
- **Breaking changes**: Manual intervention flags with detailed guidance
- **Configuration mismatches**: Template-based fixes with validation
- **Test failures**: Isolation and specific error reporting

### Recovery Strategies
- Automatic rollback on critical failures
- Partial migration recovery points
- Manual intervention guidance
- Progress preservation for resume capability

## Best Practices

### Before Migration
1. **Create backup**: Always create a snapshot before starting
2. **Run tests**: Ensure existing test suite passes
3. **Check dependencies**: Verify all dependencies are compatible
4. **Document current state**: Record current stack and configurations

### During Migration
1. **Follow the plan**: Execute steps in the recommended order
2. **Validate each step**: Run validation after each major change
3. **Monitor progress**: Track completed steps and any issues
4. **Save checkpoints**: Create restore points during complex migrations

### After Migration
1. **Run full test suite**: Ensure all functionality works
2. **Performance testing**: Verify no performance regressions
3. **Documentation update**: Update project documentation
4. **Team training**: Train team on new framework/version

## Integration with Other Skills

This skill works well with:
- **code-review** skills for validating migration changes
- **testing** skills for comprehensive test coverage
- **documentation** skills for updating project docs
- **team-collaboration** skills for coordinating migrations

## Troubleshooting

### Migration Fails Mid-Process
1. Check the error logs in the migration report
2. Use rollback scripts to return to previous state
3. Fix the identified issue
4. Resume migration from the failed step

### Dependency Conflicts
1. Review conflict resolution suggestions
2. Manually update package.json if needed
3. Clear node_modules and reinstall
4. Re-run dependency resolution step

### Test Failures
1. Isolate failing tests
2. Check if tests need updates for new framework
3. Update test code accordingly
4. Re-run test suite

## Contributing

To add support for new migrations:
1. Add breaking changes to `data/breaking_changes.json`
2. Create transformation scripts in `scripts/`
3. Add test cases to `templates/`
4. Update this SKILL.md documentation

## Version History

- **v1.0.0**: Initial release with React 18→19, Express→Fastify, JS→TS support
- **v1.1.0**: Added Vue 2→3 migration support
- **v1.2.0**: Enhanced breaking changes database
- **v1.3.0**: Added automated rollback capabilities
