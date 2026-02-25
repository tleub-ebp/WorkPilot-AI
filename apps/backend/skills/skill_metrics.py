#!/usr/bin/env python3
"""
Advanced Skill Metrics and Monitoring System

Comprehensive monitoring for Claude Agent Skills with detailed metrics,
performance tracking, optimization suggestions, and alerting.

Features:
- Execution time tracking
- Token usage monitoring
- Success rate analysis
- Performance optimization suggestions
- Alerting system
- Historical data analysis
"""

import json
import logging
import psutil
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import threading

logger = logging.getLogger(__name__)


@dataclass
class SkillExecutionMetrics:
    """Metrics for a single skill execution."""
    skill_name: str
    timestamp: float
    execution_time: float
    tokens_used: int
    success: bool
    memory_usage: int
    cache_hit: bool
    error_message: Optional[str] = None
    user_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'skill_name': self.skill_name,
            'timestamp': self.timestamp,
            'execution_time': self.execution_time,
            'tokens_used': self.tokens_used,
            'success': self.success,
            'memory_usage': self.memory_usage,
            'cache_hit': self.cache_hit,
            'error_message': self.error_message,
            'user_context': self.user_context
        }


@dataclass
class SkillPerformanceStats:
    """Aggregated performance statistics for a skill."""
    skill_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    avg_tokens_used: int = 0
    total_tokens_used: int = 0
    cache_hit_rate: float = 0.0
    avg_memory_usage: float = 0.0
    last_execution: float = 0.0
    
    @property
    def success_rate(self) -> float:
        return self.successful_executions / self.total_executions if self.total_executions > 0 else 0.0
    
    @property
    def failure_rate(self) -> float:
        return self.failed_executions / self.total_executions if self.total_executions > 0 else 0.0
    
    @property
    def tokens_per_execution(self) -> float:
        return self.avg_tokens_used if self.total_executions > 0 else 0.0
    
    def update(self, metrics: SkillExecutionMetrics):
        """Update stats with new execution metrics."""
        self.total_executions += 1
        
        if metrics.success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        # Update execution time stats
        if self.total_executions == 1:
            self.avg_execution_time = metrics.execution_time
            self.min_execution_time = metrics.execution_time
            self.max_execution_time = metrics.execution_time
        else:
            alpha = 0.1  # Exponential moving average
            self.avg_execution_time = alpha * metrics.execution_time + (1 - alpha) * self.avg_execution_time
            self.min_execution_time = min(self.min_execution_time, metrics.execution_time)
            self.max_execution_time = max(self.max_execution_time, metrics.execution_time)
        
        # Update token stats
        self.total_tokens_used += metrics.tokens_used
        self.avg_tokens_used = self.total_tokens_used // self.total_executions
        
        # Update memory stats
        if self.total_executions == 1:
            self.avg_memory_usage = metrics.memory_usage
        else:
            alpha = 0.1
            self.avg_memory_usage = alpha * metrics.memory_usage + (1 - alpha) * self.avg_memory_usage
        
        # Update cache hit rate
        if metrics.cache_hit:
            self.cache_hit_rate = (self.cache_hit_rate * (self.total_executions - 1) + 1) / self.total_executions
        else:
            self.cache_hit_rate = self.cache_hit_rate * (self.total_executions - 1) / self.total_executions
        
        self.last_execution = metrics.timestamp


