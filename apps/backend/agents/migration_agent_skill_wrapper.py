"""
Migration Agent Skill Wrapper

Provides backward compatibility for the existing MigrationAgent interface
while using the new Agent Skills architecture internally.

This wrapper allows existing code to continue using MigrationAgent without
changes while benefiting from the new skills-based system.

Example:
    # Old usage (still works):
    agent = MigrationAgent(project_root="/path/to/project")
    analysis = agent.analyze_stack()
    
    # New usage (also works):
    agent = MigrationAgentSkillWrapper(project_root="/path/to/project")
    analysis = agent.analyze_stack()
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

# Import the original classes for compatibility
from migration_agent import (
    MigrationPlan,
    MigrationResult,
    StackAnalysis,
    MigrationType,
    MigrationStatus,
    StepRisk,
    BreakingChangeType,
    DetectedDependency,
    MigrationStep,
)

# Import the new skill manager
import sys
sys.path.append(str(Path(__file__).parent.parent / "skills"))
from skill_manager import SkillManager

logger = logging.getLogger(__name__)


class MigrationAgentSkillWrapper:
    """
    Wrapper that provides the same interface as MigrationAgent
    but uses the new Agent Skills architecture internally.
    """
    
    def __init__(self, project_root: str = ".", llm_client: Any = None) -> None:
        """Initialize the wrapper with skill manager."""
        self.project_root = project_root
        self._llm_client = llm_client
        
        # Initialize skill manager
        skills_dir = Path(__file__).parent.parent / "skills"
        self.skill_manager = SkillManager(str(skills_dir))
        
        # Load the migration skill
        try:
            self.migration_skill = self.skill_manager.load_skill("framework-migration")
            logger.info("Loaded framework-migration skill successfully")
        except Exception as e:
            logger.error(f"Failed to load framework-migration skill: {e}")
            self.migration_skill = None
        
        # Internal state for compatibility
        self._plans: dict[str, MigrationPlan] = {}
        self._results: dict[str, MigrationResult] = {}
        self._counter = 0
        
        logger.info(f"MigrationAgentSkillWrapper initialized for {project_root}")
    
    def analyze_stack(self) -> StackAnalysis:
        """Analyze the project's current technology stack using the skill."""
        if not self.migration_skill:
            logger.error("Migration skill not available")
            return StackAnalysis(project_root=self.project_root)
        
        try:
            # Execute the analyze_stack.py script from the skill
            result = self.migration_skill.execute_script(
                "analyze_stack.py",
                {"project-root": self.project_root}
            )
            
            if result["success"]:
                # Parse the JSON output and convert to StackAnalysis
                analysis_data = json.loads(result["stdout"])
                return self._dict_to_stack_analysis(analysis_data)
            else:
                logger.error(f"Stack analysis failed: {result['stderr']}")
                return StackAnalysis(project_root=self.project_root)
                
        except Exception as e:
            logger.error(f"Error analyzing stack: {e}")
            return StackAnalysis(project_root=self.project_root)
    
    def analyze_stack_from_data(self, **kwargs) -> StackAnalysis:
        """Analyze from provided data (for testing or when filesystem is unavailable)."""
        if not self.migration_skill:
            logger.error("Migration skill not available")
            return StackAnalysis(project_root=self.project_root)
        
        try:
            # Execute the analyze_stack.py script with provided data
            args = {}
            if "languages" in kwargs:
                args["languages"] = ",".join(kwargs["languages"])
            if "frameworks" in kwargs:
                args["frameworks"] = ",".join(kwargs["frameworks"])
            if "dependencies" in kwargs:
                args["dependencies"] = json.dumps(kwargs["dependencies"])
            
            result = self.migration_skill.execute_script("analyze_stack.py", args)
            
            if result["success"]:
                analysis_data = json.loads(result["stdout"])
                return self._dict_to_stack_analysis(analysis_data)
            else:
                logger.error(f"Stack analysis from data failed: {result['stderr']}")
                return StackAnalysis(project_root=self.project_root)
                
        except Exception as e:
            logger.error(f"Error analyzing stack from data: {e}")
            return StackAnalysis(project_root=self.project_root)
    
    def create_migration_plan(
        self,
        source_framework: str,
        source_version: str,
        target_version: str,
        target_framework: Optional[str] = None,
        migration_type: str = "version_upgrade",
        custom_steps: Optional[list[dict]] = None,
    ) -> MigrationPlan:
        """
        Create a migration plan using the skill's breaking changes database
        and templates.
        """
        self._counter += 1
        plan_id = f"mig-{self._counter:04d}"
        
        target_fw = target_framework or source_framework
        
        # Create basic migration plan structure
        plan = MigrationPlan(
            plan_id=plan_id,
            migration_type=migration_type,
            source_framework=source_framework,
            source_version=source_version,
            target_framework=target_fw,
            target_version=target_version,
        )
        
        if not self.migration_skill:
            logger.warning("Migration skill not available, creating basic plan")
            self._plans[plan_id] = plan
            return plan
        
        try:
            # Load breaking changes data
            breaking_changes_data = self.migration_skill.get_data("breaking_changes.json")
            
            # Look up known breaking changes
            key = f"{source_framework}:{source_version.split('.')[0]}:{target_version.split('.')[0]}"
            known = breaking_changes_data.get(key, {})
            
            # Add breaking changes to plan
            bc_counter = 0
            for bc_data in known.get("breaking_changes", []):
                bc_counter += 1
                bc = BreakingChange(
                    change_id=f"{plan_id}-bc-{bc_counter:03d}",
                    change_type=bc_data.get("change_type", "unknown"),
                    description=bc_data.get("description", ""),
                    old_api=bc_data.get("old_api"),
                    new_api=bc_data.get("new_api"),
                    migration_guide=bc_data.get("migration_guide"),
                    auto_fixable=bc_data.get("auto_fixable", False),
                    affected_files=bc_data.get("affected_files", []),
                )
                plan.breaking_changes.append(bc)
            
            # Generate migration steps using the template
            self._generate_migration_steps(plan, known, custom_steps)
            
            # Calculate estimated time
            plan.estimated_total_minutes = sum(s.estimated_minutes for s in plan.steps)
            
            self._plans[plan_id] = plan
            logger.info(f"Created migration plan {plan_id}: {source_framework} {source_version} → {target_fw} {target_version}")
            
        except Exception as e:
            logger.error(f"Error creating migration plan: {e}")
            # Create a basic plan as fallback
            self._generate_basic_migration_steps(plan, custom_steps)
            self._plans[plan_id] = plan
        
        return plan
    
    def _generate_migration_steps(self, plan: MigrationPlan, known: dict, custom_steps: Optional[list[dict]]) -> None:
        """Generate migration steps using the skill's logic."""
        step_counter = 0
        
        # Step 1: always backup / create snapshot
        step_counter += 1
        plan.steps.append(MigrationStep(
            step_id=f"{plan.plan_id}-step-{step_counter:03d}",
            order=step_counter,
            title="Create backup snapshot",
            description="Create a snapshot of the current codebase before migration",
            step_type="manual",
            risk="low",
            estimated_minutes=2.0,
        ))
        
        # Step 2: update dependencies
        dep_updates = known.get("dependency_updates", {})
        if dep_updates or plan.target_framework != plan.source_framework:
            step_counter += 1
            plan.steps.append(MigrationStep(
                step_id=f"{plan.plan_id}-step-{step_counter:03d}",
                order=step_counter,
                title=f"Update dependencies to {plan.target_framework} {plan.target_version}",
                description=f"Update package dependencies: {json.dumps(dep_updates) if dep_updates else 'update to target version'}",
                step_type="dependency_update",
                risk="medium",
                commands=[f"npm install {k}@{v}" for k, v in dep_updates.items()] if dep_updates else [],
                rollback_commands=["git checkout -- package.json package-lock.json && npm install"],
                estimated_minutes=5.0,
            ))
        
        # Step 3+: address each breaking change
        for bc in plan.breaking_changes:
            if bc.auto_fixable:
                step_counter += 1
                plan.steps.append(MigrationStep(
                    step_id=f"{plan.plan_id}-step-{step_counter:03d}",
                    order=step_counter,
                    title=f"Fix: {bc.description[:60]}",
                    description=bc.description,
                    step_type="code_change",
                    risk="medium" if bc.change_type != "api_removed" else "high",
                    breaking_changes=[bc.change_id],
                    code_transforms=[{
                        "old": bc.old_api,
                        "new": bc.new_api,
                        "description": bc.description,
                    }] if bc.old_api and bc.new_api else [],
                    affected_files=bc.affected_files,
                    estimated_minutes=10.0,
                ))
            else:
                step_counter += 1
                plan.steps.append(MigrationStep(
                    step_id=f"{plan.plan_id}-step-{step_counter:03d}",
                    order=step_counter,
                    title=f"Manual review: {bc.description[:50]}",
                    description=f"MANUAL: {bc.description}",
                    step_type="manual",
                    risk="high",
                    breaking_changes=[bc.change_id],
                    estimated_minutes=15.0,
                ))
        
        # Add custom steps
        if custom_steps:
            for cs in custom_steps:
                step_counter += 1
                plan.steps.append(MigrationStep(
                    step_id=f"{plan.plan_id}-step-{step_counter:03d}",
                    order=step_counter,
                    title=cs.get("title", "Custom step"),
                    description=cs.get("description", ""),
                    step_type=cs.get("step_type", "code_change"),
                    risk=cs.get("risk", "medium"),
                    estimated_minutes=cs.get("estimated_minutes", 10.0),
                ))
        
        # Final step: run tests
        step_counter += 1
        plan.steps.append(MigrationStep(
            step_id=f"{plan.plan_id}-step-{step_counter:03d}",
            order=step_counter,
            title="Run regression tests",
            description="Execute the test suite to verify migration success",
            step_type="test_update",
            risk="low",
            commands=["npm test", "npm run lint"],
            estimated_minutes=5.0,
        ))
    
    def _generate_basic_migration_steps(self, plan: MigrationPlan, custom_steps: Optional[list[dict]]) -> None:
        """Generate basic migration steps when skill is not available."""
        step_counter = 0
        
        # Basic backup step
        step_counter += 1
        plan.steps.append(MigrationStep(
            step_id=f"{plan.plan_id}-step-{step_counter:03d}",
            order=step_counter,
            title="Create backup snapshot",
            description="Create a snapshot of the current codebase before migration",
            step_type="manual",
            risk="low",
            estimated_minutes=2.0,
        ))
        
        # Basic dependency update
        step_counter += 1
        plan.steps.append(MigrationStep(
            step_id=f"{plan.plan_id}-step-{step_counter:03d}",
            order=step_counter,
            title=f"Update dependencies to {plan.target_framework} {plan.target_version}",
            description="Update package dependencies to target version",
            step_type="dependency_update",
            risk="medium",
            estimated_minutes=5.0,
        ))
        
        # Add custom steps if provided
        if custom_steps:
            for cs in custom_steps:
                step_counter += 1
                plan.steps.append(MigrationStep(
                    step_id=f"{plan.plan_id}-step-{step_counter:03d}",
                    order=step_counter,
                    title=cs.get("title", "Custom step"),
                    description=cs.get("description", ""),
                    step_type=cs.get("step_type", "code_change"),
                    risk=cs.get("risk", "medium"),
                    estimated_minutes=cs.get("estimated_minutes", 10.0),
                ))
        
        # Final test step
        step_counter += 1
        plan.steps.append(MigrationStep(
            step_id=f"{plan.plan_id}-step-{step_counter:03d}",
            order=step_counter,
            title="Run regression tests",
            description="Execute the test suite to verify migration success",
            step_type="test_update",
            risk="low",
            estimated_minutes=5.0,
        ))
    
    def get_plan(self, plan_id: str) -> Optional[MigrationPlan]:
        """Get a migration plan by ID."""
        return self._plans.get(plan_id)
    
    def list_plans(self, status: Optional[str] = None) -> list[MigrationPlan]:
        """List all plans, optionally filtered by status."""
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        return plans
    
    def update_step_status(self, plan_id: str, step_id: str, status: str, error: Optional[str] = None) -> Optional[MigrationStep]:
        """Update the status of a single step."""
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        for step in plan.steps:
            if step.step_id == step_id:
                step.status = status
                if error:
                    step.error = error
                return step
        return None
    
    def execute_migration(self, plan_id: str, dry_run: bool = False) -> MigrationResult:
        """Execute a migration plan using the skill."""
        plan = self._plans.get(plan_id)
        if not plan:
            return MigrationResult(
                plan_id=plan_id, success=False,
                errors=[f"Plan {plan_id} not found"],
            )
        
        if not self.migration_skill:
            logger.error("Migration skill not available for execution")
            return MigrationResult(
                plan_id=plan_id, success=False,
                errors=["Migration skill not available"],
            )
        
        try:
            # Save plan to temporary file for the script
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(plan.to_dict(), f, indent=2)
                plan_file = f.name
            
            # Execute the migration script
            result = self.migration_skill.execute_script(
                "execute_migration.py",
                {
                    "plan-file": plan_file,
                    "dry-run": str(dry_run).lower()
                }
            )
            
            # Clean up temporary file
            import os
            os.unlink(plan_file)
            
            if result["success"]:
                # Parse the result
                result_data = json.loads(result["stdout"])
                migration_result = self._dict_to_migration_result(result_data)
                
                # Update plan status
                plan.status = "completed" if migration_result.success else "failed"
                plan.actual_total_minutes = migration_result.duration_seconds / 60
                
                self._results[plan_id] = migration_result
                return migration_result
            else:
                logger.error(f"Migration execution failed: {result['stderr']}")
                return MigrationResult(
                    plan_id=plan_id, success=False,
                    errors=[f"Script execution failed: {result['stderr']}"],
                )
                
        except Exception as e:
            logger.error(f"Error executing migration: {e}")
            return MigrationResult(
                plan_id=plan_id, success=False,
                errors=[f"Execution error: {str(e)}"],
            )
    
    def rollback_migration(self, plan_id: str) -> MigrationResult:
        """Rollback a migration using the skill."""
        plan = self._plans.get(plan_id)
        if not plan:
            return MigrationResult(plan_id=plan_id, success=False, errors=["Plan not found"])
        
        if not self.migration_skill:
            logger.error("Migration skill not available for rollback")
            return MigrationResult(
                plan_id=plan_id, success=False,
                errors=["Migration skill not available"],
            )
        
        try:
            # Save plan to temporary file for the script
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(plan.to_dict(), f, indent=2)
                plan_file = f.name
            
            # Execute rollback
            result = self.migration_skill.execute_script(
                "execute_migration.py",
                {
                    "plan-file": plan_file,
                    "rollback": ""
                }
            )
            
            # Clean up temporary file
            import os
            os.unlink(plan_file)
            
            if result["success"]:
                result_data = json.loads(result["stdout"])
                rollback_result = self._dict_to_migration_result(result_data)
                
                plan.status = "rolled_back"
                self._results[plan_id] = rollback_result
                return rollback_result
            else:
                logger.error(f"Rollback failed: {result['stderr']}")
                return MigrationResult(
                    plan_id=plan_id, success=False,
                    errors=[f"Rollback failed: {result['stderr']}"],
                )
                
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return MigrationResult(
                plan_id=plan_id, success=False,
                errors=[f"Rollback error: {str(e)}"],
            )
    
    def get_results(self, plan_id: Optional[str] = None) -> list[MigrationResult]:
        """Get migration results."""
        if plan_id:
            r = self._results.get(plan_id)
            return [r] if r else []
        return list(self._results.values())
    
    def get_stats(self) -> dict:
        """Get overall migration statistics."""
        plans = list(self._plans.values())
        results = list(self._results.values())
        
        return {
            "total_plans": len(plans),
            "plans_by_status": {
                s: sum(1 for p in plans if p.status == s)
                for s in set(p.status for p in plans)
            } if plans else {},
            "total_migrations_executed": len(results),
            "successful_migrations": sum(1 for r in results if r.success),
            "failed_migrations": sum(1 for r in results if not r.success),
            "total_steps_completed": sum(r.steps_completed for r in results),
            "total_tests_generated": sum(r.tests_generated for r in results),
        }
    
    def _dict_to_stack_analysis(self, data: dict) -> StackAnalysis:
        """Convert dictionary to StackAnalysis object."""
        dependencies = []
        for dep_data in data.get("dependencies", []):
            dependencies.append(DetectedDependency(**dep_data))
        
        return StackAnalysis(
            project_root=data.get("project_root", self.project_root),
            detected_languages=data.get("detected_languages", []),
            detected_frameworks=data.get("detected_frameworks", []),
            detected_build_tools=data.get("detected_build_tools", []),
            dependencies=dependencies,
            config_files=data.get("config_files", []),
            total_files_scanned=data.get("total_files_scanned", 0),
            analysis_timestamp=data.get("analysis_timestamp", ""),
        )
    
    def _dict_to_migration_result(self, data: dict) -> MigrationResult:
        """Convert dictionary to MigrationResult object."""
        return MigrationResult(
            plan_id=data.get("plan_id", ""),
            success=data.get("success", False),
            steps_completed=data.get("steps_completed", 0),
            steps_failed=data.get("steps_failed", 0),
            steps_total=data.get("steps_total", 0),
            files_modified=data.get("files_modified", []),
            tests_generated=data.get("tests_generated", 0),
            test_code=data.get("test_code"),
            errors=data.get("errors", []),
            duration_seconds=data.get("duration_seconds", 0.0),
            rollback_performed=data.get("rollback_performed", False),
        )


# For backward compatibility, also expose as MigrationAgent
MigrationAgent = MigrationAgentSkillWrapper
