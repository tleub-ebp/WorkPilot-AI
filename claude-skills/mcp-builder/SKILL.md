name: mcp-builder
description: Guide pour créer des serveurs MCP (Model Context Protocol) de haute qualité qui permettent aux LLMs d'interagir avec des services externes via des outils bien conçus. Utiliser lors de la création de serveurs MCP pour intégrer des APIs ou services externes, que ce soit en Python (FastMCP) ou Node/TypeScript (MCP SDK).
license: Complete terms in LICENSE.txt
---

# Guide de Développement de Serveurs MCP

## Vue d'ensemble

Créer des serveurs MCP (Model Context Protocol) qui permettent aux LLMs d'interagir avec des services externes via des outils bien conçus. La qualité d'un serveur MCP se mesure par sa capacité à permettre aux LLMs d'accomplir des tâches du monde réel.

---

# Processus

## 🚀 Workflow de Haut Niveau

La création d'un serveur MCP de haute qualité implique quatre phases principales :

### Phase 1: Recherche Approfondie et Planification

#### 1.1 Comprendre la Conception MCP Moderne

**Couverture API vs Outils Workflow:**
Équilibrer la couverture complète des endpoints API avec des outils de workflow spécialisés. Les outils workflow peuvent être plus pratiques pour des tâches spécifiques, tandis que la couverture complète donne aux agents la flexibilité de composer des opérations. Les performances varient selon le client—certains bénéficient de l'exécution de code qui combine des outils de base, tandis que d'autres fonctionnent mieux avec des workflows de plus haut niveau. En cas d'incertitude, prioriser la couverture API complète.

**Nomination et Découverte des Outils:**
Des noms d'outils clairs et descriptifs aident les agents à trouver rapidement les bons outils. Utiliser des préfixes cohérents (ex: `github_create_issue`, `github_list_repos`) et une nomination orientée action.

**Gestion du Contexte:**
Les agents bénéficient de descriptions d'outils concises et de la capacité à filtrer/paginer les résultats. Concevoir des outils qui retournent des données focalisées et pertinentes. Certains clients supportent l'exécution de code qui peut aider les agents à filtrer et traiter les données efficacement.

**Messages d'Erreur Actionnables:**
Les messages d'erreur doivent guider les agents vers des solutions avec des suggestions spécifiques et prochaines étapes.

#### 1.2 Étudier la Documentation du Protocole MCP

**Naviguer dans la spécification MCP:**

Commencer avec le sitemap pour trouver les pages pertinentes : `https://modelcontextprotocol.io/sitemap.xml`

Puis récupérer les pages spécifiques avec le suffixe `.md` pour le format markdown (ex: `https://modelcontextprotocol.io/specification/draft.md`).

Pages clés à consulter :
- Vue d'ensemble de la spécification et architecture
- Mécanismes de transport (streamable HTTP, stdio)
- Définitions d'outils, ressources et prompts

#### 1.3 Étudier la Documentation des Frameworks

