"""
Hybrid Memory Manager
Intégration du système de mémoire BMAD avec les capacités autonomous
Fournit une interface unifiée pour la mémoire persistante hybride
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import hashlib

from ide_detector import IDEDetector
try:
    from memory.bmad_memory import BMADMemorySystem
except ImportError:
    # Fallback if memory module is not available
    BMADMemorySystem = None


class HybridMemoryManager:
    """Gestionnaire de mémoire hybride unifié"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        
        # Initialiser le détecteur IDE d'abord
        self.ide_detector = IDEDetector()
        self.ide_info = self.ide_detector.detect_ide(str(self.project_root))
        
        # Initialiser les systèmes de mémoire
        if BMADMemorySystem:
            self.bmad_memory = BMADMemorySystem(str(self.project_root / "_bmad" / "_memory"))
        else:
            self.bmad_memory = None
        
        # Configuration hybride
        self.config = self._load_hybrid_config()
        
        # Méta-données
        self.session_id = self._generate_session_id()
        
    def _load_hybrid_config(self) -> Dict[str, Any]:
        """Charge la configuration hybride"""
        config_path = self.project_root / "_bmad" / "_config" / "hybrid-config.json"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Configuration par défaut
        return {
            "memory_retention_days": 90,
            "auto_cleanup": True,
            "quality_threshold": 0.7,
            "parallel_processing": True,
            "ide_adaptation": True,
            "cross_project_learning": True
        }
    
    def _generate_session_id(self) -> str:
        """Génère un ID de session unique"""
        timestamp = datetime.now().isoformat()
        ide_name = self.ide_info.get('ide_name', 'generic')
        return hashlib.sha256(f"{timestamp}_{ide_name}".encode()).hexdigest()[:16]
    
    def store_decision(self, decision_type: str, decision_data: Dict[str, Any]) -> str:
        """
        Stocke une décision dans la mémoire hybride
        
        Args:
            decision_type: Type de décision (architecture, implementation, etc.)
            decision_data: Données de la décision
            
        Returns:
            ID de la décision stockée
        """
        if not self.bmad_memory:
            return "no_memory_system"
        
        # Enrichir les données avec des informations hybrides
        enhanced_data = {
            **decision_data,
            "hybrid_metadata": {
                "session_id": self.session_id,
                "ide_info": self.ide_info,
                "timestamp": datetime.now().isoformat(),
                "decision_type": decision_type,
                "quality_score": self._calculate_quality_score(decision_data),
                "cross_ide_compatible": True
            }
        }
        
        # Stocker dans la mémoire BMAD
        if decision_type == "architecture":
            return self._store_architecture_decision(enhanced_data)
        elif decision_type == "implementation":
            return self._store_implementation_decision(enhanced_data)
        elif decision_type == "sprint":
            return self._store_sprint_decision(enhanced_data)
        else:
            return self._store_generic_decision(enhanced_data)
    
    def _store_architecture_decision(self, data: Dict[str, Any]) -> str:
        """Stocke une décision architecturale"""
        from ..memory.bmad_memory import ArchitectureMemory
        
        decision = ArchitectureMemory(
            decision_id=self._generate_decision_id(),
            timestamp=datetime.now(),
            component=data.get("component", "unknown"),
            decision=data.get("decision", ""),
            autonomous_analysis=data.get("autonomous_analysis", {}),
            bmm_structured_workflow=data.get("bmm_workflow", ""),
            rationale=data.get("rationale", ""),
            stakeholders=data.get("stakeholders", []),
            quality_score=data.get("quality_score", 0.0),
            impact_assessment=data.get("impact_assessment", {})
        )
        
        if self.bmad_memory:
            self.bmad_memory.add_architecture_decision(decision)
        return decision.decision_id
    
    def _store_implementation_decision(self, data: Dict[str, Any]) -> str:
        """Stocke une décision d'implémentation"""
        if not self.bmad_memory:
            return "no_memory_system"
            
        # Créer une entrée de mémoire générique pour l'implémentation
        try:
            from ..memory.bmad_memory import MemoryEntry
        except ImportError:
            # Fallback if memory module is not available
            return "no_memory_module"
        
        entry = MemoryEntry(
            id=self._generate_decision_id(),
            timestamp=datetime.now(),
            agent_type="hybrid",
            agent_name=data.get("agent", "hybrid-agent"),
            context=data.get("context", {}),
            decision=data.get("decision", ""),
            rationale=data.get("rationale", ""),
            quality_score=data.get("quality_score", 0.0),
            tags=data.get("tags", []) + ["implementation"]
        )
        
        if self.bmad_memory:
            self.bmad_memory.add_entry(entry)
        return entry.id
    
    def _store_sprint_decision(self, data: Dict[str, Any]) -> str:
        """Stocke une décision de sprint"""
        if not self.bmad_memory:
            return "no_memory_system"
            
        # Créer une entrée de mémoire pour le sprint
        try:
            from ..memory.bmad_memory import MemoryEntry
        except ImportError:
            # Fallback if memory module is not available
            return "no_memory_module"
        
        entry = MemoryEntry(
            id=self._generate_decision_id(),
            timestamp=datetime.now(),
            agent_type="hybrid",
            agent_name=data.get("agent", "scrum-master"),
            context=data.get("context", {}),
            decision=data.get("decision", ""),
            rationale=data.get("rationale", ""),
            quality_score=data.get("quality_score", 0.0),
            tags=data.get("tags", []) + ["sprint", "planning"]
        )
        
        if self.bmad_memory:
            self.bmad_memory.add_entry(entry)
        return entry.id
    
    def _store_generic_decision(self, data: Dict[str, Any]) -> str:
        """Stocke une décision générique"""
        if not self.bmad_memory:
            return "no_memory_system"
            
        try:
            from ..memory.bmad_memory import MemoryEntry
        except ImportError:
            # Fallback if memory module is not available
            return "no_memory_module"
        
        entry = MemoryEntry(
            id=self._generate_decision_id(),
            timestamp=datetime.now(),
            agent_type="hybrid",
            agent_name=data.get("agent", "hybrid-agent"),
            context=data.get("context", {}),
            decision=data.get("decision", ""),
            rationale=data.get("rationale", ""),
            quality_score=data.get("quality_score", 0.0),
            tags=data.get("tags", [])
        )
        
        if self.bmad_memory:
            self.bmad_memory.add_entry(entry)
        return entry.id
    
    def retrieve_patterns(self, pattern_type: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Récupère les patterns pertinents de la mémoire
        
        Args:
            pattern_type: Type de pattern (architecture, implementation, sprint)
            context: Contexte pour la recherche
            
        Returns:
            Liste des patterns trouvés
        """
        if not self.bmad_memory:
            return []
        
        # Mapper le type de pattern vers la méthode appropriéecture":
            return self._retrieve_architecture_patterns(context)
        elif pattern_type == "implementation":
            return self._retrieve_implementation_patterns(context)
        elif pattern_type == "sprint":
            return self._retrieve_sprint_patterns(context)
        else:
            return self._retrieve_generic_patterns(context)
    
    def _retrieve_architecture_patterns(self, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Récupère les patterns architecturaux"""
        if not self.bmad_memory:
            return []
        
        decisions = self.bmad_memory.get_architecture_decisions(
            component=context.get("component") if context else None,
            agent_type="hybrid"
        )
        
        patterns = []
        for decision in decisions:
            pattern = {
                "id": decision.decision_id,
                "component": decision.component,
                "decision": decision.decision,
                "rationale": decision.rationale,
                "quality_score": decision.quality_score,
                "timestamp": decision.timestamp.isoformat(),
                "stakeholders": decision.stakeholders,
                "impact_assessment": decision.impact_assessment,
                "autonomous_analysis": decision.autonomous_analysis,
                "bmm_workflow": decision.bmm_structured_workflow
            }
            patterns.append(pattern)
        
        # Trier par qualité et date
        patterns.sort(key=lambda x: (x["quality_score"], x["timestamp"]), reverse=True)
        return patterns
    
    def _retrieve_implementation_patterns(self, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Récupère les patterns d'implémentation"""
        if not self.bmad_memory:
            return []
        
        # Rechercher dans les entrées de mémoire
        search_query = "implementation"
        if context:
            search_query += f" {context.get('technology', '')}"
        
        entries = self.bmad_memory.search(search_query, agent_type="hybrid")
        
        patterns = []
        for entry in entries:
            pattern = {
                "id": entry.id,
                "decision": entry.decision,
                "rationale": entry.rationale,
                "quality_score": entry.quality_score,
                "timestamp": entry.timestamp.isoformat(),
                "agent": entry.agent_name,
                "context": entry.context,
                "tags": entry.tags
            }
            patterns.append(pattern)
        
        return patterns
    
    def _retrieve_sprint_patterns(self, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Récupère les patterns de sprint"""
        if not self.bmad_memory:
            return []
        
        search_query = "sprint"
        if context:
            search_query += f" {context.get('team', '')}"
        
        entries = self.bmad_memory.search(search_query, agent_type="hybrid")
        
        patterns = []
        for entry in entries:
            pattern = {
                "id": entry.id,
                "decision": entry.decision,
                "rationale": entry.rationale,
                "quality_score": entry.quality_score,
                "timestamp": entry.timestamp.isoformat(),
                "agent": entry.agent_name,
                "context": entry.context,
                "tags": entry.tags
            }
            patterns.append(pattern)
        
        return patterns
    
    def _retrieve_generic_patterns(self, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Récupère les patterns génériques"""
        if not self.bmad_memory:
            return []
        
        search_query = ""
        if context:
            search_query = context.get("query", "")
        
        if not search_query:
            return []
        
        entries = self.bmad_memory.search(search_query, agent_type="hybrid")
        
        patterns = []
        for entry in entries:
            pattern = {
                "id": entry.id,
                "decision": entry.decision,
                "rationale": entry.rationale,
                "quality_score": entry.quality_score,
                "timestamp": entry.timestamp.isoformat(),
                "agent": entry.agent_name,
                "context": entry.context,
                "tags": entry.tags
            }
            patterns.append(pattern)
        
        return patterns
    
    def get_recommendations(self, current_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Génère des recommandations basées sur la mémoire et le contexte actuel
        
        Args:
            current_context: Contexte actuel du projet
            
        Returns:
            Liste de recommandations
        """
        if not self.bmad_memory:
            return ["No memory system available"]
        
        recommendations = []
        
        # Analyser le type de décision nécessaire
        decision_type = self._infer_decision_type(current_context)
        
        # Récupérer les patterns pertinents
        patterns = self.retrieve_patterns(decision_type, current_context)
        
        # Générer des recommandations basées sur les patterns
        if patterns:
            top_patterns = patterns[:5]  # Top 5 patterns
            
            for pattern in top_patterns:
                if pattern["quality_score"] >= self.config["quality_threshold"]:
                    recommendation = {
                        "type": "pattern_based",
                        "confidence": pattern["quality_score"],
                        "pattern_id": pattern["id"],
                        "recommendation": f"Based on similar successful {decision_type} decisions",
                        "details": pattern["decision"],
                        "rationale": pattern["rationale"],
                        "applicable_context": self._check_pattern_applicability(pattern, current_context)
                    }
                    recommendations.append(recommendation)
        
        # Ajouter des recommandations IDE-spécifiques
        ide_recommendations = self._get_ide_recommendations(current_context)
        recommendations.extend(ide_recommendations)
        
        return recommendations
    
    def _infer_decision_type(self, context: Dict[str, Any]) -> str:
        """Déduit le type de décision nécessaire basé sur le contexte"""
        context_str = str(context).lower()
        
        if any(keyword in context_str for keyword in ["architecture", "design", "structure", "technical"]):
            return "architecture"
        elif any(keyword in context_str for keyword in ["implement", "code", "develop", "story", "feature"]):
            return "implementation"
        elif any(keyword in context_str for keyword in ["sprint", "plan", "iteration", "backlog"]):
            return "sprint"
        else:
            return "generic"
    
    def _check_pattern_applicability(self, pattern: Dict[str, Any], current_context: Dict[str, Any]) -> bool:
        """Vérifie si un pattern est applicable au contexte actuel"""
        # Vérifier la compatibilité IDE
        if pattern.get("ide_specific", False):
            return False
        
        # Vérifier la pertinence temporelle
        pattern_date = datetime.fromisoformat(pattern["timestamp"])
        days_old = (datetime.now() - pattern_date).days
        
        if days_old > self.config["memory_retention_days"]:
            return False
        
        # Vérifier la pertinence du contexte
        return True
    
    def _get_ide_recommendations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Génère des recommandations spécifiques à l'IDE"""
        ide_recommendations = []
        
        ide_name = self.ide_info.get("ide_name", "generic")
        ide_features = self.ide_info.get("features", {})
        
        # Recommandations basées sur les fonctionnalités de l'IDE
        if ide_features.get("workflow_integration", False):
            ide_recommendations.append({
                "type": "ide_specific",
                "confidence": 0.9,
                "recommendation": f"Use {ide_name} workflow integration for seamless BMAD execution",
                "details": f"Your {ide_name} environment supports workflow integration"
            })
        
        if ide_features.get("multi_file_editing", False):
            ide_recommendations.append({
                "type": "ide_specific",
                "confidence": 0.8,
                "recommendation": f"Consider batch operations for multiple file edits in {ide_name}",
                "details": f"{ide_name} supports multi-file editing capabilities"
            })
        
        return ide_recommendations
    
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calcule un score de qualité pour les données"""
        score = 0.0
        
        # Facteurs de qualité
        if data.get("rationale"):
            score += 0.2
        
        if data.get("context"):
            score += 0.1
        
        if data.get("tags") and len(data["tags"]) > 0:
            score += 0.1
        
        if data.get("stakeholders"):
            score += 0.1
        
        if data.get("impact_assessment"):
            score += 0.2
        
        if data.get("quality_score"):
            # Utiliser le score existant s'il est fourni
            return min(data["quality_score"], 1.0)
        
        return min(score, 1.0)
    
    def _generate_decision_id(self) -> str:
        """Génère un ID de décision unique"""
        timestamp = datetime.now().isoformat()
        session_id = self.session_id
        return hashlib.md5(f"{timestamp}_{session_id}".encode()).hexdigest()[:16]
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la mémoire hybride"""
        if self.bmad_memory:
            bmad_stats = self.bmad_memory.get_memory_statistics()
        else:
            bmad_stats = {"entries_by_agent": {}, "total_entries": 0}
        
        # Ajouter des statistiques hybrides
        hybrid_stats = {
            **bmad_stats,
            "hybrid_info": {
                "session_id": self.session_id,
                "ide_info": self.ide_info,
                "config": self.config,
                "total_hybrid_decisions": len(bmad_stats.get("entries_by_agent", {})),
                "cross_ide_patterns": self._count_cross_ide_patterns()
            }
        }
        
        return hybrid_stats
    
    def _count_cross_ide_patterns(self) -> int:
        """Compte les patterns cross-IDE"""
        # Implémentation simple pour l'instant
        return 0
    
    def cleanup_old_memories(self) -> int:
        """Nettoie les anciennes mémoires"""
        if not self.bmad_memory:
            return 0
        
        return self.bmad_memory.cleanup_old_entries(
            days_to_keep=self.config["memory_retention_days"]
        )
    
    def export_memory(self, output_path: str = None) -> str:
        """Exporte la mémoire hybride"""
        if output_path is None:
            output_path = str(self.project_root / "_bmad-output" / "hybrid-memory-export.json")
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "ide_info": self.ide_info,
            "config": self.config,
            "statistics": self.get_memory_statistics(),
            "patterns": {
                "architecture": self._retrieve_architecture_patterns(),
                "implementation": self._retrieve_implementation_patterns(),
                "sprint": self._retrieve_sprint_patterns(),
                "generic": self._retrieve_generic_patterns()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return output_path


# Point d'entrée principal
if __name__ == "__main__":
    manager = HybridMemoryManager()
    
    # Test de la mémoire hybride
    test_decision = {
        "decision": "Use microservices architecture for scalability",
        "rationale": "Microservices provide better scalability and team autonomy",
        "component": "backend",
        "stakeholders": ["development-team", "product-team"],
        "tags": ["architecture", "microservices", "scalability"]
    }
    
    decision_id = manager.store_decision("architecture", test_decision)
    print(f"Decision stored with ID: {decision_id}")
    
    # Test de récupération de patterns
    patterns = manager.retrieve_patterns("architecture")
    print(f"Found {len(patterns)} architecture patterns")
    
    # Test de recommandations
    context = {"query": "scalable backend architecture"}
    recommendations = manager.get_recommendations(context)
    print(f"Generated {len(recommendations)} recommendations")
