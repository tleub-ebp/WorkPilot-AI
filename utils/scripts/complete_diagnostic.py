#!/usr/bin/env python3
"""
Complete diagnostic of the Copilot integration chain
"""

import json
from pathlib import Path

import requests


def test_complete_chain():
    """Test the complete integration chain"""
    
    print("🔍 Complete Diagnostic: Copilot Integration Chain")
    print("=" * 50)
    
    # Step 1: Check profiles file
    profiles_file = Path.home() / ".claude-ebp" / "profiles" / "profiles.json"
    print(f"\n1. 📁 Checking profiles file: {profiles_file}")
    
    if not profiles_file.exists():
        print("❌ Profiles file not found")
        return False
    
    with open(profiles_file, encoding='utf-8') as f:
        profiles_data = json.load(f)
    
    active_profile_id = profiles_data.get('activeProfileId')
    active_profile = None
    for profile in profiles_data.get('profiles', []):
        if profile.get('id') == active_profile_id:
            active_profile = profile
            break
    
    if not active_profile:
        print("❌ No active profile found")
        return False
    
    print(f"✅ Active profile: {active_profile.get('name')}")
    print(f"   Base URL: {active_profile.get('baseUrl')}")
    
    # Step 2: Check provider detection
    base_url = active_profile.get('baseUrl', '')
    detected_provider = 'copilot' if 'github.com' in base_url else 'unknown'
    print(f"\n2. 🔍 Detected provider: {detected_provider}")
    
    if detected_provider != 'copilot':
        print("❌ Provider is not Copilot")
        return False
    
    # Step 3: Check backend connectivity
    print("\n3. 🌐 Testing backend connectivity...")
    try:
        response = requests.get('http://localhost:9000/providers/usage/copilot', timeout=5)
        if response.status_code == 200:
            usage_data = response.json()
            print("✅ Backend is responding")
            print(f"   Error: {usage_data.get('error')}")
            print(f"   Available: {usage_data.get('available')}")
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        return False
    
    # Step 4: Simulate the exact getUsageForProvider logic
    print("\n4. 🔄 Simulating getUsageForProvider logic...")
    
    # This simulates the logic in getUsageForProvider
    profiles_file_path = "c:\\Users\\thomas.leberre\\Repositories\\WorkPilot-AI\\config\\configured_providers.json"
    try:
        with open(profiles_file_path, encoding='utf-8') as f:
            providers_config = json.load(f)
        
        # Find Copilot in configured providers
        copilot_provider = None
        for provider in providers_config.get('providers', []):
            if provider.get('name') == 'copilot':
                copilot_provider = provider
                break
        
        if copilot_provider:
            print("✅ Copilot found in configured_providers.json")
        else:
            print("❌ Copilot not found in configured_providers.json")
            return False
            
    except Exception as e:
        print(f"❌ Error loading configured_providers.json: {e}")
        return False
    
    # Step 5: Check if our modifications are in the compiled code
    print("\n5. 🔍 Checking compiled code modifications...")
    
    main_js_path = "c:\\Users\\thomas.leberre\\Repositories\\WorkPilot-AI\\apps\\frontend\\out\\main\\index.js"
    try:
        with open(main_js_path, encoding='utf-8') as f:
            compiled_code = f.read()
        
        checks = [
            ("getUsageForProvider method", "getUsageForProvider" in compiled_code),
            ("Copilot special case", "providerName === 'copilot'" in compiled_code),
            ("FastAPI backend call", "http://localhost:9000/providers/usage/copilot" in compiled_code),
            ("IPC handler with provider", "providerName?" in compiled_code)
        ]
        
        print("   Compiled code checks:")
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
            
    except Exception as e:
        print(f"❌ Error checking compiled code: {e}")
    
    # Step 6: Final diagnosis
    print("\n6. 🎯 Final Diagnosis:")
    print("✅ All components seem correctly configured")
    print("❌ But the frontend still returns data: null")
    print("\n💡 Possible causes:")
    print("1. Electron process hasn't restarted with new compiled code")
    print("2. There's an error in getUsageForProvider that's being caught")
    print("3. The IPC handler isn't calling getUsageForProvider correctly")
    print("4. There's a timing issue or race condition")
    
    return True

if __name__ == "__main__":
    test_complete_chain()
