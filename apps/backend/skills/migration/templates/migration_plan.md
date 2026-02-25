# Migration Plan: {{source_framework}} {{source_version}} → {{target_framework}} {{target_version}}

**Plan ID**: {{plan_id}}  
**Created**: {{created_at}}  
**Estimated Time**: {{estimated_total_minutes}} minutes  
**Risk Level**: {{risk_level}}  

## Overview

This migration plan outlines the step-by-step process to upgrade from {{source_framework}} {{source_version}} to {{target_framework}} {{target_version}}. The plan includes dependency updates, code transformations, and validation steps.

## Pre-Migration Checklist

- [ ] Create a full backup of the codebase
- [ ] Ensure all tests pass in current environment
- [ ] Document current configuration and dependencies
- [ ] Notify team members of upcoming migration
- [ ] Schedule maintenance window if needed

## Migration Steps

{% for step in steps %}
### Step {{step.order}}: {{step.title}}

**Type**: {{step.step_type}}  
**Risk**: {{step.risk}}  
**Estimated Time**: {{step.estimated_minutes}} minutes  
**Status**: {{step.status}}

**Description**: {{step.description}}

{% if step.commands %}
**Commands to Run**:
```bash
{% for command in step.commands %}
{{command}}
{% endfor %}
```
{% endif %}

{% if step.code_transforms %}
**Code Transformations**:
{% for transform in step.code_transforms %}
- **File**: `{{transform.file_pattern}}`
- **Change**: `{{transform.old}}` → `{{transform.new}}`
- **Description**: {{transform.description}}
{% endfor %}
{% endif %}

{% if step.rollback_commands %}
**Rollback Commands**:
```bash
{% for command in step.rollback_commands %}
{{command}}
{% endfor %}
```
{% endif %}

---

{% endfor %}

## Breaking Changes

{% for breaking_change in breaking_changes %}
### {{breaking_change.change_type|title}}: {{breaking_change.description}}

**Old API**: `{{breaking_change.old_api}}`  
**New API**: `{{breaking_change.new_api}}`  
**Auto-fixable**: {{breaking_change.auto_fixable}}  
**Affected Files**: {{breaking_change.affected_files|join(', ')}}

{% if breaking_change.migration_guide %}
**Migration Guide**: {{breaking_change.migration_guide}}
{% endif %}

---

{% endfor %}

## Dependency Updates

{% for dep_name, dep_version in dependency_updates.items() %}
- **{{dep_name}}**: Upgrade to `{{dep_version}}`
{% endfor %}

## Post-Migration Validation

### Required Tests
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Application starts successfully
- [ ] Key user workflows function correctly
- [ ] Performance benchmarks meet expectations

### Manual Verification
- [ ] Check application logs for errors
- [ ] Verify UI components render correctly
- [ ] Test API endpoints
- [ ] Validate configuration files
- [ ] Check build and deployment processes

## Rollback Plan

If migration fails, execute rollback in reverse order:

{% for step in steps|reverse %}
{% if step.rollback_commands %}
1. **Rollback Step {{step.order}}**: {{step.title}}
   ```bash
   {% for command in step.rollback_commands %}
   {{command}}
   {% endfor %}
   ```
{% endif %}
{% endfor %}

## Contact Information

- **Migration Lead**: [Name]
- **Technical Contact**: [Name]
- **Emergency Contact**: [Name]

## Notes

{% for note in notes %}
- {{note}}
{% endfor %}

---

*This migration plan was generated automatically by the Framework Migration Skill.*
