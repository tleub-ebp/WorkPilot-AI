"""
Quality Integration Module
===========================

Intégration du Quality Scorer avec les plateformes (GitHub, Azure DevOps, GitLab).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .quality_badge import QualityBadgeFormatter
from .quality_scorer import QualityScore, QualityScorer


class QualityReviewIntegration:
    """Intègre le Quality Scorer dans le workflow de review."""

    def __init__(self, project_dir: Path):
        """Initialize integration."""
        self.project_dir = project_dir
        self.scorer = QualityScorer(project_dir)
        self.formatter = QualityBadgeFormatter()
        self.history_dir = project_dir / '.auto-claude' / 'quality'
        self.history_dir.mkdir(parents=True, exist_ok=True)

    async def review_pr(
        self,
        pr_diff: str,
        changed_files: list[str],
        pr_description: str,
        provider: str = 'github',
        pr_id: str = '',
    ) -> dict[str, Any]:
        """
        Review une PR et génère un rapport complet.
        
        Args:
            pr_diff: Le diff de la PR
            changed_files: Liste des fichiers modifiés
            pr_description: Description de la PR
            provider: 'github', 'azure', ou 'gitlab'
            pr_id: ID de la PR
            
        Returns:
            Dict avec score, rapport, et métadonnées
        """
        # Score la PR
        score = self.scorer.score_pr(pr_diff, changed_files, pr_description)
        
        # Génère les rapports
        markdown_report = self.formatter.generate_markdown_summary(score)
        json_report = self.formatter.generate_json_report(score)
        badge_url = self.formatter.generate_shields_badge_url(score)
        
        # Sauvegarde l'historique
        timestamp = datetime.now().isoformat()
        history_entry = {
            'timestamp': timestamp,
            'pr_id': pr_id,
            'provider': provider,
            'score': score.overall_score,
            'grade': score.grade,
            'passing': score.is_passing,
            'total_issues': score.total_issues,
            'critical_issues': score.critical_issues,
            'files': changed_files,
        }
        
        self._save_history(history_entry)
        
        # Sauvegarde le rapport
        report_path = self.history_dir / f'report_{pr_id or timestamp}.md'
        self.formatter.save_markdown_report(score, report_path)
        
        return {
            'score': score.overall_score,
            'grade': score.grade,
            'is_passing': score.is_passing,
            'total_issues': score.total_issues,
            'critical_issues': score.critical_issues,
            'markdown': markdown_report,
            'json': json_report,
            'badge_url': badge_url,
            'report_path': str(report_path),
            'timestamp': timestamp,
        }

    def _save_history(self, entry: dict[str, Any]) -> None:
        """Sauvegarde une entrée dans l'historique."""
        history_file = self.history_dir / 'history.jsonl'
        
        with history_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')

    def get_historical_scores(self, limit: int = 10) -> list[dict[str, Any]]:
        """Récupère l'historique des scores."""
        history_file = self.history_dir / 'history.jsonl'
        
        if not history_file.exists():
            return []
        
        entries = []
        with history_file.open('r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        # Retourner les plus récentes en premier
        return list(reversed(entries[-limit:]))

    def get_quality_trends(self) -> dict[str, Any]:
        """Calcule les tendances de qualité."""
        history = self.get_historical_scores(limit=100)
        
        if not history:
            return {
                'total_prs': 0,
                'average_score': 0,
                'median_score': 0,
                'best_score': 0,
                'worst_score': 0,
                'trend': 'no_data',
            }
        
        scores = [entry['score'] for entry in history]
        
        # Calculs statistiques
        avg_score = sum(scores) / len(scores)
        sorted_scores = sorted(scores)
        median_score = sorted_scores[len(sorted_scores) // 2]
        best_score = max(scores)
        worst_score = min(scores)
        
        # Tendance (comparer première moitié vs deuxième moitié)
        if len(scores) >= 4:
            first_half_avg = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            
            if second_half_avg > first_half_avg + 5:
                trend = 'improving'
            elif second_half_avg < first_half_avg - 5:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        # Distribution des grades
        grade_distribution = {}
        for entry in history:
            grade = entry.get('grade', 'Unknown')
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        return {
            'total_prs': len(history),
            'average_score': avg_score,
            'median_score': median_score,
            'best_score': best_score,
            'worst_score': worst_score,
            'trend': trend,
            'grade_distribution': grade_distribution,
            'recent_scores': scores[-10:],
        }

    def post_github_comment(self, pr_number: int, score: QualityScore) -> dict[str, Any]:
        """
        Poste un commentaire sur une PR GitHub.
        
        Note: Nécessite l'API GitHub configurée.
        """
        markdown = self.formatter.generate_markdown_summary(score)
        
        # Structure pour l'intégration GitHub
        return {
            'action': 'post_comment',
            'pr_number': pr_number,
            'body': markdown,
            'badge_url': self.formatter.generate_shields_badge_url(score),
        }

    def post_azure_thread(self, pr_id: int, score: QualityScore) -> dict[str, Any]:
        """
        Poste un thread sur une PR Azure DevOps.
        
        Note: Nécessite l'API Azure DevOps configurée.
        """
        markdown = self.formatter.generate_markdown_summary(score)
        
        # Structure pour l'intégration Azure DevOps
        return {
            'action': 'post_thread',
            'pr_id': pr_id,
            'content': markdown,
            'status': 'active' if not score.is_passing else 'closed',
        }


async def review_current_pr(
    project_dir: Path,
    changed_files: list[str],
    pr_description: str = '',
    provider: str = 'github',
    pr_id: str = '',
) -> dict[str, Any]:
    """
    Fonction helper pour reviewer la PR courante.
    
    Usage:
        result = await review_current_pr(
            Path('.'),
            ['src/main.py', 'src/utils.py'],
            'Add new feature',
            'github',
            '123'
        )
    """
    integration = QualityReviewIntegration(project_dir)
    return await integration.review_pr('', changed_files, pr_description, provider, pr_id)


def display_quality_report(score: QualityScore) -> None:
    """Affiche un rapport de qualité dans le terminal."""
    formatter = QualityBadgeFormatter()
    output = formatter.generate_terminal_output(score)
    print(output)

