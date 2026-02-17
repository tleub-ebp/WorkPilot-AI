// Types unifiés pour la gestion multi-connecteur
export type LLMProvider = 'claude' | 'openai' | 'mistral' | 'grok' | 'gemini' | 'cohere' | 'openrouter' | 'groq' | 'ollama' | string;

export interface MultiConnectorAccount {
  id: string;
  provider: LLMProvider;
  name: string;
  apiKey?: string;
  baseUrl?: string;
  email?: string;
  status: 'connected' | 'disconnected' | 'error' | 'pending';
  isActive: boolean;
  createdAt?: number;
  updatedAt?: number;
  // Ajoutez d'autres champs spécifiques si besoin
}

export interface MultiConnectorProvider {
  provider: LLMProvider;
  label: string;
  logoUrl?: string;
  accounts: MultiConnectorAccount[];
  canAddMultiple: boolean;
  docUrl?: string;
}
