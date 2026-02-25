#!/usr/bin/env python3
"""
Predictive Cache for Claude Agent Skills

Implements intelligent caching based on usage patterns and ML predictions
to pre-load likely skills and optimize performance.

Features:
- Pattern-based prediction
- Usage history tracking
- Pre-loading of likely skills
- Adaptive learning
- Token optimization
"""

import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class UsagePattern:
    """Represents a usage pattern for prediction."""
    query_pattern: str
    skill_sequence: List[str]
    frequency: int = 0
    last_used: float = 0.0
    success_rate: float = 1.0
    avg_tokens: float = 0.0
    
    def update_usage(self, skills: List[str], success: bool, tokens: int):
        """Update pattern with new usage data."""
        self.skill_sequence = skills
        self.frequency += 1
        self.last_used = time.time()
        
        # Update success rate with exponential moving average
        alpha = 0.1  # Learning rate
        self.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * self.success_rate
        
        # Update average tokens
        self.avg_tokens = alpha * tokens + (1 - alpha) * self.avg_tokens


@dataclass
class PredictionResult:
    """Result of skill prediction."""
    predicted_skills: List[str]
    confidence: float
    reasoning: str
    tokens_saved: int = 0


class SimplePatternMatcher:
    """Lightweight pattern matching for skill prediction."""
    
    def __init__(self):
        self.patterns: Dict[str, UsagePattern] = {}
        self.query_history: deque = deque(maxlen=1000)  # Last 1000 queries
        self.skill_transitions: defaultdict = defaultdict(lambda: defaultdict(int))
        
    def add_usage(self, query: str, skills: List[str], success: bool = True, tokens: int = 0):
        """Add usage data for learning."""
        # Normalize query for pattern matching
        normalized_query = self._normalize_query(query)
        
        # Update or create pattern
        if normalized_query not in self.patterns:
            self.patterns[normalized_query] = UsagePattern(
                query_pattern=normalized_query,
                skill_sequence=skills
            )
        else:
            self.patterns[normalized_query].update_usage(skills, success, tokens)
        
        # Track transitions between skills
        for i in range(len(skills) - 1):
            self.skill_transitions[skills[i]][skills[i + 1]] += 1
        
        # Add to history
        self.query_history.append((query, skills, time.time()))
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching."""
        # Convert to lowercase
        normalized = query.lower()
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'is', 'are', 'was', 'were'}
        words = [word for word in normalized.split() if word not in stop_words]
        
        # Extract key terms (frameworks, actions, etc.)
        key_terms = []
        for word in words:
            if len(word) > 2:  # Skip very short words
                key_terms.append(word)
        
        return ' '.join(sorted(key_terms))  # Sort for consistent ordering
    
    def predict_next_skills(self, query: str, context: Optional[Dict] = None) -> PredictionResult:
        """Predict likely next skills based on patterns."""
        normalized_query = self._normalize_query(query)
        
        # Direct pattern match
        if normalized_query in self.patterns:
            pattern = self.patterns[normalized_query]
            return PredictionResult(
                predicted_skills=pattern.skill_sequence.copy(),
                confidence=min(0.9, pattern.frequency / 10.0),  # Cap at 90%
                reasoning=f"Direct pattern match (frequency: {pattern.frequency})",
                tokens_saved=int(pattern.avg_tokens * 0.7)  # Estimate 70% token savings
            )
        
        # Partial pattern matching
        best_match = None
        best_score = 0.0
        
        for pattern_name, pattern in self.patterns.items():
            score = self._calculate_similarity(normalized_query, pattern_name)
            if score > best_score and score > 0.3:  # Minimum similarity threshold
                best_score = score
                best_match = pattern
        
        if best_match:
            return PredictionResult(
                predicted_skills=best_match.skill_sequence.copy(),
                confidence=best_score * 0.7,  # Reduce confidence for partial matches
                reasoning=f"Partial pattern match (similarity: {best_score:.2f})",
                tokens_saved=int(best_match.avg_tokens * 0.5)
            )
        
        # Context-based prediction
        if context and 'recent_skills' in context:
            recent_skills = context['recent_skills']
            if recent_skills:
                # Predict next skill based on transitions
                last_skill = recent_skills[-1]
                if last_skill in self.skill_transitions:
                    transitions = self.skill_transitions[last_skill]
                    most_likely = max(transitions.items(), key=lambda x: x[1])
                    return PredictionResult(
                        predicted_skills=[most_likely[0]],
                        confidence=0.4,
                        reasoning=f"Transition prediction from {last_skill}",
                        tokens_saved=50  # Estimate
                    )
        
        # Default prediction
        return PredictionResult(
            predicted_skills=[],
            confidence=0.0,
            reasoning="No pattern found",
            tokens_saved=0
        )
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two normalized queries."""
        words1 = set(query1.split())
        words2 = set(query2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


class PredictiveCache:
    """Intelligent caching system with prediction capabilities."""
    
    def __init__(self, max_cache_size: int = 100, prediction_threshold: float = 0.5):
        self.max_cache_size = max_cache_size
        self.prediction_threshold = prediction_threshold
        
        # Cache storage
        self.skill_cache: Dict[str, Any] = {}
        self.cache_metadata: Dict[str, Dict] = {}
        
        # Prediction system
        self.pattern_matcher = SimplePatternMatcher()
        self.prediction_stats = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'tokens_saved': 0
        }
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.prediction_hits = 0
        
    def get_skill(self, skill_name: str) -> Optional[Any]:
        """Get skill from cache with tracking."""
        if skill_name in self.skill_cache:
            self.cache_hits += 1
            self.cache_metadata[skill_name]['last_access'] = time.time()
            self.cache_metadata[skill_name]['access_count'] += 1
            return self.skill_cache[skill_name]
        
        self.cache_misses += 1
        return None
    
    def cache_skill(self, skill_name: str, skill_data: Any, tokens_used: int = 0):
        """Cache skill data with metadata."""
        # Check cache size limit
        if len(self.skill_cache) >= self.max_cache_size:
            self._evict_least_used()
        
        self.skill_cache[skill_name] = skill_data
        self.cache_metadata[skill_name] = {
            'cached_at': time.time(),
            'last_access': time.time(),
            'access_count': 1,
            'tokens_used': tokens_used
        }
    
    def predict_and_preload(self, query: str, skill_loader, context: Optional[Dict] = None) -> List[str]:
        """Predict likely skills and preload them."""
        prediction = self.pattern_matcher.predict_next_skills(query, context)
        
        if prediction.confidence >= self.prediction_threshold:
            logger.info(f"Preloading {len(prediction.predicted_skills)} skills with confidence {prediction.confidence:.2f}")
            
            preloaded_skills = []
            for skill_name in prediction.predicted_skills:
                if skill_name not in self.skill_cache:
                    try:
                        skill_data = skill_loader(skill_name)
                        self.cache_skill(skill_name, skill_data)
                        preloaded_skills.append(skill_name)
                        self.prediction_hits += 1
                    except Exception as e:
                        logger.warning(f"Failed to preload skill {skill_name}: {e}")
            
            # Update prediction stats
            self.prediction_stats['total_predictions'] += 1
            if preloaded_skills:
                self.prediction_stats['successful_predictions'] += 1
                self.prediction_stats['tokens_saved'] += prediction.tokens_saved
            
            return preloaded_skills
        
        return []
    
    def record_usage(self, query: str, skills_used: List[str], success: bool = True, tokens_used: int = 0):
        """Record usage for learning and optimization."""
        self.pattern_matcher.add_usage(query, skills_used, success, tokens_used)
        
        # Update cache metadata for used skills
        for skill_name in skills_used:
            if skill_name in self.cache_metadata:
                self.cache_metadata[skill_name]['last_used'] = time.time()
                self.cache_metadata[skill_name]['usage_count'] = self.cache_metadata[skill_name].get('usage_count', 0) + 1
    
    def _evict_least_used(self):
        """Evict least used skill from cache."""
        if not self.cache_metadata:
            return
        
        # Find skill with lowest usage score
        worst_skill = min(
            self.cache_metadata.items(),
            key=lambda x: self._calculate_usage_score(x[1])
        )
        
        skill_name = worst_skill[0]
        del self.skill_cache[skill_name]
        del self.cache_metadata[skill_name]
        
        logger.debug(f"Evicted skill {skill_name} from cache")
    
    def _calculate_usage_score(self, metadata: Dict) -> float:
        """Calculate usage score for eviction decisions."""
        current_time = time.time()
        time_factor = 1.0 / (1.0 + (current_time - metadata.get('last_used', 0)) / 3600)  # Decay over hours
        access_factor = metadata.get('access_count', 0) / 10.0  # Normalize access count
        
        return time_factor + access_factor
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
        
        prediction_accuracy = (
            self.prediction_stats['successful_predictions'] / 
            self.prediction_stats['total_predictions']
            if self.prediction_stats['total_predictions'] > 0 else 0.0
        )
        
        return {
            'cache_size': len(self.skill_cache),
            'max_cache_size': self.max_cache_size,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': hit_rate,
            'prediction_hits': self.prediction_hits,
            'prediction_accuracy': prediction_accuracy,
            'tokens_saved': self.prediction_stats['tokens_saved'],
            'patterns_learned': len(self.pattern_matcher.patterns),
            'cache_efficiency': self._calculate_efficiency()
        }
    
    def _calculate_efficiency(self) -> float:
        """Calculate overall cache efficiency."""
        if not self.cache_metadata:
            return 0.0
        
        total_tokens_saved = sum(meta.get('tokens_used', 0) for meta in self.cache_metadata.values())
        total_tokens_used = sum(meta.get('tokens_used', 0) for meta in self.cache_metadata.values())
        
        return total_tokens_saved / (total_tokens_used + total_tokens_saved) if (total_tokens_used + total_tokens_saved) > 0 else 0.0
    
    def optimize_cache(self):
        """Optimize cache based on usage patterns."""
        logger.info("Optimizing predictive cache...")
        
        # Remove unused skills
        unused_skills = [
            name for name, meta in self.cache_metadata.items()
            if meta.get('usage_count', 0) == 0 and 
            time.time() - meta.get('cached_at', 0) > 3600  # 1 hour old
        ]
        
        for skill_name in unused_skills:
            if skill_name in self.skill_cache:
                del self.skill_cache[skill_name]
            del self.cache_metadata[skill_name]
        
        logger.info(f"Removed {len(unused_skills)} unused skills from cache")
        
        # Pre-load high-frequency patterns
        high_freq_patterns = sorted(
            self.pattern_matcher.patterns.items(),
            key=lambda x: x[1].frequency,
            reverse=True
        )[:5]  # Top 5 patterns
        
        logger.info(f"Top patterns: {[p[0] for p in high_freq_patterns]}")
    
    def save_patterns(self, filepath: str):
        """Save learned patterns to file."""
        patterns_data = {}
        for name, pattern in self.pattern_matcher.patterns.items():
            patterns_data[name] = {
                'query_pattern': pattern.query_pattern,
                'skill_sequence': pattern.skill_sequence,
                'frequency': pattern.frequency,
                'last_used': pattern.last_used,
                'success_rate': pattern.success_rate,
                'avg_tokens': pattern.avg_tokens
            }
        
        with open(filepath, 'w') as f:
            json.dump(patterns_data, f, indent=2)
        
        logger.info(f"Saved {len(patterns_data)} patterns to {filepath}")
    
    def load_patterns(self, filepath: str):
        """Load learned patterns from file."""
        try:
            with open(filepath, 'r') as f:
                patterns_data = json.load(f)
            
            for name, data in patterns_data.items():
                pattern = UsagePattern(
                    query_pattern=data['query_pattern'],
                    skill_sequence=data['skill_sequence'],
                    frequency=data['frequency'],
                    last_used=data['last_used'],
                    success_rate=data['success_rate'],
                    avg_tokens=data['avg_tokens']
                )
                self.pattern_matcher.patterns[name] = pattern
            
            logger.info(f"Loaded {len(patterns_data)} patterns from {filepath}")
        except FileNotFoundError:
            logger.warning(f"Pattern file not found: {filepath}")
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
