# AI Skills System - Claude Configuration

## Overview
This directory contains the AI skills system with optimized token usage and dynamic context management.

## Code Style
- Use type hints for all function signatures
- Implement proper error handling with try/catch blocks
- Follow PEP 8 naming conventions
- Use dataclasses for structured data
- Implement logging for debugging and monitoring

## Token Optimization Guidelines
- Limit skill descriptions to 512 characters maximum
- Keep trigger lists under 5 items
- Use sampling for large file collections (>5 files)
- Implement caching for repeated operations
- Compress metadata before validation

## Context Management
- Use aggressive context compaction when >70% of limit
- Create checkpoints for important states
- Clean up context between unrelated tasks
- Prioritize essential information (user_preferences, active_session)

## Performance Optimization
- Default max_workers: 3 (reduced from 4)
- Default timeout: 25s (reduced from 30s)
- Enable optimization for all composite skills
- Use subagents for complex skill combinations (>3 skills)

## File Organization
- `context_optimizer.py` - Context compaction and checkpoint management
- `token_optimizer.py` - Token counting, caching, and compression
- `personalized_context.py` - User profile and project context management
- `dynamic_skill_manager.py` - Runtime skill registration and validation
- `composite_skills.py` - Multi-skill orchestration with subagents

## Testing Strategy
- Focus on single test execution for performance
- Test optimization metrics (compression ratio, cache hit rate)
- Validate token savings vs. original implementation
- Test subagent functionality and error handling

## Workflow Commands
- Use `python -m pytest tests/test_optimization.py` for optimization tests
- Run `python skills/performance_test.py` for performance benchmarks
- Check `python skills/token_optimizer.py` for token usage analysis

## Additional Instructions
- Always optimize metadata before skill validation
- Use predictive caching for frequently accessed content
- Implement subagent investigation for complex skill dependencies
- Monitor and report optimization statistics regularly
