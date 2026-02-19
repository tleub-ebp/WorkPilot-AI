#!/usr/bin/env python3
"""
Check and fix localStorage provider selection
"""

import json
from pathlib import Path

def check_provider_context():
    """Check what provider is currently selected"""
    
    print("🔍 Checking current provider selection...")
    
    # The frontend uses localStorage which is stored in a file
    # For Electron, localStorage is typically stored in:
    # %APPDATA%\electron-app-name\Local Storage\leveldb
    
    # Since we can't easily access localStorage from Python,
    # let's create a simple HTML file to check it
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Check Provider Selection</title>
</head>
<body>
    <h1>Provider Selection Check</h1>
    <div id="result"></div>
    
    <script>
        // Check current provider
        const currentProvider = localStorage.getItem('selectedProvider');
        const result = document.getElementById('result');
        
        if (currentProvider) {
            result.innerHTML = `
                <p><strong>Current selectedProvider:</strong> ${currentProvider}</p>
                <p><strong>Is Copilot?</strong> ${currentProvider === 'copilot' ? '✅ YES' : '❌ NO'}</p>
            `;
            
            // If not copilot, offer to set it
            if (currentProvider !== 'copilot') {
                result.innerHTML += `
                    <button onclick="setCopilot()">Set to Copilot</button>
                `;
            }
        } else {
            result.innerHTML = `
                <p><strong>No provider selected in localStorage</strong></p>
                <button onclick="setCopilot()">Set to Copilot</button>
            `;
        }
        
        function setCopilot() {
            localStorage.setItem('selectedProvider', 'copilot');
            location.reload();
        }
    </script>
</body>
</html>
    """
    
    with open('check_provider.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Created check_provider.html")
    print("📝 Open this file in a browser to check the current provider selection")
    print("🔧 If it's not set to 'copilot', click the button to set it")
    
    return True

def create_provider_fix_script():
    """Create a script to help fix the provider selection"""
    
    script_content = """
// Script to set provider to copilot
// Run this in the browser console when the app is open

localStorage.setItem('selectedProvider', 'copilot');
console.log('✅ Provider set to copilot');
console.log('🔄 Refresh the page to see changes');

// Verify it was set
console.log('Current provider:', localStorage.getItem('selectedProvider'));
"""
    
    with open('fix_provider.js', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("✅ Created fix_provider.js")
    print("📝 Copy and paste this script in the browser console when the app is open")
    
    return True

if __name__ == "__main__":
    print("🔧 Provider Selection Fix Tools")
    print("=" * 40)
    
    check_provider_context()
    print()
    create_provider_fix_script()
    
    print("\n🎯 To fix the issue:")
    print("1. Open the frontend application")
    print("2. Open check_provider.html in a browser")
    print("3. If provider is not 'copilot', click the button")
    print("4. OR run the fix_provider.js script in the browser console")
    print("5. Refresh the frontend application")
    print("\n💡 Alternative: The issue might be that the frontend needs to be restarted")
    print("   to pick up the new Copilot profile we created.")
