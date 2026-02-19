import fs from 'node:fs';
import path from 'node:path';
import { ProviderService, type Provider } from '../../../../shared/services/providerService';

// IMPORTANT : La liste des connecteurs est désormais centralisée dans configured_providers.json à la racine du projet.
// Le backend lit déjà ce fichier. Le frontend doit le charger dynamiquement pour garantir la synchronisation.

// Fonction asynchrone pour charger la liste des connecteurs depuis le JSON partagé
export async function getAllConnectors(): Promise<Array<{ id: string, label: string }>> {
  const providers = await ProviderService.getAllProviders();
  return providers.map((p: Provider) => ({ id: p.name, label: p.label }));
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
export async function saveUserProviderConfig(provider: string, config: ProviderConfig) {
  await ProviderService.saveUserProviderConfig(provider, config);
}