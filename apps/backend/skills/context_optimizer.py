#!/usr/bin/env python3
"""
Context Optimizer for AI Agents

Implements aggressive context management based on Claude Code best practices:
- Automatic context compaction
- Checkpoint management
- Context cleanup between unrelated tasks
- Token-efficient context preservation

Features:
- Smart context compaction with priority preservation
- Checkpoint system for state recovery
- Context relevance scoring
- Automatic cleanup policies
"""

import json
import logging
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import deque
import threading

logger = logging.getLogger(__name__)


@dataclass
class ContextCheckpoint:
    """Represents a saved context state."""
    id: str
    timestamp: float
    context_hash: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'context_hash': self.context_hash,
            'data': self.data,
            'metadata': self.metadata,
            'priority': self.priority
        }


@dataclass
class ContextMetrics:
    """Metrics for context optimization."""
    total_context_size: int = 0
    compacted_size: int = 0
    compression_ratio: float = 0.0
    cleanup_frequency: int = 0
    last_cleanup: float = 0.0
    checkpoints_created: int = 0
    checkpoints_restored: int = 0
    
    def update_compression(self, original: int, compacted: int):
        self.total_context_size = original
        self.compacted_size = compacted
        self.compression_ratio = (original - compacted) / original if original > 0 else 0.0


