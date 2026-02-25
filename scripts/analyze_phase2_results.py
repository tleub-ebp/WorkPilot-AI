#!/usr/bin/env python3
"""
Phase 2 Results Analyzer
=====================

This script analyzes Phase 2 evaluation results and provides detailed insights
into GitHub Copilot optimization impact and Claude Code isolation.

Usage:
    python scripts/analyze_phase2_results.py [--input FILE] [--output FILE]
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from apps.backend.core.optimization.phase2_evaluation import Phase2DecisionFramework, RiskAssessment
except ImportError as e:
    print(f"❌ Error importing optimization modules: {e}")
    print("Make sure the optimization module is properly installed.")
    sys.exit(1)


class Phase2ResultsAnalyzer:
    """Analyzer for Phase 2 evaluation results."""
    
    def __init__(self, input_file=None, output_file=None):
        self.input_file = input_file
        self.output_file = output_file
        self.results = None
        self.analysis = None
    
    def load_results(self):
        """Load evaluation results from file."""
        if not self.input_file:
            # Find the latest results file
            pattern = "phase2_evaluation_results_*.json"
            matching_files = list(Path('.').glob(pattern))
            
            if not matching_files:
                print("❌ No evaluation results files found")
                print("Run the evaluation first or specify --input FILE")
                return False
            
            self.input_file = max(matching_files, key=lambda x: x.stat().st_mtime)
            print(f"📂 Using latest results file: {self.input_file}")
        
        try:
            with open(self.input_file, 'r') as f:
                self.results = json.load(f)
            
            print(f"📂 Loaded evaluation results from: {self.input_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading results file: {e}")
            return False
    
    def analyze_results(self):
        """Analyze the evaluation results."""
        if not self.results:
            print("❌ No results to analyze")
            return
        
        print("🔍 Analyzing Phase 2 Evaluation Results")
        print("=" * 50)
        
        # Extract key metrics
        if self.results['evaluation_type'] == 'full':
            self._analyze_full_evaluation()
        else:
            self._analyze_partial_evaluation()
        
        # Generate analysis report
        self._generate_analysis_report()
    
    def _analyze_full_evaluation(self):
        """Analyze full evaluation results."""
        baseline = self.results['baseline_results']
        optimized = self.results['optimized_results']
        analysis = self.results['analysis_results']
        
        print("\n📊 Full Evaluation Analysis")
        print("-" * 30)
        
        # Token usage analysis
        print("🪙 Token Usage Analysis:")
        if 'token_impact' in analysis:
            token = analysis['token_impact']
            print(f"  Token Reduction: {token['token_reduction_percentage']:.1f}%")
            print(f"  Baseline Tokens: {token['baseline_tokens']}")
            print(f"  Optimized Tokens: {token['optimized_tokens']}")
            print(f"  Tokens Saved: {token['tokens_saved']}")
            print(f"  Assessment: {token['assessment']}")
        
        # Performance analysis
        print("\n⚡ Performance Analysis:")
        if 'performance_impact' in analysis:
            perf = analysis['performance_impact']
            print(f"  Performance Improvement: {perf['performance_improvement_percentage']:.1f}%")
            print(f"  Baseline Avg Time: {perf['baseline_avg_time']:.2f}s")
            print(f"  Optimized Avg Time: {perf['optimized_avg_time']:.2f}s")
            print(f"  Time Saved: {perf['time_saved']:.2f}s")
            print(f"  Assessment: {perf['assessment']}")
        
        # Quality analysis
        print("\n✅ Quality Analysis:")
        if 'quality_impact' in analysis:
            quality = analysis['quality_impact']
            print(f"  Quality Change: {quality['quality_change_percentage']:.1f}%")
            print(f"  Baseline Success Rate: {quality['baseline_success_rate']:.2%}")
            print(f"  Optimized Success Rate: {quality['optimized_success_rate']:.2%}")
            print(f"  Assessment: {quality['assessment']}")
        
        # Claude Code isolation analysis
        print("\n🔒 Claude Code Isolation Analysis:")
        if 'claude_isolation' in analysis:
            claude = analysis['claude_isolation']
            print(f"  Response Time Change: {claude['response_time_change']:.1f}%")
            print(f"  Functionality Impact: {claude['functionality_impact']:.1f}%")
            print(f"  Resource Impact: {claude['resource_impact']:.1f}%")
            print(f"  Impact Assessment: {claude['impact_assessment']}")
        
        # Phase 2 recommendation
        print("\n🎯 Phase 2 Recommendation:")
        recommendation = self.results.get('phase2_recommendation', 'UNKNOWN')
        print(f"  Recommendation: {recommendation}")
        
        # Decision framework analysis
        print("\n📋 Decision Framework Analysis:")
        if 'analysis_results' in self.results:
            decision_framework = Phase2DecisionFramework()
            decision_result = decision_framework.evaluate_phase1_success(analysis)
            
            print(f"  Overall Score: {decision_result['total_score']:.3f}")
            print(f"  Recommendation: {decision_result['recommendation']}")
            
            print("\n  Individual Scores:")
            for criterion, score in decision_result['individual_scores'].items():
                print(f"    {criterion}: {score:.3f}")
        
        # Risk assessment
        print("\n⚠️ Risk Assessment:")
        if 'analysis_results' in self.results:
            risk_assessment = RiskAssessment()
            risk_result = risk_assessment.assess_phase2_risks(analysis)
            
            print(f"  Overall Risk: {risk_result['risk_level']}")
            print(f"  Risk Score: {risk_result['overall_risk']:.3f}")
            
            print("\n  Individual Risks:")
            for risk, score in risk_result['individual_risks'].items():
                print(f"    {risk}: {score:.3f}")
    
    def _analyze_partial_evaluation(self):
        """Analyze partial evaluation results (baseline or optimized only)."""
        evaluation_type = self.results['evaluation_type']
        results = self.results['results']
        
        print(f"\n📊 {evaluation_type.title()} Evaluation Analysis")
        print("-" * 30)
        
        if evaluation_type == 'baseline':
            print("📊 Baseline Results:")
        else:
            print("📊 Optimized Results:")
        
        # Analyze each category
        for category, data in results.items():
            if category == 'evaluation_type' or category == 'timestamp':
                continue
            
            print(f"\n📊 {category.title()} Analysis:")
            
            if isinstance(data, dict):
                if 'global_tokens' in data:
                    print(f"  Total Tokens: {data['global_tokens']}")
                if 'success_rate' in data:
                    print(f"  Success Rate: {data['success_rate']:.2%}")
                if 'average_tokens_per_task' in data:
                    print(f"  Avg Tokens/Task: {data['average_tokens_per_task']:.1f}")
                if 'budget_utilization' in data:
                    print(f"  Budget Usage: {data['budget_utilization']:.1f}%")
    
    def _generate_analysis_report(self):
        """Generate comprehensive analysis report."""
        if not self.results:
            print("❌ No results to analyze")
            return
        
        # Create analysis report
        analysis = {
            'analysis_timestamp': datetime.now().isoformat(),
            'evaluation_type': self.results['evaluation_type'],
            'input_file': self.input_file,
            'output_file': self.output_file,
            'key_findings': self._extract_key_findings(),
            'recommendations': self._generate_recommendations(),
            'risk_assessment': self._extract_risk_assessment(),
            'decision_framework': self._extract_decision_framework()
        }
        
        self.analysis = analysis
        
        # Save analysis
        if self.output_file:
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            print(f"\n📄 Analysis report saved to: {output_path}")
        else:
            # Generate default filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"phase2_analysis_report_{timestamp}.json"
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            print(f"\n📄 Analysis report saved to: {output_path}")
    
    def _extract_key_findings(self):
        """Extract key findings from the analysis."""
        findings = {}
        
        if self.results['evaluation_type'] == 'full':
            analysis = self.results['analysis_results']
            
            # Token usage findings
            if 'token_impact' in analysis:
                token = analysis['token_impact']
                findings['token_reduction'] = f"{token['token_reduction_percentage']:.1f}%"
                findings['token_savings'] = f"{token['tokens_saved']} tokens"
            
            # Performance findings
            if 'performance_impact' in analysis:
                perf = analysis['performance_impact']
                findings['performance_improvement'] = f"{perf['performance_improvement_percentage']:.1f}%"
                findings['time_savings'] = f"{perf['time_saved']:.2f}s"
            
            # Quality findings
            if 'quality_impact' in analysis:
                quality = analysis['quality_impact']
                findings['quality_maintenance'] = f"{quality['quality_change_percentage']:+.1f}%"
                findings['success_rate_change'] = f"{quality['quality_change_percentage']:+.1f}%"
            
            # Claude Code findings
            if 'claude_isolation' in analysis:
                claude = analysis['claude_isolation']
                findings['claude_isolation'] = "VERIFIED" if claude['impact_assessment'] == 'minimal' else "NEEDS_ATTENTION"
        
        return findings
    
    def _generate_recommendations(self):
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if self.results['evaluation_type'] == 'full':
            analysis = self.results['analysis_results']
            
            # Token usage recommendations
            if 'token_impact' in analysis:
                token = analysis['token_impact']
                if token['token_reduction_percentage'] >= 30:
                    recommendations.append("✅ Excellent token reduction achieved")
                elif token['token_reduction_percentage'] >= 20:
                    recommendations.append("✅ Good token reduction achieved")
                else:
                    recommendations.append("⚠️ Consider increasing optimization level")
            
            # Performance recommendations
            if 'performance_impact' in analysis:
                perf = analysis['performance_impact']
                if perf['performance_improvement_percentage'] >= 20:
                    recommendations.append("✅ Excellent performance improvement")
                elif perf['performance_improvement'] >= 15:
                    recommendations.append("✅ Good performance improvement")
                else:
                    recommendations.append("⚠️ Consider performance tuning")
            
            # Quality recommendations
            if 'quality_impact' in analysis:
                quality = analysis['quality_impact']
                if abs(quality['quality_change_percentage']) <= 2:
                    recommendations.append("✅ Quality maintained")
                else:
                    recommendations.append("⚠️ Monitor quality closely")
            
            # Claude Code recommendations
            if 'claude_isolation' in analysis:
                claude = analysis['claude_isolation']
                if claude['impact_assessment'] == 'minimal':
                    recommendations.append("✅ Claude Code isolation verified")
                else:
                    recommendations.append("⚠️ Review Claude Code integration")
            
            # Phase 2 recommendations
            phase2_recommendation = self.results.get('phase2_recommendation', 'UNKNOWN')
            if phase2_recommendation == 'PROCEED_WITH_PHASE2':
                recommendations.append("🚀 Ready for Phase 2 implementation")
            elif phase2_recommendation == 'PROCEED_WITH_CAUTIONS':
                recommendations.append("⚠️ Proceed with Phase 2 with caution")
            elif phase2_recommendation == 'DELAY_PHASE2':
                recommendations.append("⏸️ Delay Phase 2 until issues are resolved")
            else:
                recommendations.append("❌ Unknown recommendation")
        
        return recommendations
    
    def _extract_risk_assessment(self):
        """Extract risk assessment from analysis."""
        if self.results['evaluation_type'] == 'full':
            analysis = self.results['analysis_results']
            
            if 'analysis_results' in analysis:
                risk_assessment = RiskAssessment()
                risk_result = risk_assessment.assess_phase2_risks(analysis)
                
                return {
                    'risk_level': risk_result['risk_level'],
                    'overall_risk': risk_result['overall_risk'],
                    'key_risks': list(risk_result['individual_risks'].items())
                }
        
        return {'risk_level': 'UNKNOWN', 'overall_risk': 0.0, 'key_risks': []}
    
    def _extract_decision_framework(self):
        """Extract decision framework analysis."""
        if self.results['evaluation_type'] == 'full':
            analysis = self.results['analysis_results']
            
            if 'analysis_results' in analysis:
                decision_framework = Phase2DecisionFramework()
                decision_result = decision_framework.evaluate_phase1_success(analysis)
                
                return {
                    'total_score': decision_result['total_score'],
                    'recommendation': decision_result['recommendation'],
                    'individual_scores': decision_result['individual_scores']
                }
        
        return {'total_score': 0.0, 'recommendation': 'UNKNOWN', 'individual_scores': {}}
    
    def print_summary(self):
        """Print a concise summary of the analysis."""
        if not self.analysis:
            print("❌ No analysis to summarize")
            return
        
        print("\n📊 Summary")
        print("=" * 30)
        
        # Key metrics
        if 'key_findings' in self.analysis:
            findings = self.analysis['key_findings']
            print("Key Findings:")
            for key, value in findings.items():
                print(f"  {key}: {value}")
        
        # Recommendations
        if 'recommendations' in self.analysis:
            recommendations = self.analysis['recommendations']
            print("\nRecommendations:")
            for rec in recommendations:
                print(f"  {rec}")
        
        # Risk assessment
        if 'risk_assessment' in self.analysis:
            risk = self.analysis['risk_assessment']
            print(f"\nRisk Level: {risk['risk_level']}")
        
        # Decision framework
        if 'decision_framework' in self.analysis:
            decision = self.analysis['decision_framework']
            print(f"\nPhase 2 Recommendation: {decision['recommendation']}")
        
        print(f"\n📊 Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Phase 2 Results Analyzer')
    
    parser.add_argument(
        '--input',
        type=str,
        help='Input file with evaluation results'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for analysis report'
    )
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = Phase2ResultsAnalyzer(
        input_file=args.input,
        output_file=args.output
    )
    
    # Load results
    if not analyzer.load_results():
        sys.exit(1)
    
    # Analyze results
    analyzer.analyze_results()
    
    # Print summary
    analyzer.print_summary()


if __name__ == "__main__":
    main()
