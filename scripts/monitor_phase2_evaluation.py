#!/usr/bin/env python3
"""
Phase 2 Evaluation Monitor
======================

This script monitors the Phase 2 evaluation progress and provides real-time updates
on token usage, performance, and Claude Code isolation.

Usage:
    python scripts/monitor_phase2_evaluation.py [--interval SECONDS]
"""

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
    from apps.backend.core.optimization import TokenTracker
    # Phase2DecisionFramework and RiskAssessment are available but not used in this monitor
    print("✅ Optimization modules imported successfully")
except ImportError as e:
    print(f"❌ Error importing optimization modules: {e}")
    print("Make sure the optimization module is properly installed.")
    sys.exit(1)


class Phase2Monitor:
    """Monitor for Phase 2 evaluation."""
    
    def __init__(self, interval_seconds=60):
        self.interval_seconds = interval_seconds
        self.running = False
        self.tracker = TokenTracker()
        self.start_time = datetime.now()
        self.data_points = []
        
        # Set budgets
        self.tracker.set_budget("copilot_runtime", 2000)
        self.tracker.set_budget("copilot_client", 3000)
        self.tracker.set_global_budget(10000)
    
    def start_monitoring(self):
        """Start the monitoring loop."""
        print("🔍 Starting Phase 2 Evaluation Monitor")
        print(f"Interval: {self.interval_seconds} seconds")
        print("Press Ctrl+C to stop monitoring")
        print("=" * 50)
        
        self.running = True
        
        try:
            asyncio.run(self._monitoring_loop())
        except KeyboardInterrupt:
            print("\n⚠️ Monitoring stopped by user")
        finally:
            self.running = False
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect current metrics
                current_metrics = self._collect_current_metrics()
                
                # Add to data points
                self.data_points.append(current_metrics)
                
                # Display dashboard
                self._display_dashboard(current_metrics)
                
                # Check for alerts
                self._check_alerts(current_metrics)
                
                # Wait for next interval
                await asyncio.sleep(self.interval_seconds)
                
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(self.interval_seconds)
    
    def _collect_current_metrics(self):
        """Collect current metrics from all components."""
        # Get token tracker stats
        global_stats = self.tracker.get_global_stats()
        runtime_stats = self.tracker.get_agent_stats("copilot_runtime")
        client_stats = self.tracker.get_agent_stats("copilot_client")
        
        # Calculate efficiency scores
        runtime_efficiency = self.tracker.get_efficiency_score("copilot_runtime")
        client_efficiency = self.tracker.get_efficiency("copilot_client")
        
        # Calculate budget utilization
        runtime_budget = 2000
        client_budget = 3000
        global_budget = 10000
        
        runtime_utilization = (runtime_stats.total_tokens / runtime_budget) * 100
        client_utilization = (client_stats.total_tokens / client_budget) * 100
        global_utilization = (global_stats.total_tokens / global_budget) * 100
        
        # Calculate elapsed time
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'elapsed_time_seconds': elapsed_time,
            'global_stats': {
                'total_tokens': global_stats.total_tokens,
                'success_rate': global_stats.successful_tasks / max(global_stats.successful_tasks + global_stats.failed_tasks, 1),
                'average_tokens_per_task': global_stats.average_tokens_per_task,
                'budget_utilization': global_utilization
            },
            'runtime_stats': {
                'total_tokens': runtime_stats.total_tokens,
                'success_rate': runtime_stats.successful_tasks / max(runtime_stats.successful_tasks + runtime_stats.failed_tasks, 1),
                'average_tokens_per_task': runtime_stats.average_tokens_per_task,
                'budget_utilization': runtime_utilization,
                'efficiency_score': runtime_efficiency
            },
            'client_stats': {
                'total_tokens': client_stats.total_tokens,
                'success_rate': client_stats.successful_tasks / max(client_stats.successful_tasks + client_stats.failed_tasks, 1),
                'average_tokens_per_task': client_stats.average_tokens_per_task,
                'budget_utilization': client_utilization,
                'efficiency_score': client_efficiency
            },
            'data_points_count': len(self.data_points)
        }
    
    def _display_dashboard(self, metrics):
        """Display monitoring dashboard."""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🔍 Phase 2 Evaluation Monitor")
        print("=" * 60)
        print(f"⏰ Time Elapsed: {metrics['elapsed_time_seconds'] // 60}m {metrics['elapsed_time_seconds'] % 60}s")
        print(f"📊 Data Points: {metrics['data_points_count']}")
        print("=" * 60)
        
        # Global metrics
        print("📊 Global Metrics:")
        print(f"  Total Tokens: {metrics['global_stats']['total_tokens']}")
        print(f"  Success Rate: {metrics['global_stats']['success_rate']:.2%}")
        print(f"  Avg Tokens/Task: {metrics['global_stats']['average_tokens_per_task']:.1f}")
        print(f"  Budget Usage: {metrics['global_stats']['budget_utilization']:.1f}%")
        print()
        
        # Runtime metrics
        print("🚀 Runtime Metrics:")
        print(f"  Tokens Used: {metrics['runtime_stats']['total_tokens']}")
        print(f"  Success Rate: {metrics['runtime_stats']['success_rate']:.2%}")
        print(f"  Avg Tokens/Task: {metrics['runtime_stats']['average_tokens_per_task']:.1f}")
        print(f"  Budget Usage: {metrics['runtime_stats']['budget_utilization']:.1f}%")
        print(f"  Efficiency Score: {metrics['runtime_stats']['efficiency_score']:.3f}")
        print()
        
        # Client metrics
        print("🤖 Client Metrics:")
        print(f"  Tokens Used: {metrics['client_stats']['total_tokens']}")
        print(f"  Success Rate: {metrics['client_stats']['success_rate']:.2%}")
        print(f"  Avg Tokens/Task: {metrics['client_stats']['average_tokens_per_task']:.1f}")
        print(f"  Budget Usage: {metrics['client_stats']['budget_utilization']:.1f}%")
        print(f"  Efficiency Score: {metrics['client_stats']['efficiency_score']:.3f}")
        print()
        
        # Status indicators
        print("📈 Status Indicators:")
        self._print_status_indicator("Global Budget", metrics['global_stats']['budget_utilization'])
        self._print_status_indicator("Runtime Budget", metrics['runtime_stats']['budget_utilization'])
        self._print_status_indicator("Client Budget", metrics['client_stats']['budget_utilization'])
        self._print_status_indicator("Global Success Rate", metrics['global_stats']['success_rate'] * 100)
        self._print_status_indicator("Runtime Efficiency", metrics['runtime_stats']['efficiency_score'] * 100)
        self._print_status_indicator("Client Efficiency", metrics['client_stats']['efficiency_score'] * 100)
        print()
        
        # Trend analysis
        if len(self.data_points) > 1:
            self._display_trends()
    
    def _print_status_indicator(self, label, value):
        """Print a status indicator."""
        if label == "Global Budget":
            if value < 70:
                print(f"  🔴 {label}: {value:.1f}% (HIGH USAGE)")
            elif value < 90:
                print(f"  🟡 {label}: {value:.1f}% (NORMAL)")
            else:
                print(f"  🟢 {label}: {value:.1f}% (GOOD)")
        elif label == "Global Success Rate":
            if value < 80:
                print(f"  🔴 {label}: {value:.1f}% (LOW)")
            elif value < 95:
                print(f"  🟡 {label}: {value:.1f}% (NORMAL)")
            else:
                print(f"  🟢 {label}: {value:.1f}% (HIGH)")
        elif label == "Runtime Budget":
            if value < 70:
                print(f"  🔴 {label}: {value:.1f}% (HIGH USAGE)")
            elif value < 90:
                print(f"  🟡 {label}: {value:.1f}% (NORMAL)")
            else:
                print(f"  🟢 {label}: {value:.1f}% (GOOD)")
        elif label == "Client Budget":
            if value < 70:
                print(f"  🔴 {label}: {value:.1f}% (HIGH USAGE)")
            elif value < 90:
                print(f"  🟡 {label}: {value:.1f}% (NORMAL)")
            else:
                print(f"  🟢 {label}: {value:.1f}% (GOOD)")
        elif label in ["Runtime Efficiency", "Client Efficiency"]:
            if value < 70:
                print(f"  🔴 {label}: {value:.1f}% (LOW)")
            elif value < 85:
                print(f"  🟡 {label}: {value:.1f}% (NORMAL)")
            else:
                print(f"  🟢 {label}: {value:.1f}% (HIGH)")
    
    def _display_trends(self):
        """Display trend analysis."""
        if len(self.data_points) < 2:
            return
        
        print("📈 Trend Analysis (Last 10 points):")
        
        # Get last 10 data points
        recent_points = self.data_points[-10:]
        
        # Calculate trends
        global_tokens_trend = [point['global_stats']['total_tokens'] for point in recent_points]
        runtime_tokens_trend = [point['runtime_stats']['total_tokens'] for point in recent_points]
        client_tokens_trend = [point['client_stats']['total_tokens'] for point in recent_points]
        
        # Calculate trend direction
        def get_trend(values):
            if len(values) < 2:
                return "stable"
            
            recent_avg = sum(values[-3:]) / len(values[-3:]) if len(values) >= 3 else sum(values) / len(values)
            earlier_avg = sum(values[:-3:]) / len(values[:-3:]) if len(values) >= 6 else sum(values) / len(values)
            
            if recent_avg > earlier_avg * 1.05:
                return "increasing"
            elif recent_avg < earlier_avg * 0.95:
                return "decreasing"
            else:
                return "stable"
        
        global_trend = get_trend(global_tokens_trend)
        runtime_trend = get_trend(runtime_tokens_trend)
        client_trend = get_trend(client_tokens_trend)
        
        print(f"  Global Tokens: {global_trend}")
        print(f"  Runtime Tokens: {runtime_trend}")
        print(f"  Client Tokens: {client_trend}")
        print()
        
        # Calculate rates
        if len(self.data_points) >= 2:
            recent_point = self.data_points[-1]
            previous_point = self.data_points[-2]
            
            token_rate = (recent_point['global_stats']['total_tokens'] - previous_point['global_stats']['total_tokens']) / 3600  # tokens per hour
            success_rate = recent_point['global_stats']['success_rate']
            
            print(f"  Token Rate: {token_rate:.1f} tokens/hour")
            print(f"  Success Rate: {success_rate:.2%}")
    
    def _check_alerts(self, metrics):
        """Check for alerts and warnings."""
        alerts = []
        
        # Budget warnings
        if metrics['global_stats']['budget_utilization'] > 90:
            alerts.append("🚨 HIGH GLOBAL BUDGET USAGE")
        
        if metrics['runtime_stats']['budget_utilization'] > 90:
            alerts.append("🚨 HIGH RUNTIME BUDGET USAGE")
        
        if metrics['client_stats']['budget_utilization'] > 90:
            alerts.append("🚨 HIGH CLIENT BUDGET USAGE")
        
        # Success rate warnings
        if metrics['global_stats']['success_rate'] < 0.85:
            alerts.append("⚠️ LOW SUCCESS RATE")
        
        if metrics['runtime_stats']['success_rate'] < 0.85:
            alerts.append("⚠️ LOW RUNTIME SUCCESS RATE")
        
        if metrics['client_stats']['success_rate'] < 0.85:
            alerts.append("⚠️ LOW CLIENT SUCCESS RATE")
        
        # Efficiency warnings
        if metrics['runtime_stats']['efficiency_score'] < 0.7:
            alerts.append("⚠️ LOW RUNTIME EFFICIENCY")
        
        if metrics['client_stats']['efficiency_score'] < 0.7:
            alerts.append("⚠️ LOW CLIENT EFFICIENCY")
        
        # Display alerts
        if alerts:
            print("\n🚨 Alerts:")
            for alert in alerts:
                print(f"  {alert}")
        else:
            print("\n✅ No alerts")
    
    def generate_report(self):
        """Generate a monitoring report."""
        if not self.data_points:
            print("❌ No data points to report")
            return
        
        # Calculate summary statistics
        total_tokens = sum(point['global_stats']['total_tokens'] for point in self.data_points)
        avg_success_rate = sum(point['global_stats']['success_rate'] for point in self.data_points) / len(self.data_points)
        avg_efficiency = sum(point['runtime_stats']['efficiency_score'] for point in self.data_points) / len(self.data_points)
        
        # Create report
        report = {
            'monitoring_period': {
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600
            },
            'summary_statistics': {
                'total_tokens': total_tokens,
                'average_success_rate': avg_success_rate,
                'average_efficiency': avg_efficiency,
                'data_points_count': len(self.data_points)
            },
            'final_metrics': self.data_points[-1] if self.data_points else None,
            'alerts_triggered': self._get_alerts_count()
        }
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"phase2_monitoring_report_{timestamp}.json"
        
        report_path = Path(report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Monitoring report saved to: {report_path}")
        return report_path
    
    def _get_alerts_count(self):
        """Get count of triggered alerts."""
        alerts_count = 0
        
        if not self.data_points:
            return 0
        
        for point in self.data_points:
            if point['global_stats']['budget_utilization'] > 90:
                alerts_count += 1
            
            if point['runtime_stats']['budget_utilization'] > 90:
                alerts_count += 1
            
            if point['client_stats']['budget_utilization'] > 90:
                alerts_count += 1
            
            if point['global_stats']['success_rate'] < 0.85:
                alerts_count += 1
            
            if point['runtime_stats']['success_rate'] < 0.85:
                alerts_count += 1
            
            if point['client_stats']['success_rate'] < 0.85:
                alerts_count += 1
            
            if point['runtime_stats']['efficiency_score'] < 0.7:
                alerts_count += 1
            
            if point['client_stats']['efficiency_score'] < 0.7:
                alerts_count += 1
        
        return alerts_count
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.running = False
        print("\n🛑 Stopping monitoring...")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 2 Evaluation Monitor')
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Monitoring interval in seconds (default: 60)'
    )
    
    args = parser.parse_args()
    
    # Validate interval
    if args.interval < 10:
        print("❌ Interval must be at least 10 seconds")
        sys.exit(1)
    
    if args.interval > 300:  # 5 minutes
        print("⚠️  Interval cannot exceed 300 seconds (5 minutes)")
        print("   Use a shorter interval for more responsive monitoring")
    
    # Create and start monitor
    monitor = Phase2Monitor(interval_seconds=args.interval)
    monitor.start_monitoring()


if __name__ == "__main__":
    main()
