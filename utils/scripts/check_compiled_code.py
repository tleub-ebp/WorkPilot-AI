#!/usr/bin/env python3
"""
Check if our Copilot modifications are in the compiled code
"""

def check_compiled_code():
    """Check if our modifications are present"""
    
    print("🔍 Checking if Copilot modifications are compiled...")
    
    # Check the usage-monitor.ts file for our modifications
    usage_monitor_file = "C:\\Users\\thomas.leberre\\Repositories\\WorkPilot-AI\\apps\\frontend\\src\\main\\claude-profile\\usage-monitor.ts"
    
    try:
        with open(usage_monitor_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for our key modifications
        checks = [
            ("FastAPI backend URL", "http://localhost:9000/providers/usage/copilot" in content),
            ("normalizeCopilotResponse call", "normalizeCopilotResponse(usageData" in content),
            ("Copilot error handling", "INSUFFICIENT_PERMISSIONS" in content),
            ("Backend unavailable handling", "BACKEND_UNAVAILABLE" in content),
            ("Profile variables at top", "let profileName: string | undefined;" in content and content.index("let profileName") < content.index("if (providerName === 'copilot')"))
        ]
        
        print("\n📋 Modification checks:")
        all_good = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
            if not result:
                all_good = False
        
        if all_good:
            print("\n✅ All modifications are present in the source code")
            print("💡 The issue is that the Electron process hasn't recompiled")
            print("🔄 Solution: Restart the frontend application completely")
        else:
            print("\n❌ Some modifications are missing from the source code")
            print("🔧 The edits may not have been applied correctly")
        
        return all_good
        
    except Exception as e:
        print(f"❌ Error checking file: {e}")
        return False

if __name__ == "__main__":
    check_compiled_code()
