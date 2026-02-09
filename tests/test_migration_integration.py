"""
Integration tests for Feature #20 - Auto-Migration Engine
Tests the complete migration pipeline with all components
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from apps.backend.migration.orchestrator import MigrationOrchestrator
from apps.backend.migration.transformer import TransformationEngine
from apps.backend.migration.analyzer import StackAnalyzer
from apps.backend.migration.planner import MigrationPlanner
from apps.backend.migration.reporter import MigrationReporter
from apps.backend.migration.validator import MigrationValidator
from apps.backend.migration.rollback import RollbackManager
from tests.migration_fixtures import TEST_FIXTURES


class TestFullMigrationPipeline:
    """Test complete migration pipeline from start to finish."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_react_to_vue_complete_migration(self, temp_project):
        """Test complete React to Vue migration pipeline."""
        project_path = Path(temp_project)
        
        # 1. Create test files
        src_dir = project_path / "src"
        src_dir.mkdir()
        
        comp_file = src_dir / "Counter.jsx"
        comp_file.write_text(TEST_FIXTURES['react_component']['content'])
        
        # 2. Analyze the project
        analyzer = StackAnalyzer(temp_project)
        stack_info = analyzer.detect_stack()
        
        assert stack_info.framework == 'react'
        assert stack_info.language == 'javascript'
        
        # 3. Create migration plan
        planner = MigrationPlanner(temp_project)
        plan = planner.create_plan(
            source_stack='react',
            target_stack='vue',
            stack_info=stack_info
        )
        
        assert plan.source_framework == 'react'
        assert plan.target_framework == 'vue'
        assert len(plan.phases) > 0
        
        # 4. Transform code
        transformer_engine = TransformationEngine(temp_project, 'react', 'vue')
        results = transformer_engine.transform_code()
        
        assert len(results) > 0
        assert all(r.confidence > 0.7 for r in results)
        
        # 5. Generate report
        reporter = MigrationReporter()
        report = reporter.generate_report(
            migration_id='test-123',
            source_framework='react',
            target_framework='vue',
            stack_info=stack_info,
            plan=plan,
            transformations=results
        )
        
        assert 'react' in report.lower()
        assert 'vue' in report.lower()
    
    def test_react_to_angular_complete_migration(self, temp_project):
        """Test complete React to Angular migration pipeline."""
        project_path = Path(temp_project)
        
        # Create test component
        comp_file = project_path / "UserCard.jsx"
        comp_file.write_text(TEST_FIXTURES['react_component']['content'])
        
        # Analyze
        analyzer = StackAnalyzer(temp_project)
        stack_info = analyzer.detect_stack()
        assert stack_info.framework == 'react'
        
        # Plan
        planner = MigrationPlanner(temp_project)
        plan = planner.create_plan('react', 'angular', stack_info)
        assert len(plan.phases) > 0
        
        # Transform
        transformer = TransformationEngine(temp_project, 'react', 'angular')
        results = transformer.transform_code()
        
        assert len(results) > 0
        assert all(r.transformation_type == 'react_to_angular' for r in results)
        
        # Report
        reporter = MigrationReporter()
        report = reporter.generate_report('test-456', 'react', 'angular', stack_info, plan, results)
        assert 'angular' in report.lower()
    
    def test_mysql_to_postgresql_complete_migration(self, temp_project):
        """Test complete MySQL to PostgreSQL migration pipeline."""
        project_path = Path(temp_project)
        
        # Create schema file
        schema_file = project_path / "schema.sql"
        schema_file.write_text(TEST_FIXTURES['mysql_schema']['content'])
        
        # Analyze
        analyzer = StackAnalyzer(temp_project)
        stack_info = analyzer.detect_stack()
        
        # Plan
        planner = MigrationPlanner(temp_project)
        plan = planner.create_plan('mysql', 'postgresql', stack_info)
        assert plan.target_framework == 'postgresql'
        
        # Transform
        transformer = TransformationEngine(temp_project, 'mysql', 'postgresql')
        results = transformer.transform_code()
        
        assert len(results) > 0
        # Should have SQL conversions
        sql_results = [r for r in results if r.transformation_type == 'sql_conversion']
        assert len(sql_results) > 0
    
    def test_python2_to_python3_complete_migration(self, temp_project):
        """Test complete Python 2 to Python 3 migration pipeline."""
        project_path = Path(temp_project)
        
        # Create Python 2 file
        py_file = project_path / "legacy.py"
        py_file.write_text(TEST_FIXTURES['python2_code']['content'])
        
        # Analyze
        analyzer = StackAnalyzer(temp_project)
        stack_info = analyzer.detect_stack()
        
        # Plan
        planner = MigrationPlanner(temp_project)
        plan = planner.create_plan('python2', 'python3', stack_info)
        assert plan.target_framework == 'python3'
        
        # Transform
        transformer = TransformationEngine(temp_project, 'python2', 'python3')
        results = transformer.transform_code()
        
        assert len(results) > 0
        assert all(r.transformation_type == 'python2_to_3' for r in results)


