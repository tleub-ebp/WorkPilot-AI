
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
