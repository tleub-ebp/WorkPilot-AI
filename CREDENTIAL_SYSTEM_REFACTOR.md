# Refactor du Système de Credentials - Documentation

## 🎯 Objectif

Centraliser la gestion des credentials et rendre les composants frontend "dumb" en déplaçant la logique métier vers le backend.

## 🏗️ Architecture mise en place

### Backend (Node.js/Electron)

#### 1. CredentialManager (`src/main/services/credential-manager.ts`)
- **Rôle** : Service centralisé de gestion des credentials
- **Fonctionnalités** :
  - Gestion OAuth / API Key pour tous les providers
  - Switch automatique entre modes d'authentification
  - Stockage centralisé dans `profiles.json`
  - Événements temps réel pour les changements

#### 2. Credential Handlers (`src/main/ipc-handlers/credential-handlers.ts`)
- **Rôle** : Interface IPC entre frontend et CredentialManager
- **Endpoints** :
  - `credential:getActive` - Obtenir le credential actif
  - `credential:setActive` - Définir le provider actif
  - `usage:getData` - Obtenir les données d'usage
  - `usage:updateData` - Mettre à jour les données d'usage
  - `credential:validate` - Valider les credentials

#### 3. Credential Integration (`src/main/services/credential-integration.ts`)
- **Rôle** : Pont avec les systèmes existants
- **Fonctionnalités** :
  - Connecte le nouveau système au `usage-monitor` existant
  - Migre les données d'usage vers le nouveau format
  - Assure la rétrocompatibilité

### Frontend (React)

#### 1. CredentialService (`src/shared/services/credentialService.ts`)
- **Rôle** : Service frontend pour communiquer avec le backend
- **Fonctionnalités** :
  - Wrapper autour des appels IPC
  - Gestion des événements temps réel
  - Interface TypeScript fortement typée

#### 2. useCredentialService Hook (`src/renderer/hooks/useCredentialService.ts`)
- **Rôle** : Hook React pour faciliter l'utilisation du CredentialService
- **Fonctionnalités** :
  - Gestion d'état automatique
  - Abonnement aux événements
  - Actions simplifiées

#### 3. Composants "Dumb"
- **UsageIndicatorDumb** (`src/renderer/components/UsageIndicatorDumb.tsx`)
- **UsageIndicatorSimple** (`src/renderer/components/UsageIndicatorSimple.tsx`)
- **Caractéristiques** :
  - Uniquement de l'affichage
  - Pas de logique métier
  - Reçoivent les données via props/hooks

## 📁 Fichiers de configuration centralisés

### profiles.json
**Emplacement** : `AppData/Roaming/auto-claude-ui/auto-claude/profiles.json`

**Structure** :
```json
{
  "profiles": [
    {
      "id": "uuid",
      "name": "Anthropic API",
      "baseUrl": "https://api.anthropic.com",
      "apiKey": "sk-ant-...",
      "models": {
        "default": "claude-3-5-sonnet-20241022"
      },
      "createdAt": 1234567890,
      "updatedAt": 1234567890
    }
  ],
  "activeProfileId": "uuid",
  "version": 1
}
```

### Variables d'environnement
Le système génère automatiquement les variables d'environnement pour le processus Python :
- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`
- etc.

## 🔄 Flux de données

### 1. Initialisation
```
Backend Startup
├── CredentialManager.initialize()
├── Chargement de profiles.json
├── Intégration avec usage-monitor existant
└── Enregistrement des handlers IPC
```

### 2. Switch de provider
```
Frontend Action
├── useCredentialService().setActiveProvider()
├── IPC: credential:setActive
├── CredentialManager.setActiveProvider()
├── Mise à jour de profiles.json
├── Émission d'événements
└── Frontend reçoit les mises à jour
```

### 3. Suivi d'usage
```
Usage Monitor Existant
├── Détection de nouvelle données d'usage
├── Émission vers CredentialManager
├── Conversion au nouveau format
├── Émission vers frontend
└── Mise à jour de l'UI
```

## 🚀 Migration

### Étapes pour migrer l'ancien système :

1. **Remplacer UsageIndicator** :
   ```tsx
   // Ancien
   import { UsageIndicator } from './UsageIndicator';
   
   // Nouveau
   import { UsageIndicatorSimple } from './UsageIndicatorSimple';
   ```

2. **Initialiser l'intégration** dans `main/index.ts` :
   ```typescript
   import { initializeCredentialIntegration } from './services/credential-integration';
   
   // Après la création de la fenêtre
   await initializeCredentialIntegration();
   ```

3. **Mettre à jour les appels d'environnement** :
   ```typescript
   // Ancien
   import { getAPIProfileEnv } from './services/profile-service';
   const env = await getAPIProfileEnv();
   
   // Nouveau
   import { getEnvironmentVariables } from './services/credential-integration';
   const env = await getEnvironmentVariables();
   ```

## ✅ Avantages

### Centralisation
- ✅ Un seul fichier pour tous les credentials
- ✅ Format unifié pour tous les providers
- ✅ Gestion automatique du switch OAuth/API Key

### Séparation des responsabilités
- ✅ Backend : Logique métier
- ✅ Frontend : Uniquement l'UI
- ✅ Services : Communication et état

### Maintenabilité
- ✅ Code plus modulaire
- ✅ Tests plus simples
- ✅ Évolution plus facile

### Sécurité
- ✅ Credentials dans AppData (protégé)
- ✅ Pas de credentials dans le frontend
- ✅ Gestion centralisée des permissions

## 🔧 Dépannage

### Problèmes courants

1. **Credentials non chargés**
   - Vérifier que `initializeCredentialIntegration()` est appelé
   - Vérifier les permissions du fichier `profiles.json`

2. **UI ne se met pas à jour**
   - Vérifier que les handlers IPC sont enregistrés
   - Vérifier les abonnements aux événements

3. **Switch de provider ne fonctionne pas**
   - Vérifier la structure de `profiles.json`
   - Vérifier les logs du CredentialManager

### Logs utiles

```bash
# Backend
[CredentialManager] Initializing...
[CredentialManager] Loaded profiles from profiles.json
[CredentialIntegration] Connected to existing usage monitor

# Frontend
[CredentialService] Failed to get active credential
[UsageIndicatorSimple] Loading initial data...
```

## 📋 Checklist de migration

- [ ] Initialiser `initializeCredentialIntegration()` dans main
- [ ] Remplacer `UsageIndicator` par `UsageIndicatorSimple`
- [ ] Mettre à jour les appels `getAPIProfileEnv()`
- [ ] Tester le switch OAuth/API Key
- [ ] Vérifier que l'usage s'affiche correctement
- [ ] Tester la réauthentification
- [ ] Vérifier la persistance des credentials

## 🎉 Résultat

Une architecture centralisée, maintenable et sécurisée où :
- Le backend gère toute la logique métier
- Le frontend affiche seulement les données
- Les credentials sont centralisés et sécurisés
- Le switch entre providers est transparent