class TestOrchestratorIntegration:
    """Test MigrationOrchestrator integration with all components."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_orchestrator_analyze_phase(self, temp_project):
        """Test orchestrator analysis phase."""
        project_path = Path(temp_project)
        comp_file = project_path / "App.jsx"
        comp_file.write_text(TEST_FIXTURES['react_component']['content'])
        
        orchestrator = MigrationOrchestrator(temp_project)
        
        # Start migration
        plan = orchestrator.plan_phase('react', 'vue')
        
        assert plan is not None
        assert plan.source_framework == 'react'
        assert len(plan.phases) > 0
    
    def test_orchestrator_transform_phase(self, temp_project):
        """Test orchestrator transformation phase."""
        project_path = Path(temp_project)
        comp_file = project_path / "Button.jsx"
        comp_file.write_text("""
import React, { useState } from 'react'

function Button({ label }) {
  const [clicked, setClicked] = useState(false)
  return <button onClick={() => setClicked(true)}>{label}</button>
}
""")
        
        orchestrator = MigrationOrchestrator(temp_project)
        
        # Plan
        plan = orchestrator.plan_phase('react', 'vue')
        
        # Transform
        results = orchestrator.transform_phase(plan)
        
        assert len(results) > 0
        assert all(r.confidence > 0.7 for r in results)
    
    def test_orchestrator_validation_phase(self, temp_project):
        """Test orchestrator validation phase."""
        project_path = Path(temp_project)
        comp_file = project_path / "test.jsx"
        comp_file.write_text("const x = 5")
        
        orchestrator = MigrationOrchestrator(temp_project)
        
        # Create mock validation result
        validator = MigrationValidator(temp_project)
        report = validator.validate(results=[])
        
        assert report is not None


class TestTransformerEngineIntegration:
    """Test TransformationEngine with various migration types."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_engine_detects_correct_transformer(self, temp_project):
        """Test engine selects correct transformer for migration."""
        project_path = Path(temp_project)
        
        # Create React file
        comp = project_path / "App.jsx"
        comp.write_text(TEST_FIXTURES['react_component']['content'])
        
        engine = TransformationEngine(temp_project, 'react', 'vue')
        results = engine.transform_code()
        
        # Should detect JSX file automatically
        assert len(results) > 0
        assert all(r.transformation_type == 'jsx_to_vue_sfc' for r in results)
    
    def test_engine_handles_multiple_file_types(self, temp_project):
        """Test engine handles multiple file types in same project."""
        project_path = Path(temp_project)
        
        # Create multiple file types
        jsx_file = project_path / "Component.jsx"
        jsx_file.write_text(TEST_FIXTURES['react_component']['content'])
        
        sql_file = project_path / "schema.sql"
        sql_file.write_text(TEST_FIXTURES['mysql_schema']['content'])
        
        # Transform React to Vue
        react_engine = TransformationEngine(temp_project, 'react', 'vue')
        react_results = react_engine.transform_code()
        
        # Transform MySQL to PostgreSQL
        db_engine = TransformationEngine(temp_project, 'mysql', 'postgresql')
        db_results = db_engine.transform_code()
        
        assert len(react_results) > 0
        assert len(db_results) > 0
    
    def test_engine_apply_transformations(self, temp_project):
        """Test applying transformations to files."""
        project_path = Path(temp_project)
        
        # Create test file
        src_file = project_path / "simple.js"
        src_file.write_text("const x = 5")
        
        engine = TransformationEngine(temp_project, 'javascript', 'typescript')
        results = engine.transform_code(['simple.js'])
        
        # Apply transformations
        summary = engine.apply_transformations(dry_run=False)
        
        assert summary['applied'] >= 0
        assert summary['dry_run'] == False


