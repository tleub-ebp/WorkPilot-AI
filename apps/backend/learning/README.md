# Learning Mode Module

> Module pédagogique pour explications en temps réel et onboarding automatisé

## 📁 Structure

```
learning/
├── __init__.py                  # Exports principaux
├── learning_mode.py             # Mode apprentissage avec explications (451 lignes)
├── documentation_generator.py   # Génération de documentation automatique
├── tutorial_generator.py        # Génération de tutoriels personnalisés
└── onboarding_assistant.py      # Assistant d'onboarding pour nouveaux devs
```

## 🎯 Modules

### 1. `learning_mode.py`

**Classe principale** : `LearningMode`

Fournit des explications en temps réel de tout ce que Claude fait.

**Fonctionnalités** :
- 4 niveaux d'explication (Beginner, Intermediate, Advanced, Expert)
- Explications d'utilisation d'outils
- Explications de décisions avec alternatives
- Explications de code avec patterns et best practices
- Génération de rapports markdown
- Sauvegarde de sessions pour base de connaissances

**Exemple** :
```python
from learning import LearningMode, LearningModeConfig, ExplanationLevel

config = LearningModeConfig(
    enabled=True,
    explanation_level=ExplanationLevel.INTERMEDIATE,
    explain_tools=True,
    explain_decisions=True,
    prefer_examples=True
)

learning_mode = LearningMode(config)

# Expliquer l'utilisation d'un outil
explanation = learning_mode.explain_tool_use(
    tool_name="Read",
    tool_input={"file_path": "auth.py"},
    reason="Analyzing authentication system",
    expected_outcome="Understanding OAuth flow"
)

print(explanation.explanation)
```

### 2. `documentation_generator.py`

**Classe principale** : `DocumentationGenerator`

Génère automatiquement de la documentation à partir du code.

**Types de documentation** :
- `README` : Documentation projet complète
- `API_DOC` : Documentation API avec endpoints
- `INLINE_COMMENT` : Commentaires éducatifs dans le code
- `TUTORIAL` : Tutoriels et guides
- `ARCHITECTURE` : Documentation d'architecture
- `CHANGELOG` : Historique des changements
- `CONTRIBUTING` : Guide de contribution

**Exemple** :
```python
from pathlib import Path
from learning import DocumentationGenerator

doc_gen = DocumentationGenerator(Path("/path/to/project"))

# Générer README
await doc_gen.generate_readme(
    project_name="Mon Projet",
    description="Une super application",
    features=["Auth OAuth", "API REST", "Dashboard"]
)

# Générer documentation API
await doc_gen.generate_api_documentation(
    api_name="Mon API",
    endpoints=[...],
    auth_required=True
)
```

### 3. `tutorial_generator.py`

**Classe principale** : `TutorialGenerator`

Crée des tutoriels step-by-step personnalisés.

**Topics** :
- `GETTING_STARTED` : Premiers pas
- `API_USAGE` : Utilisation de l'API
- `BEST_PRACTICES` : Bonnes pratiques
- `ARCHITECTURE` : Architecture du système
- `DEBUGGING` : Debugging et troubleshooting
- `TESTING` : Tests et QA
- `DEPLOYMENT` : Déploiement

**Exemple** :
```python
from learning import TutorialGenerator, TutorialTopic, TutorialStep

tutorial_gen = TutorialGenerator(Path("/path/to/project"))

tutorial = await tutorial_gen.generate_tutorial(
    topic=TutorialTopic.API_USAGE,
    code_context={"endpoints": [...]},
    target_audience="intermediate"
)

# Ajouter des étapes
tutorial_gen.add_step(tutorial, TutorialStep(
    step_number=1,
    title="Installation",
    description="Installer les dépendances",
    code_example="npm install",
    tips=["Use Node 18+"]
))
```

### 4. `onboarding_assistant.py`

**Classe principale** : `OnboardingAssistant`

Guide les nouveaux développeurs dans le projet.

**Étapes d'onboarding** :
- `WELCOME` : Bienvenue dans l'équipe
- `PROJECT_OVERVIEW` : Vue d'ensemble du projet
- `SETUP_ENVIRONMENT` : Configuration de l'environnement
- `FIRST_TASK` : Première tâche guidée
- `CODE_REVIEW` : Apprentissage du code review
- `DEPLOYMENT` : Processus de déploiement
- `RESOURCES` : Ressources et documentation

**Exemple** :
```python
from learning import OnboardingAssistant, OnboardingStep

assistant = OnboardingAssistant(Path("/path/to/project"))

# Démarrer l'onboarding
progress = await assistant.start_onboarding(
    developer_name="Alice",
    experience_level="intermediate"
)

# Obtenir l'étape suivante
next_step = await assistant.get_next_step("Alice")

# Marquer comme complété
await assistant.complete_step(
    developer_name="Alice",
    step=OnboardingStep.SETUP_ENVIRONMENT,
    notes="Environment setup successful"
)
```

## 🔧 Configuration

### LearningModeConfig