class ContextCompactor:
    """Handles context compaction following Claude best practices."""
    
    def __init__(self, max_context_size: int = 10000, compaction_threshold: float = 0.7):
        self.max_context_size = max_context_size
        self.compaction_threshold = compaction_threshold
        self.preservation_rules = self._default_preservation_rules()
    
    def _default_preservation_rules(self) -> Dict[str, float]:
        """Default rules for context preservation priority."""
        return {
            'user_preferences': 1.0,
            'active_session': 1.0,
            'recent_errors': 0.9,
            'skill_metadata': 0.8,
            'project_context': 0.8,
            'usage_history': 0.6,
            'old_errors': 0.4,
            'debug_logs': 0.3,
            'temporary_data': 0.1
        }
    
    def compact_context(self, context: Dict[str, Any], instructions: Optional[str] = None) -> Dict[str, Any]:
        """Compact context preserving important information."""
        if not self._should_compact(context):
            return context
        
        logger.info("Starting context compaction")
        start_size = self._calculate_size(context)
        
        # Apply custom instructions if provided
        if instructions:
            compacted = self._compact_with_instructions(context, instructions)
        else:
            compacted = self._compact_default(context)
        
        end_size = self._calculate_size(compacted)
        compression_ratio = (start_size - end_size) / start_size if start_size > 0 else 0.0
        
        logger.info(f"Context compacted: {start_size} -> {end_size} bytes ({compression_ratio:.1%} reduction)")
        
        return compacted
    
    def _should_compact(self, context: Dict[str, Any]) -> bool:
        """Check if context should be compacted."""
        size = self._calculate_size(context)
        return size > self.max_context_size * self.compaction_threshold
    
    def _calculate_size(self, context: Dict[str, Any]) -> int:
        """Calculate approximate size of context."""
        return len(json.dumps(context, default=str))
    
    def _compact_default(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Default compaction strategy."""
        compacted = {}
        
        for key, value in context.items():
            priority = self.preservation_rules.get(key, 0.5)
            
            if priority >= 0.8:
                # High priority - keep as is
                compacted[key] = value
            elif priority >= 0.5:
                # Medium priority - compress
                compacted[key] = self._compress_value(value)
            elif priority >= 0.2:
                # Low priority - summarize
                compacted[key] = self._summarize_value(value)
            # Very low priority - discard
        
        return compacted
    
    def _compact_with_instructions(self, context: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """Compact context based on specific instructions."""
        compacted = {}
        
        # Parse instructions for specific preservation rules
        if "preserve" in instructions.lower():
            # Extract items to preserve from instructions
            preserve_items = self._extract_preserve_items(instructions)
            for key, value in context.items():
                if any(item in key for item in preserve_items):
                    compacted[key] = value
                else:
                    compacted[key] = self._compress_value(value)
        else:
            # Use default compaction with instruction focus
            compacted = self._compact_default(context)
            
            # Apply instruction-specific modifications
            if "api changes" in instructions.lower():
                compacted = self._focus_on_api_changes(compacted)
            elif "modified files" in instructions.lower():
                compacted = self._focus_on_modified_files(compacted)
        
        return compacted
    
    def _compress_value(self, value: Any) -> Any:
        """Compress a value while preserving essential information."""
        if isinstance(value, dict):
            compressed = {}
            for k, v in value.items():
                if isinstance(v, list) and len(v) > 10:
                    # Keep only first 5 and last 5 items
                    compressed[k] = v[:5] + v[-5:] if len(v) > 10 else v
                elif isinstance(v, str) and len(v) > 500:
                    # Truncate long strings
                    compressed[k] = v[:497] + "..."
                else:
                    compressed[k] = v
            return compressed
        elif isinstance(value, list):
            if len(value) > 10:
                return value[:5] + value[-5:] if len(value) > 10 else value
            return value
        elif isinstance(value, str) and len(value) > 500:
            return value[:497] + "..."
        
        return value
    
    def _summarize_value(self, value: Any) -> Any:
        """Create a summary of a value."""
        if isinstance(value, dict):
            return {
                'summary': f"Dictionary with {len(value)} keys",
                'keys': list(value.keys())[:5]  # First 5 keys
            }
        elif isinstance(value, list):
            return {
                'summary': f"List with {len(value)} items",
                'first_item': value[0] if value else None,
                'last_item': value[-1] if value else None
            }
        elif isinstance(value, str):
            return {
                'summary': f"String ({len(value)} chars)",
                'preview': value[:100] + "..." if len(value) > 100 else value
            }
        
        return {'type': type(value).__name__, 'summary': str(value)[:50]}
    
    def _extract_preserve_items(self, instructions: str) -> List[str]:
        """Extract items to preserve from instructions."""
        preserve_items = []
        if "preserve" in instructions.lower():
            # Simple extraction - could be enhanced with NLP
            words = instructions.lower().split()
            for i, word in enumerate(words):
                if word == "preserve" and i + 1 < len(words):
                    preserve_items.append(words[i + 1])
        return preserve_items
    
    def _focus_on_api_changes(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Focus compaction on API changes."""
        focused = {}
        for key, value in context.items():
            if any(api_term in key.lower() for api_term in ['api', 'endpoint', 'route', 'service']):
                focused[key] = value
            else:
                focused[key] = self._summarize_value(value)
        return focused
    
    def _focus_on_modified_files(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Focus compaction on modified files."""
        focused = {}
        for key, value in context.items():
            if any(file_term in key.lower() for file_term in ['file', 'modified', 'changed', 'path']):
                focused[key] = value
            else:
                focused[key] = self._summarize_value(value)
        return focused


class ContextOptimizer:
    """Main context optimizer implementing Claude best practices."""
    
    def __init__(self, max_context_size: int = 10000, checkpoint_dir: str = "context_checkpoints"):
        self.max_context_size = max_context_size
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self.compactor = ContextCompactor(max_context_size)
        self.checkpoints: Dict[str, ContextCheckpoint] = {}
        self.metrics = ContextMetrics()
        self.cleanup_lock = threading.Lock()
        
        # Cleanup policies
        self.max_checkpoints = 50
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
        
        logger.info("Context optimizer initialized")
    
    def optimize_context(self, context: Dict[str, Any], 
                        instructions: Optional[str] = None,
                        force_compaction: bool = False) -> Dict[str, Any]:
        """Optimize context for token efficiency."""
        start_time = time.time()
        
        # Check if compaction is needed
        if force_compaction or self.compactor._should_compact(context):
            optimized = self.compactor.compact_context(context, instructions)
            
            # Update metrics
            original_size = self.compactor._calculate_size(context)
            optimized_size = self.compactor._calculate_size(optimized)
            self.metrics.update_compression(original_size, optimized_size)
            
            logger.info(f"Context optimized in {time.time() - start_time:.3f}s")
            return optimized
        
        return context
    
    def create_checkpoint(self, context: Dict[str, Any], 
                         metadata: Optional[Dict[str, Any]] = None,
                         priority: float = 1.0) -> str:
        """Create a context checkpoint."""
        context_hash = self._hash_context(context)
        checkpoint_id = hashlib.md5(f"{context_hash}:{time.time()}".encode()).hexdigest()[:16]
        
        checkpoint = ContextCheckpoint(
            id=checkpoint_id,
            timestamp=time.time(),
            context_hash=context_hash,
            data=context.copy(),
            metadata=metadata or {},
            priority=priority
        )
        
        self.checkpoints[checkpoint_id] = checkpoint
        self.metrics.checkpoints_created += 1
        
        # Save to file
        self._save_checkpoint(checkpoint)
        
        # Cleanup old checkpoints
        self._cleanup_checkpoints()
        
        logger.info(f"Created checkpoint: {checkpoint_id}")
        return checkpoint_id
    
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Restore context from checkpoint."""
        if checkpoint_id in self.checkpoints:
            checkpoint = self.checkpoints[checkpoint_id]
            self.metrics.checkpoints_restored += 1
            logger.info(f"Restored checkpoint: {checkpoint_id}")
            return checkpoint.data.copy()
        
        # Try to load from file
        checkpoint = self._load_checkpoint(checkpoint_id)
        if checkpoint:
            self.checkpoints[checkpoint_id] = checkpoint
            self.metrics.checkpoints_restored += 1
            logger.info(f"Loaded checkpoint from file: {checkpoint_id}")
            return checkpoint.data
        
        logger.warning(f"Checkpoint not found: {checkpoint_id}")
        return None
    
    def cleanup_context(self, context: Dict[str, Any], task_type: Optional[str] = None) -> Dict[str, Any]:
        """Clean up context between unrelated tasks."""
        with self.cleanup_lock:
            if task_type:
                cleaned = self._cleanup_by_task_type(context, task_type)
            else:
                cleaned = self._cleanup_default(context)
            
            self.metrics.cleanup_frequency += 1
            self.metrics.last_cleanup = time.time()
            
            logger.info("Context cleanup completed")
            return cleaned
    
    def _cleanup_by_task_type(self, context: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """Clean up context based on task type."""
        # Define cleanup rules for different task types
        cleanup_rules = {
            'development': ['debug_logs', 'temporary_data', 'old_errors'],
            'analysis': ['user_preferences', 'temporary_data'],
            'migration': ['debug_logs', 'temporary_data'],
            'testing': ['old_errors', 'debug_logs']
        }
        
        cleaned = context.copy()
        remove_keys = cleanup_rules.get(task_type, [])
        
        for key in remove_keys:
            cleaned.pop(key, None)
        
        return cleaned
    
    def _cleanup_default(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Default cleanup strategy."""
        cleaned = {}
        
        for key, value in context.items():
            # Keep essential items
            if key in ['user_preferences', 'active_session', 'project_context']:
                cleaned[key] = value
            # Clean up temporary data
            elif key in ['debug_logs', 'temporary_data', 'cache']:
                if isinstance(value, dict):
                    # Keep only recent items (last hour)
                    cutoff = time.time() - 3600
                    cleaned[key] = {
                        k: v for k, v in value.items()
                        if isinstance(v, dict) and v.get('timestamp', 0) > cutoff
                    }
                else:
                    cleaned[key] = None
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Create hash of context for deduplication."""
        context_str = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(context_str.encode()).hexdigest()
    
    def _save_checkpoint(self, checkpoint: ContextCheckpoint):
        """Save checkpoint to file."""
        try:
            filepath = self.checkpoint_dir / f"{checkpoint.id}.json"
            with open(filepath, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint {checkpoint.id}: {e}")
    
    def _load_checkpoint(self, checkpoint_id: str) -> Optional[ContextCheckpoint]:
        """Load checkpoint from file."""
        try:
            filepath = self.checkpoint_dir / f"{checkpoint_id}.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    return ContextCheckpoint(
                        id=data['id'],
                        timestamp=data['timestamp'],
                        context_hash=data['context_hash'],
                        data=data['data'],
                        metadata=data.get('metadata', {}),
                        priority=data.get('priority', 1.0)
                    )
        except Exception as e:
            logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}")
        
        return None
    
    def _cleanup_checkpoints(self):
        """Clean up old checkpoints."""
        if len(self.checkpoints) <= self.max_checkpoints:
            return
        
        # Sort by priority and timestamp
        sorted_checkpoints = sorted(
            self.checkpoints.values(),
            key=lambda cp: (cp.priority, cp.timestamp),
            reverse=True
        )
        
        # Keep top checkpoints
        keep_checkpoints = sorted_checkpoints[:self.max_checkpoints]
        keep_ids = {cp.id for cp in keep_checkpoints}
        
        # Remove old checkpoints
        to_remove = [cp_id for cp_id in self.checkpoints if cp_id not in keep_ids]
        for cp_id in to_remove:
            del self.checkpoints[cp_id]
            # Remove file
            try:
                filepath = self.checkpoint_dir / f"{cp_id}.json"
                if filepath.exists():
                    filepath.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove checkpoint file {cp_id}: {e}")
        
        logger.info(f"Cleaned up {len(to_remove)} old checkpoints")
    
    def get_metrics(self) -> ContextMetrics:
        """Get optimization metrics."""
        return self.metrics
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List available checkpoints."""
        return [
            {
                'id': cp.id,
                'timestamp': cp.timestamp,
                'priority': cp.priority,
                'metadata': cp.metadata
            }
            for cp in sorted(self.checkpoints.values(), key=lambda x: x.timestamp, reverse=True)
        ]
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        if checkpoint_id in self.checkpoints:
            del self.checkpoints[checkpoint_id]
            try:
                filepath = self.checkpoint_dir / f"{checkpoint_id}.json"
                if filepath.exists():
                    filepath.unlink()
                logger.info(f"Deleted checkpoint: {checkpoint_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete checkpoint file {checkpoint_id}: {e}")
        
        return False


# Factory functions and utilities
def create_context_optimizer(max_context_size: int = 10000, 
                           checkpoint_dir: str = "context_checkpoints") -> ContextOptimizer:
    """Create a context optimizer with default settings."""
    return ContextOptimizer(max_context_size, checkpoint_dir)


def create_compaction_rule(name: str, preserve_items: List[str], 
                          compress_items: List[str], 
                          summarize_items: List[str]) -> Dict[str, float]:
    """Create a custom compaction rule."""
    rule = {}
    
    for item in preserve_items:
        rule[item] = 1.0
    
    for item in compress_items:
        rule[item] = 0.6
    
    for item in summarize_items:
        rule[item] = 0.3
    
    return rule


# Example usage
if __name__ == "__main__":
    optimizer = create_context_optimizer()
    
    # Example context
    context = {
        'user_preferences': {'theme': 'dark', 'language': 'fr'},
        'active_session': {'user_id': 'user123', 'project': 'test'},
        'debug_logs': ['log1', 'log2', 'log3'] * 100,
        'temporary_data': {'cache': 'data'} * 50,
        'skill_metadata': {'name': 'test', 'description': 'A test skill'}
    }
    
    # Optimize context
    optimized = optimizer.optimize_context(context)
    print(f"Original size: {len(json.dumps(context))}")
    print(f"Optimized size: {len(json.dumps(optimized))}")
    
    # Create checkpoint
    checkpoint_id = optimizer.create_checkpoint(optimized, {'task': 'test'})
    print(f"Created checkpoint: {checkpoint_id}")
    
    # Restore checkpoint
    restored = optimizer.restore_checkpoint(checkpoint_id)
    print(f"Restored context keys: {list(restored.keys()) if restored else 'None'}")
