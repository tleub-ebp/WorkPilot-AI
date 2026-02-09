﻿"""
Performance Profiling & Analysis
=================================

Analyse statique pour détecter les problèmes de performance potentiels.
"""

from __future__ import annotations

import ast
from pathlib import Path

from .quality_scorer import IssueSeverity, QualityCategory, QualityIssue


class PerformanceAnalyzer:
    """Analyseur de performance statique."""

    def __init__(self):
        self.issues: list[QualityIssue] = []

    def analyze_python(self, file_path: str, content: str) -> list[QualityIssue]:
        """Analyse les problèmes de performance Python."""
        issues = []
        
        try:
            tree = ast.parse(content)
            issues.extend(self._check_loops(file_path, tree, content))
            issues.extend(self._check_imports(file_path, tree))
            issues.extend(self._check_string_concat(file_path, tree, content))
            issues.extend(self._check_list_operations(file_path, tree, content))
        except SyntaxError:
            pass
        
        return issues

    def _check_loops(self, file_path: str, tree: ast.AST, content: str) -> list[QualityIssue]:
        """Détecte les loops inefficaces."""
        issues = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            # Nested loops
            if isinstance(node, (ast.For, ast.While)):
                nested_loops = self._count_nested_loops(node)
                if nested_loops >= 3:
                    issues.append(QualityIssue(
                        category=QualityCategory.COMPLEXITY,
                        severity=IssueSeverity.HIGH,
                        title=f"{nested_loops}-level nested loops detected",
                        description="Deep nested loops can cause O(n³) or worse performance",
                        file=file_path,
                        line=node.lineno,
                        suggestion="Consider refactoring to reduce nesting or use better data structures",
                    ))
                
                # Loop with append
                if isinstance(node, ast.For):
                    has_append = self._has_list_append(node)
                    if has_append:
                        # Vérifier si c'est dans une list comprehension
                        line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        if '.append(' in line and 'for' in line:
                            issues.append(QualityIssue(
                                category=QualityCategory.MAINTAINABILITY,
                                severity=IssueSeverity.LOW,
                                title="Loop with append() detected",
                                description="Consider using list comprehension for better performance",
                                file=file_path,
                                line=node.lineno,
                                suggestion="Use list comprehension: [x for x in items]",
                            ))
        
        return issues

    def _count_nested_loops(self, node: ast.AST, depth: int = 1) -> int:
        """Compte la profondeur de nesting de loops."""
        max_depth = depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                child_depth = self._count_nested_loops(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth

    def _has_list_append(self, node: ast.For) -> bool:
        """Vérifie si un loop contient .append()."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr == 'append':
                        return True
        return False

    def _check_imports(self, file_path: str, tree: ast.AST) -> list[QualityIssue]:
        """Détecte les imports inefficaces."""
        issues = []
        
        for node in ast.walk(tree):
            # Import * is bad for performance
            if isinstance(node, ast.ImportFrom):
                if any(alias.name == '*' for alias in node.names):
                    issues.append(QualityIssue(
                        category=QualityCategory.MAINTAINABILITY,
                        severity=IssueSeverity.MEDIUM,
                        title="Wildcard import detected",
                        description="Wildcard imports (from x import *) are inefficient and unclear",
                        file=file_path,
                        line=node.lineno,
                        suggestion="Import only what you need explicitly",
                    ))
        
        return issues

    def _check_string_concat(self, file_path: str, tree: ast.AST, content: str) -> list[QualityIssue]:
        """Détecte la concaténation de strings inefficace."""
        issues = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            # String concatenation in loops
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign):
                        if isinstance(child.op, ast.Add):
                            # Vérifier si c'est une string
                            line_num = child.lineno
                            if line_num <= len(lines):
                                line = lines[line_num - 1]
                                if '+=' in line and ('"' in line or "'" in line):
                                    issues.append(QualityIssue(
                                        category=QualityCategory.COMPLEXITY,
                                        severity=IssueSeverity.MEDIUM,
                                        title="String concatenation in loop",
                                        description="String concatenation in loops is O(n²) in Python",
                                        file=file_path,
                                        line=line_num,
                                        suggestion="Use list and ''.join() or io.StringIO for better performance",
                                    ))
        
        return issues

    def _check_list_operations(self, file_path: str, tree: ast.AST, content: str) -> list[QualityIssue]:
        """Détecte les opérations de liste inefficaces."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # list.index() in loop
            if 'for ' in line and '.index(' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="list.index() in loop",
                    description="list.index() is O(n), making loop O(n²)",
                    file=file_path,
                    line=i,
                    suggestion="Use dictionary or set for O(1) lookups",
                ))
            
            # in list check in loop
            if 'for ' in line and ' in ' in line and '[' in line:
                # Simple heuristic
                if line.count('in') >= 2:  # for x in ... if y in list
                    issues.append(QualityIssue(
                        category=QualityCategory.COMPLEXITY,
                        severity=IssueSeverity.MEDIUM,
                        title="'in list' check in loop",
                        description="'in list' is O(n), consider using set for O(1) lookup",
                        file=file_path,
                        line=i,
                        suggestion="Convert list to set if order doesn't matter",
                    ))
        
        return issues

    def analyze_javascript(self, file_path: str, content: str) -> list[QualityIssue]:
        """Analyse les problèmes de performance JavaScript."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # document.getElementById in loop
            if ('for' in line or 'while' in line) and 'document.getElementById' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.COMPLEXITY,
                    severity=IssueSeverity.MEDIUM,
                    title="DOM query in loop",
                    description="DOM queries in loops are slow",
                    file=file_path,
                    line=i,
                    suggestion="Cache DOM elements outside the loop",
                ))
            
            # Array operations in nested loops
            if line.count('for') >= 2 and ('.map(' in line or '.filter(' in line):
                issues.append(QualityIssue(
                    category=QualityCategory.COMPLEXITY,
                    severity=IssueSeverity.HIGH,
                    title="Array operations in nested loops",
                    description="Nested array operations can be O(n³)",
                    file=file_path,
                    line=i,
                    suggestion="Optimize algorithm or use better data structures",
                ))
            
            # Synchronous forEach with async
            if 'forEach' in line and ('async' in line or 'await' in line):
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.HIGH,
                    title="async/await in forEach",
                    description="forEach doesn't wait for async functions",
                    file=file_path,
                    line=i,
                    suggestion="Use for...of loop or Promise.all() instead",
                ))
        
        return issues

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """Analyse un fichier."""
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.py':
            return self.analyze_python(str(file_path), content)
        elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
            return self.analyze_javascript(str(file_path), content)
        
        return []


def analyze_project_performance(
    project_dir: Path,
    file_patterns: list[str] | None = None,
) -> list[QualityIssue]:
    """
    Analyse la performance d'un projet.
    
    Returns:
        Liste d'issues de performance détectées
    """
    if file_patterns is None:
        file_patterns = ['**/*.py', '**/*.js', '**/*.ts']
    analyzer = PerformanceAnalyzer()
    all_issues = []
    
    for pattern in file_patterns:
        for file in project_dir.glob(pattern):
            issues = analyzer.analyze_file(file)
            all_issues.extend(issues)
    
    return all_issues

