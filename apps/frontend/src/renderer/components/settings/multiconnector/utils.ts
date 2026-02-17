import fs from 'node:fs';
import path from 'node:path';

// Utilitaire pour retourner la liste des connecteurs supportés
// IMPORTANT : Garder ces identifiants synchronisés avec la liste canonique du backend (provider_api.py, /providers)
export function getAllConnectors() {
  const connectors = [
    { id: 'anthropic', label: 'Anthropic (Claude)' },
    { id: 'openai', label: 'OpenAI (Chat GPT' },
    { id: 'google', label: 'Google (Gemini)' },
    { id: 'meta', label: 'Meta (Facebook/Meta AI)' },
    { id: 'mistral', label: 'Mistral AI' },
    { id: 'deepseek', label: 'DeepSeek AI' },
    { id: 'aws', label: 'Amazon Web Services (AWS)' },
    { id: 'ollama', label: 'LLM local (Ollama, LM Studio, etc.)' },
  ];

  const seen = new Set();
  const result = [];
  for (const c of connectors) {
    if (!seen.has(c.id)) {
      result.push(c);
      seen.add(c.id);
    }
  }
  return result;
}

// Écrit la liste des providers configurés dans le fichier partagé pour le backend
export function saveConfiguredProviders(providers: { name: string, label: string, description: string }[]) {
  const configPath = path.resolve(__dirname, '../../../../../../configured_providers.json');
  fs.writeFileSync(configPath, JSON.stringify({ providers }, null, 2), 'utf-8');
}

// Ajout d'une interface pour typer l'objet de configuration
interface ProviderConfig {
  api_key?: string;
  base_url?: string;
  validated?: boolean;
}

// Écrit la config d’un provider dans le fichier utilisateur pour le backend
export function saveUserProviderConfig(provider: string, config: ProviderConfig) {
  const configPath = path.resolve(process.env.HOME || process.env.USERPROFILE || '', '.work_pilot_ai_llm_providers.json');
  let allConfigs: Record<string, ProviderConfig> = {};
  if (fs.existsSync(configPath)) {
    try {
      allConfigs = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    } catch {}
  }
  // Merge avec l’existant
  allConfigs[provider] = { ...(allConfigs[provider]), ...config };
  fs.writeFileSync(configPath, JSON.stringify(allConfigs, null, 2), 'utf-8');
}