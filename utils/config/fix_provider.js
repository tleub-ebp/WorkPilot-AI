
// Script to set provider to copilot
// Run this in the browser console when the app is open

localStorage.setItem('selectedProvider', 'copilot');
console.log('✅ Provider set to copilot');
console.log('🔄 Refresh the page to see changes');

// Verify it was set
console.log('Current provider:', localStorage.getItem('selectedProvider'));