**Stack recommandé:**
- **Langage**: TypeScript (support SDK de haute qualité et bonne compatibilité dans de nombreux environnements d'exécution ex: MCPB. De plus, les modèles IA sont bons à générer du code TypeScript, bénéficiant de son large usage, typage statique et bons outils de linting)
- **Transport**: Streamable HTTP pour serveurs distants, utilisant JSON stateless (plus simple à scaler et maintenir, par opposition aux sessions stateful et réponses streaming). stdio pour serveurs locaux.

**Charger la documentation du framework:**

- **Meilleures Pratiques MCP**: [📋 Voir Meilleures Pratiques](./reference/mcp_best_practices.md) - Lignes directrices principales

**Pour TypeScript (recommandé):**
- **TypeScript SDK**: Utiliser WebFetch pour charger `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
- [⚡ Guide TypeScript](./reference/node_mcp_server.md) - Patterns et exemples TypeScript

**Pour Python:**
- **Python SDK**: Utiliser WebFetch pour charger `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- [🐍 Guide Python](./reference/python_mcp_server.md) - Patterns et exemples Python

#### 1.4 Planifier Votre Implémentation

**Comprendre l'API:**
Examiner la documentation API du service pour identifier les endpoints clés, requirements d'authentification, et modèles de données. Utiliser la recherche web et WebFetch au besoin.

**Sélection des Outils:**
Prioriser la couverture API complète. Lister les endpoints à implémenter, en commençant par les opérations les plus courantes.

---

### Phase 2: Implémentation

#### 2.1 Mettre en Place la Structure du Projet

Voir les guides spécifiques au langage pour la configuration du projet :
- [⚡ Guide TypeScript](./reference/node_mcp_server.md) - Structure du projet, package.json, tsconfig.json
- [🐍 Guide Python](./reference/python_mcp_server.md) - Organisation des modules, dépendances

#### 2.2 Implémenter l'Infrastructure de Base

Créer des utilitaires partagés :
- Client API avec authentification
- Aides gestion d'erreurs
- Formatage des réponses (JSON/Markdown)
- Support pagination

#### 2.3 Implémenter les Outils

Pour chaque outil :

**Schéma d'Entrée:**
- Utiliser Zod (TypeScript) ou Pydantic (Python)
- Inclure contraintes et descriptions claires
- Ajouter des exemples dans les descriptions de champs

**Schéma de Sortie:**
- Définir `outputSchema` où possible pour les données structurées
- Utiliser `structuredContent` dans les réponses d'outils (fonctionnalité TypeScript SDK)
- Aide les clients à comprendre et traiter les sorties d'outils

**Description de l'Outil:**
- Résumé concis de la fonctionnalité
- Descriptions des paramètres
- Schéma de type de retour

**Implémentation:**
- Async/await pour les opérations I/O
- Gestion d'erreurs appropriée avec messages actionnables
- Support pagination où applicable
- Retourner à la fois contenu textuel et données structurées lors de l'utilisation de SDKs modernes

**Annotations:**
- `readOnlyHint`: true/false
- `destructiveHint`: true/false
- `idempotentHint`: true/false
- `openWorldHint`: true/false

---

### Phase 3: Revue et Test

#### 3.1 Qualité du Code

Rechercher :
- Aucun code dupliqué (principe DRY)
- Gestion d'erreurs cohérente
- Couverture de type complète
- Descriptions d'outils claires

#### 3.2 Build et Test

**TypeScript:**
- Exécuter `npm run build` pour vérifier la compilation
- Tester avec MCP Inspector: `npx @modelcontextprotocol/inspector`

**Python:**
- Vérifier la syntaxe: `python -m py_compile votre_server.py`
- Tester avec MCP Inspector

Voir les guides spécifiques au langage pour approches de test détaillées et checklists de qualité.

---

### Phase 4: Créer des Évaluations

Après avoir implémenté votre serveur MCP, créer des évaluations complètes pour tester son efficacité.

**Charger [✅ Guide d'Évaluation](./reference/evaluation.md) pour les lignes directrices complètes d'évaluation.**

#### 4.1 Comprendre le Purpose de l'Évaluation

Utiliser les évaluations pour tester si les LLMs peuvent utiliser efficacement votre serveur MCP pour répondre à des questions réalistes et complexes.

#### 4.2 Créer 10 Questions d'Évaluation

Pour créer des évaluations efficaces, suivre le processus décrit dans le guide d'évaluation :

1. **Inspection des Outils**: Lister les outils disponibles et comprendre leurs capacités
2. **Exploration de Contenu**: Utiliser les opérations READ-ONLY pour explorer les données disponibles
3. **Génération de Questions**: Créer 10 questions complexes et réalistes
4. **Vérification des Réponses**: Résoudre chaque question soi-même pour vérifier les réponses

#### 4.3 Requirements d'Évaluation

Assurer que chaque question est :
- **Indépendante**: Pas dépendante d'autres questions
- **Read-only**: Seulement opérations non-destructives requises
- **Complexe**: Requérant multiples appels d'outils et exploration profonde
- **Réaliste**: Basée sur cas d'usage réels que les humains apprécieraient
- **Vérifiable**: Réponse unique et claire vérifiable par comparaison de chaînes
- **Stable**: La réponse ne changera pas avec le temps

#### 4.4 Format de Sortie

Créer un fichier XML avec cette structure :

```xml
<evaluation>
  <qa_pair>
    <question>Trouver des discussions sur les lancements de modèles IA avec noms de code animaux. Un modèle avait besoin d'une désignation de sécurité spécifique utilisant le format ASL-X. Quel nombre X était déterminé pour le modèle nommé d'après un chat sauvage tacheté ?</question>
    <answer>3</answer>
  </qa_pair>
<!-- Plus de qa_pairs... -->
</evaluation>
```

---

# Fichiers de Référence

## 📚 Bibliothèque de Documentation

Charger ces ressources au besoin pendant le développement :

### Documentation MCP Principale (Charger en Premier)
- **Protocole MCP**: Commencer avec le sitemap à `https://modelcontextprotocol.io/sitemap.xml`, puis récupérer les pages spécifiques avec le suffixe `.md`
- [📋 Meilleures Pratiques MCP](./reference/mcp_best_practices.md) - Lignes directrices MCP universelles incluant :
  - Conventions de nommage de serveurs et outils
  - Lignes directrices de formatage de réponse (JSON vs Markdown)
  - Meilleures pratiques de pagination
  - Sélection du transport (streamable HTTP vs stdio)
  - Standards de sécurité et gestion d'erreurs

### Documentation SDK (Charger pendant Phase 1/2)
- **Python SDK**: Récupérer depuis `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- **TypeScript SDK**: Récupérer depuis `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`

### Guides d'Implémentation Spécifiques au Langage (Charger pendant Phase 2)
- [🐍 Guide d'Implémentation Python](./reference/python_mcp_server.md) - Guide complet Python/FastMCP avec :
  - Patterns d'initialisation de serveur
  - Exemples de modèles Pydantic
  - Enregistrement d'outils avec `@mcp.tool`
  - Exemples de travail complets
  - Checklist de qualité

- [⚡ Guide d'Implémentation TypeScript](./reference/node_mcp_server.md) - Guide TypeScript complet avec :
  - Structure du projet
  - Patterns de schéma Zod
  - Enregistrement d'outils avec `server.registerTool`
  - Exemples de travail complets
  - Checklist de qualité

### Guide d'Évaluation (Charger pendant Phase 4)
- [✅ Guide d'Évaluation](./reference/evaluation.md) - Guide complet de création d'évaluation avec :
  - Lignes directrices de création de questions
  - Stratégies de vérification des réponses
  - Spécifications de format XML
  - Exemples de questions et réponses
  - Exécution d'une évaluation avec les scripts fournis
