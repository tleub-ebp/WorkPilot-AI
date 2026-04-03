#!/usr/bin/env python3
"""
Update Copilot profile with latest models
"""

import json
from pathlib import Path


def update_copilot_profile():
    """Update Copilot profile with latest models"""
    
    profiles_dir = Path.home() / ".claude-ebp" / "profiles"
    profiles_file = profiles_dir / "profiles.json"
    
    # Latest models from PROVIDER_MODELS_MAP
    latest_models = [
        "gpt-5.2",
        "gpt-5",
        "o3",
        "claude-opus-4-6",
        "claude-sonnet-4-5",
        "gpt-4o",
        "o3-mini",
        "claude-3.5-sonnet",
        "gpt-4o-mini"
    ]
    
    # Read existing profiles
    with open(profiles_file, encoding='utf-8') as f:
        profiles_data = json.load(f)
    
    # Update Copilot profile models
    for profile in profiles_data.get('profiles', []):
        if profile.get('name') == 'GitHub Copilot':
            profile['models'] = latest_models
            profile['updatedAt'] = '2025-02-19T14:59:00.000Z'
            print(f"✅ Updated Copilot profile with {len(latest_models)} models:")
            for model in latest_models:
                print(f"   - {model}")
            break
    else:
        print("❌ Copilot profile not found")
        return False
    
    # Save updated profiles
    with open(profiles_file, 'w', encoding='utf-8') as f:
        json.dump(profiles_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved updated profile to: {profiles_file}")
    return True

if __name__ == "__main__":
    update_copilot_profile()
