#!/usr/bin/env python3
"""
Script to create a Copilot API profile for testing
"""

import json
import os
from pathlib import Path

def create_copilot_profile():
    """Create a Copilot profile in the profiles file"""
    
    # Find the profiles file location
    home_dir = Path.home()
    profiles_dir = home_dir / ".claude-ebp" / "profiles"
    profiles_file = profiles_dir / "profiles.json"
    
    if not profiles_file.exists():
        print(f"❌ Profiles file not found at {profiles_file}")
        return False
    
    # Read existing profiles
    try:
        with open(profiles_file, 'r', encoding='utf-8') as f:
            profiles_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading profiles file: {e}")
        return False
    
    # Check if Copilot profile already exists
    existing_copilot = None
    for profile in profiles_data.get('profiles', []):
        if 'copilot' in profile.get('name', '').lower() or 'github.com' in profile.get('baseUrl', ''):
            existing_copilot = profile
            break
    
    if existing_copilot:
        print(f"✅ Copilot profile already exists: {existing_copilot.get('name', 'Unknown')}")
        print(f"   ID: {existing_copilot.get('id', 'Unknown')}")
        print(f"   Base URL: {existing_copilot.get('baseUrl', 'Unknown')}")
        return True
    
    # Create new Copilot profile
    import uuid
    from datetime import datetime
    
    copilot_profile = {
        "id": str(uuid.uuid4()),
        "name": "GitHub Copilot",
        "baseUrl": "https://github.com",
        "apiKey": "copilot-cli-key",  # Placeholder key
        "models": ["gpt-4o", "claude-3.5-sonnet"],
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat()
    }
    
    # Add to profiles
    if 'profiles' not in profiles_data:
        profiles_data['profiles'] = []
    
    profiles_data['profiles'].append(copilot_profile)
    
    # Save back to file
    try:
        with open(profiles_file, 'w', encoding='utf-8') as f:
            json.dump(profiles_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created Copilot profile:")
        print(f"   ID: {copilot_profile['id']}")
        print(f"   Name: {copilot_profile['name']}")
        print(f"   Base URL: {copilot_profile['baseUrl']}")
        print(f"   File: {profiles_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving profiles file: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Creating Copilot API profile...")
    success = create_copilot_profile()
    if success:
        print("\n🎉 Copilot profile created successfully!")
        print("\nNext steps:")
        print("1. Restart the frontend application")
        print("2. Select 'GitHub Copilot' as the provider")
        print("3. The usage indicator should now show Copilot data or errors")
    else:
        print("\n❌ Failed to create Copilot profile")
