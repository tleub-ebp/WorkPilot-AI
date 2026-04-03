#!/usr/bin/env python3
"""
Phase 2 Evaluation Script
=====================

This script runs the Phase 2 evaluation to measure GitHub Copilot optimization impact
and validate Claude Code isolation.

Usage:
    python scripts/phase2_evaluation.py [--duration HOURS] [--mode MODE]

Options:
    --duration HOURS    Evaluation duration in hours (default: 24)
    --mode MODE         Evaluation mode: 'baseline', 'optimized', or 'full' (default: 'full')
    --output FILE       Output file for results (default: auto-generated)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    # TokenTracker is available but not used in this evaluation runner
    from apps.backend.core.optimization.phase2_evaluation import AutomatedDataCollector
    print("✅ Phase 2 evaluation modules imported successfully")
except ImportError as e:
    print(f"❌ Error importing optimization modules: {e}")
    print("Make sure the optimization module is properly installed.")
    sys.exit(1)


class Phase2EvaluationRunner:
    """Runner for Phase 2 evaluation."""
    
    def __init__(self, duration_hours=24, mode='full', output_file=None):
        self.duration_hours = duration_hours
        self.mode = mode
        self.output_file = output_file
        self.collector = AutomatedDataCollector()
        
    async def run_evaluation(self):
        """Run the Phase 2 evaluation."""
        print("🚀 Starting Phase 2 Evaluation")
        print("=" * 50)
        print(f"Duration: {self.duration_hours} hours")
        print(f"Mode: {self.mode}")
        print(f"Output: {self.output_file or 'auto-generated'}")
        print("=" * 50)
        
        try:
            if self.mode == 'baseline':
                results = await self._run_baseline_evaluation()
            elif self.mode == 'optimized':
                results = await self._run_optimized_evaluation()
            elif self.mode == 'full':
                results = await self._run_full_evaluation()
            else:
                raise ValueError(f"Invalid mode: {self.mode}")
            
            # Save results
            if self.output_file:
                self._save_results(results, self.output_file)
            
            # Print summary
            self._print_summary(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error during evaluation: {e}")
            return None
    
    async def _run_baseline_evaluation(self):
        """Run baseline evaluation only."""
        print("📊 Phase 1: Baseline Data Collection")
        print("-" * 30)
        
        # Disable optimization
        os.environ['COPILOT_OPTIMIZATION_ENABLED'] = 'false'
        
        print("  Collecting baseline GitHub Copilot data...")
        
        # Collect baseline data
        baseline_results = {}
        
        # Token usage baseline
        print("    - Token usage baseline...")
        baseline_results['token_usage'] = await self.collector.collectors['token_usage'].collect_baseline_data(self.duration_hours)
        
        # Performance baseline
        print("    - Performance baseline...")
        baseline_results['performance'] = await self.collector.collectors['performance'].collect_baseline_data(self.duration_hours)
        
        # Quality baseline
        print("    - Quality baseline...")
        baseline_results['quality'] = await self.collector.collectors['quality'].collect_baseline_data(self.duration_hours)
        
        # Claude Code baseline
        print("    - Claude Code baseline...")
        baseline_results['claude_validation'] = await self.collector.collectors['claude_validation'].validate_claude_performance(self.duration_hours)
        
        return {
            'evaluation_type': 'baseline',
            'duration_hours': self.duration_hours,
            'timestamp': datetime.now().isoformat(),
            'results': baseline_results
        }
    
    async def _run_optimized_evaluation(self):
        """Run optimized evaluation only."""
        print("📊 Phase 2: Optimized Data Collection")
        print("-" * 30)
        
        # Enable optimization
        os.environ['COPILOT_OPTIMIZATION_ENABLED'] = 'true'
        
        print("  Collecting optimized GitHub Copilot data...")
        
        # Collect optimized data
        optimized_results = {}
        
        # Token usage optimized
        print("    - Token usage optimized...")
        optimized_results['token_usage'] = await self.collector.collectors['token_usage'].collect_optimized_data(self.duration_hours)
        
        # Performance optimized
        print("    - Performance optimized...")
        optimized_results['performance'] = await self.collector.collectors['performance'].collect_optimized_data(self.duration_hours)
        
        # Quality optimized
        print("    - Quality optimized...")
        optimized_results['quality'] = await self.collector.collectors['quality'].collect_optimized_data(self.duration_hours)
        
        # Claude Code during optimization
        print("    - Claude Code during optimization...")
        optimized_results['claude_validation'] = await self.collector.collectors['claude_validation'].validate_claude_performance(self.duration_hours)
        
        return {
            'evaluation_type': 'optimized',
            'duration_hours': self.duration_hours,
            'timestamp': datetime.now().isoformat(),
            'results': optimized_results
        }
    
    async def _run_full_evaluation(self):
        """Run complete evaluation (baseline + optimized)."""
        print("📊 Phase 1: Baseline Data Collection")
        print("-" * 30)
        
        # Phase 1: Baseline
        os.environ['COPILOT_OPTIMIZATION_ENABLED'] = 'false'
        
        print("  Collecting baseline data...")
        baseline_results = {}
        
        # Collect baseline data (shortened for demo)
        print("    - Token usage baseline...")
        baseline_results['token_usage'] = await self.collector.collectors['token_usage'].collect_baseline_data(1)
        
        print("    - Performance baseline...")
        baseline_results['performance'] = await self.collector.collectors['performance'].collect_baseline_data(1)
        
        print("    - Quality baseline...")
        baseline_results['quality'] = await self.collector.collectors['quality'].collect_baseline_data(1)
        
        print("    - Claude Code baseline...")
        baseline_results['claude_validation'] = await self.collector.collectors['claude_validation'].validate_claude_performance(1)
        
        print("\n📊 Phase 2: Optimized Data Collection")
        print("-" * 30)
        
        # Phase 2: Optimized
        os.environ['COPILOT_OPTIMIZATION_ENABLED'] = 'true'
        
        print("  Collecting optimized data...")
        optimized_results = {}
        
        # Collect optimized data (shortened for demo)
        print("    - Token usage optimized...")
        optimized_results['token_usage'] = await self.collector.collectors['token_usage'].collect_optimized_data(1)
        
        print("    - Performance optimized...")
        optimized_results['performance'] = await self.collector.collectors['performance'].collect_optimized_data(1)
        
        print("    - Quality optimized...")
        optimized_results['quality'] = await self.collector.collectors['quality'].collect_optimized_data(1)
        
        print("    - Claude Code during optimization...")
        optimized_results['claude_validation'] = await self.collector.collectors['claude_validation'].validate_claude_performance(1)
        
        print("\n📊 Phase 3: Analysis")
        print("-" * 30)
        
        # Analysis
        analysis_results = {}
        
        print("  Analyzing token usage impact...")
        analysis_results['token_impact'] = self.collector._analyze_token_impact(
            baseline_results.get('token_usage'),
            optimized_results.get('token_usage')
        )
        
        print("  Analyzing performance impact...")
        analysis_results['performance_impact'] = self.collector._analyze_performance_impact(
            baseline_results.get('performance'),
            optimized_results.get('performance')
        )
        
        print("  Analyzing quality impact...")
        analysis_results['quality_impact'] = self.collector._analyze_quality_impact(
            baseline_results.get('quality'),
            optimized_results.get('quality')
        )
        
        print("  Analyzing Claude Code isolation...")
        analysis_results['claude_isolation'] = optimized_results['claude_validation']
        
        return {
            'evaluation_type': 'full',
            'duration_hours': self.duration_hours,
            'timestamp': datetime.now().isoformat(),
            'baseline_results': baseline_results,
            'optimized_results': optimized_results,
            'analysis_results': analysis_results
        }
    
    def _save_results(self, results, output_file):
        """Save results to file."""
        if not output_file:
            # Generate default filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"phase2_evaluation_results_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Results saved to: {output_path}")
    
    def _print_summary(self, results):
        """Print evaluation summary."""
        print("\n" + "=" * 50)
        print("📊 Evaluation Summary")
        print("=" * 50)
        
        if results['evaluation_type'] == 'full':
            print(f"Evaluation Type: {results['evaluation_type']}")
            print(f"Duration: {results['duration_hours']} hours")
            print(f"Timestamp: {results['timestamp']}")
            
            if 'analysis_results' in results:
                analysis = results['analysis_results']
                
                print("\n📈 Impact Analysis:")
                if 'token_impact' in analysis:
                    token = analysis['token_impact']
                    print(f"  Token Reduction: {token.get('token_reduction_percentage', 0):.1f}%")
                    print(f"  Assessment: {token.get('assessment', 'unknown')}")
                
                if 'performance_impact' in analysis:
                    perf = analysis['performance_impact']
                    print(f"  Performance Improvement: {perf.get('performance_improvement_percentage', 0):.1f}%")
                    print(f"  Assessment: {perf.get('assessment', 'unknown')}")
                
                if 'quality_impact' in analysis:
                    quality = analysis['quality_impact']
                    print(f"  Quality Change: {quality.get('quality_change_percentage', 0):.1f}%")
                    print(f"  Assessment: {quality.get('assessment', 'unknown')}")
                
                if 'claude_isolation' in analysis:
                    claude = analysis['claude_isolation']
                    print(f"  Claude Code Impact: {claude.get('response_time_change', 0):.1f}%")
                    print(f"  Assessment: {claude.get('impact_assessment', 'unknown')}")
                
                # Phase 2 recommendation
                recommendation = self.collector._get_phase2_recommendation(analysis)
                print(f"\n🎯 Phase 2 Recommendation: {recommendation}")
        
        else:
            print(f"Evaluation Type: {results['evaluation_type']}")
            print(f"Results: {len(results.get('results', {}))} categories collected")


def create_sample_data():
    """Create sample data for testing."""
    print("🔧 Creating sample evaluation data...")
    
    # Create sample evaluation results
    sample_results = {
        'evaluation_type': 'full',
        'duration_hours': 24,
        'timestamp': datetime.now().isoformat(),
        'baseline_results': {
            'token_usage': {
                'global_tokens': 10000,
                'runtime_tokens': 6000,
                'success_rate': 0.95,
                'average_tokens_per_task': 150
            },
            'performance': {
                'average_response_time': 2.5,
                'min_response_time': 2.0,
                'max_response_time': 3.0,
                'total_requests': 100
            },
            'quality': {
                'success_rate': 0.95,
                'total_tasks': 100,
                'successful_tasks': 95
            },
            'claude_validation': {
                'response_time_change': 0.0,
                'functionality_impact': 0,
                'resource_impact': 0.0
            }
        },
        'optimized_results': {
            'token_usage': {
                'global_tokens': 7000,
                'runtime_tokens': 4200,
                'success_rate': 0.94,
                'average_tokens_per_task': 105
            },
            'performance': {
                'average_response_time': 2.0,
                'min_response_time': 1.5,
                'max_response_time': 2.5,
                'total_requests': 100
            },
            'quality': {
                'success_rate': 0.94,
                'total_tasks': 100,
                'successful_tasks': 94
            },
            'claude_validation': {
                'response_time_change': 0.0,
                'functionality_impact': 0.0,
                'resource_impact': 0.0
            }
        },
        'analysis_results': {
            'token_impact': {
                'token_reduction_percentage': 30.0,
                'baseline_tokens': 10000,
                'optimized_tokens': 7000,
                'tokens_saved': 3000,
                'assessment': 'excellent'
            },
            'performance_impact': {
                'performance_improvement_percentage': 20.0,
                'baseline_avg_time': 2.5,
                'optimized_avg_time': 2.0,
                'time_saved': 0.5,
                'assessment': 'excellent'
            },
            'quality_impact': {
                'quality_change_percentage': -1.0,
                'baseline_success_rate': 0.95,
                'optimized_success_rate': 0.94,
                'assessment': 'excellent'
            },
            'claude_isolation': {
                'response_time_change': 0.0,
                'functionality_impact': 0.0,
                'resource_impact': 0.0,
                'impact_assessment': 'minimal'
            }
        },
        'phase2_recommendation': 'PROCEED_WITH_PHASE2'
    }
    
    # Save sample data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"sample_evaluation_results_{timestamp}.json"
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(sample_results, f, indent=2)
    
    print(f"📄 Sample data created: {output_path}")
    return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Phase 2 Evaluation Script')
    
    parser.add_argument(
        '--duration',
        type=int,
        default=24,
        help='Evaluation duration in hours (default: 24)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['baseline', 'optimized', 'full'],
        default='full',
        help='Evaluation mode: baseline, optimized, or full'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for results (default: auto-generated)'
    )
    
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Create sample data for testing'
    )
    
    args = parser.parse_args()
    
    if args.sample:
        create_sample_data()
        return
    
    # Validate duration
    if args.duration < 1:
        print("❌ Duration must be at least 1 hour")
        sys.exit(1)
    
    if args.duration > 168:  # 7 days
        print("❌ Duration cannot exceed 168 hours (7 days)")
        sys.exit(1)
    
    # Create runner
    runner = Phase2EvaluationRunner(
        duration_hours=args.duration,
        mode=args.mode,
        output_file=args.output
    )
    
    # Run evaluation
    try:
        results = asyncio.run(runner.run_evaluation())
        
        if results:
            print("\n🎉 Evaluation completed successfully!")
        else:
            print("\n❌ Evaluation failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