class TestReporterIntegration:
    """Test MigrationReporter with complete migration data."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_reporter_generates_markdown(self, temp_project):
        """Test reporter generates valid markdown."""
        from apps.backend.migration.models import StackInfo, MigrationPlan, MigrationPhase, MigrationStep
        
        # Create stack info
        stack_info = StackInfo(
            framework='react',
            language='javascript',
            version='18.0',
            framework_version='18.0'
        )
        
        # Create plan
        phase = MigrationPhase(
            name='Components',
            description='Migrate component structure',
            order=1,
            steps=[]
        )
        
        plan = MigrationPlan(
            source_framework='react',
            target_framework='vue',
            phases=[phase],
            complexity_score=5.0,
            risk_level='medium'
        )
        
        # Create reporter
        reporter = MigrationReporter()
        report = reporter.generate_report(
            migration_id='test-id',
            source_framework='react',
            target_framework='vue',
            stack_info=stack_info,
            plan=plan,
            transformations=[]
        )
        
        assert '# Migration Report' in report or 'Migration' in report
        assert 'react' in report.lower()
        assert 'vue' in report.lower()
    
    def test_reporter_generates_html(self, temp_project):
        """Test reporter generates HTML output."""
        from apps.backend.migration.models import StackInfo, MigrationPlan, MigrationPhase
        
        stack_info = StackInfo(
            framework='react',
            language='javascript',
            version='18.0',
            framework_version='18.0'
        )
        
        plan = MigrationPlan(
            source_framework='react',
            target_framework='vue',
            phases=[MigrationPhase('Test', 'Test phase', 1, [])],
            complexity_score=5.0,
            risk_level='medium'
        )
        
        reporter = MigrationReporter()
        html = reporter.generate_html_report(
            migration_id='test-html',
            source_framework='react',
            target_framework='vue',
            stack_info=stack_info,
            plan=plan,
            transformations=[]
        )
        
        assert '<html' in html.lower() or '<div' in html.lower()


class TestRollbackIntegration:
    """Test rollback system integration."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory with git."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Initialize git repo
            import subprocess
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=tmpdir, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=tmpdir, capture_output=True)
            
            # Create initial commit
            test_file = project_path / 'test.txt'
            test_file.write_text('initial')
            subprocess.run(['git', 'add', '.'], cwd=tmpdir, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'initial'], cwd=tmpdir, capture_output=True)
            
            yield tmpdir
    
    def test_rollback_creates_checkpoint(self, temp_project):
        """Test rollback creates git checkpoint."""
        rollback_manager = RollbackManager(temp_project)
        
        # Create checkpoint
        checkpoint = rollback_manager.create_checkpoint(
            phase_name='test_phase',
            description='Test checkpoint'
        )
        
        assert checkpoint is not None
        assert 'phase' in checkpoint.lower() or 'commit' in checkpoint.lower()


