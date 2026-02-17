import fs from 'node:fs';
import path from 'node:path';

// IMPORTANT : La liste des connecteurs est désormais centralisée dans configured_providers.json à la racine du projet.
// Le backend lit déjà ce fichier. Le frontend doit le charger dynamiquement pour garantir la synchronisation.

// Fonction asynchrone pour charger la liste des connecteurs depuis le JSON partagé
export async function getAllConnectors(): Promise<Array<{ id: string, label: string }>> {
  try {
    // En Electron, fetch fonctionne aussi en file://, sinon fallback HTTP
    let response;
    try {
      response = await fetch('/configured_providers.json');
      if (!response.ok) throw new Error('HTTP error');
    } catch {
      // Fallback local (dev ou test)
      const fs = await import('node:fs/promises');
      const path = await import('node:path');
      const configPath = path.resolve(__dirname, '../../../../../../configured_providers.json');
      const data = await fs.readFile(configPath, 'utf-8');
      response = { json: () => JSON.parse(data) };
    }
    const data = await response.json();
    return (data.providers || []).map((p: any) => ({ id: p.name, label: p.label }));
  } catch (e) {
    // Fallback statique si tout échoue (évite crash UI)
    return [
      { id: 'anthropic', label: 'Anthropic (Claude)' },
      { id: 'openai', label: 'OpenAI (Chat GPT)' },
      { id: 'google', label: 'Google DeepMind (Gemini)' },
      { id: 'meta', label: 'Meta (Facebook/Meta AI)' },
      { id: 'mistral', label: 'Mistral AI' },
      { id: 'deepseek', label: 'DeepSeek AI' },
      { id: 'aws', label: 'Amazon Web Services (AWS)' },
      { id: 'ollama', label: 'LLM local (Ollama, LM Studio, etc.)' }
    ];
  }
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