#!/usr/bin/env python3
"""
Composite Skills System

Allows creation and execution of composite skills that combine multiple
individual skills with composition rules and orchestration.

Features:
- Skill composition and orchestration
- Dependency management
- Result combination and filtering
- Parallel and sequential execution
- Error handling and recovery
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from .token_optimizer import TokenOptimizer, create_token_optimizer
from .context_optimizer import ContextOptimizer

logger = logging.getLogger(__name__)


class CompositionType(Enum):
    """Types of skill composition."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    PIPELINE = "pipeline"


class ExecutionStatus(Enum):
    """Status of skill execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SkillExecutionResult:
    """Result of skill execution with optimization."""
    skill_name: str
    status: ExecutionStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    optimized: bool = False  # Track if result was optimized
    
    def to_dict(self) -> Dict:
        return {
            'skill_name': self.skill_name,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time,
            'tokens_used': self.tokens_used,
            'metadata': self.metadata,
            'optimized': self.optimized
        }


@dataclass
class CompositionRule:
    """Rule for skill composition."""
    name: str
    condition: Optional[Callable[[Dict], bool]] = None
    transformer: Optional[Callable[[Any], Any]] = None
    validator: Optional[Callable[[Any], bool]] = None
    error_handler: Optional[Callable[[Exception], Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompositeSkill:
    """Represents a composite skill that combines multiple skills with optimization."""
    name: str
    description: str
    sub_skills: List[str]
    composition_type: CompositionType
    composition_rules: List[CompositionRule] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    max_parallel_workers: int = 3  # Reduced from 4 for resource optimization
    timeout: float = 25.0  # Reduced from 30.0
    retry_attempts: int = 1  # Reduced from default for efficiency
    optimization_enabled: bool = True
    
    def __post_init__(self):
        # Validate composition
        self._validate_composition()
    
    def _validate_composition(self):
        """Validate the composition configuration."""
        if not self.sub_skills:
            raise ValueError("Composite skill must have at least one sub-skill")
        
        # Check for circular dependencies
        if self._has_circular_dependencies():
            raise ValueError("Circular dependencies detected in composite skill")
    
    def _has_circular_dependencies(self) -> bool:
        """Check for circular dependencies."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(skill: str) -> bool:
            if skill in rec_stack:
                return True
            if skill in visited:
                return False
            
            visited.add(skill)
            rec_stack.add(skill)
            
            for dep in self.dependencies.get(skill, []):
                if has_cycle(dep):
                    return True
            
            rec_stack.remove(skill)
            return False
        
        for skill in self.sub_skills:
            if has_cycle(skill):
                return True
        
        return False


