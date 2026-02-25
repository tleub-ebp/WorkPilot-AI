#!/usr/bin/env python3
"""
Token Optimizer for AI Agents

Optimizes token consumption through intelligent caching, compression,
and context management following Claude Code best practices.

Features:
- Predictive caching for repeated queries
- Metadata compression and deduplication
- Token counting and budgeting
- Context reference optimization
- Smart content summarization
"""

import json
import logging
import time
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Union
from collections import defaultdict, deque
import threading
from functools import lru_cache

# Import optimization configuration
try:
    from .optimization_config import get_optimization_config, MAX_DESCRIPTION_LENGTH, MAX_TRIGGERS_COUNT, SAMPLING_THRESHOLD, COMPRESSION_THRESHOLD, PREDICTIVE_CACHE_SIZE, DEDUPLICATION_MIN_LENGTH
except ImportError:
    # Fallback for direct execution
    from optimization_config import get_optimization_config, MAX_DESCRIPTION_LENGTH, MAX_TRIGGERS_COUNT, SAMPLING_THRESHOLD, COMPRESSION_THRESHOLD, PREDICTIVE_CACHE_SIZE, DEDUPLICATION_MIN_LENGTH

logger = logging.getLogger(__name__)


@dataclass
class TokenMetrics:
    """Metrics for token optimization."""
    total_tokens: int = 0
    saved_tokens: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    compression_ratio: float = 0.0
    deduplication_ratio: float = 0.0
    
    def update_savings(self, original: int, optimized: int):
        """Update token savings metrics."""
        self.total_tokens += original
        self.saved_tokens += original - optimized
        self.compression_ratio = self.saved_tokens / self.total_tokens if self.total_tokens > 0 else 0.0
    
    def update_cache_hit(self):
        """Update cache hit metrics."""
        self.cache_hits += 1
    
    def update_cache_miss(self):
        """Update cache miss metrics."""
        self.cache_misses += 1
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


@dataclass
class CacheEntry:
    """Represents a cached entry."""
    key: str
    content: Any
    token_count: int
    timestamp: float
    access_count: int = 0
    last_access: float = 0.0
    ttl: float = 3600.0  # 1 hour default
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.timestamp > self.ttl
    
    def access(self):
        """Update access information."""
        self.access_count += 1
        self.last_access = time.time()


class TokenCounter:
    """Counts tokens in various content types."""
    
    def __init__(self):
        # Simple token approximation (can be replaced with actual tokenizer)
        self.word_pattern = re.compile(r'\b\w+\b')
        self.code_pattern = re.compile(r'\w+|[^\w\s]')
    
    def count_tokens(self, content: Union[str, Dict, List]) -> int:
        """Count tokens in content."""
        if isinstance(content, str):
            return self._count_string_tokens(content)
        elif isinstance(content, dict):
            return sum(self.count_tokens(v) for v in content.values())
        elif isinstance(content, list):
            return sum(self.count_tokens(item) for item in content)
        else:
            return len(str(content).split())
    
    def _count_string_tokens(self, text: str) -> int:
        """Count tokens in string content."""
        # Simple approximation: count words and code tokens
        words = len(self.word_pattern.findall(text))
        code_tokens = len(self.code_pattern.findall(text))
        return max(words, code_tokens)
    
    def estimate_tokens(self, content: Any) -> int:
        """Quick token estimation."""
        if isinstance(content, str):
            return len(content.split())
        elif isinstance(content, (dict, list)):
            return len(json.dumps(content, default=str).split())
        else:
            return len(str(content).split())


