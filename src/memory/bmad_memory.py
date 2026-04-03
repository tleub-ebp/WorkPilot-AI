"""
BMAD Hybrid Memory System
Système de mémoire persistante pour les agents hybrides autonomous+BMAD
Combine l'exécution autonome avec la structuration agile de BMAD
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    """Entrée de mémoire hybride EBP+BMAD"""
    id: str
    timestamp: datetime
    agent_type: str  # 'ebp', 'bmm', 'hybrid'
    agent_name: str
    context: dict[str, Any]
    decision: str
    rationale: str
    quality_score: float
    tags: list[str]
    related_entries: list[str] = None
    
    def __post_init__(self):
        if self.related_entries is None:
            self.related_entries = []


@dataclass
class PerformanceMemory:
    """Mémoire des patterns de performance"""
    pattern_id: str
    timestamp: datetime
    scenario: str
    optimization: str
    results: dict[str, float]
    ebp_analysis: dict[str, Any]
    bmm_workflow: str
    quality_score: float
    applicable_contexts: list[str]


@dataclass
class ArchitectureMemory:
    """Mémoire des décisions architecturales"""
    decision_id: str
    timestamp: datetime
    component: str
    decision: str
    ebp_autonomous_analysis: dict[str, Any]
    bmm_structured_workflow: str
    rationale: str
    stakeholders: list[str]
    quality_score: float
    impact_assessment: dict[str, Any]


@dataclass
class WorkflowMemory:
    """Mémoire des workflows BMAD"""
    workflow_id: str
    timestamp: datetime
    workflow_type: str
    duration: timedelta
    participants: list[str]
    outcomes: list[str]
    autonomous_contributions: list[str]
    success_metrics: dict[str, float]
    lessons_learned: list[str]


class BMADMemorySystem:
    """Système de mémoire hybride principal"""
    
    def __init__(self, memory_path: str = None):
        self.memory_path = Path(memory_path or ".bmad/memory")
        self.memory_path.mkdir(parents=True, exist_ok=True)
        
        # Fichiers de mémoire
        self.entries_file = self.memory_path / "entries.json"
        self.performance_file = self.memory_path / "performance.json"
        self.architecture_file = self.memory_path / "architecture.json"
        self.workflows_file = self.memory_path / "workflows.json"
        self.index_file = self.memory_path / "index.json"
        
        # Structures de mémoire
        self.entries: list[MemoryEntry] = []
        self.performance_patterns: list[PerformanceMemory] = []
        self.architecture_decisions: list[ArchitectureMemory] = []
        self.workflow_history: list[WorkflowMemory] = []
        self.search_index: dict[str, list[str]] = {}
        
        # Charger mémoire existante
        self.load_memory()
        
    def load_memory(self):
        """Charge la mémoire depuis les fichiers"""
        try:
            if self.entries_file.exists():
                with open(self.entries_file, encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [
                        MemoryEntry(
                            id=entry['id'],
                            timestamp=datetime.fromisoformat(entry['timestamp']),
                            agent_type=entry['agent_type'],
                            agent_name=entry['agent_name'],
                            context=entry['context'],
                            decision=entry['decision'],
                            rationale=entry['rationale'],
                            quality_score=entry['quality_score'],
                            tags=entry['tags'],
                            related_entries=entry.get('related_entries', [])
                        )
                        for entry in data
                    ]
        except Exception as e:
            print(f"Erreur chargement entrées: {e}")
            
        try:
            if self.performance_file.exists():
                with open(self.performance_file, encoding='utf-8') as f:
                    data = json.load(f)
                    self.performance_patterns = [
                        PerformanceMemory(
                            pattern_id=entry['pattern_id'],
                            timestamp=datetime.fromisoformat(entry['timestamp']),
                            scenario=entry['scenario'],
                            optimization=entry['optimization'],
                            results=entry['results'],
                            ebp_analysis=entry['ebp_analysis'],
                            bmm_workflow=entry['bmm_workflow'],
                            quality_score=entry['quality_score'],
                            applicable_contexts=entry['applicable_contexts']
                        )
                        for entry in data
                    ]
        except Exception as e:
            print(f"Erreur chargement performance: {e}")
            
        try:
            if self.architecture_file.exists():
                with open(self.architecture_file, encoding='utf-8') as f:
                    data = json.load(f)
                    self.architecture_decisions = [
                        ArchitectureMemory(
                            decision_id=entry['decision_id'],
                            timestamp=datetime.fromisoformat(entry['timestamp']),
                            component=entry['component'],
                            decision=entry['decision'],
                            ebp_autonomous_analysis=entry['ebp_autonomous_analysis'],
                            bmm_structured_workflow=entry['bmm_structured_workflow'],
                            rationale=entry['rationale'],
                            stakeholders=entry['stakeholders'],
                            quality_score=entry['quality_score'],
                            impact_assessment=entry['impact_assessment']
                        )
                        for entry in data
                    ]
        except Exception as e:
            print(f"Erreur chargement architecture: {e}")
            
        try:
            if self.workflows_file.exists():
                with open(self.workflows_file, encoding='utf-8') as f:
                    data = json.load(f)
                    self.workflow_history = [
                        WorkflowMemory(
                            workflow_id=entry['workflow_id'],
                            timestamp=datetime.fromisoformat(entry['timestamp']),
                            workflow_type=entry['workflow_type'],
                            duration=timedelta(seconds=entry['duration_seconds']),
                            participants=entry['participants'],
                            outcomes=entry['outcomes'],
                            ebp_contributions=entry['ebp_contributions'],
                            success_metrics=entry['success_metrics'],
                            lessons_learned=entry['lessons_learned']
                        )
                        for entry in data
                    ]
        except Exception as e:
            print(f"Erreur chargement workflows: {e}")
            
        try:
            if self.index_file.exists():
                with open(self.index_file, encoding='utf-8') as f:
                    self.search_index = json.load(f)
        except Exception as e:
            print(f"Erreur chargement index: {e}")
            
        # Reconstruire index si nécessaire
        if not self.search_index:
            self.rebuild_search_index()
    
    def save_memory(self):
        """Sauvegarde la mémoire dans les fichiers"""
        try:
            # Sauvegarder les entrées
            entries_data = []
            for entry in self.entries:
                entry_dict = asdict(entry)
                entry_dict['timestamp'] = entry.timestamp.isoformat()
                entries_data.append(entry_dict)
            
            with open(self.entries_file, 'w', encoding='utf-8') as f:
                json.dump(entries_data, f, indent=2, ensure_ascii=False)
                
            # Sauvegarder les patterns de performance
            performance_data = []
            for pattern in self.performance_patterns:
                pattern_dict = asdict(pattern)
                pattern_dict['timestamp'] = pattern.timestamp.isoformat()
                performance_data.append(pattern_dict)
            
            with open(self.performance_file, 'w', encoding='utf-8') as f:
                json.dump(performance_data, f, indent=2, ensure_ascii=False)
                
            # Sauvegarder les décisions architecturales
            architecture_data = []
            for decision in self.architecture_decisions:
                decision_dict = asdict(decision)
                decision_dict['timestamp'] = decision.timestamp.isoformat()
                architecture_data.append(decision_dict)
            
            with open(self.architecture_file, 'w', encoding='utf-8') as f:
                json.dump(architecture_data, f, indent=2, ensure_ascii=False)
                
            # Sauvegarder les workflows
            workflows_data = []
            for workflow in self.workflow_history:
                workflow_dict = asdict(workflow)
                workflow_dict['timestamp'] = workflow.timestamp.isoformat()
                workflow_dict['duration_seconds'] = workflow.duration.total_seconds()
                workflows_data.append(workflow_dict)
            
            with open(self.workflows_file, 'w', encoding='utf-8') as f:
                json.dump(workflows_data, f, indent=2, ensure_ascii=False)
                
            # Sauvegarder l'index
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.search_index, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Erreur sauvegarde mémoire: {e}")
    
    def add_entry(self, entry: MemoryEntry):
        """Ajoute une entrée de mémoire"""
        self.entries.append(entry)
        self.update_search_index(entry)
        self.save_memory()
    
    def add_performance_pattern(self, pattern: PerformanceMemory):
        """Ajoute un pattern de performance"""
        self.performance_patterns.append(pattern)
        self.save_memory()
    
    def add_architecture_decision(self, decision: ArchitectureMemory):
        """Ajoute une décision architecturale"""
        self.architecture_decisions.append(decision)
        self.save_memory()
    
    def add_workflow_memory(self, workflow: WorkflowMemory):
        """Ajoute un mémoire de workflow"""
        self.workflow_history.append(workflow)
        self.save_memory()
    
    def update_search_index(self, entry: MemoryEntry):
        """Met à jour l'index de recherche"""
        # Mots-clés depuis différentes sources
        keywords = []
        
        # Tags
        keywords.extend(entry.tags)
        
        # Contexte
        for key, value in entry.context.items():
            if isinstance(value, str):
                keywords.extend(value.lower().split())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        keywords.extend(item.lower().split())
        
        # Décision et rationale
        keywords.extend(entry.decision.lower().split())
        keywords.extend(entry.rationale.lower().split())
        
        # Agent
        keywords.append(entry.agent_name.lower())
        keywords.append(entry.agent_type.lower())
        
        # Ajouter à l'index
        for keyword in set(keywords):  # Éliminer les doublons
            if keyword not in self.search_index:
                self.search_index[keyword] = []
            if entry.id not in self.search_index[keyword]:
                self.search_index[keyword].append(entry.id)
    
    def rebuild_search_index(self):
        """Reconstruit l'index de recherche complet"""
        self.search_index = {}
        for entry in self.entries:
            self.update_search_index(entry)
    
    def search(self, query: str, agent_type: str = None, limit: int = 10) -> list[MemoryEntry]:
        """Recherche dans la mémoire"""
        query_words = query.lower().split()
        matching_ids = set()
        
        # Recherche par mots-clés
        for word in query_words:
            if word in self.search_index:
                matching_ids.update(self.search_index[word])
        
        # Filtrer par type d'agent si spécifié
        if agent_type:
            filtered_entries = []
            for entry_id in matching_ids:
                entry = next((e for e in self.entries if e.id == entry_id), None)
                if entry and entry.agent_type == agent_type:
                    filtered_entries.append(entry)
            return filtered_entries[:limit]
        
        # Retourner les entrées correspondantes
        matching_entries = []
        for entry_id in matching_ids:
            entry = next((e for e in self.entries if e.id == entry_id), None)
            if entry:
                matching_entries.append(entry)
        
        # Trier par qualité et date
        matching_entries.sort(key=lambda x: (x.quality_score, x.timestamp), reverse=True)
        
        return matching_entries[:limit]
    
    def get_similar_performance_patterns(self, scenario: str, threshold: float = 0.8) -> list[PerformanceMemory]:
        """Trouve des patterns de performance similaires"""
        similar_patterns = []
        scenario_words = set(scenario.lower().split())
        
        for pattern in self.performance_patterns:
            pattern_words = set(pattern.scenario.lower().split())
            
            # Calcul de similarité simple (Jaccard)
            intersection = len(scenario_words.intersection(pattern_words))
            union = len(scenario_words.union(pattern_words))
            
            if union > 0:
                similarity = intersection / union
                if similarity >= threshold:
                    similar_patterns.append(pattern)
        
        # Trier par qualité
        similar_patterns.sort(key=lambda x: x.quality_score, reverse=True)
        
        return similar_patterns
    
    def get_architecture_decisions(self, component: str = None,
                                 agent_type: str = None) -> list[ArchitectureMemory]:
        """Récupère les décisions architecturales"""
        decisions = self.architecture_decisions
        
        if component:
            decisions = [d for d in decisions if component.lower() in d.component.lower()]
        
        if agent_type:
            decisions = [d for d in decisions if agent_type in d.stakeholders]
        
        return sorted(decisions, key=lambda x: x.timestamp, reverse=True)
    
    def get_workflow_history(self, workflow_type: str = None,
                           days_back: int = 30) -> list[WorkflowMemory]:
        """Récupère l'historique des workflows"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        workflows = [w for w in self.workflow_history if w.timestamp >= cutoff_date]
        
        if workflow_type:
            workflows = [w for w in workflows if w.workflow_type == workflow_type]
        
        return sorted(workflows, key=lambda x: x.timestamp, reverse=True)
    
    def get_memory_statistics(self) -> dict[str, Any]:
        """Retourne des statistiques sur la mémoire"""
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        stats = {
            "total_entries": len(self.entries),
            "total_performance_patterns": len(self.performance_patterns),
            "total_architecture_decisions": len(self.architecture_decisions),
            "total_workflows": len(self.workflow_history),
            "search_index_size": len(self.search_index),
            
            # Statistiques par type d'agent
            "entries_by_agent_type": {},
            "entries_by_agent": {},
            
            # Statistiques temporelles
            "entries_last_week": 0,
            "entries_last_month": 0,
            "average_quality_score": 0.0,
            
            # Patterns les plus utilisés
            "top_tags": [],
            "top_scenarios": []
        }
        
        # Calculer les statistiques
        if self.entries:
            # Par type d'agent
            for entry in self.entries:
                agent_type = entry.agent_type
                agent_name = entry.agent_name
                
                stats["entries_by_agent_type"][agent_type] = \
                    stats["entries_by_agent_type"].get(agent_type, 0) + 1
                
                stats["entries_by_agent"][agent_name] = \
                    stats["entries_by_agent"].get(agent_name, 0) + 1
                
                # Temporel
                if entry.timestamp >= week_ago:
                    stats["entries_last_week"] += 1
                if entry.timestamp >= month_ago:
                    stats["entries_last_month"] += 1
            
            # Qualité moyenne
            stats["average_quality_score"] = \
                sum(e.quality_score for e in self.entries) / len(self.entries)
            
            # Tags les plus fréquents
            tag_counts = {}
            for entry in self.entries:
                for tag in entry.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            stats["top_tags"] = sorted(tag_counts.items(),
                                     key=lambda x: x[1], reverse=True)[:10]
        
        # Scenarios de performance les plus fréquents
        if self.performance_patterns:
            scenario_counts = {}
            for pattern in self.performance_patterns:
                scenario_counts[pattern.scenario] = \
                    scenario_counts.get(pattern.scenario, 0) + 1
            
            stats["top_scenarios"] = sorted(scenario_counts.items(),
                                          key=lambda x: x[1], reverse=True)[:10]
        
        return stats
    
    def cleanup_old_entries(self, days_to_keep: int = 90):
        """Nettoie les anciennes entrées de mémoire"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Conserver uniquement les entrées récentes
        self.entries = [e for e in self.entries if e.timestamp >= cutoff_date]
        self.performance_patterns = [p for p in self.performance_patterns if p.timestamp >= cutoff_date]
        self.architecture_decisions = [d for d in self.architecture_decisions if d.timestamp >= cutoff_date]
        self.workflow_history = [w for w in self.workflow_history if w.timestamp >= cutoff_date]
        
        # Reconstruire l'index
        self.rebuild_search_index()
        
        # Sauvegarder
        self.save_memory()
        
        print(f"Nettoyage terminé. Entrées conservées depuis {days_to_keep} jours.")