class AlertManager:
    """Manages alerts for skill performance issues."""
    
    def __init__(self):
        self.alert_thresholds = {
            'max_execution_time': 5.0,  # seconds
            'max_failure_rate': 0.1,  # 10%
            'max_memory_usage': 500 * 1024 * 1024,  # 500MB
            'min_success_rate': 0.9,  # 90%
            'max_token_usage': 10000
        }
        self.active_alerts = []
        self.alert_history = deque(maxlen=1000)
    
    def check_performance_alerts(self, stats: SkillPerformanceStats) -> List[Dict]:
        """Check for performance alerts and return active ones."""
        alerts = []
        
        # Execution time alert
        if stats.avg_execution_time > self.alert_thresholds['max_execution_time']:
            alerts.append({
                'type': 'performance',
                'severity': 'warning',
                'skill': stats.skill_name,
                'message': f"High execution time: {stats.avg_execution_time:.2f}s",
                'threshold': self.alert_thresholds['max_execution_time'],
                'value': stats.avg_execution_time
            })
        
        # Failure rate alert
        if stats.failure_rate > self.alert_thresholds['max_failure_rate']:
            alerts.append({
                'type': 'reliability',
                'severity': 'error',
                'skill': stats.skill_name,
                'message': f"High failure rate: {stats.failure_rate:.1%}",
                'threshold': self.alert_thresholds['max_failure_rate'],
                'value': stats.failure_rate
            })
        
        # Memory usage alert
        if stats.avg_memory_usage > self.alert_thresholds['max_memory_usage']:
            alerts.append({
                'type': 'resource',
                'severity': 'warning',
                'skill': stats.skill_name,
                'message': f"High memory usage: {stats.avg_memory_usage / 1024 / 1024:.1f}MB",
                'threshold': self.alert_thresholds['max_memory_usage'],
                'value': stats.avg_memory_usage
            })
        
        # Success rate alert
        if stats.success_rate < self.alert_thresholds['min_success_rate'] and stats.total_executions > 10:
            alerts.append({
                'type': 'reliability',
                'severity': 'error',
                'skill': stats.skill_name,
                'message': f"Low success rate: {stats.success_rate:.1%}",
                'threshold': self.alert_thresholds['min_success_rate'],
                'value': stats.success_rate
            })
        
        # Token usage alert
        if stats.tokens_per_execution > self.alert_thresholds['max_token_usage']:
            alerts.append({
                'type': 'cost',
                'severity': 'warning',
                'skill': stats.skill_name,
                'message': f"High token usage: {stats.tokens_per_execution}",
                'threshold': self.alert_thresholds['max_token_usage'],
                'value': stats.tokens_per_execution
            })
        
        # Update active alerts
        self.active_alerts = alerts
        for alert in alerts:
            alert['timestamp'] = time.time()
            self.alert_history.append(alert)
        
        return alerts


class OptimizationSuggester:
    """Suggests optimizations based on performance metrics."""
    
    def __init__(self):
        self.suggestion_rules = [
            self._suggest_cache_optimization,
            self._suggest_token_optimization,
            self._suggest_performance_optimization,
            self._suggest_memory_optimization
        ]
    
    def get_suggestions(self, stats: SkillPerformanceStats) -> List[Dict]:
        """Get optimization suggestions for a skill."""
        suggestions = []
        
        for rule in self.suggestion_rules:
            rule_suggestions = rule(stats)
            suggestions.extend(rule_suggestions)
        
        return suggestions
    
    def _suggest_cache_optimization(self, stats: SkillPerformanceStats) -> List[Dict]:
        """Suggest cache-related optimizations."""
        suggestions = []
        
        if stats.cache_hit_rate < 0.5 and stats.total_executions > 5:
            suggestions.append({
                'type': 'cache',
                'priority': 'high',
                'title': 'Improve Cache Hit Rate',
                'description': f"Cache hit rate is only {stats.cache_hit_rate:.1%}. Consider implementing better caching strategies.",
                'actions': [
                    'Implement result caching for repeated queries',
                    'Add preloading for frequently used skills',
                    'Optimize cache key generation'
                ],
                'estimated_improvement': '20-40% performance boost'
            })
        
        return suggestions
    
    def _suggest_token_optimization(self, stats: SkillPerformanceStats) -> List[Dict]:
        """Suggest token usage optimizations."""
        suggestions = []
        
        if stats.tokens_per_execution > 5000:
            suggestions.append({
                'type': 'tokens',
                'priority': 'high',
                'title': 'Reduce Token Usage',
                'description': f"Average token usage is {stats.tokens_per_execution}. Consider optimizing prompts and responses.",
                'actions': [
                    'Use skill summaries instead of full content',
                    'Implement progressive loading',
                    'Optimize prompt templates',
                    'Remove redundant information'
                ],
                'estimated_improvement': '30-60% token reduction'
            })
        
        return suggestions
    
    def _suggest_performance_optimization(self, stats: SkillPerformanceStats) -> List[Dict]:
        """Suggest performance optimizations."""
        suggestions = []
        
        if stats.avg_execution_time > 2.0:
            suggestions.append({
                'type': 'performance',
                'priority': 'medium',
                'title': 'Improve Execution Speed',
                'description': f"Average execution time is {stats.avg_execution_time:.2f}s. Consider performance optimizations.",
                'actions': [
                    'Optimize algorithms and data structures',
                    'Implement lazy loading',
                    'Add parallel processing where possible',
                    'Profile and optimize bottlenecks'
                ],
                'estimated_improvement': '25-50% speed improvement'
            })
        
        return suggestions
    
    def _suggest_memory_optimization(self, stats: SkillPerformanceStats) -> List[Dict]:
        """Suggest memory usage optimizations."""
        suggestions = []
        
        if stats.avg_memory_usage > 100 * 1024 * 1024:  # 100MB
            suggestions.append({
                'type': 'memory',
                'priority': 'medium',
                'title': 'Reduce Memory Usage',
                'description': f"Average memory usage is {stats.avg_memory_usage / 1024 / 1024:.1f}MB. Consider memory optimizations.",
                'actions': [
                    'Implement streaming for large datasets',
                    'Use generators instead of lists',
                    'Optimize data structures',
                    'Add memory cleanup'
                ],
                'estimated_improvement': '15-30% memory reduction'
            })
        
        return suggestions