```python
@dataclass
class LearningModeConfig:
    enabled: bool = True
    explanation_level: ExplanationLevel = ExplanationLevel.INTERMEDIATE
    explain_tools: bool = True              # Expliquer les outils
    explain_decisions: bool = True          # Expliquer les décisions
    explain_code: bool = True               # Expliquer le code
    explain_patterns: bool = True           # Expliquer les patterns
    explain_best_practices: bool = True     # Expliquer les best practices
    generate_inline_comments: bool = True   # Ajouter des commentaires
    generate_summary: bool = True           # Générer un résumé
    save_learnings: bool = True             # Sauvegarder les explications
    prefer_visual_diagrams: bool = False    # Générer des diagrammes Mermaid
    prefer_examples: bool = True            # Inclure des exemples
    prefer_comparisons: bool = True         # Comparer avec alternatives
```

### ExplanationLevel (Enum)

```python
class ExplanationLevel(str, Enum):
    BEGINNER = "beginner"           # Très détaillé
    INTERMEDIATE = "intermediate"   # Équilibré
    ADVANCED = "advanced"           # Concis
    EXPERT = "expert"               # Minimal
```

## 📊 Modèles de données

### LearningExplanation

```python
@dataclass
class LearningExplanation:
    timestamp: datetime
    category: str  # tool_use, decision, code, pattern, best_practice
    title: str
    explanation: str
    code_snippet: Optional[str] = None
    diagram: Optional[str] = None
    alternative_approaches: List[Dict[str, str]] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    difficulty: ExplanationLevel = ExplanationLevel.INTERMEDIATE
```

### Tutorial

```python
@dataclass
class Tutorial:
    topic: TutorialTopic
    title: str
    description: str
    difficulty: str
    estimated_time_minutes: int
    prerequisites: List[str] = field(default_factory=list)
    steps: List[TutorialStep] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
```

### OnboardingProgress

```python
@dataclass
class OnboardingProgress:
    developer_name: str
    start_date: datetime
    current_step: OnboardingStep
    completed_steps: List[OnboardingStep] = field(default_factory=list)
    notes: Dict[str, str] = field(default_factory=dict)
    estimated_completion_date: Optional[datetime] = None
```

## 🚀 Utilisation

### En CLI

```bash
# Activer Learning Mode avec niveau intermédiaire
python runners/insights_runner.py \
  --project-dir /path/to/project \
  --message "Explain the authentication system" \
  --learning-mode \
  --explanation-level intermediate

# Niveau débutant pour formation
python runners/insights_runner.py \
  --project-dir /path/to/project \
  --message "How does the routing work?" \
  --learning-mode \
  --explanation-level beginner
```

### Dans le code

```python
# Créer et configurer Learning Mode
config = LearningModeConfig(
    enabled=True,
    explanation_level=ExplanationLevel.ADVANCED,
    explain_tools=True,
    explain_decisions=True,
    prefer_visual_diagrams=True
)

learning_mode = LearningMode(config)

# Utiliser pendant l'exécution
explanation = learning_mode.explain_tool_use(...)
learning_mode.explain_decision(...)
learning_mode.explain_code(...)

# Générer un rapport
report = learning_mode.generate_markdown_report()

# Sauvegarder la session
session_file = learning_mode.save_session(Path(".workpilot/learning"))
```

### Dans l'UI (Insights)

1. Ouvrir l'onglet Insights
2. Cliquer sur "Mode Apprentissage" 🎓
3. Choisir le niveau d'explication
4. Poser des questions
5. Les explications apparaissent en temps réel

## 📈 Métriques

Les sessions Learning Mode collectent automatiquement :

```python
{
    "session_duration_seconds": 125.5,
    "total_explanations": 15,
    "explanations_by_category": {
        "tool_use": 8,
        "decision": 4,
        "code": 2,
        "pattern": 1
    },
    "tools_used": ["Read", "Grep", "Glob"],
    "patterns_used": ["Factory Pattern", "Singleton"],
    "explanation_level": "intermediate"
}
```

## 🧪 Tests

```bash
# Lancer les tests
pytest tests/test_learning_mode.py -v

# Tests disponibles
- test_learning_mode_initialization
- test_explain_tool_use
- test_explain_decision
- test_explanation_levels
- test_session_summary
- test_markdown_report
- test_save_session
- test_disabled_learning_mode
- test_documentation_generator
- test_api_documentation
```

## 📚 Documentation

- **Guide utilisateur** : `docs/features/LEARNING_MODE.md`
- **Roadmap** : `docs/roadmap/killing-features.md` (Feature #10)
- **CHANGELOG** : `CHANGELOG.md`

## 🎯 Cas d'usage

### 1. Formation des juniors
```python
config = LearningModeConfig(explanation_level=ExplanationLevel.BEGINNER)
```

### 2. Code review entre seniors
```python
config = LearningModeConfig(explanation_level=ExplanationLevel.ADVANCED)
```

### 3. Documentation automatique
```python
doc_gen = DocumentationGenerator(project_root)
await doc_gen.generate_readme(...)
await doc_gen.generate_api_documentation(...)
```

### 4. Onboarding nouveaux devs
```python
assistant = OnboardingAssistant(project_root)
await assistant.start_onboarding("Bob", "intermediate")
```

## 🔮 Évolutions futures

- Support multilingue (FR, EN, ES, DE)
- Génération de vidéos tutorielles
- Quiz interactifs
- Gamification
- Export PDF/EPUB

---

**Status** : ✅ **PRODUCTION READY**
**Version** : 1.0.0
**Date** : 9 février 2026

