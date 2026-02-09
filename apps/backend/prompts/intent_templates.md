# Intent-Specific Prompt Templates

This directory contains optimized prompt templates for different intent categories.

## Template Structure

Each intent category should have:

1. **Analysis Focus** - What to pay attention to
2. **Common Patterns** - Typical approaches for this intent
3. **Best Practices** - Industry standards and guidelines
4. **Risk Considerations** - What could go wrong
5. **Verification Strategy** - How to validate success

## Intent Categories

### Bug Fix

**Focus:** Root cause identification, minimal changes, regression prevention

**Patterns:**
- Reproduce → Isolate → Fix → Verify
- Add failing test first (TDD)
- Check for similar bugs elsewhere

**Risks:**
- Introducing new bugs
- Not addressing root cause
- Missing edge cases

---

### Performance Optimization

**Focus:** Measurement, profiling, optimization, validation

**Patterns:**
- Establish baseline metrics
- Profile to find bottlenecks
- Optimize the slowest parts first
- Measure improvement

**Risks:**
- Premature optimization
- Code complexity increase
- Breaking functionality

**Tools:**
- Profilers (cProfile, py-spy)
- Benchmark frameworks
- Load testing tools

---

### Security Fix

**Focus:** Vulnerability assessment, secure coding, testing

**Patterns:**
- Understand the vulnerability (OWASP Top 10)
- Implement defense in depth
- Security testing (SAST/DAST)
- Security review before merge

**Risks:**
- Incomplete fix
- Breaking legitimate use cases
- New vulnerabilities introduced

**Required:**
- Security scan before and after
- Penetration testing
- Security expert review

---

### Refactoring

**Focus:** Behavior preservation, incremental changes, test coverage

**Patterns:**
- Ensure good test coverage first
- Small, incremental changes
- Refactor → Test → Commit cycle
- Keep refactoring separate from features

**Risks:**
- Breaking existing functionality
- Scope creep (adding features)
- Incomplete refactoring

**Guidelines:**
- Don't refactor and add features simultaneously
- Keep PR focused and reviewable
- Run full test suite frequently

---

### API Design

**Focus:** RESTful principles, versioning, documentation

**Patterns:**
- RESTful resource naming
- Proper HTTP methods and status codes
- Comprehensive error responses
- OpenAPI/Swagger documentation

**Best Practices:**
- Consistent naming conventions
- Version your API (v1, v2)
- Pagination for list endpoints
- Rate limiting considerations

**Validation:**
- Contract tests
- API documentation
- Client examples

---

### Data Migration

**Focus:** Safety, rollback strategy, validation

**Patterns:**
- Backup before migration
- Test on staging first
- Incremental migration
- Validation after each step

**Risks:**
- Data loss
- Data corruption
- Downtime
- Performance impact

**Required:**
- Backup strategy
- Rollback plan
- Data validation scripts
- Dry-run on copy of production data

---

### UI/UX Enhancement

**Focus:** Accessibility, responsiveness, user testing

**Patterns:**
- Mobile-first design
- Accessibility from the start (WCAG 2.1)
- Progressive enhancement
- User testing and feedback

**Considerations:**
- Keyboard navigation
- Screen reader compatibility
- Color contrast
- Loading states

**Validation:**
- Visual regression tests
- Accessibility audit
- Cross-browser testing
- User acceptance testing

---

### Infrastructure Changes

**Focus:** Reliability, monitoring, rollback capability

**Patterns:**
- Infrastructure as Code
- Blue-green deployment
- Canary releases
- Comprehensive monitoring

**Risks:**
- Service outages
- Configuration errors
- Security misconfigurations

**Required:**
- Staging environment testing
- Rollback plan
- Monitoring and alerts
- Documentation updates

---

## Using Templates in Prompts

When generating prompts for the coder, include the relevant template section:

```python
def get_intent_specific_guidance(intent_category: IntentCategory) -> str:
    """Get intent-specific guidance for the coder prompt."""
    templates = {
        IntentCategory.BUG_FIX: BUG_FIX_TEMPLATE,
        IntentCategory.PERFORMANCE: PERFORMANCE_TEMPLATE,
        # ... etc
    }
    return templates.get(intent_category, DEFAULT_TEMPLATE)
```

## Future Templates

- [ ] Testing strategy templates
- [ ] Documentation templates
- [ ] Deployment templates
- [ ] Monitoring setup templates
- [ ] Code review checklists per intent