class SkillMetrics:
    """Main metrics collection and analysis system."""
    
    def __init__(self, metrics_file: Optional[str] = None):
        self.metrics_file = metrics_file or "skill_metrics.json"
        self.skill_stats: Dict[str, SkillPerformanceStats] = {}
        self.execution_history: deque = deque(maxlen=10000)
        self.alert_manager = AlertManager()
        self.optimization_suggester = OptimizationSuggester()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Global metrics
        self.global_stats = {
            'total_executions': 0,
            'total_tokens_used': 0,
            'total_errors': 0,
            'start_time': time.time()
        }
        
        # Load existing metrics
        self._load_metrics()
    
    def track_execution(self, skill_name: str, execution_time: float, 
                        tokens_used: int, success: bool, 
                        error_message: Optional[str] = None,
                        user_context: Optional[Dict] = None) -> None:
        """Track a skill execution with detailed metrics."""
        with self._lock:
            # Get current memory usage
            try:
                process = psutil.Process()
                memory_usage = process.memory_info().rss
            except:
                memory_usage = 0
            
            # Check if this was a cache hit (simplified)
            cache_hit = self._is_cache_hit(skill_name, user_context)
            
            # Create metrics
            metrics = SkillExecutionMetrics(
                skill_name=skill_name,
                timestamp=time.time(),
                execution_time=execution_time,
                tokens_used=tokens_used,
                success=success,
                memory_usage=memory_usage,
                cache_hit=cache_hit,
                error_message=error_message,
                user_context=user_context or {}
            )
            
            # Update skill stats
            if skill_name not in self.skill_stats:
                self.skill_stats[skill_name] = SkillPerformanceStats(skill_name=skill_name)
            
            self.skill_stats[skill_name].update(metrics)
            
            # Update global stats
            self.global_stats['total_executions'] += 1
            self.global_stats['total_tokens_used'] += tokens_used
            if not success:
                self.global_stats['total_errors'] += 1
            
            # Add to history
            self.execution_history.append(metrics)
            
            # Check for alerts
            alerts = self.alert_manager.check_performance_alerts(self.skill_stats[skill_name])
            if alerts:
                self._handle_alerts(alerts)
            
            # Auto-save metrics periodically
            if len(self.execution_history) % 100 == 0:
                self._save_metrics()
            
            logger.debug(f"Tracked execution for {skill_name}: {execution_time:.3f}s, {tokens_used} tokens")
    
    def _is_cache_hit(self, skill_name: str, user_context: Optional[Dict]) -> bool:
        """Determine if execution was a cache hit."""
        # Simplified logic - in real implementation, this would check actual cache
        if user_context and 'cache_key' in user_context:
            return True
        return False
    
    def _handle_alerts(self, alerts: List[Dict]):
        """Handle performance alerts."""
        for alert in alerts:
            if alert['severity'] == 'error':
                logger.error(f"Skill Alert [{alert['type']}]: {alert['message']}")
            else:
                logger.warning(f"Skill Alert [{alert['type']}]: {alert['message']}")
    
    def get_skill_metrics(self, skill_name: str) -> Optional[Dict]:
        """Get comprehensive metrics for a specific skill."""
        with self._lock:
            if skill_name not in self.skill_stats:
                return None
            
            stats = self.skill_stats[skill_name]
            
            # Get suggestions
            suggestions = self.optimization_suggester.get_suggestions(stats)
            
            # Get recent executions
            recent_executions = [
                m for m in self.execution_history 
                if m.skill_name == skill_name and 
                time.time() - m.timestamp < 3600  # Last hour
            ]
            
            return {
                'skill_name': skill_name,
                'stats': stats.to_dict(),
                'suggestions': suggestions,
                'recent_executions': [m.to_dict() for m in recent_executions],
                'alerts': [a for a in self.alert_manager.active_alerts if a['skill'] == skill_name]
            }
    
    def get_global_metrics(self) -> Dict:
        """Get global metrics across all skills."""
        with self._lock:
            uptime = time.time() - self.global_stats['start_time']
            
            # Calculate global averages
            total_executions = sum(stats.total_executions for stats in self.skill_stats.values())
            total_successful = sum(stats.successful_executions for stats in self.skill_stats.values())
            avg_execution_time = 0.0
            avg_tokens_used = 0.0
            
            if total_executions > 0:
                avg_execution_time = sum(stats.avg_execution_time * stats.total_executions 
                                        for stats in self.skill_stats.values()) / total_executions
                avg_tokens_used = sum(stats.avg_tokens_used * stats.total_executions 
                                       for stats in self.skill_stats.values()) / total_executions
            
            return {
                'global_stats': self.global_stats,
                'uptime_hours': uptime / 3600,
                'total_skills': len(self.skill_stats),
                'total_executions': total_executions,
                'global_success_rate': total_successful / total_executions if total_executions > 0 else 0.0,
                'avg_execution_time': avg_execution_time,
                'avg_tokens_used': avg_tokens_used,
                'total_alerts': len(self.alert_manager.active_alerts),
                'skill_count': len(self.skill_stats),
                'top_skills': self._get_top_skills(),
                'performance_summary': self._get_performance_summary()
            }
    
    def _get_top_skills(self) -> List[Dict]:
        """Get top performing skills."""
        skills = []
        for skill_name, stats in self.skill_stats.items():
            if stats.total_executions > 0:
                skills.append({
                    'skill_name': skill_name,
                    'executions': stats.total_executions,
                    'success_rate': stats.success_rate,
                    'avg_execution_time': stats.avg_execution_time,
                    'tokens_per_execution': stats.tokens_per_execution,
                    'performance_score': self._calculate_performance_score(stats)
                })
        
        # Sort by performance score
        skills.sort(key=lambda x: x['performance_score'], reverse=True)
        return skills[:10]
    
    def _calculate_performance_score(self, stats: SkillPerformanceStats) -> float:
        """Calculate overall performance score for a skill."""
        # Weighted score based on multiple factors
        weights = {
            'success_rate': 0.4,
            'speed': 0.3,  # Inverse execution time
            'efficiency': 0.2,  # Inverse token usage
            'reliability': 0.1  # Cache hit rate
        }
        
        score = 0.0
        score += stats.success_rate * weights['success_rate']
        score += (1.0 / max(stats.avg_execution_time, 0.1)) * weights['speed']
        score += (1.0 / max(stats.tokens_per_execution, 1)) * weights['efficiency']
        score += stats.cache_hit_rate * weights['reliability']
        
        return score
    
    def _get_performance_summary(self) -> Dict:
        """Get overall performance summary."""
        if not self.skill_stats:
            return {}
        
        all_stats = list(self.skill_stats.values())
        
        return {
            'avg_success_rate': sum(s.success_rate for s in all_stats) / len(all_stats),
            'avg_execution_time': sum(s.avg_execution_time for s in all_stats) / len(all_stats),
            'avg_tokens_per_execution': sum(s.tokens_per_execution for s in all_stats) / len(all_stats),
            'avg_cache_hit_rate': sum(s.cache_hit_rate for s in all_stats) / len(all_stats),
            'total_alerts': len(self.alert_manager.active_alerts),
            'skills_with_alerts': len(set(a['skill'] for a in self.alert_manager.active_alerts))
        }
    
    def get_optimization_suggestions(self) -> Dict[str, List[Dict]]:
        """Get optimization suggestions for all skills."""
        suggestions = {}
        
        for skill_name, stats in self.skill_stats.items():
            skill_suggestions = self.optimization_suggester.get_suggestions(stats)
            if skill_suggestions:
                suggestions[skill_name] = skill_suggestions
        
        return suggestions
    
    def export_metrics(self, filepath: str, format: str = 'json') -> None:
        """Export metrics to file."""
        data = {
            'export_timestamp': time.time(),
            'global_metrics': self.get_global_metrics(),
            'skill_metrics': {
                name: self.get_skill_metrics(name)
                for name in self.skill_stats.keys()
            },
            'optimization_suggestions': self.get_optimization_suggestions()
        }
        
        try:
            with open(filepath, 'w') as f:
                if format == 'json':
                    json.dump(data, f, indent=2)
                else:
                    # Simple text format
                    f.write("Skill Metrics Export\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Export Time: {datetime.fromtimestamp(data['export_timestamp'])}\n")
                    f.write(f"Total Skills: {data['global_metrics']['total_skills']}\n")
                    f.write(f"Total Executions: {data['global_metrics']['total_executions']}\n")
                    f.write(f"Global Success Rate: {data['global_metrics']['global_success_rate']:.2%}\n")
            
            logger.info(f"Metrics exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
    
    def _load_metrics(self):
        """Load existing metrics from file."""
        try:
            if Path(self.metrics_file).exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                
                # Load skill stats
                if 'skill_metrics' in data:
                    for skill_name, stats_data in data['skill_metrics'].items():
                        stats = SkillPerformanceStats(skill_name=skill_name)
                        # Restore stats from data
                        stats.total_executions = stats_data.get('total_executions', 0)
                        stats.successful_executions = stats_data.get('successful_executions', 0)
                        stats.failed_executions = stats_data.get('failed_executions', 0)
                        stats.avg_execution_time = stats_data.get('avg_execution_time', 0.0)
                        stats.avg_tokens_used = stats_data.get('avg_tokens_used', 0)
                        stats.cache_hit_rate = stats_data.get('cache_hit_rate', 0.0)
                        self.skill_stats[skill_name] = stats
                
                logger.info(f"Loaded metrics for {len(self.skill_stats)} skills")
        except Exception as e:
            logger.warning(f"Failed to load metrics: {e}")
    
    def _save_metrics(self):
        """Save metrics to file."""
        try:
            data = {
                'skill_stats': {
                    name: stats.to_dict()
                    for name, stats in self.skill_stats.items()
                },
                'global_stats': self.global_stats,
                'last_updated': time.time()
            }
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Metrics saved to file")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def cleanup_old_metrics(self, days_to_keep: int = 30):
        """Clean up old metrics data."""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        with self._lock:
            # Clean execution history
            original_length = len(self.execution_history)
            self.execution_history = deque(
                (m for m in self.execution_history if m.timestamp > cutoff_time),
                maxlen=10000
            )
            
            cleaned_count = original_length - len(self.execution_history)
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old metric records")
            
            # Clean old alerts
            original_alerts = len(self.alert_manager.alert_history)
            self.alert_manager.alert_history = deque(
                (a for a in self.alert_manager.alert_history if a['timestamp'] > cutoff_time),
                maxlen=1000
            )
            
            cleaned_alerts = original_alerts - len(self.alert_manager.alert_history)
            if cleaned_alerts > 0:
                logger.info(f"Cleaned up {cleaned_alerts} old alerts")
