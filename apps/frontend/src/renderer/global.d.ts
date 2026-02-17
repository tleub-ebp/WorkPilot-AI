// Ajoute le type global pour window.electronAPI avec createClaudeProfileDirectory
interface ElectronAPI {
  createClaudeProfileDirectory: (profileName: string) => Promise<{ success: boolean; data?: string; error?: string }>;
  // ...autres méthodes existantes...
}

interface Window {
  electronAPI: ElectronAPI;
}
