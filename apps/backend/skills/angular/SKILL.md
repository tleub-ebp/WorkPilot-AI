---
name: angular-development
description: Angular framework development, migration, and component generation. Use for Angular projects, version upgrades, component creation, and Angular-specific optimizations.
triggers: ["angular", "@angular", "ng", "angular-cli", "angular upgrade", "angular component", "angular migration"]
category: development
version: "1.0.0"
author: "Auto-Claude EBP Team"
---

# Angular Development Skill

## Quick Actions
- **Analyze project**: Run `analyze_angular_project.py` to detect Angular version and project structure
- **Upgrade version**: Run `upgrade_angular_version.py` for Angular version migrations
- **Generate component**: Run `generate_component.py` to create new Angular components
- **Optimize performance**: Analyze and optimize Angular performance patterns

## Supported Angular Versions
- **Angular 15→16**: Standalone components migration, signals introduction
- **Angular 16→17**: Improved signals, new control flow syntax
- **Angular 17→18**: Zoneless applications, deferred loading
- **Angular 18→19**: Enhanced hydration, better performance

## Key Features
- Automatic Angular project detection and version analysis
- Breaking changes database with auto-fix capabilities
- Component generation with best practices
- Performance optimization recommendations
- Standalone component migration support
- Signals adoption guidance

## Resources
- **Scripts**: `analyze_angular_project.py`, `upgrade_angular_version.py`, `generate_component.py`
- **Templates**: Component templates in `templates/` directory
- **Data**: `angular_breaking_changes.json` (known breaking changes database)

## Usage Examples

### Project Analysis
```python
# Analyze Angular project
analysis = skill.execute_script("analyze_angular_project.py", {"project_root": "/path/to/project"})

# Get version and dependencies
version = analysis.angular_version
dependencies = analysis.dependencies
```

### Version Upgrade
```python
# Upgrade Angular 16 to 17
upgrade = skill.execute_script("upgrade_angular_version.py", {
    "project_root": "/path/to/project",
    "target_version": "17.0.0"
})
```

### Component Generation
```python
# Generate new component
component = skill.execute_script("generate_component.py", {
    "name": "UserProfile",
    "type": "component",
    "standalone": True,
    "project_root": "/path/to/project"
})
```

## Angular Best Practices

### Component Structure
- Use standalone components when possible
- Implement proper change detection strategies
- Follow Angular style guide conventions
- Use signals for reactive state management

### Performance Optimization
- Implement OnPush change detection
- Use trackBy in ngFor loops
- Lazy load modules and components
- Optimize bundle size with tree-shaking

### Migration Guidelines
- Update dependencies incrementally
- Test breaking changes thoroughly
- Use Angular CLI migration commands
- Implement proper error handling

## Breaking Changes Database

The skill includes a comprehensive database of Angular breaking changes with:
- Automatic detection of affected code
- Suggested fixes and migrations
- Compatibility checks
- Rollback capabilities

## Integration with Other Skills

This Angular skill works seamlessly with:
- **framework-migration**: For complex technology stack changes
- **typescript**: For TypeScript-specific optimizations
- **testing**: For Angular testing setup and best practices