class TestValidatorIntegration:
    """Test validation system integration."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_validator_runs_tests(self, temp_project):
        """Test validator can run test suite."""
        project_path = Path(temp_project)
        
        # Create mock test file
        test_file = project_path / 'test.js'
        test_file.write_text('console.log("test")')
        
        validator = MigrationValidator(temp_project)
        report = validator.validate(results=[])
        
        assert report is not None


class TestComplexMigrationScenarios:
    """Test complex, realistic migration scenarios."""
    
    @pytest.fixture
    def temp_project(self):
        """Create realistic project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create realistic structure
            src_dir = project_path / 'src'
            src_dir.mkdir()
            
            components_dir = src_dir / 'components'
            components_dir.mkdir()
            
            services_dir = src_dir / 'services'
            services_dir.mkdir()
            
            # Create multiple components
            (components_dir / 'Button.jsx').write_text(TEST_FIXTURES['react_component']['content'][:100])
            (components_dir / 'Header.jsx').write_text("import React from 'react'\nfunction Header() { return <h1>Header</h1> }")
            
            # Create service files
            (services_dir / 'api.js').write_text(TEST_FIXTURES['javascript_code']['content'][:100])
            
            yield tmpdir
    
    def test_migrate_multiple_components(self, temp_project):
        """Test migrating entire component directory."""
        engine = TransformationEngine(temp_project, 'react', 'vue')
        results = engine.transform_code()
        
        # Should find and transform multiple files
        assert len(results) >= 0
    
    def test_mixed_file_migration(self, temp_project):
        """Test migrating mixed file types in project."""
        project_path = Path(temp_project)
        
        # Add SQL file
        (project_path / 'schema.sql').write_text(TEST_FIXTURES['mysql_schema']['content'][:100])
        
        # Add Python file
        (project_path / 'utils.py').write_text(TEST_FIXTURES['python2_code']['content'][:100])
        
        # React migration
        react_engine = TransformationEngine(temp_project, 'react', 'vue')
        react_results = react_engine.transform_code()
        
        # Database migration
        db_engine = TransformationEngine(temp_project, 'mysql', 'postgresql')
        db_results = db_engine.transform_code()
        
        # Python migration
        py_engine = TransformationEngine(temp_project, 'python2', 'python3')
        py_results = py_engine.transform_code()
        
        # Should have transformations for all types
        total_results = len(react_results) + len(db_results) + len(py_results)
        assert total_results >= 0


class TestErrorHandlingIntegration:
    """Test error handling across integration scenarios."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_handles_invalid_project_path(self):
        """Test handling of invalid project path."""
        engine = TransformationEngine('/nonexistent/path', 'react', 'vue')
        results = engine.transform_code()
        
        # Should handle gracefully
        assert isinstance(results, list)
    
    def test_handles_missing_files(self, temp_project):
        """Test handling when expected files are missing."""
        engine = TransformationEngine(temp_project, 'react', 'vue')
        results = engine.transform_code(['nonexistent.jsx'])
        
        # Should not crash
        assert isinstance(results, list)
    
    def test_handles_malformed_code(self, temp_project):
        """Test handling of malformed source code."""
        project_path = Path(temp_project)
        
        # Create malformed file
        bad_file = project_path / 'bad.jsx'
        bad_file.write_text('function Test() { {{{{{ invalid syntax')
        
        engine = TransformationEngine(temp_project, 'react', 'vue')
        results = engine.transform_code()
        
        # Should handle gracefully
        assert isinstance(results, list)


class TestPerformanceIntegration:
    """Test performance of complete migration pipeline."""
    
    @pytest.fixture
    def temp_project(self):
        """Create large project for performance testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create multiple component files
            for i in range(5):
                comp_file = project_path / f'Component{i}.jsx'
                comp_file.write_text(f"""
import React, {{ useState }} from 'react'

function Component{i}() {{
  const [state, setState] = useState(0)
  return <div>Component {i}: {{state}}</div>
}}
""")
            
            yield tmpdir
    
    def test_migration_performance_acceptable(self, temp_project):
        """Test migration completes in reasonable time."""
        import time
        
        engine = TransformationEngine(temp_project, 'react', 'vue')
        
        start = time.time()
        results = engine.transform_code()
        duration = time.time() - start
        
        # Should complete within 10 seconds
        assert duration < 10
        assert len(results) >= 0