# Fonctions utilitaires pour créer des entrées de mémoire
def create_hybrid_entry(agent_name: str, decision: str, rationale: str,
                       context: dict[str, Any], quality_score: float,
                       tags: list[str] = None) -> MemoryEntry:
    """Crée une entrée de mémoire hybride"""
    entry_id = hashlib.sha256(
        f"{agent_name}{decision}{datetime.now().isoformat()}".encode()
    ).hexdigest()
    
    return MemoryEntry(
        id=entry_id,
        timestamp=datetime.now(),
        agent_type="hybrid",
        agent_name=agent_name,
        context=context,
        decision=decision,
        rationale=rationale,
        quality_score=quality_score,
        tags=tags or []
    )


def create_performance_memory(scenario: str, optimization: str,
                           results: dict[str, float], ebp_analysis: dict[str, Any],
                           bmm_workflow: str, quality_score: float) -> PerformanceMemory:
    """Crée une mémoire de performance"""
    pattern_id = hashlib.md5(
        f"{scenario}{optimization}{datetime.now().isoformat()}".encode()
    ).hexdigest()
    
    return PerformanceMemory(
        pattern_id=pattern_id,
        timestamp=datetime.now(),
        scenario=scenario,
        optimization=optimization,
        results=results,
        ebp_analysis=ebp_analysis,
        bmm_workflow=bmm_workflow,
        quality_score=quality_score,
        applicable_contexts=[]
    )


# Point d'entrée principal pour l'utilisation
if __name__ == "__main__":
    # Exemple d'utilisation
    memory = BMADMemorySystem()
    
    # Ajouter une entrée de test
    test_entry = create_hybrid_entry(
        agent_name="bmad-net-architect",
        decision="Use microservices architecture",
        rationale="Scalability requirements demand distributed approach",
        context={"project": "Platform", "complexity": "high"},
        quality_score=0.85,
        tags=["architecture", "microservices", "scalability"]
    )
    
    memory.add_entry(test_entry)
    
    # Afficher les statistiques
    stats = memory.get_memory_statistics()
    print("Statistiques de la mémoire:", json.dumps(stats, indent=2, default=str))
