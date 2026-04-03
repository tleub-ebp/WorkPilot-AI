#!/usr/bin/env python3
"""
Script pour connecter le compte Windsurf dans la page "Comptes"
Vérifie la configuration et active le provider Windsurf
"""

import json
import os
import sys

import requests

# Ajouter le répertoire du backend au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'apps', 'backend'))

def check_windsurf_config():
    """Vérifie la configuration Windsurf"""
    print("🔍 Vérification de la configuration Windsurf...")
    print("=" * 60)
    
    # 1. Vérifier le token OAuth
    token_file = ".env.windsurf"
    oauth_token = None
    
    if os.path.exists(token_file):
        print(f"✅ Fichier {token_file} trouvé")
        with open(token_file) as f:
            for line in f:
                if line.startswith('WINDSURF_OAUTH_TOKEN='):
                    oauth_token = line.split('=', 1)[1].strip()
                    break
    
    if oauth_token:
        print(f"✅ Token OAuth Windsurf présent ({len(oauth_token)} caractères)")
        print(f"   Token: {oauth_token[:20]}...{oauth_token[-20:]}")
    else:
        print("❌ Token OAuth Windsurf NON trouvé")
        return False
    
    # 2. Vérifier la variable d'environnement
    env_token = os.getenv("WINDSURF_OAUTH_TOKEN")
    if env_token:
        print(f"✅ Token dans environnement: {len(env_token)} caractères")
    else:
        print("⚠️  Token non dans l'environnement - chargement...")
        os.environ["WINDSURF_OAUTH_TOKEN"] = oauth_token
        print("✅ Token chargé dans l'environnement")
    
    return True

def check_backend_status():
    """Vérifie le statut du backend"""
    print("\n🌐 Vérification du backend...")
    print("-" * 40)
    
    # Essayer plusieurs ports possibles
    ports = [8000, 9000, 8080]
    
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Backend accessible sur port {port}")
                return True
        except requests.exceptions.ConnectionError:
            continue
        except Exception as e:
            continue
    
    print("❌ Backend non démarré")
    print("   Commande: cd apps/backend && python start_backend.py")
    return False

def check_windsurf_provider():
    """Vérifie le provider Windsurf dans le backend"""
    print("\n🔧 Vérification du provider Windsurf...")
    print("-" * 40)
    
    # Essayer plusieurs ports possibles
    ports = [8000, 9000, 8080]
    
    for port in ports:
        try:
            response = requests.get(f"http://localhost:{port}/providers/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                providers = data.get("providers", [])
                status = data.get("status", {})
                
                print(f"📋 Providers disponibles: {', '.join(providers)}")
                
                if "windsurf" in providers:
                    windsurf_status = status.get("windsurf", False)
                    if windsurf_status:
                        print("✅ Provider Windsurf ACTIVÉ")
                        return True
                    else:
                        print("⚠️  Provider Windsurf présent mais INACTIF")
                else:
                    print("❌ Provider Windsurf NON trouvé dans la liste")
                break
        except requests.exceptions.ConnectionError:
            continue
        except Exception as e:
            continue
    
    return False

def activate_windsurf_account():
    """Active le compte Windsurf"""
    print("\n🚀 Activation du compte Windsurf...")
    print("-" * 40)
    
    # Vérifier la configuration dans configured_providers.json
    config_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'utils', 'config', 'configured_providers.json')
    
    if os.path.exists(config_file):
        with open(config_file) as f:
            config = json.load(f)
        
        # Le fichier a une structure {"providers": [...]}
        providers_list = config.get("providers", [])
        
        windsurf_found = False
        for provider in providers_list:
            # S'assurer que provider est un dictionnaire
            if isinstance(provider, dict) and provider.get("label") == "Windsurf AI":
                windsurf_found = True
                print(f"✅ Provider Windsurf dans config: {provider.get('description')}")
                break
        
        if not windsurf_found:
            print("⚠️  Provider Windsurf non trouvé dans configured_providers.json")
            print("   Ajout du provider...")
            
            # Ajouter Windsurf à la configuration
            windsurf_provider = {
                "name": "windsurf",
                "label": "Windsurf AI",
                "description": "Provider Windsurf pour l'utilisation des tokens Windsurf."
            }
            providers_list.append(windsurf_provider)
            config["providers"] = providers_list
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print("✅ Provider Windsurf ajouté à la configuration")
        else:
            print("✅ Provider Windsurf déjà configuré")
    else:
        print(f"❌ Fichier de configuration non trouvé: {config_file}")
    
    return True

def test_windsurf_models():
    """Test les modèles Windsurf"""
    print("\n🧪 Test des modèles Windsurf...")
    print("-" * 40)
    
    try:
        # Importer le registry pour tester
        from services.provider_registry import provider_registry
        
        # Vérifier le statut du provider Windsurf
        status = provider_registry.check_provider_status("windsurf")
        
        print("📊 Statut Windsurf:")
        print(f"   • Available: {status.available}")
        print(f"   • Authenticated: {status.authenticated}")
        if status.error:
            print(f"   • Error: {status.error}")
        if status.last_checked:
            print(f"   • Last checked: {status.last_checked}")
        
        # Lister les modèles
        provider = provider_registry.get_provider("windsurf")
        if provider:
            print(f"\n📋 Modèles disponibles ({len(provider.models)}):")
            for model in provider.models:
                print(f"   • {model['label']} ({model['tier']})")
        
        return status.authenticated
        
    except Exception as e:
        print(f"❌ Erreur test modèles: {e}")
        return False

def main():
    """Fonction principale"""
    print("🔌 PLUGIN WINDSURF - PAGE COMPTES")
    print("=" * 60)
    
    success = True
    
    # 1. Vérifier la configuration
    if not check_windsurf_config():
        success = False
    
    # 2. Vérifier le backend
    if not check_backend_status():
        print("\n⚠️  Veuillez démarrer le backend avant de continuer")
        return False
    
    # 3. Vérifier le provider
    if not check_windsurf_provider():
        success = False
    
    # 4. Activer le compte
    if not activate_windsurf_account():
        success = False
    
    # 5. Tester les modèles
    if not test_windsurf_models():
        success = False
    
    # Résultat final
    print("\n" + "=" * 60)
    if success:
        print("🎉 COMPTE WINDSURF CONNECTÉ AVEC SUCCÈS!")
        print("\n📋 Étapes suivantes:")
        print("   1. Allez dans la page 'Comptes' de l'application")
        print("   2. Le provider Windsurf AI devrait apparaître")
        print("   3. Sélectionnez-le pour l'activer")
        print("   4. Choisissez vos modèles (SWE-1.5, Claude Opus 4.6, etc.)")
    else:
        print("❌ ERREUR LORS DE LA CONNEXION DU COMPTE WINDSURF")
        print("\n🔧 Actions recommandées:")
        print("   1. Vérifiez que le token OAuth est valide")
        print("   2. Démarrez le backend: cd apps/backend && python start_backend.py")
        print("   3. Rechargez la page 'Comptes'")
    
    return success

if __name__ == "__main__":
    main()
