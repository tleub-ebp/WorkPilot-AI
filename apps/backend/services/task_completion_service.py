"""
Service de complétion de tâches
================================

Ce service gère la création automatique de PR lorsqu'une tâche passe en statut "done".

Workflow:
1. Détecte quand une tâche passe en statut "done"
2. Push la branche vers origin
3. Crée une PR pour validation humaine
4. Associe l'URL de la PR à la tâche
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

from core.worktree import WorktreeManager

logger = logging.getLogger(__name__)


class TaskCompletionResult(TypedDict):
    """Résultat de la complétion d'une tâche"""

    success: bool
    pr_url: Optional[str]
    pr_already_exists: bool
    error: Optional[str]


@dataclass
class TaskCompletionService:
    """Service de gestion de la complétion des tâches"""

    project_path: Path
    base_branch: str = "develop"

    def __post_init__(self):
        """Initialise le gestionnaire de worktree"""
        self.worktree_manager = WorktreeManager(
            project_dir=self.project_path, base_branch=self.base_branch
        )

    def complete_task(
        self,
        spec_id: str,
        task_title: str,
        task_description: Optional[str] = None,
        target_branch: Optional[str] = None,
    ) -> TaskCompletionResult:
        """
        Complète une tâche en créant une PR pour validation humaine.

        Cette méthode:
        1. Push la branche de la tâche vers origin
        2. Crée une PR vers la branche cible (develop par défaut)
        3. La PR reste ouverte pour validation humaine (pas de merge automatique)

        Args:
            spec_id: ID de la spec (correspond au nom du worktree)
            task_title: Titre de la tâche
            task_description: Description optionnelle de la tâche
            target_branch: Branche cible pour la PR (défaut: self.base_branch)

        Returns:
            TaskCompletionResult avec:
                - success: True si la PR a été créée
                - pr_url: URL de la PR créée
                - pr_already_exists: True si une PR existe déjà
                - error: Message d'erreur si échec
        """
        logger.info(
            f"[TaskCompletionService] Complétion de la tâche: {spec_id} - {task_title}"
        )

        target = target_branch or self.base_branch

        # Étape 1: Push de la branche vers origin
        logger.info("[TaskCompletionService] Push de la branche vers origin...")
        push_result = self.worktree_manager.push_branch(spec_id, force=False)

        if not push_result["success"]:
            error_msg = f"Échec du push de la branche: {push_result.get('error', 'Erreur inconnue')}"
            logger.error(f"[TaskCompletionService] {error_msg}")
            return TaskCompletionResult(
                success=False,
                pr_url=None,
                pr_already_exists=False,
                error=error_msg,
            )

        logger.info(
            f"[TaskCompletionService] Branche {push_result['branch']} poussée avec succès"
        )

        # Étape 2: Création de la PR avec template de vérification humaine
        pr_title = f"Task: {task_title}"
        pr_body = self._build_pr_body(task_title, task_description)

        logger.info(
            f"[TaskCompletionService] Création de la PR vers {target}..."
        )
        pr_result = self.worktree_manager.create_pull_request(
            spec_name=spec_id,
            target_branch=target,
            title=pr_title,
            draft=False,  # PR normale qui nécessite review
        )

        if not pr_result["success"]:
            error_msg = f"Échec de la création de la PR: {pr_result.get('error', 'Erreur inconnue')}"
            logger.error(f"[TaskCompletionService] {error_msg}")
            return TaskCompletionResult(
                success=False,
                pr_url=None,
                pr_already_exists=False,
                error=error_msg,
            )

        pr_url = pr_result.get("pr_url")
        pr_already_exists = pr_result.get("already_exists", False)

        if pr_already_exists:
            logger.info(
                f"[TaskCompletionService] PR déjà existante: {pr_url}"
            )
        else:
            logger.info(
                f"[TaskCompletionService] PR créée avec succès: {pr_url}"
            )

        return TaskCompletionResult(
            success=True,
            pr_url=pr_url,
            pr_already_exists=pr_already_exists,
            error=None,
        )

    def _build_pr_body(
        self, task_title: str, task_description: Optional[str]
    ) -> str:
        """
        Construit le corps de la PR avec checklist de vérification humaine.

        Args:
            task_title: Titre de la tâche
            task_description: Description optionnelle de la tâche

        Returns:
            Corps formaté de la PR en Markdown
        """
        body_parts = [
            "## 🤖 Tâche terminée - Vérification humaine requise",
            "",
            f"**Tâche:** {task_title}",
        ]

        if task_description:
            body_parts.extend(["", f"**Description:** {task_description}"])

        body_parts.extend(
            [
                "",
                "### ✅ Checklist de vérification",
                "- [ ] Le code respecte les standards du projet",
                "- [ ] Les tests passent (si applicables)",
                "- [ ] La documentation est à jour",
                "- [ ] Les changements sont cohérents avec la tâche",
                "- [ ] Aucune régression détectée",
                "",
                "---",
                "⚠️ **Cette PR nécessite une validation humaine avant merge**",
                "",
                "_PR créée automatiquement par Auto-Claude_",
            ]
        )

        return "\n".join(body_parts)


def create_task_completion_service(
    project_path: str | Path, base_branch: str = "develop"
) -> TaskCompletionService:
    """
    Factory pour créer un service de complétion de tâches.

    Args:
        project_path: Chemin du projet Git
        base_branch: Branche de base (défaut: "develop")

    Returns:
        Instance de TaskCompletionService
    """
    return TaskCompletionService(
        project_path=Path(project_path), base_branch=base_branch
    )