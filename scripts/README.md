# Scripts Utilitaires

Ce dossier contient les scripts de diagnostic et d'utilitaires du projet.

## Scripts Azure DevOps

### `diagnose_and_fix_azure.ps1`
Script PowerShell pour diagnostiquer et corriger les problèmes de configuration Azure DevOps.

**Usage** :
```powershell
.\scripts\diagnose_and_fix_azure.ps1
```

**Fonctions** :
- Recherche "MeCa Web" dans les fichiers `.env`
- Vérifie les variables d'environnement système
- Analyse l'URL Git remote
- Propose des corrections automatiques

### `diagnose_azure_config.py`
Script Python pour diagnostiquer la configuration Azure DevOps.

**Usage** :
```bash
python scripts/diagnose_azure_config.py
```

### `verify_azure_config.py`
Script Python pour vérifier la configuration Azure DevOps.

**Usage** :
```bash
python scripts/verify_azure_config.py
```

## Autres Scripts

### `check_encoding.py`
Vérification de l'encodage des fichiers.

### `fix_azure_devops_config.py`
Correction automatique de la configuration Azure DevOps.

### `bump-version.js`
Script de gestion des versions.

### `install-backend.js`
Installation des dépendances backend.

### `test-backend.js`
Tests backend.

### `validate-release.js`
Validation des releases.

---

**Note** : Les scripts PowerShell nécessitent Windows PowerShell 5.1+ ou PowerShell Core 7+

