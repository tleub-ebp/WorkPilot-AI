#!/usr/bin/env python3
"""
Create Copilot profile with proper UTF-8 encoding
"""

import json
from pathlib import Path

def create_copilot_profile():
    """Create Copilot profile with proper encoding"""
    
    profiles_dir = Path.home() / ".claude-ebp" / "profiles"
    profiles_file = profiles_dir / "profiles.json"
    
    # Ensure directory exists
    profiles_dir.mkdir(parents=True, exist_ok=True)
    
    # Create profile data
    profiles_data = {
        "profiles": [
            {
                "id": "copilot-profile-001",
                "name": "GitHub Copilot",
                "baseUrl": "https://github.com",
                "apiKey": "copilot-cli-key",
                "models": ["gpt-4o", "claude-3.5-sonnet"],
                "createdAt": "2025-02-19T14:55:00.000Z",
                "updatedAt": "2025-02-19T14:55:00.000Z"
            }
        ],
        "activeProfileId": "copilot-profile-001"
    }
    
    # Write with UTF-8 encoding (no BOM)
    with open(profiles_file, 'w', encoding='utf-8') as f:
        json.dump(profiles_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created Copilot profile at: {profiles_file}")
    return True

if __name__ == "__main__":
    create_copilot_profile()