class SubAgent:
    """Subagent for specialized investigation tasks."""
    
    def __init__(self, name: str, handler: Callable):
        self.name = name
        self.handler = handler
        self.usage_count = 0
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute subagent task."""
        self.usage_count += 1
        return self.handler(*args, **kwargs)


class CompositeSkillExecutor:
    """Executes composite skills with orchestration and subagent optimization."""
    
    def __init__(self, skill_manager, max_workers: int = 3):  # Reduced from 4
        self.skill_manager = skill_manager
        self.max_workers = max_workers
        self.execution_history: List[Dict] = []
        
        # Optimization systems
        self.token_optimizer = create_token_optimizer()
        self.context_optimizer = ContextOptimizer(max_context_size=6000)
        
        # Subagent system for investigation
        self.subagents = {
            'investigator': SubAgent('investigator', self._investigate_skill),
            'validator': SubAgent('validator', self._validate_result),
            'optimizer': SubAgent('optimizer', self._optimize_execution)
        }
        
        # Performance metrics
        self.performance_metrics = {
            'total_executions': 0,
            'optimized_executions': 0,
            'subagent_usage': 0,
            'token_savings': 0
        }
    
    def execute(self, composite_skill: CompositeSkill, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a composite skill with optimization and subagents."""
        start_time = time.time()
        context = context or {}
        
        logger.info(f"Executing optimized composite skill: {composite_skill.name}")
        self.performance_metrics['total_executions'] += 1
        
        try:
            # Optimize context if enabled
            if composite_skill.optimization_enabled:
                optimized_context = self.context_optimizer.optimize_context(context)
                self.performance_metrics['optimized_executions'] += 1
            else:
                optimized_context = context
            
            # Use subagents for investigation if complex skill
            if len(composite_skill.sub_skills) > 3:
                investigation_result = self._use_subagent('investigator', composite_skill, optimized_context)
                if investigation_result:
                    optimized_context.update(investigation_result)
                    self.performance_metrics['subagent_usage'] += 1
            
            # Execute based on composition type
            if composite_skill.composition_type == CompositionType.SEQUENTIAL:
                results = self._execute_sequential(composite_skill, optimized_context)
            elif composite_skill.composition_type == CompositionType.PARALLEL:
                results = self._execute_parallel(composite_skill, optimized_context)
            elif composite_skill.composition_type == CompositionType.CONDITIONAL:
                results = self._execute_conditional(composite_skill, optimized_context)
            elif composite_skill.composition_type == CompositionType.PIPELINE:
                results = self._execute_pipeline(composite_skill, optimized_context)
            else:
                raise ValueError(f"Unsupported composition type: {composite_skill.composition_type}")
            
            # Optimize results with subagent validation
            optimized_results = self._optimize_results(results, composite_skill)
            
            # Combine results
            combined_result = self._combine_results(optimized_results, composite_skill)
            
            execution_time = time.time() - start_time
            
            # Record execution
            execution_record = {
                'composite_skill': composite_skill.name,
                'execution_time': execution_time,
                'success': all(r.status == ExecutionStatus.COMPLETED for r in results.values()),
                'sub_skill_results': {name: result.to_dict() for name, result in results.items()},
                'context': optimized_context,
                'optimized': composite_skill.optimization_enabled,
                'subagents_used': self.performance_metrics['subagent_usage']
            }
            self.execution_history.append(execution_record)
            
            # Update performance metrics
            self.performance_metrics['token_savings'] += self.token_optimizer.metrics.saved_tokens
            
            logger.info(f"Completed optimized composite skill {composite_skill.name} in {execution_time:.2f}s")
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Failed to execute composite skill {composite_skill.name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def _execute_sequential(self, composite_skill: CompositeSkill, context: Dict) -> Dict[str, SkillExecutionResult]:
        """Execute skills sequentially."""
        results = {}
        
        # Execute in dependency order
        ordered_skills = self._get_dependency_order(composite_skill)
        
        for skill_name in ordered_skills:
            result = self._execute_single_skill(skill_name, context, composite_skill)
            results[skill_name] = result
            
            # Stop on failure if not configured to continue
            if result.status == ExecutionStatus.FAILED:
                logger.warning(f"Skill {skill_name} failed, stopping sequential execution")
                break
        
        return results
    
    def _execute_parallel(self, composite_skill: CompositeSkill, context: Dict) -> Dict[str, SkillExecutionResult]:
        """Execute skills in parallel."""
        results = {}
        
        # Get skills that can run in parallel (no dependencies)
        independent_skills = self._get_independent_skills(composite_skill)
        
        with ThreadPoolExecutor(max_workers=min(composite_skill.max_parallel_workers, len(independent_skills))) as executor:
            # Submit all independent skills
            future_to_skill = {
                executor.submit(self._execute_single_skill, skill_name, context, composite_skill): skill_name
                for skill_name in independent_skills
            }
            
            # Collect results
            for future in as_completed(future_to_skill):
                skill_name = future_to_skill[future]
                try:
                    result = future.result()
                    results[skill_name] = result
                except Exception as e:
                    logger.error(f"Parallel execution failed for {skill_name}: {e}")
                    results[skill_name] = SkillExecutionResult(
                        skill_name=skill_name,
                        status=ExecutionStatus.FAILED,
                        error=str(e)
                    )
        
        # Execute dependent skills sequentially
        dependent_skills = [skill for skill in composite_skill.sub_skills if skill not in independent_skills]
        for skill_name in dependent_skills:
            result = self._execute_single_skill(skill_name, context, composite_skill)
            results[skill_name] = result
        
        return results
    
    def _execute_conditional(self, composite_skill: CompositeSkill, context: Dict) -> Dict[str, SkillExecutionResult]:
        """Execute skills based on conditions."""
        results = {}
        
        for skill_name in composite_skill.sub_skills:
            # Check if skill should be executed
            should_execute = True
            
            for rule in composite_skill.composition_rules:
                if rule.name == f"condition_{skill_name}" and rule.condition:
                    should_execute = rule.condition(context)
                    break
            
            if should_execute:
                result = self._execute_single_skill(skill_name, context, composite_skill)
                results[skill_name] = result
            else:
                results[skill_name] = SkillExecutionResult(
                    skill_name=skill_name,
                    status=ExecutionStatus.SKIPPED,
                    metadata={'reason': 'Condition not met'}
                )
        
        return results
    
    def _execute_pipeline(self, composite_skill: CompositeSkill, context: Dict) -> Dict[str, SkillExecutionResult]:
        """Execute skills as a pipeline with data flow."""
        results = {}
        pipeline_data = context.copy()
        
        for skill_name in composite_skill.sub_skills:
            # Update context with results from previous skills
            skill_context = pipeline_data.copy()
            skill_context['previous_results'] = {name: result.result for name, result in results.items() if result.result}
            
            result = self._execute_single_skill(skill_name, skill_context, composite_skill)
            results[skill_name] = result
            
            # Update pipeline data with current result
            if result.result:
                pipeline_data[f'{skill_name}_result'] = result.result
                
                # Apply transformation rules
                for rule in composite_skill.composition_rules:
                    if rule.name == f"transform_{skill_name}" and rule.transformer:
                        try:
                            transformed = rule.transformer(result.result)
                            pipeline_data[f'{skill_name}_transformed'] = transformed
                        except Exception as e:
                            logger.warning(f"Transformation failed for {skill_name}: {e}")
            
            # Stop on failure
            if result.status == ExecutionStatus.FAILED:
                logger.warning(f"Pipeline stopped at {skill_name} due to failure")
                break
        
        return results
    
    def _execute_single_skill(self, skill_name: str, context: Dict, composite_skill: CompositeSkill) -> SkillExecutionResult:
        """Execute a single skill with retry logic."""
        start_time = time.time()
        
        for attempt in range(composite_skill.retry_attempts + 1):
            try:
                logger.debug(f"Executing skill {skill_name} (attempt {attempt + 1})")
                
                # Get skill from manager
                skill = self.skill_manager.load_skill(skill_name)
                if not skill:
                    raise ValueError(f"Skill not found: {skill_name}")
                
                # Execute skill
                result = skill.execute_script("main.py", context) if hasattr(skill, 'execute_script') else None
                
                execution_time = time.time() - start_time
                
                # Apply validation rules
                for rule in composite_skill.composition_rules:
                    if rule.name == f"validate_{skill_name}" and rule.validator:
                        if not rule.validator(result):
                            raise ValueError(f"Validation failed for {skill_name}")
                
                return SkillExecutionResult(
                    skill_name=skill_name,
                    status=ExecutionStatus.COMPLETED,
                    result=result,
                    execution_time=execution_time,
                    tokens_used=0  # Would be calculated in real implementation
                )
                
            except Exception as e:
                if attempt < composite_skill.retry_attempts:
                    logger.warning(f"Skill {skill_name} failed (attempt {attempt + 1}), retrying: {e}")
                    time.sleep(1)  # Brief delay before retry
                    continue
                else:
                    # Apply error handling rules
                    error_result = None
                    for rule in composite_skill.composition_rules:
                        if rule.name == f"error_{skill_name}" and rule.error_handler:
                            try:
                                error_result = rule.error_handler(e)
                            except Exception as handler_error:
                                logger.error(f"Error handler failed for {skill_name}: {handler_error}")
                    
                    return SkillExecutionResult(
                        skill_name=skill_name,
                        status=ExecutionStatus.FAILED,
                        error=str(e),
                        execution_time=time.time() - start_time,
                        result=error_result
                    )
    
    def _get_dependency_order(self, composite_skill: CompositeSkill) -> List[str]:
        """Get skills in dependency order (topological sort)."""
        visited = set()
        result = []
        
        def visit(skill: str):
            if skill in visited:
                return
            visited.add(skill)
            
            for dep in composite_skill.dependencies.get(skill, []):
                visit(dep)
            
            result.append(skill)
        
        for skill in composite_skill.sub_skills:
            visit(skill)
        
        return result
    
    def _get_independent_skills(self, composite_skill: CompositeSkill) -> List[str]:
        """Get skills that have no dependencies."""
        return [skill for skill in composite_skill.sub_skills 
                if not composite_skill.dependencies.get(skill)]
    
    def _combine_results(self, results: Dict[str, SkillExecutionResult], composite_skill: CompositeSkill) -> Dict[str, Any]:
        """Combine results from multiple skills."""
        combined = {
            'composite_skill': composite_skill.name,
            'success': all(r.status == ExecutionStatus.COMPLETED for r in results.values()),
            'sub_skills': len(results),
            'completed': sum(1 for r in results.values() if r.status == ExecutionStatus.COMPLETED),
            'failed': sum(1 for r in results.values() if r.status == ExecutionStatus.FAILED),
            'skipped': sum(1 for r in results.values() if r.status == ExecutionStatus.SKIPPED),
            'results': {},
            'execution_summary': {}
        }
        
        # Collect individual results
        for skill_name, result in results.items():
            combined['results'][skill_name] = {
                'status': result.status.value,
                'result': result.result,
                'error': result.error,
                'execution_time': result.execution_time,
                'tokens_used': result.tokens_used
            }
        
        # Calculate summary statistics
        if results:
            total_time = sum(r.execution_time for r in results.values())
            total_tokens = sum(r.tokens_used for r in results.values())
            
            combined['execution_summary'] = {
                'total_execution_time': total_time,
                'average_execution_time': total_time / len(results),
                'total_tokens_used': total_tokens,
                'success_rate': combined['completed'] / len(results)
            }
        
        # Apply combination rules
        for rule in composite_skill.composition_rules:
            if rule.name == "combine_results" and rule.transformer:
                try:
                    combined = rule.transformer(combined)
                except Exception as e:
                    logger.warning(f"Result combination failed: {e}")
        
        return combined
    
    def get_execution_history(self, limit: int = 100) -> List[Dict]:
        """Get execution history."""
        return self.execution_history[-limit:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics with optimization metrics."""
        if not self.execution_history:
            return {
                'total_executions': 0,
                'optimized_executions': 0,
                'subagent_usage': 0,
                'token_savings': 0,
                'token_optimizer_metrics': self.token_optimizer.get_optimization_report()
            }
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for record in self.execution_history if record['success'])
        
        execution_times = [record['execution_time'] for record in self.execution_history]
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': successful_executions / total_executions,
            'average_execution_time': sum(execution_times) / len(execution_times),
            'min_execution_time': min(execution_times),
            'max_execution_time': max(execution_times),
            'optimization_metrics': self.performance_metrics,
            'token_optimizer_metrics': self.token_optimizer.get_optimization_report(),
            'subagent_stats': {
                name: {'usage_count': agent.usage_count} 
                for name, agent in self.subagents.items()
            }
        }
    
    def _use_subagent(self, agent_name: str, composite_skill: CompositeSkill, context: Dict) -> Optional[Dict]:
        """Use a subagent for specialized task."""
        if agent_name in self.subagents:
            try:
                return self.subagents[agent_name].execute(composite_skill, context)
            except Exception as e:
                logger.warning(f"Subagent {agent_name} failed: {e}")
        return None
    
    def _investigate_skill(self, composite_skill: CompositeSkill, context: Dict) -> Dict:
        """Investigator subagent: analyze skill dependencies and requirements."""
        investigation = {
            'dependency_analysis': {},
            'resource_requirements': {},
            'optimization_suggestions': []
        }
        
        # Analyze dependencies
        for skill_name in composite_skill.sub_skills:
            skill_info = self.skill_manager.get_skill_info(skill_name)
            if skill_info:
                investigation['dependency_analysis'][skill_name] = {
                    'complexity': 'high' if skill_info.get('dependencies') else 'low',
                    'estimated_tokens': skill_info.get('token_count', 0)
                }
        
        # Suggest optimizations
        if len(composite_skill.sub_skills) > 5:
            investigation['optimization_suggestions'].append('Consider splitting into smaller composite skills')
        
        return investigation
    
    def _validate_result(self, result: Any, context: Dict) -> bool:
        """Validator subagent: validate execution results."""
        if isinstance(result, dict):
            return result.get('success', False) is True
        return result is not None
    
    def _optimize_execution(self, composite_skill: CompositeSkill, context: Dict) -> Dict:
        """Optimizer subagent: suggest execution optimizations."""
        optimizations = {
            'parallel_opportunities': [],
            'cache_suggestions': [],
            'resource_optimizations': []
        }
        
        # Identify parallel execution opportunities
        if composite_skill.composition_type == CompositionType.SEQUENTIAL:
            independent_skills = []
            for skill in composite_skill.sub_skills:
                dependencies = composite_skill.dependencies.get(skill, [])
                if not dependencies or not any(dep in composite_skill.sub_skills for dep in dependencies):
                    independent_skills.append(skill)
            
            if len(independent_skills) > 1:
                optimizations['parallel_opportunities'] = independent_skills
        
        return optimizations
    
    def _optimize_results(self, results: Dict[str, SkillExecutionResult], 
                         composite_skill: CompositeSkill) -> Dict[str, SkillExecutionResult]:
        """Optimize execution results."""
        optimized_results = {}
        
        for skill_name, result in results.items():
            # Optimize result content
            if result.result and isinstance(result.result, (dict, list, str)):
                optimized_content, _ = self.token_optimizer.optimize_content(
                    result.result, 'auto', use_cache=True
                )
                
                optimized_result = SkillExecutionResult(
                    skill_name=result.skill_name,
                    status=result.status,
                    result=optimized_content,
                    error=result.error,
                    execution_time=result.execution_time,
                    tokens_used=result.tokens_used,
                    metadata=result.metadata,
                    optimized=True
                )
                optimized_results[skill_name] = optimized_result
            else:
                optimized_results[skill_name] = result
        
        return optimized_results


class CompositeSkillManager:
    """Manager for creating and managing composite skills."""
    
    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
        self.executor = CompositeSkillExecutor(skill_manager)
        self.composite_skills: Dict[str, CompositeSkill] = {}
        self.skill_templates: Dict[str, Dict] = {}
        
        # Load default templates
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default composite skill templates."""
        self.skill_templates = {
            'full_migration': {
                'description': 'Complete migration with analysis, planning, execution, and validation',
                'sub_skills': ['framework-migration', 'code-review', 'testing'],
                'composition_type': CompositionType.SEQUENTIAL,
                'dependencies': {
                    'code-review': ['framework-migration'],
                    'testing': ['framework-migration', 'code-review']
                }
            },
            'parallel_analysis': {
                'description': 'Run multiple analysis skills in parallel',
                'sub_skills': ['stack-analyzer', 'dependency-checker', 'security-scanner'],
                'composition_type': CompositionType.PARALLEL
            },
            'conditional_deployment': {
                'description': 'Deploy based on conditions and validation',
                'sub_skills': ['test-runner', 'deployer', 'monitor'],
                'composition_type': CompositionType.CONDITIONAL
            }
        }
    
    def create_composite_skill(self, name: str, description: str, sub_skills: List[str],
                              composition_type: Union[str, CompositionType],
                              **kwargs) -> CompositeSkill:
        """Create a new composite skill."""
        if isinstance(composition_type, str):
            composition_type = CompositionType(composition_type)
        
        # Validate sub-skills exist
        for skill_name in sub_skills:
            if not self.skill_manager.get_skill_info(skill_name):
                raise ValueError(f"Sub-skill not found: {skill_name}")
        
        composite_skill = CompositeSkill(
            name=name,
            description=description,
            sub_skills=sub_skills,
            composition_type=composition_type,
            dependencies=kwargs.get('dependencies', {}),
            max_parallel_workers=kwargs.get('max_parallel_workers', 4),
            timeout=kwargs.get('timeout', 30.0),
            retry_attempts=kwargs.get('retry_attempts', 0)
        )
        
        # Add composition rules if provided
        if 'composition_rules' in kwargs:
            composite_skill.composition_rules = kwargs['composition_rules']
        
        self.composite_skills[name] = composite_skill
        logger.info(f"Created composite skill: {name}")
        
        return composite_skill
    
    def create_from_template(self, name: str, template_name: str, 
                           sub_skills: List[str], **kwargs) -> CompositeSkill:
        """Create composite skill from template."""
        if template_name not in self.skill_templates:
            raise ValueError(f"Template not found: {template_name}")
        
        template = self.skill_templates[template_name]
        
        return self.create_composite_skill(
            name=name,
            description=template['description'],
            sub_skills=sub_skills or template['sub_skills'],
            composition_type=template['composition_type'],
            dependencies=template.get('dependencies', {}),
            **kwargs
        )
    
    def get_composite_skill(self, name: str) -> Optional[CompositeSkill]:
        """Get a composite skill by name."""
        return self.composite_skills.get(name)
    
    def list_composite_skills(self) -> List[str]:
        """List all composite skill names."""
        return list(self.composite_skills.keys())
    
    def execute_composite_skill(self, name: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a composite skill."""
        composite_skill = self.get_composite_skill(name)
        if not composite_skill:
            raise ValueError(f"Composite skill not found: {name}")
        
        return self.executor.execute(composite_skill, context)
    
    def add_composition_rule(self, skill_name: str, rule: CompositionRule):
        """Add a composition rule to a composite skill."""
        if skill_name in self.composite_skills:
            self.composite_skills[skill_name].composition_rules.append(rule)
            logger.info(f"Added composition rule {rule.name} to {skill_name}")
        else:
            raise ValueError(f"Composite skill not found: {skill_name}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return self.executor.get_performance_stats()
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        return list(self.skill_templates.keys())
    
    def get_template(self, name: str) -> Optional[Dict]:
        """Get template by name."""
        return self.skill_templates.get(name)
    
    def export_composite_skill(self, name: str, filepath: str):
        """Export composite skill configuration."""
        if name not in self.composite_skills:
            raise ValueError(f"Composite skill not found: {name}")
        
        skill = self.composite_skills[name]
        
        export_data = {
            'name': skill.name,
            'description': skill.description,
            'sub_skills': skill.sub_skills,
            'composition_type': skill.composition_type.value,
            'dependencies': skill.dependencies,
            'max_parallel_workers': skill.max_parallel_workers,
            'timeout': skill.timeout,
            'retry_attempts': skill.retry_attempts,
            'composition_rules': [
                {
                    'name': rule.name,
                    'metadata': rule.metadata
                }
                for rule in skill.composition_rules
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported composite skill {name} to {filepath}")
    
    def import_composite_skill(self, filepath: str) -> CompositeSkill:
        """Import composite skill from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct composition rules
        composition_rules = []
        for rule_data in data.get('composition_rules', []):
            rule = CompositionRule(
                name=rule_data['name'],
                metadata=rule_data.get('metadata', {})
            )
            composition_rules.append(rule)
        
        composite_skill = self.create_composite_skill(
            name=data['name'],
            description=data['description'],
            sub_skills=data['sub_skills'],
            composition_type=data['composition_type'],
            dependencies=data.get('dependencies', {}),
            max_parallel_workers=data.get('max_parallel_workers', 4),
            timeout=data.get('timeout', 30.0),
            retry_attempts=data.get('retry_attempts', 0),
            composition_rules=composition_rules
        )
        
        logger.info(f"Imported composite skill {data['name']} from {filepath}")
        return composite_skill
