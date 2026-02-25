name: webapp-testing
description: Boîte à outils pour interagir avec et tester les applications web locales en utilisant Playwright. Supporte la vérification de la fonctionnalité frontend, le débogage du comportement UI, la capture de screenshots du navigateur, et la visualisation des logs du navigateur.
license: Complete terms in LICENSE.txt
---

# Test d'Applications Web

Pour tester les applications web locales, écrire des scripts Python Playwright natifs.

**Scripts Helper Disponibles**:
- `scripts/with_server.py` - Gère le cycle de vie du serveur (supporte serveurs multiples)

**Toujours exécuter les scripts avec `--help` d'abord** pour voir l'utilisation. NE PAS lire le code source jusqu'à essayer d'exécuter le script d'abord et trouver qu'une solution personnalisée est absolument nécessaire. Ces scripts peuvent être très volumineux et ainsi polluer votre fenêtre de contexte. Ils existent pour être appelés directement comme des scripts boîte noire plutôt que d'être ingérés dans votre fenêtre de contexte.

## Arbre de Décision: Choisir Votre Approche

```
Tâche utilisateur → Est-ce du HTML statique ?
    ├─ Oui → Lire le fichier HTML directement pour identifier les sélecteurs
    │         ├─ Succès → Écrire un script Playwright en utilisant les sélecteurs
    │         └─ Échec/Incomplet → Traiter comme dynamique (ci-dessous)
    │
    └─ Non (webapp dynamique) → Le serveur est-il déjà en cours ?
        ├─ Non → Exécuter: python scripts/with_server.py --help
        │        Puis utiliser le helper + écrire un script Playwright simplifié
        │
        └─ Oui → Reconnaissance-then-action:
            1. Naviguer et attendre networkidle
            2. Prendre screenshot ou inspecter le DOM
            3. Identifier les sélecteurs depuis l'état rendu
            4. Exécuter les actions avec les sélecteurs découverts
```

## Exemple: Utilisation de with_server.py

Pour démarrer un serveur, exécuter `--help` d'abord, puis utiliser le helper :

**Serveur unique:**
```bash
python scripts/with_server.py --server "npm run dev" --port 5173 -- python votre_automation.py
```

**Serveurs multiples (ex: backend + frontend):**
```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python votre_automation.py
```

Pour créer un script d'automation, inclure uniquement la logique Playwright (les serveurs sont gérés automatiquement):
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) # Toujours lancer chromium en mode headless
    page = browser.new_page()
    page.goto('http://localhost:5173') # Serveur déjà en cours et prêt
    page.wait_for_load_state('networkidle') # CRITIQUE: Attendre l'exécution du JS
    # ... votre logique d'automation
    browser.close()
```

## Pattern Reconnaissance-Then-Action

1. **Inspecter le DOM rendu**:
   ```python
   page.screenshot(path='/tmp/inspect.png', full_page=True)
   content = page.content()
   page.locator('button').all()
   ```

2. **Identifier les sélecteurs** depuis les résultats d'inspection

3. **Exécuter les actions** en utilisant les sélecteurs découverts

## Piège Commun

❌ **Ne pas** inspecter le DOM avant d'attendre `networkidle` sur les apps dynamiques
✅ **Faire** attendre `page.wait_for_load_state('networkidle')` avant l'inspection

## Meilleures Pratiques

- **Utiliser les scripts groupés comme boîtes noires** - Pour accomplir une tâche, considérer si un des scripts disponibles dans `scripts/` peut aider. Ces scripts gèrent des workflows complexes et communs de manière fiable sans encombrer la fenêtre de contexte. Utiliser `--help` pour voir l'utilisation, puis invoquer directement.
- Utiliser `sync_playwright()` pour les scripts synchrones
- Toujours fermer le navigateur une fois terminé
- Utiliser des sélecteurs descriptifs: `text=`, `role=`, sélecteurs CSS, ou IDs
- Ajouter des attentes appropriées: `page.wait_for_selector()` ou `page.wait_for_timeout()`

## Fichiers de Référence

- **examples/** - Exemples montrant les patterns communs :
  - `element_discovery.py` - Découverte de boutons, liens et inputs sur une page
  - `static_html_automation.py` - Utilisation de URLs file:// pour HTML local
  - `console_logging.py` - Capture des logs console pendant l'automation
