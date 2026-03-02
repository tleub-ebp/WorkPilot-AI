"""
Tests for Smart Estimation Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from services.smart_estimation_service import (
    SmartEstimationService,
    TaskComplexityFactors,
    EstimationResult,
    get_smart_estimation_service
)


class TestSmartEstimationService:
    """Test suite for SmartEstimationService"""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for each test"""
        with patch('services.smart_estimation_service.get_current_model_info'):
            return SmartEstimationService()

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        with patch('services.smart_estimation_service.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_get_db.return_value.__exit__.return_value = None
            yield mock_session

    def test_extract_file_patterns(self, service):
        """Test file pattern extraction from task descriptions"""
        # Test with various file types
        description = "Create a new component with service and controller"
        patterns = service._extract_file_patterns(description)
        
        assert 'component' in patterns
        assert 'service' in patterns
        assert 'controller' in patterns

    def test_count_implicit_files(self, service):
        """Test implicit file counting"""
        # UI task should count multiple files
        ui_desc = "Create a new login page"
        assert service._count_implicit_files(ui_desc) >= 2

        # API task should count multiple files
        api_desc = "Add user authentication endpoint"
        assert service._count_implicit_files(api_desc) >= 2

        # Database task should count multiple files
        db_desc = "Create user migration"
        assert service._count_implicit_files(db_desc) >= 2

    def test_identify_risk_factors(self, service):
        """Test risk factor identification"""
        # High-risk keywords
        risky_desc = "Refactor the authentication database for production"
        risks = service._identify_risk_factors(risky_desc)
        
        assert any('refactor' in risk.lower() for risk in risks)
        assert any('database' in risk.lower() for risk in risks)
        assert any('production' in risk.lower() for risk in risks)

    def test_identify_complexity_indicators(self, service):
        """Test complexity indicator identification"""
        complex_desc = "Create a scalable real-time distributed system with async operations"
        indicators = service._identify_complexity_indicators(complex_desc)
        
        assert any('scalable' in indicator.lower() for indicator in indicators)
        assert any('real-time' in indicator.lower() for indicator in indicators)
        assert any('distributed' in indicator.lower() for indicator in indicators)
        assert any('async' in indicator.lower() for indicator in indicators)

    def test_calculate_text_similarity(self, service):
        """Test text similarity calculation"""
        text1 = "create user authentication with JWT"
        text2 = "implement user login with JWT tokens"
        
        similarity = service._calculate_text_similarity(text1, text2)
        assert 0 <= similarity <= 1
        assert similarity > 0.5  # Should be quite similar

        # Test with completely different texts
        text3 = "fix button color in CSS"
        similarity = service._calculate_text_similarity(text1, text3)
        assert similarity < 0.3  # Should be quite different

    def test_infer_complexity_from_metrics(self, service):
        """Test complexity inference from build metrics"""
        from analytics.database_schema import Build, BuildPhase, QAResult, BuildStatus
        
        # Create mock build with high complexity metrics
        build = Mock()
        build.total_duration_seconds = 18000  # 5 hours
        build.qa_iterations = 3
        build.total_tokens_used = 15000
        
        # Create mock phases with some failures
        phases = [
            Mock(success=True),
            Mock(success=False),  # One failure
            Mock(success=True)
        ]
        
        qa_results = []
        
        complexity = service._infer_complexity_from_metrics(build, phases, qa_results)
        assert complexity >= 5  # Should be high due to duration and failures

    def test_calculate_complexity_score(self, service):
        """Test complexity score calculation"""
        # Create factors with high complexity
        factors = TaskComplexityFactors(
            estimated_files_impacted=8,
            codebase_coverage_percentage=80.0,
            similar_tasks_history=[],
            risk_factors=['High risk factor 1', 'High risk factor 2'],
            complexity_indicators=['Complex indicator 1']
        )
        
        similar_tasks = [
            {'complexity_score': 8},
            {'complexity_score': 9},
            {'complexity_score': 7}
        ]
        
        score = service._calculate_complexity_score(factors, similar_tasks)
        assert 1 <= score <= 13
        assert score >= 6  # Should be relatively high

    def test_calculate_confidence_level(self, service):
        """Test confidence level calculation"""
        # High confidence with many similar tasks
        similar_tasks_high = [
            {'similarity_score': 0.9},
            {'similarity_score': 0.8},
            {'similarity_score': 0.85}
        ]
        factors = TaskComplexityFactors(0, 0, [], [], [])
        
        confidence = service._calculate_confidence_level(similar_tasks_high, factors)
        assert confidence >= 0.7

        # Low confidence with few similar tasks
        similar_tasks_low = [{'similarity_score': 0.3}]
        confidence = service._calculate_confidence_level(similar_tasks_low, factors)
        assert confidence <= 0.6

    @patch('services.smart_estimation_service.get_project_context')
    def test_analyze_task_description_success(self, mock_get_context, service, mock_db):
        """Test successful task analysis"""
        # Mock project context
        mock_get_context.return_value = {
            'project_path': '/path/to/project'
        }
        
        # Mock database queries
        mock_build = Mock()
        mock_build.build_id = 'build-123'
        mock_build.spec_name = 'Add user authentication'
        mock_build.total_duration_seconds = 3600
        mock_build.qa_iterations = 2
        mock_build.total_tokens_used = 5000
        mock_build.total_cost_usd = 2.5
        mock_build.status = 'COMPLETE'
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_build
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Test analysis
        result = service.analyze_task_description(
            "Add user authentication with JWT",
            "project-123"
        )
        
        assert isinstance(result, EstimationResult)
        assert 1 <= result.complexity_score <= 13
        assert 0 <= result.confidence_level <= 1
        assert len(result.reasoning) > 0
        assert isinstance(result.estimated_duration_hours, (int, float, type(None)))
        assert isinstance(result.estimated_qa_iterations, (int, float, type(None)))

    @patch('services.smart_estimation_service.get_project_context')
    def test_analyze_task_description_no_project(self, mock_get_context, service):
        """Test task analysis with no project context"""
        mock_get_context.return_value = {}
        
        with pytest.raises(ValueError, match="Project context not found"):
            service.analyze_task_description(
                "Add user authentication",
                "invalid-project"
            )

    def test_generate_recommendations(self, service):
        """Test recommendation generation"""
        factors = TaskComplexityFactors(
            estimated_files_impacted=10,
            codebase_coverage_percentage=90.0,
            similar_tasks_history=[],
            risk_factors=['Production deployment risk'],
            complexity_indicators=['Distributed system complexity']
        )
        
        similar_tasks = [
            {'status': 'FAILED'},
            {'status': 'COMPLETE'}
        ]
        
        recommendations = service._generate_recommendations(factors, 10, similar_tasks)
        
        assert len(recommendations) > 0
        assert any('branch' in rec.lower() for rec in recommendations)
        assert any('testing' in rec.lower() for rec in recommendations)

    def test_estimate_duration_fallback(self, service):
        """Test duration estimation fallback"""
        duration = service._estimate_duration([], 5)
        assert duration is not None
        assert duration > 0

    def test_estimate_qa_iterations_fallback(self, service):
        """Test QA iterations estimation fallback"""
        iterations = service._estimate_qa_iterations([], 6)
        assert iterations is not None
        assert iterations >= 1

    def test_estimate_token_cost_fallback(self, service):
        """Test token cost estimation fallback"""
        cost = service._estimate_token_cost([], 7)
        assert cost is not None
        assert cost > 0

    def test_get_smart_estimation_service_singleton(self):
        """Test that the service is a singleton"""
        service1 = get_smart_estimation_service()
        service2 = get_smart_estimation_service()
        
        assert service1 is service2


class TestSmartEstimationIntegration:
    """Integration tests for Smart Estimation"""

    @patch('services.smart_estimation_service.get_project_context')
    @patch('services.smart_estimation_service.get_db')
    def test_full_estimation_flow(self, mock_get_db, mock_get_context):
        """Test complete estimation flow with realistic data"""
        with patch('services.smart_estimation_service.get_current_model_info'):
            service = SmartEstimationService()
        
        # Setup mocks
        mock_get_context.return_value = {
            'project_path': '/test/project'
        }
        
        # Mock realistic build data
        mock_builds = [
            Mock(
                build_id='build-1',
                spec_name='Add user login feature',
                total_duration_seconds=7200,  # 2 hours
                qa_iterations=2,
                total_tokens_used=8000,
                total_cost_usd=4.0,
                status='COMPLETE'
            ),
            Mock(
                build_id='build-2',
                spec_name='Implement authentication system',
                total_duration_seconds=10800,  # 3 hours
                qa_iterations=3,
                total_tokens_used=12000,
                total_cost_usd=6.0,
                status='COMPLETE'
            )
        ]
        
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_builds
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None
        
        # Run estimation
        result = service.analyze_task_description(
            "Implement user authentication with OAuth2",
            "project-123"
        )
        
        # Verify results
        assert isinstance(result, EstimationResult)
        assert result.complexity_score >= 3  # Should be moderate to high
        assert result.confidence_level > 0.5  # Should have reasonable confidence
        assert len(result.reasoning) > 0
        assert len(result.similar_tasks) > 0
        assert result.estimated_duration_hours is not None
        assert result.estimated_qa_iterations is not None
        assert result.token_cost_estimate is not None


if __name__ == '__main__':
    pytest.main([__file__])
