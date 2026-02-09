"""
Migration Planner: Generates detailed migration plans.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Set, Optional
from pathlib import Path

from .models import (
    StackInfo,
    MigrationPlan,
    MigrationPhase,
    MigrationStep,
    RiskLevel,
)
from .config import SUPPORTED_MIGRATIONS, MIGRATION_PHASES


class MigrationPlanner:
    """Generates detailed migration plans."""

    def __init__(self, source_stack: StackInfo, target_stack: StackInfo):
        self.source_stack = source_stack
        self.target_stack = target_stack
        self.migration_key = (source_stack.framework, target_stack.framework)

    def create_plan(self) -> MigrationPlan:
        """Create a comprehensive migration plan."""
        plan = MigrationPlan(
            id=str(uuid.uuid4()),
            source_stack=self.source_stack,
            target_stack=self.target_stack,
        )

        # Generate phases
        plan.phases = self._generate_phases()
        plan.total_steps = sum(len(phase.steps) for phase in plan.phases)

        # Assess effort and risk
        config = SUPPORTED_MIGRATIONS.get(self.migration_key, {})
        plan.estimated_effort = self._calculate_effort(config)
        plan.risk_level = self._calculate_risk(plan.phases)
        plan.estimated_duration_hours = float(
            config.get("estimated_effort_hours", 20)
        )

        # Determine if approvals needed
        plan.approvals_required = plan.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

        return plan

    def _generate_phases(self) -> List[MigrationPhase]:
        """Generate migration phases."""
        phases = []

        # Phase 1: Analysis (uses template)
        phases.append(self._create_analysis_phase())

        # Phase 2: Planning (uses template)
        phases.append(self._create_planning_phase())

        # Phase 3: Backup & Checkpoint
        phases.append(self._create_backup_phase())

        # Phase 4: Code Transformation (varies by migration type)
        phases.extend(self._create_transformation_phases())

        # Phase 5: Validation & Testing
        phases.append(self._create_validation_phase())

        # Phase 6: Auto-Fix Issues (if needed)
        phases.append(self._create_autofix_phase())

        # Phase 7: Reporting
        phases.append(self._create_reporting_phase())

        return phases

    def _create_analysis_phase(self) -> MigrationPhase:
        """Create analysis phase."""
        step1 = MigrationStep(
            id="analyze_source_code",
            title="Analyze Source Code Structure",
            description=f"Analyze {self.source_stack.framework} codebase structure, patterns, and dependencies",
            category="analysis",
            files_affected=[],
            transformation_type="analysis",
            expected_changes=0,
            validation_checks=["structure_valid", "patterns_identified"],
        )

        step2 = MigrationStep(
            id="assess_migration_risk",
            title="Assess Migration Risk",
            description="Evaluate complexity, breaking changes, and data migration needs",
            category="analysis",
            files_affected=[],
            transformation_type="analysis",
            expected_changes=0,
            validation_checks=["risk_assessed"],
        )

        phase = MigrationPhase(
            id="analysis",
            name="Analysis",
            description="Analyze source code and create migration plan",
            steps=[step1, step2],
            estimated_effort="Low",
            risk_level=RiskLevel.LOW,
        )
        return phase

    def _create_planning_phase(self) -> MigrationPhase:
        """Create planning phase."""
        step1 = MigrationStep(
            id="create_migration_plan",
            title="Create Detailed Migration Plan",
            description="Generate step-by-step migration plan with dependencies",
            category="planning",
            files_affected=[],
            transformation_type="planning",
            expected_changes=0,
            validation_checks=["plan_valid", "dependencies_resolved"],
        )

        step2 = MigrationStep(
            id="identify_breaking_changes",
            title="Identify Breaking Changes",
            description="Document breaking changes and compatibility issues",
            category="planning",
            files_affected=[],
            transformation_type="analysis",
            expected_changes=0,
            validation_checks=["breaking_changes_identified"],
        )

        phase = MigrationPhase(
            id="planning",
            name="Planning",
            description="Generate detailed migration plan",
            steps=[step1, step2],
            estimated_effort="Low",
            risk_level=RiskLevel.LOW,
        )
        return phase

    def _create_backup_phase(self) -> MigrationPhase:
        """Create backup and checkpoint phase."""
        step1 = MigrationStep(
            id="create_git_branch",
            title="Create Migration Branch",
            description="Create git branch for migration with checkpoint",
            category="backup",
            files_affected=[],
            transformation_type="backup",
            expected_changes=0,
            rollback_procedure="git checkout original_branch",
            validation_checks=["branch_created", "checkpoint_saved"],
        )

        step2 = MigrationStep(
            id="save_state_checkpoint",
            title="Save State Checkpoint",
            description="Save migration state for rollback capability",
            category="backup",
            files_affected=[],
            transformation_type="backup",
            expected_changes=0,
            rollback_procedure="restore from checkpoint",
            validation_checks=["checkpoint_valid"],
        )

        phase = MigrationPhase(
            id="backup",
            name="Backup & Checkpoint",
            description="Create backup and checkpoint for rollback",
            steps=[step1, step2],
            estimated_effort="Low",
            risk_level=RiskLevel.LOW,
        )
        return phase

    def _create_transformation_phases(self) -> List[MigrationPhase]:
        """Create transformation phases based on migration type."""
        phases = []

        if self.migration_key == ("react", "vue"):
            phases.extend(self._create_react_to_vue_phases())
        elif self.migration_key == ("mysql", "postgresql"):
            phases.extend(self._create_database_migration_phases())
        elif self.migration_key == ("python2", "python3"):
            phases.extend(self._create_python_migration_phases())
        elif self.migration_key == ("rest", "graphql"):
            phases.extend(self._create_rest_to_graphql_phases())
        elif self.migration_key == ("javascript", "typescript"):
            phases.extend(self._create_js_to_ts_phases())

        return phases

    def _create_react_to_vue_phases(self) -> List[MigrationPhase]:
        """Create React to Vue transformation phases."""
        # Phase: Component Migration
        component_steps = [
            MigrationStep(
                id="convert_jsx_to_sfc",
                title="Convert JSX to Vue Single File Components",
                description="Transform React JSX components to Vue .vue files",
                category="component",
                files_affected=["**/*.jsx", "**/*.tsx"],
                transformation_type="jsx_to_template",
                expected_changes=150,
                validation_checks=["syntax_valid", "imports_resolved"],
                dependencies=[],
            ),
            MigrationStep(
                id="migrate_component_logic",
                title="Migrate Component Logic",
                description="Convert React component logic to Vue composition API",
                category="component",
                files_affected=["**/*.jsx", "**/*.tsx"],
                transformation_type="hooks_to_composition_api",
                expected_changes=100,
                validation_checks=["logic_preserved", "tests_pass"],
                dependencies=["convert_jsx_to_sfc"],
            ),
        ]
        component_phase = MigrationPhase(
            id="react_components",
            name="Component Migration",
            description="Transform React components to Vue",
            steps=component_steps,
            estimated_effort="High",
            risk_level=RiskLevel.MEDIUM,
        )

        # Phase: State Management
        state_steps = [
            MigrationStep(
                id="migrate_state_management",
                title="Migrate State Management",
                description="Convert Redux/Vuex to Vue 3 composition API",
                category="state",
                files_affected=["**/store/**", "**/redux/**"],
                transformation_type="state_management",
                expected_changes=50,
                validation_checks=["state_valid", "mutations_work"],
                dependencies=["convert_jsx_to_sfc"],
            ),
        ]
        state_phase = MigrationPhase(
            id="state_management",
            name="State Management",
            description="Migrate state management solution",
            steps=state_steps,
            estimated_effort="Medium",
            risk_level=RiskLevel.MEDIUM,
        )

        # Phase: Routing
        routing_steps = [
            MigrationStep(
                id="migrate_routing",
                title="Migrate Routing",
                description="Convert React Router to Vue Router 4",
                category="routing",
                files_affected=["**/routes/**", "**/router/**"],
                transformation_type="routing",
                expected_changes=30,
                validation_checks=["routes_valid", "navigation_works"],
                dependencies=["migrate_state_management"],
            ),
        ]
        routing_phase = MigrationPhase(
            id="routing",
            name="Routing & Navigation",
            description="Migrate routing configuration",
            steps=routing_steps,
            estimated_effort="Medium",
            risk_level=RiskLevel.MEDIUM,
        )

        # Phase: Styling
        styling_steps = [
            MigrationStep(
                id="migrate_styling",
                title="Migrate CSS & Styling",
                description="Convert styled-components or CSS modules to Vue scoped styles",
                category="styling",
                files_affected=["**/*.css", "**/*.scss", "**/*.styled.*"],
                transformation_type="styling",
                expected_changes=40,
                validation_checks=["styles_applied", "responsive_works"],
                dependencies=["convert_jsx_to_sfc"],
            ),
        ]
        styling_phase = MigrationPhase(
            id="styling",
            name="Styling & CSS",
            description="Migrate styling approach",
            steps=styling_steps,
            estimated_effort="Medium",
            risk_level=RiskLevel.LOW,
        )

        return [
            component_phase,
            state_phase,
            routing_phase,
            styling_phase,
        ]

    def _create_database_migration_phases(self) -> List[MigrationPhase]:
        """Create MySQL to PostgreSQL migration phases."""
        # Phase: Schema Migration
        schema_steps = [
            MigrationStep(
                id="export_mysql_schema",
                title="Export MySQL Schema",
                description="Extract MySQL schema and structure",
                category="database",
                files_affected=["**/*.sql"],
                transformation_type="schema_export",
                expected_changes=1,
                validation_checks=["schema_exported", "valid_sql"],
                dependencies=[],
            ),
            MigrationStep(
                id="convert_schema_syntax",
                title="Convert Schema to PostgreSQL Syntax",
                description="Convert MySQL DDL to PostgreSQL DDL",
                category="database",
                files_affected=["**/migrations/**"],
                transformation_type="syntax_conversion",
                expected_changes=30,
                validation_checks=["syntax_valid", "types_mapped"],
                dependencies=["export_mysql_schema"],
            ),
        ]
        schema_phase = MigrationPhase(
            id="schema_migration",
            name="Schema Migration",
            description="Migrate database schema",
            steps=schema_steps,
            estimated_effort="Medium",
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
        )

        # Phase: Data Migration
        data_steps = [
            MigrationStep(
                id="prepare_data_migration",
                title="Prepare Data Export/Import",
                description="Set up data migration procedures",
                category="database",
                files_affected=[],
                transformation_type="data_preparation",
                expected_changes=0,
                validation_checks=["export_valid"],
                dependencies=["convert_schema_syntax"],
            ),
        ]
        data_phase = MigrationPhase(
            id="data_migration",
            name="Data Migration",
            description="Migrate data from MySQL to PostgreSQL",
            steps=data_steps,
            estimated_effort="High",
            risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
        )

        # Phase: Application Code
        app_steps = [
            MigrationStep(
                id="update_db_drivers",
                title="Update Database Drivers",
                description="Update MySQL driver to PostgreSQL (e.g., mysql2 → pg)",
                category="application",
                files_affected=["**/*.js", "**/*.py"],
                transformation_type="dependency_update",
                expected_changes=20,
                validation_checks=["drivers_updated", "imports_valid"],
                dependencies=["convert_schema_syntax"],
            ),
            MigrationStep(
                id="update_db_calls",
                title="Update Database Calls",
                description="Update SQL queries for PostgreSQL compatibility",
                category="application",
                files_affected=["**/*.js", "**/*.ts", "**/*.py"],
                transformation_type="sql_conversion",
                expected_changes=50,
                validation_checks=["queries_valid", "compatible"],
                dependencies=["update_db_drivers"],
            ),
        ]
        app_phase = MigrationPhase(
            id="application_updates",
            name="Application Updates",
            description="Update application code for PostgreSQL",
            steps=app_steps,
            estimated_effort="Medium",
            risk_level=RiskLevel.MEDIUM,
        )

        return [
            schema_phase,
            data_phase,
            app_phase,
        ]

    def _create_python_migration_phases(self) -> List[MigrationPhase]:
        """Create Python 2 to Python 3 migration phases."""
        steps = [
            MigrationStep(
                id="update_print_statements",
                title="Convert Print Statements to Functions",
                description="Convert Python 2 print statements to Python 3 print functions",
                category="syntax",
                files_affected=["**/*.py"],
                transformation_type="print_function",
                expected_changes=100,
                validation_checks=["syntax_valid"],
                dependencies=[],
            ),
            MigrationStep(
                id="fix_imports",
                title="Fix Imports",
                description="Update deprecated imports and modules",
                category="imports",
                files_affected=["**/*.py"],
                transformation_type="imports",
                expected_changes=50,
                validation_checks=["imports_valid"],
                dependencies=["update_print_statements"],
            ),
            MigrationStep(
                id="update_string_types",
                title="Update String Types",
                description="Handle str/unicode differences",
                category="types",
                files_affected=["**/*.py"],
                transformation_type="unicode",
                expected_changes=80,
                validation_checks=["encoding_valid"],
                dependencies=["fix_imports"],
            ),
            MigrationStep(
                id="fix_division",
                title="Fix Division Operations",
                description="Update division operators for Python 3",
                category="operators",
                files_affected=["**/*.py"],
                transformation_type="division",
                expected_changes=30,
                validation_checks=["math_valid"],
                dependencies=["update_string_types"],
            ),
        ]
        phase = MigrationPhase(
            id="python_migration",
            name="Python 2 to 3 Migration",
            description="Migrate codebase to Python 3",
            steps=steps,
            estimated_effort="High",
            risk_level=RiskLevel.MEDIUM,
        )
        return [phase]

    def _create_rest_to_graphql_phases(self) -> List[MigrationPhase]:
        """Create REST to GraphQL migration phases."""
        steps = [
            MigrationStep(
                id="design_schema",
                title="Design GraphQL Schema",
                description="Create GraphQL schema from REST endpoints",
                category="schema",
                files_affected=["**/schema/**"],
                transformation_type="schema_design",
                expected_changes=50,
                validation_checks=["schema_valid"],
                dependencies=[],
            ),
            MigrationStep(
                id="implement_resolvers",
                title="Implement Resolvers",
                description="Convert REST handlers to GraphQL resolvers",
                category="resolvers",
                files_affected=["**/routes/**", "**/handlers/**"],
                transformation_type="resolver_implementation",
                expected_changes=100,
                validation_checks=["resolvers_valid"],
                dependencies=["design_schema"],
            ),
            MigrationStep(
                id="migrate_client",
                title="Migrate Client Code",
                description="Update client to use GraphQL queries instead of REST calls",
                category="client",
                files_affected=["**/client/**", "**/*.js", "**/*.ts"],
                transformation_type="client_migration",
                expected_changes=120,
                validation_checks=["queries_valid"],
                dependencies=["implement_resolvers"],
            ),
        ]
        phase = MigrationPhase(
            id="graphql_migration",
            name="REST to GraphQL Migration",
            description="Migrate from REST API to GraphQL",
            steps=steps,
            estimated_effort="Very High",
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
        )
        return [phase]

    def _create_js_to_ts_phases(self) -> List[MigrationPhase]:
        """Create JavaScript to TypeScript migration phases."""
        steps = [
            MigrationStep(
                id="add_type_annotations",
                title="Add Type Annotations",
                description="Add TypeScript type annotations to JavaScript files",
                category="types",
                files_affected=["**/*.js", "**/*.jsx"],
                transformation_type="type_annotations",
                expected_changes=200,
                validation_checks=["types_valid", "no_errors"],
                dependencies=[],
            ),
            MigrationStep(
                id="generate_interfaces",
                title="Generate Type Interfaces",
                description="Create interfaces for complex types and objects",
                category="types",
                files_affected=["**/types/**"],
                transformation_type="interface_generation",
                expected_changes=50,
                validation_checks=["interfaces_valid"],
                dependencies=["add_type_annotations"],
            ),
            MigrationStep(
                id="enable_strict_mode",
                title="Enable Strict Mode",
                description="Enable TypeScript strict compiler options",
                category="configuration",
                files_affected=["tsconfig.json"],
                transformation_type="configuration",
                expected_changes=1,
                validation_checks=["config_valid", "compiles"],
                dependencies=["generate_interfaces"],
            ),
        ]
        phase = MigrationPhase(
            id="typescript_migration",
            name="JavaScript to TypeScript",
            description="Migrate to TypeScript",
            steps=steps,
            estimated_effort="Medium",
            risk_level=RiskLevel.LOW,
        )
        return [phase]

    def _create_validation_phase(self) -> MigrationPhase:
        """Create validation and testing phase."""
        steps = [
            MigrationStep(
                id="run_tests",
                title="Run Test Suite",
                description="Execute all unit and integration tests",
                category="validation",
                files_affected=[],
                transformation_type="validation",
                expected_changes=0,
                validation_checks=["all_tests_pass"],
                dependencies=[],
            ),
            MigrationStep(
                id="check_build",
                title="Check Build",
                description="Verify project builds successfully",
                category="validation",
                files_affected=[],
                transformation_type="validation",
                expected_changes=0,
                validation_checks=["build_succeeds"],
                dependencies=["run_tests"],
            ),
            MigrationStep(
                id="check_lint",
                title="Check Linting",
                description="Run linter to check code quality",
                category="validation",
                files_affected=[],
                transformation_type="validation",
                expected_changes=0,
                validation_checks=["linting_passed"],
                dependencies=["check_build"],
            ),
        ]
        phase = MigrationPhase(
            id="validation",
            name="Validation & Testing",
            description="Validate transformations and run tests",
            steps=steps,
            estimated_effort="Medium",
            risk_level=RiskLevel.MEDIUM,
        )
        return phase

    def _create_autofix_phase(self) -> MigrationPhase:
        """Create auto-fix phase."""
        step = MigrationStep(
            id="auto_fix_failures",
            title="Auto-Fix Test Failures",
            description="Automatically fix validation failures using Auto-Fix loop",
            category="fixup",
            files_affected=[],
            transformation_type="auto_fix",
            expected_changes=0,
            validation_checks=["all_fixed"],
        )
        phase = MigrationPhase(
            id="autofix",
            name="Auto-Fix Issues",
            description="Automatically fix validation failures",
            steps=[step],
            estimated_effort="Medium",
            risk_level=RiskLevel.LOW,
        )
        return phase

    def _create_reporting_phase(self) -> MigrationPhase:
        """Create reporting phase."""
        steps = [
            MigrationStep(
                id="generate_report",
                title="Generate Migration Report",
                description="Create comprehensive migration report and documentation",
                category="reporting",
                files_affected=[],
                transformation_type="reporting",
                expected_changes=0,
                validation_checks=["report_generated"],
                dependencies=[],
            ),
            MigrationStep(
                id="create_changelog",
                title="Create Changelog",
                description="Document all changes in CHANGELOG.md",
                category="documentation",
                files_affected=["CHANGELOG.md"],
                transformation_type="documentation",
                expected_changes=1,
                validation_checks=["changelog_valid"],
                dependencies=["generate_report"],
            ),
        ]
        phase = MigrationPhase(
            id="reporting",
            name="Report Generation",
            description="Generate migration report and documentation",
            steps=steps,
            estimated_effort="Low",
            risk_level=RiskLevel.LOW,
        )
        return phase

    def _calculate_effort(self, config: Dict) -> str:
        """Calculate effort level."""
        hours = config.get("estimated_effort_hours", 20)
        if hours < 10:
            return "Low"
        elif hours < 30:
            return "Medium"
        elif hours < 60:
            return "High"
        else:
            return "Very High"

    def _calculate_risk(self, phases: List[MigrationPhase]) -> RiskLevel:
        """Calculate overall risk from phases."""
        if not phases:
            return RiskLevel.LOW

        risk_scores = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }

        avg_risk = sum(risk_scores.get(p.risk_level, 1) for p in phases) / len(phases)

        if avg_risk >= 3.5:
            return RiskLevel.CRITICAL
        elif avg_risk >= 2.5:
            return RiskLevel.HIGH
        elif avg_risk >= 1.5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
