"""
Token Tracker
============

Tracks token usage across agents and provides optimization insights.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of token usage"""
    INPUT = "input"
    OUTPUT = "output"
    CONTEXT = "context"
    SYSTEM = "system"


@dataclass
class TokenUsage:
    """Single token usage record"""
    agent_id: str
    task_id: str
    token_type: TokenType
    tokens_used: int
    timestamp: datetime = field(default_factory=datetime.now)
    task_complexity: float = 0.0
    success: bool = True


@dataclass
class TokenStats:
    """Token usage statistics"""
    total_tokens: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_tokens_per_task: float = 0.0
    peak_usage: int = 0


class TokenTracker:
    """
    Tracks and analyzes token usage for optimization.
    
    This class provides:
    - Real-time token tracking
    - Usage statistics
    - Optimization recommendations
    - Budget monitoring
    """
    
    def __init__(self):
        self.usage_history: List[TokenUsage] = []
        self.agent_stats: Dict[str, TokenStats] = {}
        self.global_budget: Optional[int] = None
        self.agent_budgets: Dict[str, int] = {}
    
    def record_usage(self, 
                     agent_id: str, 
                     task_id: str, 
                     token_type: TokenType,
                     tokens_used: int,
                     task_complexity: float = 0.0,
                     success: bool = True):
        """Record token usage for a task"""
        
        usage = TokenUsage(
            agent_id=agent_id,
            task_id=task_id,
            token_type=token_type,
            tokens_used=tokens_used,
            task_complexity=task_complexity,
            success=success
        )
        
        self.usage_history.append(usage)
        self._update_agent_stats(agent_id, usage)
        
        logger.debug(f"Recorded {tokens_used} tokens for {agent_id}:{task_id}")
    
    def _update_agent_stats(self, agent_id: str, usage: TokenUsage):
        """Update statistics for a specific agent"""
        if agent_id not in self.agent_stats:
            self.agent_stats[agent_id] = TokenStats()
        
        stats = self.agent_stats[agent_id]
        stats.total_tokens += usage.tokens_used
        
        if usage.success:
            stats.successful_tasks += 1
        else:
            stats.failed_tasks += 1
        
        # Update average
        total_tasks = stats.successful_tasks + stats.failed_tasks
        stats.average_tokens_per_task = stats.total_tokens / max(total_tasks, 1)
        
        # Update peak
        stats.peak_usage = max(stats.peak_usage, usage.tokens_used)
    
    def get_agent_stats(self, agent_id: str) -> TokenStats:
        """Get statistics for a specific agent"""
        return self.agent_stats.get(agent_id, TokenStats())
    
    def get_global_stats(self) -> TokenStats:
        """Get global statistics across all agents"""
        global_stats = TokenStats()
        
        for stats in self.agent_stats.values():
            global_stats.total_tokens += stats.total_tokens
            global_stats.successful_tasks += stats.successful_tasks
            global_stats.failed_tasks += stats.failed_tasks
            global_stats.peak_usage = max(global_stats.peak_usage, stats.peak_usage)
        
        total_tasks = global_stats.successful_tasks + global_stats.failed_tasks
        global_stats.average_tokens_per_task = global_stats.total_tokens / max(total_tasks, 1)
        
        return global_stats
    
    def check_budget(self, agent_id: str, requested_tokens: int) -> bool:
        """Check if agent has sufficient budget for requested tokens"""
        
        # Check global budget
        if self.global_budget:
            global_stats = self.get_global_stats()
            if global_stats.total_tokens + requested_tokens > self.global_budget:
                return False
        
        # Check agent-specific budget
        if agent_id in self.agent_budgets:
            agent_stats = self.get_agent_stats(agent_id)
            if agent_stats.total_tokens + requested_tokens > self.agent_budgets[agent_id]:
                return False
        
        return True
    
    def set_budget(self, agent_id: str, budget: int):
        """Set token budget for a specific agent"""
        self.agent_budgets[agent_id] = budget
        logger.info(f"Set {budget} token budget for agent {agent_id}")
    
    def set_global_budget(self, budget: int):
        """Set global token budget"""
        self.global_budget = budget
        logger.info(f"Set global token budget to {budget}")
    
    def get_optimization_recommendations(self, agent_id: str) -> List[str]:
        """Get optimization recommendations for an agent"""
        recommendations = []
        stats = self.get_agent_stats(agent_id)
        
        if stats.average_tokens_per_task > 800:
            recommendations.append(
                "Consider using hierarchical prompts to reduce average token usage"
            )
        
        if stats.failed_tasks / max(stats.successful_tasks + stats.failed_tasks, 1) > 0.2:
            recommendations.append(
                "High failure rate detected - consider task decomposition"
            )
        
        if stats.peak_usage > stats.average_tokens_per_task * 2:
            recommendations.append(
                "High peak usage detected - implement token pooling"
            )
        
        return recommendations
    
    def estimate_tokens_for_task(self, task_description: str, complexity: float = 0.5) -> int:
        """Estimate token usage for a task based on description and complexity"""
        # Base estimation: ~1 token per 4 characters
        base_tokens = len(task_description) // 4
        
        # Adjust for complexity
        complexity_multiplier = 1.0 + (complexity * 2.0)
        
        # Add overhead for system messages and context
        overhead = 100  # Approximate overhead
        
        estimated = int((base_tokens * complexity_multiplier) + overhead)
        
        logger.debug(f"Estimated {estimated} tokens for task: {task_description[:50]}...")
        return estimated
    
    def get_efficiency_score(self, agent_id: str) -> float:
        """Calculate efficiency score (0-1) for an agent"""
        stats = self.get_agent_stats(agent_id)
        
        if stats.total_tokens == 0:
            return 1.0
        
        # Factors: success rate, token efficiency, consistency
        success_rate = stats.successful_tasks / max(stats.successful_tasks + stats.failed_tasks, 1)
        
        # Token efficiency: lower average is better (normalized to 0-1)
        # Assuming 500 tokens is ideal average
        token_efficiency = max(0, 1 - (stats.average_tokens_per_task - 500) / 1000)
        
        # Consistency: lower peak/average ratio is better
        consistency = 1.0 - (stats.peak_usage / max(stats.average_tokens_per_task, 1) - 1) / 2
        consistency = max(0, min(1, consistency))
        
        # Weighted average
        efficiency = (success_rate * 0.4) + (token_efficiency * 0.4) + (consistency * 0.2)
        
        return round(efficiency, 3)
