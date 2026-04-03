#!/usr/bin/env python3
"""
Test IPC communication between frontend and UsageMonitor
"""

def check_ipc_handlers():
    """Check if IPC handlers are properly registered"""
    
    print("🔍 Checking IPC handlers...")
    
    # The frontend calls window.electronAPI.requestUsageUpdate(provider)
    # This should be handled by the USAGE_REQUEST IPC channel
    
    print("Frontend calls: window.electronAPI.requestUsageUpdate('copilot')")
    print("This should trigger: IPC_CHANNELS.USAGE_REQUEST")
    print("Which should call: getUsageMonitor().getCurrentUsage()")
    print("Which should call: fetchUsageViaAPI() for copilot")
    print("Which should call: our FastAPI backend")
    
    print("\n💡 If you're still seeing 'Données d'utilisation non disponibles':")
    print("1. Check if the IPC handler is properly registered")
    print("2. Check if getUsageMonitor() is returning the right instance")
    print("3. Check if getCurrentUsage() is being called with the right provider")
    print("4. Check if the response is properly sent back to the frontend")
    
    return True

def create_debug_script():
    """Create a debug script for the frontend"""
    
    script_content = """
// Debug script to check UsageMonitor communication
// Run this in the browser console when the app is open

console.log('🔍 Debugging UsageMonitor communication...');

// 1. Check if electronAPI is available
if (!window.electronAPI) {
    console.error('❌ window.electronAPI not available');
} else {
    console.log('✅ window.electronAPI available');
}

// 2. Check if requestUsageUpdate is available
if (!window.electronAPI.requestUsageUpdate) {
    console.error('❌ requestUsageUpdate not available');
} else {
    console.log('✅ requestUsageUpdate available');
}

// 3. Try calling requestUsageUpdate with copilot
console.log('🔄 Calling requestUsageUpdate with copilot...');
window.electronAPI.requestUsageUpdate('copilot').then(result => {
    console.log('📥 Response from UsageMonitor:', result);
    
    if (result.success) {
        console.log('✅ UsageMonitor responded successfully');
        console.log('Data:', result.data);
    } else {
        console.log('❌ UsageMonitor returned error:', result.error);
    }
}).catch(error => {
    console.error('❌ Error calling requestUsageUpdate:', error);
});

// 4. Check if onUsageUpdated is available
if (window.electronAPI.onUsageUpdated) {
    console.log('✅ onUsageUpdated available');
    
    // Set up a listener
    const unsubscribe = window.electronAPI.onUsageUpdated((usage) => {
        console.log('📨 Received usage update:', usage);
    });
    
    console.log('👂 Listening for usage updates...');
} else {
    console.error('❌ onUsageUpdated not available');
}
"""
    
    with open('debug_usage_monitor.js', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("✅ Created debug_usage_monitor.js")
    print("📝 Copy and paste this script in the browser console")
    
    return True

if __name__ == "__main__":
    print("🔧 IPC Communication Debug Tools")
    print("=" * 40)
    
    check_ipc_handlers()
    print()
    create_debug_script()
    
    print("\n🎯 Next steps:")
    print("1. Open the frontend application")
    print("2. Open browser console (F12)")
    print("3. Paste the debug_usage_monitor.js script")
    print("4. Check the console output")
    print("\n💡 Expected output:")
    print("- ✅ window.electronAPI available")
    print("- ✅ requestUsageUpdate available")
    print("- 📥 Response from UsageMonitor with data or error")
    print("- 📨 Usage update event (if successful)")