class ContentCompressor:
    """Compresses content to reduce token usage."""
    
    def __init__(self):
        self.compression_strategies = {
            'metadata': self._compress_metadata,
            'lists': self._compress_lists,
            'strings': self._compress_strings,
            'duplicates': self._deduplicate_content
        }
    
    def compress(self, content: Any, content_type: str = 'auto') -> Any:
        """Compress content based on type."""
        if content_type == 'auto':
            content_type = self._detect_content_type(content)
        
        if content_type in self.compression_strategies:
            return self.compression_strategies[content_type](content)
        
        return content
    
    def _detect_content_type(self, content: Any) -> str:
        """Detect content type for optimal compression."""
        if isinstance(content, dict):
            if any(key in content for key in ['name', 'description', 'metadata']):
                return 'metadata'
            return 'dict'
        elif isinstance(content, list):
            return 'lists'
        elif isinstance(content, str):
            return 'strings'
        else:
            return 'generic'
    
    def _compress_metadata(self, metadata: Dict) -> Dict:
        """Compress metadata by removing redundancy."""
        compressed = {}
        
        for key, value in metadata.items():
            if key == 'description' and isinstance(value, str):
                # Truncate long descriptions
                if len(value) > 200:
                    compressed[key] = value[:197] + "..."
                else:
                    compressed[key] = value
            elif key == 'triggers' and isinstance(value, list):
                # Limit triggers to top 5
                compressed[key] = value[:5] if len(value) > 5 else value
            elif isinstance(value, (dict, list)):
                # Recursively compress nested structures
                compressed[key] = self.compress(value)
            else:
                compressed[key] = value
        
        return compressed
    
    def _compress_lists(self, items: List) -> List:
        """Compress lists by sampling and summarization."""
        if len(items) <= 10:
            return items
        
        # Keep first 3, last 3, and 2 random middle items
        import random
        middle_start = random.randint(3, len(items) - 5)
        middle_items = items[middle_start:middle_start + 2]
        
        compressed = items[:3] + middle_items + items[-3:]
        
        # Add summary
        compressed.append({
            '_summary': f'List compressed from {len(items)} to {len(compressed)} items'
        })
        
        return compressed
    
    def _compress_strings(self, text: str) -> Union[str, Dict]:
        """Compress strings by truncation and summarization."""
        if len(text) <= 500:
            return text
        
        # Create summary for long strings
        return {
            'preview': text[:200] + "..." if len(text) > 200 else text,
            'length': len(text),
            'hash': hashlib.md5(text.encode()).hexdigest()[:8],
            '_type': 'compressed_string'
        }
    
    def _deduplicate_content(self, content: Any) -> Any:
        """Remove duplicate content."""
        if isinstance(content, dict):
            # Remove duplicate values
            seen_values = set()
            deduplicated = {}
            
            for key, value in content.items():
                value_hash = hashlib.md5(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
                if value_hash not in seen_values:
                    deduplicated[key] = value
                    seen_values.add(value_hash)
                else:
                    # Mark as duplicate
                    deduplicated[key] = f"[duplicate of existing content]"
            
            return deduplicated
        
        elif isinstance(content, list):
            # Remove duplicate items
            seen_items = set()
            deduplicated = []
            
            for item in content:
                item_hash = hashlib.md5(json.dumps(item, sort_keys=True, default=str).encode()).hexdigest()
                if item_hash not in seen_items:
                    deduplicated.append(item)
                    seen_items.add(item_hash)
            
            return deduplicated
        
        return content


class PredictiveCache:
    """Predictive caching system for repeated queries."""
    
    def __init__(self, max_size: int = 1000, ttl: float = 3600.0):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_patterns: defaultdict(str, defaultdict(int)) = defaultdict(lambda: defaultdict(int))
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached content."""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    entry.access()
                    self._update_access_pattern(key)
                    return entry.content
                else:
                    # Remove expired entry
                    del self.cache[key]
        
        return None
    
    def put(self, key: str, content: Any, token_count: int, ttl: Optional[float] = None):
        """Put content in cache."""
        with self.lock:
            # Remove old entry if exists
            if key in self.cache:
                del self.cache[key]
            
            # Check cache size limit
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            entry = CacheEntry(
                key=key,
                content=content,
                token_count=token_count,
                timestamp=time.time(),
                ttl=ttl or self.ttl
            )
            
            self.cache[key] = entry
    
    def _update_access_pattern(self, key: str):
        """Update access patterns for prediction."""
        # Simple pattern tracking - could be enhanced with ML
        parts = key.split(':')
        for i in range(len(parts)):
            pattern = ':'.join(parts[:i+1])
            self.access_patterns[pattern][key] += 1
    
    def _evict_lru(self):
        """Evict least recently used entries."""
        if not self.cache:
            return
        
        # Sort by last access time
        sorted_entries = sorted(self.cache.items(), key=lambda x: x[1].last_access)
        
        # Remove oldest 25% of entries
        remove_count = max(1, len(self.cache) // 4)
        for i in range(remove_count):
            del self.cache[sorted_entries[i][0]]
    
    def predict_cache(self, query: str) -> List[str]:
        """Predict what might be needed based on query."""
        predictions = []
        
        # Simple prediction based on query parts
        parts = query.split()
        for part in parts:
            if part in self.access_patterns:
                # Get most accessed keys for this pattern
                pattern_keys = self.access_patterns[part]
                sorted_keys = sorted(pattern_keys.items(), key=lambda x: x[1], reverse=True)
                predictions.extend([key for key, _ in sorted_keys[:3]])
        
        return list(set(predictions))[:5]  # Return top 5 unique predictions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_entries = len(self.cache)
            expired_entries = sum(1 for entry in self.cache.values() if entry.is_expired())
            total_tokens = sum(entry.token_count for entry in self.cache.values())
            
            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'valid_entries': total_entries - expired_entries,
                'total_cached_tokens': total_tokens,
                'cache_size_ratio': total_entries / self.max_size
            }


class TokenOptimizer:
    """Main token optimizer implementing all optimization strategies."""
    
    def __init__(self, cache_size: int = 1000, cache_ttl: float = 3600.0):
        self.counter = TokenCounter()
        self.compressor = ContentCompressor()
        self.cache = PredictiveCache(cache_size, cache_ttl)
        self.metrics = TokenMetrics()
        
        # Optimization settings
        self.max_token_budget = 10000
        self.compression_threshold = 0.8  # Compress when using 80% of budget
        self.reference_optimization = True
        
        logger.info("Token optimizer initialized")
    
    def optimize_content(self, content: Any, content_type: str = 'auto',
                        use_cache: bool = True, compress: bool = True) -> Tuple[Any, int]:
        """Optimize content for token efficiency."""
        original_tokens = self.counter.count_tokens(content)
        
        # Check cache first
        cache_key = self._generate_cache_key(content, content_type)
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.metrics.update_cache_hit()
                logger.debug(f"Cache hit for content type: {content_type}")
                return cached, self.counter.count_tokens(cached)
            else:
                self.metrics.update_cache_miss()
        
        # Compress content
        optimized = content
        if compress:
            optimized = self.compressor.compress(content, content_type)
        
        # Apply reference optimization
        if self.reference_optimization:
            optimized = self._optimize_references(optimized)
        
        optimized_tokens = self.counter.count_tokens(optimized)
        
        # Update metrics
        self.metrics.update_savings(original_tokens, optimized_tokens)
        
        # Cache result
        if use_cache:
            self.cache.put(cache_key, optimized, optimized_tokens)
        
        logger.debug(f"Content optimized: {original_tokens} -> {optimized_tokens} tokens")
        
        return optimized, optimized_tokens
    
    def optimize_query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Optimize query with predictive caching."""
        optimized_query = {
            'query': query,
            'context': context or {},
            'predictions': []
        }
        
        # Predict related content
        predictions = self.cache.predict_cache(query)
        optimized_query['predictions'] = predictions
        
        # Optimize context
        if context:
            optimized_context, _ = self.optimize_content(context, 'metadata')
            optimized_query['context'] = optimized_context
        
        return optimized_query
    
    def optimize_skill_metadata(self, metadata: Dict) -> Dict:
        """Optimize skill metadata specifically."""
        # Apply skill-specific optimizations
        optimized = self.compressor.compress(metadata, 'metadata')
        
        # Remove redundant fields
        redundant_fields = ['internal_id', 'temp_data', 'debug_info']
        for field in redundant_fields:
            optimized.pop(field, None)
        
        # Optimize triggers
        if 'triggers' in optimized and isinstance(optimized['triggers'], list):
            # Keep only most effective triggers
            optimized['triggers'] = optimized['triggers'][:5]
        
        # Compress description
        if 'description' in optimized and len(optimized['description']) > 300:
            optimized['description'] = optimized['description'][:297] + "..."
        
        return optimized
    
    def optimize_user_history(self, history: List[Dict], max_items: int = 100) -> List[Dict]:
        """Optimize user history by sampling and summarization."""
        if len(history) <= max_items:
            return history
        
        # Keep recent items and sample older ones
        recent_items = history[-max_items//2:]  # Keep last half
        older_items = history[:-max_items//2]
        
        # Sample older items
        if older_items:
            sample_size = max_items // 2
            step = len(older_items) // sample_size
            sampled_items = older_items[::step][:sample_size]
        else:
            sampled_items = []
        
        optimized = recent_items + sampled_items
        
        # Add summary
        optimized.append({
            '_history_summary': f'History compressed from {len(history)} to {len(optimized)} items',
            '_original_count': len(history),
            '_compression_ratio': len(optimized) / len(history)
        })
        
        return optimized
    
    def _generate_cache_key(self, content: Any, content_type: str) -> str:
        """Generate cache key for content."""
        content_hash = hashlib.md5(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()
        return f"{content_type}:{content_hash}"
    
    def _optimize_references(self, content: Any) -> Any:
        """Optimize content by using references instead of duplication."""
        if isinstance(content, dict):
            optimized = {}
            for key, value in content.items():
                if isinstance(value, str) and len(value) > 100:
                    # Replace long strings with references
                    optimized[key] = f"[ref:{hashlib.md5(value.encode()).hexdigest()[:8]}]"
                else:
                    optimized[key] = value
            return optimized
        elif isinstance(content, list):
            optimized = []
            for item in content:
                if isinstance(item, str) and len(item) > 100:
                    optimized.append(f"[ref:{hashlib.md5(item.encode()).hexdigest()[:8]}]")
                else:
                    optimized.append(item)
            return optimized
        
        return content
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        return {
            'metrics': {
                'total_tokens': self.metrics.total_tokens,
                'saved_tokens': self.metrics.saved_tokens,
                'compression_ratio': self.metrics.compression_ratio,
                'cache_hit_rate': self.metrics.cache_hit_rate,
                'cache_hits': self.metrics.cache_hits,
                'cache_misses': self.metrics.cache_misses
            },
            'cache_stats': self.cache.get_stats(),
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        if self.metrics.compression_ratio < 0.2:
            recommendations.append("Consider increasing compression threshold for better token savings")
        
        if self.metrics.cache_hit_rate < 0.5:
            recommendations.append("Cache hit rate is low, consider increasing cache size or TTL")
        
        if self.metrics.total_tokens > self.max_token_budget * 0.9:
            recommendations.append("Approaching token budget limit, consider aggressive optimization")
        
        return recommendations
    
    def clear_cache(self):
        """Clear all cached content."""
        with self.cache.lock:
            self.cache.cache.clear()
        logger.info("Cache cleared")
    
    def preload_cache(self, items: List[Tuple[str, Any]]):
        """Preload cache with common items."""
        for key, content in items:
            token_count = self.counter.count_tokens(content)
            self.cache.put(key, content, token_count)
        
        logger.info(f"Preloaded {len(items)} items in cache")


# Factory functions
def create_token_optimizer(cache_size: int = 1000, cache_ttl: float = 3600.0) -> TokenOptimizer:
    """Create token optimizer with default settings."""
    return TokenOptimizer(cache_size, cache_ttl)


def create_skill_optimizer() -> TokenOptimizer:
    """Create token optimizer optimized for skills."""
    optimizer = TokenOptimizer(cache_size=500, cache_ttl=7200.0)  # 2 hour TTL for skills
    optimizer.compression_threshold = 0.7  # More aggressive compression
    return optimizer


# Example usage
if __name__ == "__main__":
    optimizer = create_token_optimizer()
    
    # Example content
    metadata = {
        'name': 'test-skill',
        'description': 'This is a very long description that goes on and on and on and should be compressed to save tokens in the system',
        'triggers': ['trigger1', 'trigger2', 'trigger3', 'trigger4', 'trigger5', 'trigger6'],
        'metadata': {'key1': 'value1', 'key2': 'value2'}
    }
    
    # Optimize metadata
    optimized, tokens = optimizer.optimize_content(metadata, 'metadata')
    print(f"Original tokens: {optimizer.counter.count_tokens(metadata)}")
    print(f"Optimized tokens: {tokens}")
    print(f"Compression ratio: {optimizer.metrics.compression_ratio:.1%}")
    
    # Test caching
    cached_result, cached_tokens = optimizer.optimize_content(metadata, 'metadata')
    print(f"Cache hit rate: {optimizer.metrics.cache_hit_rate:.1%}")
    
    # Get optimization report
    report = optimizer.get_optimization_report()
    print(f"Optimization report: {json.dumps(report, indent=2)}")
