// Ajoute le type global pour window.electronAPI avec createClaudeProfileDirectory
interface ElectronAPI {
  createClaudeProfileDirectory: (profileName: string) => Promise<{ success: boolean; data?: string; error?: string }>;
  requestUsageUpdate: (providerName?: string) => Promise<{ success: boolean; data?: any }>; // Ajout du paramètre providerName
  // ...autres méthodes existantes...
}

interface Window {
  electronAPI: ElectronAPI;
}