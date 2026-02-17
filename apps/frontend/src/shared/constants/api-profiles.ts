export type ApiProviderPreset = {
  id: string;
  baseUrl: string;
  labelKey: string;
};

export const API_PROVIDER_PRESETS: readonly ApiProviderPreset[] = [
  {
    id: 'anthropic',
    baseUrl: 'https://api.anthropic.com',
    labelKey: 'settings:apiProfiles.presets.anthropic'
  },
  {
    id: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    labelKey: 'settings:apiProfiles.presets.openai'
  },
  {
    id: 'mistral',
    baseUrl: 'https://api.mistral.ai/v1',
    labelKey: 'settings:apiProfiles.presets.mistral'
  },
  {
    id: 'grok',
    baseUrl: 'https://api.grok.x.ai/v1',
    labelKey: 'settings:apiProfiles.presets.grok'
  },
  {
    id: 'gemini',
    // Google AI Studio (la plus courante)
    // Base URL officielle pour l'API Gemini REST (Google)
    // Base URL : https://generativelanguage.googleapis.com/v1beta/
    // Endpoint type : models/{model}:generateContent
    // Exemple d'appel complet :
    //   https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=VOTRE_CLE_API
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    labelKey: 'settings:apiProfiles.presets.gemini'
  },
  {
    id: 'cohere',
    baseUrl: 'https://api.cohere.ai/v1',
    labelKey: 'settings:apiProfiles.presets.cohere'
  },
  {
    id: 'openrouter',
    baseUrl: 'https://openrouter.ai/api',
    labelKey: 'settings:apiProfiles.presets.openrouter'
  },
  {
    id: 'groq',
    baseUrl: 'https://api.groq.com/openai/v1',
    labelKey: 'settings:apiProfiles.presets.groq'
  },
  {
    id: 'ollama',
    baseUrl: 'http://localhost:11434/v1',
    labelKey: 'settings:apiProfiles.presets.ollama'
  }
];