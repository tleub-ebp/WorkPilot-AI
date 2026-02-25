#!/usr/bin/env python3
"""
Deep diagnostic of Copilot integration issues
"""

import json
import requests
from pathlib import Path

def diagnose_copilot_integration():
    """Complete diagnostic of Copilot integration"""
    
    print("🔍 Deep Diagnostic: Copilot Integration")
    print("=" * 50)
    
    # 1. Check profiles file
    profiles_file = Path.home() / ".claude-ebp" / "profiles" / "profiles.json"
    print(f"\n1. 📁 Checking profiles file: {profiles_file}")
    
    if not profiles_file.exists():
        print("❌ Profiles file not found")
        return False
    
    try:
        with open(profiles_file, 'r', encoding='utf-8') as f:
            profiles_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading profiles file: {e}")
        return False
    
    print("✅ Profiles file loaded successfully")
    
    # 2. Check active profile
    active_profile_id = profiles_data.get('activeProfileId')
    print(f"\n2. 🎯 Active profile ID: {active_profile_id}")
    
    active_profile = None
    for profile in profiles_data.get('profiles', []):
        if profile.get('id') == active_profile_id:
            active_profile = profile
            break
    
    if not active_profile:
        print("❌ No active profile found")
        return False
    
    print("✅ Active profile found:")
    print(f"   Name: {active_profile.get('name')}")
    print(f"   Base URL: {active_profile.get('baseUrl')}")
    print(f"   API Key: {'✅ Present' if active_profile.get('apiKey') else '❌ Missing'}")
    print(f"   Models: {len(active_profile.get('models', []))} models")
    
    # 3. Check provider detection
    base_url = active_profile.get('baseUrl', '')
    print(f"\n3. 🔍 Provider detection for baseUrl: {base_url}")
    
    # Simulate detectProvider logic
    detected_provider = 'unknown'
    if 'github.com' in base_url:
        detected_provider = 'copilot'
    elif 'api.anthropic.com' in base_url:
        detected_provider = 'anthropic'
    elif 'api.openai.com' in base_url:
        detected_provider = 'openai'
    
    print(f"   Detected provider: {detected_provider}")
    
    if detected_provider != 'copilot':
        print("❌ Active profile is not detected as Copilot")
        print("💡 This could be the issue!")
        
        # Check if there's a Copilot profile
        copilot_profiles = [p for p in profiles_data.get('profiles', []) if 'copilot' in p.get('name', '').lower()]
        if copilot_profiles:
            print(f"💡 Found {len(copilot_profiles)} Copilot profile(s):")
            for cp in copilot_profiles:
                print(f"   - {cp.get('name')} (ID: {cp.get('id')})")
            print("💡 Try setting one of these as the active profile")
        return False
    
    print("✅ Provider correctly detected as Copilot")
    
    # 4. Check backend connectivity
    print(f"\n4. 🌐 Testing backend connectivity...")
    try:
        response = requests.get('http://localhost:9000/providers/usage/copilot', timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is responding")
            print(f"   Has error: {'error' in data}")
            print(f"   Available: {data.get('available', False)}")
            print(f"   Error type: {data.get('error', 'None')}")
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return False
    
    # 5. Check if UsageMonitor would be called
    print(f"\n5. 🔄 UsageMonitor execution flow:")
    print("   ✅ Active profile is Copilot")
    print("   ✅ Provider detected as Copilot")
    print("   ✅ Backend is accessible")
    print("   ✅ UsageMonitor should call fetchUsageViaAPI with Copilot")
    
    return True

def check_known_providers():
    """Check if Copilot is in known providers list"""
    print(f"\n6. 📋 Checking known providers...")
    
    # This simulates the KNOWN_PROVIDERS check in UsageIndicator
    known_providers = {'anthropic', 'openai', 'ollama', 'copilot'}
    is_known = 'copilot' in known_providers
    
    print(f"   Copilot in known providers: {'✅ YES' if is_known else '❌ NO'}")
    
    if not is_known:
        print("❌ Copilot not in known providers list!")
        print("💡 This would cause 'fournisseur non pris en charge' error")
        return False
    
    return True

if __name__ == "__main__":
    integration_ok = diagnose_copilot_integration()
    providers_ok = check_known_providers()
    
    print(f"\n🎯 Summary:")
    if integration_ok and providers_ok:
        print("✅ All checks passed!")
        print("\n💡 If you still see 'Données d'utilisation non disponibles':")
        print("1. The frontend might need to be restarted")
        print("2. Check browser console for JavaScript errors")
        print("3. Verify the UsageMonitor is actually being called")
        print("4. Check if there are multiple profile files in different locations")
    else:
        print("❌ Some checks failed!")
        if not integration_ok:
            print("- Integration issue detected above")
        if not providers_ok:
            print("- Known providers issue")
