# Utils Directory

Ce répertoire contient les utilitaires et fichiers de configuration organisés pour une meilleure maintenance du projet.

## Structure

### `/scripts`
Contient tous les scripts Python et JavaScript utilisés pour le développement, le débogage et les tests :

- **Scripts de diagnostic** : `complete_diagnostic.py`, `deep_diagnostic.py`, `debug_ipc.py`
- **Scripts de profilage** : `create_copilot_profile.py`, `create_copilot_profile_clean.py`
- **Scripts de test** : `run_streaming_tests.py`, `test_streaming_e2e.py`
- **Scripts de validation** : `check_compiled_code.py`, `check_compiled_js.py`
- **Scripts de configuration** : `fix_provider_selection.py`, `fix_quality_scorer.py`, `update_copilot_models.py`
- **Scripts utilitaires** : `create_learning_modules.py`, `direct_test.py`
- **Scripts de monitoring** : `debug_usage_monitor.js`

### `/config`
Contient les fichiers de configuration temporaires et les ressources partagées :

- `card_data.txt` - Données de test pour les cartes
- `check_provider.html` - Page de test pour les fournisseurs
- `configured_providers.json` - Configuration des fournisseurs
- `fix_provider.js` - Script de correction des fournisseurs
- `fonts-setup.css` - Configuration des polices
- `plan.md` - Planification du projet

### `/system`
Contient les scripts système pour la gestion du projet :

- `merge-upstream.bat` - Script de fusion pour Windows (batch)
- `merge-upstream.ps1` - Script de fusion pour Windows (PowerShell)
- `merge-upstream.sh` - Script de fusion pour Unix/Linux

## Utilisation

La plupart de ces scripts sont conçus pour être exécutés depuis la racine du projet. Consultez chaque script individuellement pour connaître son utilisation spécifique.

## Maintenance

- Les scripts dans `/scripts` sont autonomes et ne devraient pas avoir de dépendances externes
- Les fichiers dans `/config` sont principalement des fichiers temporaires ou de test
- Les scripts dans `/system` sont utilisés pour les opérations Git et de maintenance
