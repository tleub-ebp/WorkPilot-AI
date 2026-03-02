"""
Conflict Predictor Service

Analyzes active worktrees and branches to detect potential conflicts
before they occur. Provides proactive conflict detection and resolution strategies.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import re

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from core.model_info import get_current_model_info


@dataclass
class FileModification:
    """Represents a file modification in a worktree"""
    file_path: str
    modification_type: str  # 'added', 'modified', 'deleted', 'renamed'
    lines_added: int
    lines_removed: int
    worktree_name: str
    branch_name: str


@dataclass
class ConflictRisk:
    """Represents a potential conflict between two modifications"""
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    conflict_type: str  # 'same_file', 'overlapping_changes', 'dependency_conflict'
    file_path: str
    worktree1: str
    worktree2: str
    branch1: str
    branch2: str
    description: str
    resolution_strategy: str


@dataclass
class ConflictAnalysisResult:
    """Result of conflict prediction analysis"""
    total_worktrees: int
    active_worktrees: List[str]
    conflicts_detected: List[ConflictRisk]
    modified_files: List[FileModification]
    recommendations: List[str]
    safe_merge_order: List[str]
    high_risk_areas: List[str]


class ConflictPredictorService:
    """
    Service for predicting potential conflicts between worktrees and branches.
    """
    
    def __init__(self):
        self.model_info = get_current_model_info()
    
    def analyze_project_conflicts(self, project_path: str) -> ConflictAnalysisResult:
        """
        Analyze a project for potential conflicts between active worktrees.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            ConflictAnalysisResult with detailed conflict analysis
        """
        if not project_path or not os.path.exists(project_path):
            raise ValueError(f"Invalid project path: {project_path}")
        
        # Get all worktrees and their modifications
        worktrees = self._get_active_worktrees(project_path)
        modified_files = self._get_modified_files_from_worktrees(project_path, worktrees)
        
        # Detect conflicts between modifications
        conflicts = self._detect_conflicts(modified_files)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(conflicts, modified_files)
        
        # Determine safe merge order
        safe_order = self._determine_safe_merge_order(conflicts, worktrees)
        
        # Identify high risk areas
        high_risk_areas = self._identify_high_risk_areas(conflicts, modified_files)
        
        return ConflictAnalysisResult(
            total_worktrees=len(worktrees),
            active_worktrees=worktrees,
            conflicts_detected=conflicts,
            modified_files=modified_files,
            recommendations=recommendations,
            safe_merge_order=safe_order,
            high_risk_areas=high_risk_areas
        )
    
    def _get_active_worktrees(self, project_path: str) -> List[str]:
        """Get list of active worktrees for the project"""
        worktrees = []
        
        try:
            # Get git worktrees
            result = subprocess.run(
                ['git', 'worktree', 'list'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        # Extract worktree path (first part of each line)
                        worktree_path = line.split()[0]
                        worktrees.append(os.path.basename(worktree_path))
            
            # Also check for common branch names in the main repo
            result = subprocess.run(
                ['git', 'branch', '-a'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    branch = line.strip().replace('* ', '').replace('remotes/origin/', '')
                    if branch and branch not in ['main', 'master', 'develop'] and branch not in worktrees:
                        worktrees.append(branch)
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            # Git operations failed, return empty list
            pass
        
        return worktrees
    
    def _get_modified_files_from_worktrees(self, project_path: str, worktrees: List[str]) -> List[FileModification]:
        """Get modified files from all worktrees"""
        modifications = []
        
        for worktree in worktrees:
            try:
                # Get diff for the worktree/branch
                worktree_mods = self._get_worktree_modifications(project_path, worktree)
                modifications.extend(worktree_mods)
            except Exception:
                # Skip worktree if we can't analyze it
                continue
        
        return modifications
    
    def _get_worktree_modifications(self, project_path: str, worktree_name: str) -> List[FileModification]:
        """Get modifications for a specific worktree"""
        modifications = []
        
        try:
            # Get the branch name (worktree name is often the branch name)
            branch_name = worktree_name
            
            # Get diff against main branch
            result = subprocess.run(
                ['git', 'diff', '--name-status', 'main..' + branch_name],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            status = parts[0]
                            file_path = parts[1]
                            
                            # Get detailed line changes
                            lines_added, lines_removed = self._get_line_changes(project_path, branch_name, file_path)
                            
                            modification_type = self._parse_git_status(status)
                            
                            modifications.append(FileModification(
                                file_path=file_path,
                                modification_type=modification_type,
                                lines_added=lines_added,
                                lines_removed=lines_removed,
                                worktree_name=worktree_name,
                                branch_name=branch_name
                            ))
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return modifications
    
    def _parse_git_status(self, status: str) -> str:
        """Parse git status character to modification type"""
        status_map = {
            'A': 'added',
            'M': 'modified',
            'D': 'deleted',
            'R': 'renamed',
            'C': 'copied',
            'T': 'type_changed',
            'U': 'unmerged'
        }
        return status_map.get(status, 'modified')
    
    def _get_line_changes(self, project_path: str, branch: str, file_path: str) -> Tuple[int, int]:
        """Get number of lines added/removed for a file"""
        try:
            result = subprocess.run(
                ['git', 'diff', '--numstat', 'main..' + branch, '--', file_path],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            added = int(parts[0]) if parts[0] != '-' else 0
                            removed = int(parts[1]) if parts[1] != '-' else 0
                            return added, removed
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, ValueError):
            pass
        
        return 0, 0
    
    def _detect_conflicts(self, modifications: List[FileModification]) -> List[ConflictRisk]:
        """Detect potential conflicts between modifications"""
        conflicts = []
        
        # Group modifications by file
        file_mods = {}
        for mod in modifications:
            if mod.file_path not in file_mods:
                file_mods[mod.file_path] = []
            file_mods[mod.file_path].append(mod)
        
        # Check for conflicts in each file
        for file_path, mods in file_mods.items():
            if len(mods) > 1:
                # Multiple worktrees modifying the same file
                for i in range(len(mods)):
                    for j in range(i + 1, len(mods)):
                        mod1, mod2 = mods[i], mods[j]
                        
                        conflict = self._analyze_file_conflict(mod1, mod2, file_path)
                        if conflict:
                            conflicts.append(conflict)
        
        # Check for dependency conflicts
        dependency_conflicts = self._detect_dependency_conflicts(modifications)
        conflicts.extend(dependency_conflicts)
        
        return conflicts
    
    def _analyze_file_conflict(self, mod1: FileModification, mod2: FileModification, file_path: str) -> Optional[ConflictRisk]:
        """Analyze conflict between two modifications to the same file"""
        
        # Same file modifications are always a risk
        risk_level = 'medium'
        conflict_type = 'same_file'
        description = f"Both {mod1.worktree_name} and {mod2.worktree_name} are modifying {file_path}"
        resolution_strategy = "Merge sequentially or coordinate changes"
        
        # Increase risk based on modification types
        if mod1.modification_type == 'deleted' or mod2.modification_type == 'deleted':
            risk_level = 'high'
            conflict_type = 'deletion_conflict'
            description += f" - One worktree is deleting the file"
            resolution_strategy = "Clarify if file should be deleted or preserved"
        
        # Check for extensive changes
        total_changes = mod1.lines_added + mod1.lines_removed + mod2.lines_added + mod2.lines_removed
        if total_changes > 100:
            risk_level = 'critical'
            conflict_type = 'extensive_overlap'
            description += f" - Extensive overlapping changes ({total_changes} lines)"
            resolution_strategy = "Consider rebasing one branch or creating integration branch"
        
        return ConflictRisk(
            risk_level=risk_level,
            conflict_type=conflict_type,
            file_path=file_path,
            worktree1=mod1.worktree_name,
            worktree2=mod2.worktree_name,
            branch1=mod1.branch_name,
            branch2=mod2.branch_name,
            description=description,
            resolution_strategy=resolution_strategy
        )
    
    def _detect_dependency_conflicts(self, modifications: List[FileModification]) -> List[ConflictRisk]:
        """Detect conflicts in dependencies and shared modules"""
        conflicts = []
        
        # Group by file extensions to identify related files
        config_files = [mod for mod in modifications if self._is_config_file(mod.file_path)]
        dependency_files = [mod for mod in modifications if self._is_dependency_file(mod.file_path)]
        
        # Check for multiple config file modifications
        if len(config_files) > 1:
            for i in range(len(config_files)):
                for j in range(i + 1, len(config_files)):
                    mod1, mod2 = config_files[i], config_files[j]
                    
                    conflicts.append(ConflictRisk(
                        risk_level='high',
                        conflict_type='dependency_conflict',
                        file_path=f"config_files: {mod1.file_path}, {mod2.file_path}",
                        worktree1=mod1.worktree_name,
                        worktree2=mod2.worktree_name,
                        branch1=mod1.branch_name,
                        branch2=mod2.branch_name,
                        description=f"Configuration changes in multiple worktrees may conflict",
                        resolution_strategy="Coordinate configuration changes or use environment-specific configs"
                    ))
        
        # Check for dependency file conflicts
        if len(dependency_files) > 1:
            for i in range(len(dependency_files)):
                for j in range(i + 1, len(dependency_files)):
                    mod1, mod2 = dependency_files[i], dependency_files[j]
                    
                    conflicts.append(ConflictRisk(
                        risk_level='medium',
                        conflict_type='dependency_conflict',
                        file_path=f"dependencies: {mod1.file_path}, {mod2.file_path}",
                        worktree1=mod1.worktree_name,
                        worktree2=mod2.worktree_name,
                        branch1=mod1.branch_name,
                        branch2=mod2.branch_name,
                        description=f"Dependency updates may conflict between worktrees",
                        resolution_strategy="Merge dependency changes first, then feature changes"
                    ))
        
        return conflicts
    
    def _is_config_file(self, file_path: str) -> bool:
        """Check if file is a configuration file"""
        config_patterns = [
            r'\.env',
            r'\.config\.',
            r'package\.json',
            r'pom\.xml',
            r'build\.gradle',
            r'cargo\.toml',
            r'settings\.',
            r'config/',
            r'etc/',
            r'\.yml$',
            r'\.yaml$',
            r'\.toml$',
            r'\.ini$'
        ]
        
        for pattern in config_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        return False
    
    def _is_dependency_file(self, file_path: str) -> bool:
        """Check if file is a dependency management file"""
        dependency_patterns = [
            r'package\.json',
            r'package-lock\.json',
            r'yarn\.lock',
            r'pnpm-lock\.yaml',
            r'requirements\.txt',
            r'Pipfile',
            r'poetry\.lock',
            r'pom\.xml',
            r'build\.gradle',
            r'cargo\.toml',
            r'composer\.json',
            r'Gemfile',
            r'go\.mod'
        ]
        
        for pattern in dependency_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        return False
    
    def _generate_recommendations(self, conflicts: List[ConflictRisk], modifications: List[FileModification]) -> List[str]:
        """Generate recommendations based on conflict analysis"""
        recommendations = []
        
        if not conflicts:
            recommendations.append("No conflicts detected - safe to proceed with parallel development")
            return recommendations
        
        # Count risk levels
        critical_count = len([c for c in conflicts if c.risk_level == 'critical'])
        high_count = len([c for c in conflicts if c.risk_level == 'high'])
        medium_count = len([c for c in conflicts if c.risk_level == 'medium'])
        
        # Generate based on risk levels
        if critical_count > 0:
            recommendations.append(f"URGENT: {critical_count} critical conflicts detected - immediate coordination required")
            recommendations.append("Consider creating an integration branch to resolve conflicts")
        
        if high_count > 0:
            recommendations.append(f"High priority: {high_count} high-risk conflicts need attention")
            recommendations.append("Schedule a sync meeting between teams working on conflicting areas")
        
        if medium_count > 0:
            recommendations.append(f"{medium_count} medium-risk conflicts - monitor during development")
        
        # Specific recommendations based on conflict types
        dependency_conflicts = [c for c in conflicts if c.conflict_type == 'dependency_conflict']
        if dependency_conflicts:
            recommendations.append("Coordinate dependency updates in a dedicated branch first")
        
        same_file_conflicts = [c for c in conflicts if c.conflict_type == 'same_file']
        if same_file_conflicts:
            recommendations.append("Use feature flags or create integration branches for shared file modifications")
        
        # General recommendations
        recommendations.append("Set up regular sync meetings between parallel workstreams")
        recommendations.append("Consider using a shared integration branch for coordinated changes")
        recommendations.append("Implement automated conflict detection in CI/CD pipeline")
        
        return recommendations
    
    def _determine_safe_merge_order(self, conflicts: List[ConflictRisk], worktrees: List[str]) -> List[str]:
        """Determine safe order for merging worktrees"""
        if not conflicts:
            return worktrees
        
        # Create conflict graph
        conflict_graph = {}
        for worktree in worktrees:
            conflict_graph[worktree] = set()
        
        for conflict in conflicts:
            conflict_graph[conflict.worktree1].add(conflict.worktree2)
            conflict_graph[conflict.worktree2].add(conflict.worktree1)
        
        # Simple heuristic: worktrees with fewer conflicts first
        worktree_conflict_counts = {
            worktree: len(conflict_graph[worktree])
            for worktree in worktrees
        }
        
        sorted_worktrees = sorted(
            worktrees,
            key=lambda w: (worktree_conflict_counts[w], w)
        )
        
        return sorted_worktrees
    
    def _identify_high_risk_areas(self, conflicts: List[ConflictRisk], modifications: List[FileModification]) -> List[str]:
        """Identify high-risk areas in the codebase"""
        high_risk_areas = []
        
        # Areas with multiple conflicts
        conflict_areas = {}
        for conflict in conflicts:
            area = conflict.file_path
            if area not in conflict_areas:
                conflict_areas[area] = 0
            conflict_areas[area] += 1
        
        # Sort by conflict count
        sorted_areas = sorted(
            conflict_areas.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for area, count in sorted_areas[:5]:  # Top 5 areas
            high_risk_areas.append(f"{area} ({count} conflicts)")
        
        # Areas with extensive changes
        extensive_changes = [
            mod.file_path
            for mod in modifications
            if (mod.lines_added + mod.lines_removed) > 50
        ]
        
        for area in extensive_changes[:3]:  # Top 3 extensive changes
            if area not in high_risk_areas:
                high_risk_areas.append(f"{area} (extensive changes)")
        
        return high_risk_areas


# Global service instance
_conflict_predictor_service = ConflictPredictorService()


def get_conflict_predictor_service() -> ConflictPredictorService:
    """Get the global conflict predictor service instance."""
    return _conflict_predictor_service
