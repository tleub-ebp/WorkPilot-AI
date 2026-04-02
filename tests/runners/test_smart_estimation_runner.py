"""
Tests for Smart Estimation Runner
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
from pathlib import Path
import argparse

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Mock the missing modules before importing
import unittest.mock

# Create comprehensive mocks for the entire import chain
mock_sdk = unittest.mock.MagicMock()
mock_sdk.types = unittest.mock.MagicMock()
mock_sdk.types.ResultMessage = unittest.mock.MagicMock()
mock_sdk.ClaudeSDKClient = unittest.mock.MagicMock()
mock_sdk.ClaudeAgentOptions = unittest.mock.MagicMock()
mock_sdk.AgentDefinition = unittest.mock.MagicMock()
sys.modules['claude_agent_sdk'] = mock_sdk
sys.modules['claude_agent_sdk.types'] = mock_sdk.types

# Mock core modules
sys.modules['core.context_manager'] = unittest.mock.MagicMock()
sys.modules['services.smart_estimation_service'] = unittest.mock.MagicMock()

# Mock QA modules to prevent import chain issues
mock_qa = unittest.mock.MagicMock()
mock_qa.loop = unittest.mock.MagicMock()
mock_qa.reviewer = unittest.mock.MagicMock()
mock_qa.MAX_QA_ITERATIONS = 3
mock_qa.run_qa_validation_loop = unittest.mock.MagicMock()
sys.modules['qa'] = mock_qa
sys.modules['qa.loop'] = mock_qa.loop
sys.modules['qa.reviewer'] = mock_qa.reviewer

from runners.smart_estimation_runner import SmartEstimationRunner


class TestSmartEstimationRunner:
    """Test suite for SmartEstimationRunner"""

    @pytest.fixture
    def runner(self):
        """Create a fresh runner instance for each test"""
        with patch('runners.smart_estimation_runner.get_smart_estimation_service'):
            return SmartEstimationRunner()

    @pytest.fixture
    def mock_estimation_service(self):
        """Mock the estimation service"""
        service = Mock()
        # Create a mock result object with attributes
        mock_result = Mock()
        mock_result.complexity_score = 7
        mock_result.confidence_level = 0.85
        mock_result.reasoning = ['Test reasoning']
        mock_result.similar_tasks = []
        mock_result.risk_factors = []
        mock_result.estimated_duration_hours = 3.5
        mock_result.estimated_qa_iterations = 2.0
        mock_result.token_cost_estimate = 1.75
        mock_result.recommendations = ['Test recommendation']
        service.analyze_task_description.return_value = mock_result
        return service

    @pytest.fixture
    def mock_project_context(self):
        """Mock project context"""
        return {
            'project_path': '/test/project/path'
        }

    @patch('runners.smart_estimation_runner.get_project_context')
    def test_run_estimation_success(self, mock_get_context, runner, mock_estimation_service):
        """Test successful estimation run"""
        # Setup mocks
        mock_get_context.return_value = {'project_path': '/test/project'}
        runner.estimation_service = mock_estimation_service

        # Mock the print function to capture output
        with patch('builtins.print') as mock_print:
            result = runner.run_estimation('project-123', 'Add user authentication')

        # Verify service was called correctly
        mock_estimation_service.analyze_task_description.assert_called_once_with(
            'Add user authentication',
            '/test/project'
        )

        # Verify result structure
        assert result['complexity_score'] == 7
        assert abs(result['confidence_level'] - 0.85) < 1e-9
        assert 'reasoning' in result
        assert 'similar_tasks' in result
        assert 'risk_factors' in result
        assert 'estimated_duration_hours' in result
        assert 'estimated_qa_iterations' in result
        assert 'token_cost_estimate' in result
        assert 'recommendations' in result

        # Verify events were emitted
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        event_calls = [call for call in print_calls if call.startswith('SMART_ESTIMATION_EVENT:')]
        assert len(event_calls) >= 2  # At least start and complete events

    @patch('runners.smart_estimation_runner.get_project_context')
    def test_run_estimation_no_project_context(self, mock_get_context, runner):
        """Test estimation with missing project context"""
        mock_get_context.return_value = {}

        with patch('builtins.print') as mock_print:
            with pytest.raises(ValueError, match="Project context not found"):
                runner.run_estimation('invalid-project', 'Test task')

        # Verify error event was emitted
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_calls = [call for call in print_calls if call.startswith('SMART_ESTIMATION_ERROR:')]
        assert len(error_calls) == 1

    @patch('runners.smart_estimation_runner.get_project_context')
    def test_run_estimation_service_error(self, mock_get_context, runner, mock_estimation_service):
        """Test estimation when service raises an error"""
        mock_get_context.return_value = {'project_path': '/test/project'}
        mock_estimation_service.analyze_task_description.side_effect = Exception("Service error")
        runner.estimation_service = mock_estimation_service

        with patch('builtins.print') as mock_print:
            with pytest.raises(Exception, match="Service error"):
                runner.run_estimation('project-123', 'Test task')

        # Verify error event was emitted
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_calls = [call for call in print_calls if call.startswith('SMART_ESTIMATION_ERROR:')]
        assert len(error_calls) == 1

    def test_emit_event(self, runner):
        """Test event emission"""
        with patch('builtins.print') as mock_print:
            with patch('runners.smart_estimation_runner.datetime') as mock_datetime:
                mock_dt = Mock()
                mock_dt.isoformat.return_value = '2023-01-01T00:00:00'
                mock_datetime.now.return_value = mock_dt

                runner._emit_event('test_event', {'data': 'test_data'})

        # Verify print was called with correct format
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert call_args.startswith('SMART_ESTIMATION_EVENT:')
        
        # Parse and verify event structure
        event_json = call_args.replace('SMART_ESTIMATION_EVENT:', '')
        event = json.loads(event_json)
        assert event['type'] == 'test_event'
        assert event['data'] == {'data': 'test_data'}
        assert event['timestamp'] == '2023-01-01T00:00:00'

    def test_get_timestamp(self, runner):
        """Test timestamp generation"""
        with patch('runners.smart_estimation_runner.datetime') as mock_datetime:
            mock_dt = Mock()
            mock_dt.isoformat.return_value = '2023-01-01T12:00:00'
            mock_datetime.now.return_value = mock_dt

            timestamp = runner._get_timestamp()

            assert timestamp == '2023-01-01T12:00:00'
            mock_datetime.now.assert_called_once()


class TestSmartEstimationRunnerCLI:
    """Test suite for Smart Estimation Runner CLI"""

    @patch('runners.smart_estimation_runner.SmartEstimationRunner')
    @patch('runners.smart_estimation_runner.argparse.ArgumentParser')
    def test_main_function_success(self, mock_parser, mock_runner_class):
        """Test main function with successful execution"""
        # Setup mocks
        mock_args = Mock()
        mock_args.project_id = 'test-project'
        mock_args.task_description = 'Test task description'
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser.return_value = mock_parser_instance
        
        mock_runner = Mock()
        mock_runner.run_estimation.return_value = {'result': 'test'}
        mock_runner_class.return_value = mock_runner

        with patch('sys.argv', ['smart_estimation_runner.py', '--project-id', 'test-project', '--task-description', 'Test task']):
            with patch('builtins.print') as mock_print:
                from runners.smart_estimation_runner import main
                main()

        # Verify runner was called correctly
        mock_runner_class.assert_called_once()
        mock_runner.run_estimation.assert_called_once_with('test-project', 'Test task description')

        # Verify result was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        result_calls = [call for call in print_calls if call.startswith('SMART_ESTIMATION_RESULT:')]
        assert len(result_calls) == 1

    @patch('runners.smart_estimation_runner.SmartEstimationRunner')
    @patch('runners.smart_estimation_runner.argparse.ArgumentParser')
    def test_main_function_error(self, mock_parser, mock_runner_class):
        """Test main function with error"""
        # Setup mocks
        mock_args = Mock()
        mock_args.project_id = 'test-project'
        mock_args.task_description = 'Test task description'
        
        mock_parser_instance = Mock()
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser.return_value = mock_parser_instance
        
        mock_runner = Mock()
        mock_runner.run_estimation.side_effect = Exception("Test error")
        mock_runner_class.return_value = mock_runner

        with patch('sys.argv', ['smart_estimation_runner.py', '--project-id', 'test-project', '--task-description', 'Test task']):
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit):
                    from runners.smart_estimation_runner import main
                    main()

        # Verify error was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        error_calls = [call for call in print_calls if call.startswith('SMART_ESTIMATION_ERROR:')]
        assert len(error_calls) == 1

    def test_argument_parser_setup(self):
        """Test argument parser configuration"""
        # Test the actual parser setup by calling main and checking arguments
        with patch('runners.smart_estimation_runner.SmartEstimationRunner') as mock_runner_class:
            mock_runner = Mock()
            mock_runner.run_estimation.return_value = {'result': 'test'}
            mock_runner_class.return_value = mock_runner
            
            with patch('sys.argv', ['smart_estimation_runner.py', '--project-id', 'test-project', '--task-description', 'Test task']):
                try:
                    from runners.smart_estimation_runner import main
                    main()
                except SystemExit as e:
                    if e.code != 0:
                        raise  # Re-raise if it's an error exit
            
            # Verify runner was called, which means parsing worked
            mock_runner_class.assert_called_once()
            mock_runner.run_estimation.assert_called_once_with('test-project', 'Test task')


class TestSmartEstimationRunnerIntegration:
    """Integration tests for Smart Estimation Runner"""

    @patch('runners.smart_estimation_runner.get_project_context')
    @patch('runners.smart_estimation_runner.get_smart_estimation_service')
    def test_full_runner_integration(self, mock_get_service, mock_get_context):
        """Test full runner integration with real service"""
        # Setup realistic service response
        mock_service = Mock()
        mock_result = Mock()
        mock_result.complexity_score = 8
        mock_result.confidence_level = 0.75
        mock_result.reasoning = [
            'High file impact (8 files) suggests significant changes',
            'Identified 2 risk factors that increase complexity',
            'Similar tasks historically score 7.5 on average',
            'Task has moderate complexity with several components'
        ]
        mock_result.similar_tasks = [
            {
                'build_id': 'build-123',
                'spec_name': 'Add user authentication',
                'similarity_score': 0.85,
                'complexity_score': 7,
                'duration_hours': 2.5,
                'qa_iterations': 2,
                'success_rate': 0.9,
                'tokens_used': 8000,
                'cost_usd': 4.0,
                'status': 'COMPLETE'
            }
        ]
        mock_result.risk_factors = [
            'Authentication changes affect core functionality',
            'Security changes require careful testing'
        ]
        mock_result.estimated_duration_hours = 3.0
        mock_result.estimated_qa_iterations = 2.5
        mock_result.token_cost_estimate = 4.0
        mock_result.recommendations = [
            'Consider creating a separate branch for this high-risk task',
            'Implement comprehensive testing before deployment',
            'Schedule additional code review time'
        ]
        mock_service.analyze_task_description.return_value = mock_result
        mock_get_service.return_value = mock_service
        
        mock_get_context.return_value = {
            'project_path': '/real/project/path'
        }

        # Create runner and run estimation
        with patch('runners.smart_estimation_runner.get_smart_estimation_service') as get_service:
            get_service.return_value = mock_service
            runner = SmartEstimationRunner()
            
            with patch('builtins.print') as mock_print:
                result = runner.run_estimation('real-project', 'Implement OAuth2 authentication')

        # Verify comprehensive result
        assert result['complexity_score'] == 8
        assert abs(result['confidence_level'] - 0.75) < 1e-9
        assert len(result['reasoning']) == 4
        assert len(result['similar_tasks']) == 1
        assert len(result['risk_factors']) == 2
        assert abs(result['estimated_duration_hours'] - 3.0) < 1e-9
        assert abs(result['estimated_qa_iterations'] - 2.5) < 1e-9
        assert abs(result['token_cost_estimate'] - 4.0) < 1e-9
        assert len(result['recommendations']) == 3

        # Verify event flow
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        event_calls = [call for call in print_calls if call.startswith('SMART_ESTIMATION_EVENT:')]
        
        # Should have start, progress, and complete events
        assert len(event_calls) >= 2
        
        # Parse events and verify flow
        events = [json.loads(call.replace('SMART_ESTIMATION_EVENT:', '')) for call in event_calls]
        event_types = [event['type'] for event in events]
        
        assert 'start' in event_types
        assert 'complete' in event_types


if __name__ == '__main__':
    pytest.main([__file__])
