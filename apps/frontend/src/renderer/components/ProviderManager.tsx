import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const API_BASE = typeof import.meta.env?.VITE_BACKEND_URL ? import.meta.env.VITE_BACKEND_URL : '';

// Squelette de gestion des providers LLM
export const ProviderManager: React.FC<{ selected: string }> = ({ selected }) => {
  const { t } = useTranslation(['providers', 'common']);

  const [_providers, setProviders] = useState<string[]>([]);
  const [_status, setStatus] = useState<Record<string, boolean>>({});
  const [configs, setConfigs] = useState<string[]>([]);
  const [capabilities, setCapabilities] = useState<any>(null);
  const [configForm, setConfigForm] = useState<any>({});
  const [schema, setSchema] = useState<any>(null);
  const [testResult, setTestResult] = useState<string>("");
  const [prompt, setPrompt] = useState<string>("");
  const [generation, setGeneration] = useState<string>("");

  // Ajout : hook pour profils Claude Code
  const [_claudeProfiles, setClaudeProfiles] = useState<any[]>([]);
  const [activeClaudeProfile, setActiveClaudeProfile] = useState<any>(null);
  const [claudeModels, setClaudeModels] = useState<string[]>([]);
  const [claudeAuthChecked, setClaudeAuthChecked] = useState(false);

  // Ajout d'un état pour l'erreur
  const [claudeModelsError, setClaudeModelsError] = useState<string>("");
  const [_providersError, setProvidersError] = useState<string>("");

  useEffect(() => {
    fetch(`${API_BASE}/providers`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Response is not JSON');
        }
        return res.json();
      })
      .then((data) => {
        setProviders(data.providers || []);
        setStatus(data.status || {});
        setProvidersError("");
      })
      .catch((err) => {
        if (err.message === 'Response is not JSON') {
          console.info('[ProviderManager] Backend providers API not available');
        } else {
          console.error('Failed to fetch providers:', err);
        }
        setProviders([]);
        setStatus({});
        setProvidersError(`Erreur lors de la récupération des providers: ${err.message}`);
      });
    fetch(`${API_BASE}/providers/configs`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Response is not JSON');
        }
        return res.json();
      })
      .then((data) => setConfigs(data.configs || []))
      .catch((err) => {
        console.error('Failed to fetch provider configs:', err);
        setConfigs([]);
      });
  }, []);

  useEffect(() => {
    if (selected) {
      fetch(`${API_BASE}/providers/capabilities/${selected}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const contentType = res.headers.get('content-type');
          if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Response is not JSON');
          }
          return res.json();
        })
        .then((data) => setCapabilities(data))
        .catch((err) => {
          console.error('Failed to fetch provider capabilities:', err);
          setCapabilities(null);
        });
    } else {
      setCapabilities(null);
    }
  }, [selected]);

  // Charger le schéma de config quand un provider est sélectionné
  useEffect(() => {
    if (selected) {
      fetch(`${API_BASE}/providers/schema/${selected}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const contentType = res.headers.get('content-type');
          if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Response is not JSON');
          }
          return res.json();
        })
        .then((data) => setSchema(data))
        .catch((err) => {
          console.error('Failed to fetch provider schema:', err);
          setSchema(null);
        });
      fetch(`${API_BASE}/providers/config/${selected}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const contentType = res.headers.get('content-type');
          if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Response is not JSON');
          }
          return res.json();
        })
        .then((data) => setConfigForm(data || {}))
        .catch((err) => {
          console.error('Failed to fetch provider config:', err);
          setConfigForm({});
        });
    } else {
      setSchema(null);
      setConfigForm({});
    }
  }, [selected]);

  // Détection dynamique des profils Claude Code (comme UsageIndicator)
  useEffect(() => {
    if (window.electronAPI?.requestAllProfilesUsage) {
      window.electronAPI.requestAllProfilesUsage().then((result: any) => {
        if (result?.success && result.data) {
          setClaudeProfiles(result.data.allProfiles || []);
          setActiveClaudeProfile(result.data.allProfiles.find((p: any) => p.isActive) || null);
        }
        setClaudeAuthChecked(true);
      }).catch(() => setClaudeAuthChecked(true));
    } else {
      setClaudeAuthChecked(true);
    }
  }, []);

  // Récupération dynamique des modèles pour le provider sélectionné
  useEffect(() => {
    if (!selected) {
      setClaudeModels([]);
      setClaudeModelsError("");
      return;
    }
    fetch(`${API_BASE}/providers/models/${selected}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Response is not JSON');
        }
        return res.json();
      })
      .then((data) => {
        setClaudeModels(data.models || []);
        if (data.error) {
          setClaudeModelsError(data.error);
        } else {
          setClaudeModelsError((data.models?.length === 0) ? `Aucun modèle disponible pour le provider «${selected}».` : "");
        }
      })
      .catch((err) => {
        console.error('Failed to fetch provider models:', err);
        setClaudeModels([]);
        setClaudeModelsError(`Failed to fetch models: ${err.message}`);
      });
  }, [selected]);

  // Ajout/édition de config
  const handleConfigChange = (k: string, v: string) => {
    setConfigForm((f: any) => ({ ...f, [k]: v }));
  };
  const saveConfig = useCallback(() => {
    fetch(`${API_BASE}/providers/config/${selected}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(configForm),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Response is not JSON');
        }
        return res.json();
      })
      .then(() => window.location.reload())
      .catch((err) => {
        console.error('Failed to save provider config:', err);
        setTestResult(`Failed to save config: ${err.message}`);
      });
  }, [selected, configForm]);
  const deleteConfig = useCallback(() => {
    fetch(`${API_BASE}/providers/config/${selected}`, { method: "DELETE" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Response is not JSON');
        }
        return res.json();
      })
      .then(() => window.location.reload())
      .catch((err) => {
        console.error('Failed to delete provider config:', err);
        setTestResult(`Failed to delete config: ${err.message}`);
      });
  }, [selected]);
  const testProvider = useCallback(() => {
    fetch(`${API_BASE}/providers/test/${selected}`, { method: "POST" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Response is not JSON');
        }
        return res.json();
      })
      .then((data) => setTestResult(data.status || data.detail || JSON.stringify(data)))
      .catch((err) => {
        console.error('Failed to test provider:', err);
        setTestResult(`Failed to test: ${err.message}`);
      });
  }, [selected]);
  const handlePrompt = (e: React.ChangeEvent<HTMLInputElement>) => setPrompt(e.target.value);
  const generate = useCallback(() => {
    fetch(`${API_BASE}/providers/generate/${selected}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Response is not JSON');
        }
        return res.json();
      })
      .then((data) => setGeneration(data.result || data.detail || JSON.stringify(data)))
      .catch((err) => {
        console.error('Failed to generate text:', err);
        setGeneration(`Failed to generate: ${err.message}`);
      });
  }, [selected, prompt]);

  return (
    <div>
      <h2>{t('providers:title', 'Gestion des providers LLM')}</h2>
      {/* Affichage état Claude Code comme UsageIndicator */}
      {claudeAuthChecked && (
        <div style={{ marginBottom: 12 }}>
          <b>{t('providers:claudeCodeState', 'État Claude Code')}&nbsp;:</b>
          {activeClaudeProfile?.isAuthenticated ? (
            <span style={{ color: 'green', marginLeft: 8 }}>
              {t('providers:authenticated', 'Authentifié')} ({activeClaudeProfile.profileName || activeClaudeProfile.profileEmail})
            </span>
          ) : (
            <span style={{ color: 'orange', marginLeft: 8 }}>
              {t('providers:notAuthenticated', 'Non authentifié')}
            </span>
          )}
        </div>
      )}
      {selected && (
        <div style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}>
          <h4>{t('providers:availableModels', 'Modèles disponibles pour «' + selected + '»', { provider: selected })}</h4>
          {claudeModelsError ? (
            <span style={{ color: 'red' }}>{t('providers:modelError', claudeModelsError, { error: claudeModelsError })}</span>
          ) : claudeModels.length > 0 ? (
            <ul>
              {claudeModels.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          ) : (
            <span style={{ color: 'orange' }}>{t('providers:noModels', 'Aucun modèle détecté ou chargement...')}</span>
          )}
        </div>
      )}
      <div>
        <h3>{t('providers:savedConfigs', 'Configurations enregistrées :')}</h3>
        <ul>
          {configs.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </div>
      {selected && capabilities && (
        <div>
          <h3>{t('providers:providerCapabilities', 'Capacités du provider «' + selected + '» :', { provider: selected })}</h3>
          <pre
            style={{
              background: "#f5f5f5",
              padding: 8,
            }}
          >
            {JSON.stringify(capabilities, null, 2)}
          </pre>
        </div>
      )}
      {selected && schema && (
        <div style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}>
          <h4>{t('providers:configureProvider', 'Configurer «' + selected + '»', { provider: selected })}</h4>
          {Object.entries(schema).map(([k, v]) => (
            <div key={k} style={{ marginBottom: 8 }}>
              <label>{t(`providers:configField_${k}`, k, { field: k })} ({String(v)})</label>
              <input
                type="text"
                value={configForm[k] || ""}
                onChange={e => handleConfigChange(k, e.target.value)}
                style={{ marginLeft: 8 }}
              />
            </div>
          ))}
          <button onClick={saveConfig}>{t('common:save', 'Enregistrer')}</button>
          <button onClick={deleteConfig} style={{ marginLeft: 8 }}>{t('common:delete', 'Supprimer')}</button>
          <button onClick={testProvider} style={{ marginLeft: 8 }}>{t('common:test', 'Tester')}</button>
          {testResult && <span style={{ marginLeft: 8 }}>{testResult}</span>}
        </div>
      )}
      {selected && (
        <div style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}>
          <h4>{t('providers:generateWithProvider', 'Générer avec «' + selected + '»', { provider: selected })}</h4>
          <input
            type="text"
            value={prompt}
            onChange={handlePrompt}
            placeholder={t('providers:promptPlaceholder', 'Prompt...')}
            style={{ width: 300 }}
          />
          <button onClick={generate} style={{ marginLeft: 8 }}>{t('common:generate', 'Générer')}</button>
          {generation && <pre style={{ background: "#f5f5f5", padding: 8 }}>{generation}</pre>}
        </div>
      )}
      {/* TODO: Améliorer la gestion des erreurs et des états de chargement */}
    </div>
  );
};