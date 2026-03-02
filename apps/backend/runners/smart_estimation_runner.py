"""
Smart Estimation Runner

Executes smart estimation analysis using the SmartEstimationService.
Provides streaming output and structured results.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import argparse

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from services.smart_estimation_service import get_smart_estimation_service
from core.context_manager import get_project_context
from agents.claude_agent_sdk import ClaudeAgentSDK


class SmartEstimationRunner:
    """
    Runner for smart estimation analysis with streaming support.
    """
    
    def __init__(self):
        self.estimation_service = get_smart_estimation_service()
        self.agent_sdk = ClaudeAgentSDK()
    
    def run_estimation(self, project_id: str, task_description: str) -> Dict[str, Any]:
        """
        Run smart estimation analysis for a given task.
        
        Args:
            project_id: ID of the project
            task_description: Natural language description of the task
            
        Returns:
            Dictionary containing the estimation result
        """
        try:
            # Emit start event
            self._emit_event('start', {'status': 'Analyzing task description...'})
            
            # Get project context
            self._emit_event('progress', {'status': 'Loading project context...'})
            project_context = get_project_context(project_id)
            project_path = project_context.get('project_path', '')
            
            if not project_path:
                raise ValueError(f"Project context not found for project ID: {project_id}")
            
            # Run the estimation analysis
            self._emit_event('progress', {'status': 'Analyzing complexity factors...'})
            result = self.estimation_service.analyze_task_description(task_description, project_path)
            
            # Prepare structured result
            structured_result = {
                'complexity_score': result.complexity_score,
                'confidence_level': result.confidence_level,
                'reasoning': result.reasoning,
                'similar_tasks': result.similar_tasks,
                'risk_factors': result.risk_factors,
                'estimated_duration_hours': result.estimated_duration_hours,
                'estimated_qa_iterations': result.estimated_qa_iterations,
                'token_cost_estimate': result.token_cost_estimate,
                'recommendations': result.recommendations
            }
            
            # Emit completion event
            self._emit_event('complete', structured_result)
            
            return structured_result
            
        except Exception as e:
            error_msg = f"Smart estimation failed: {str(e)}"
            self._emit_event('error', {'error': error_msg})
            raise
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to stdout for the main process to capture"""
        event = {
            'type': event_type,
            'data': data,
            'timestamp': self._get_timestamp()
        }
        print(f"SMART_ESTIMATION_EVENT:{json.dumps(event)}", flush=True)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


def main():
    """Main entry point for the smart estimation runner"""
    parser = argparse.ArgumentParser(description='Smart Estimation Runner')
    parser.add_argument('--project-id', required=True, help='Project ID')
    parser.add_argument('--task-description', required=True, help='Task description to analyze')
    
    args = parser.parse_args()
    
    try:
        runner = SmartEstimationRunner()
        result = runner.run_estimation(args.project_id, args.task_description)
        # Result is already emitted via events, but we also return it for completeness
        print(f"SMART_ESTIMATION_RESULT:{json.dumps(result)}", flush=True)
        
    except Exception as e:
        print(f"SMART_ESTIMATION_ERROR:{str(e)}", flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
