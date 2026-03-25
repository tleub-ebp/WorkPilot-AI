/**
 * Custom MCP Server Dialog
 *
 * Dialog for adding/editing custom MCP servers.
 * Supports both command-based (npx/npm) and HTTP-based servers.
 */

import { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { useTranslation } from 'react-i18next';
import type { CustomMcpServer } from '../../shared/types';
import { Terminal, Globe, X, ExternalLink } from 'lucide-react';

interface CustomMcpDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly server: CustomMcpServer | null; // null = create new, non-null = edit
  readonly existingIds: string[]; // Existing server IDs for validation
  readonly onSave: (server: CustomMcpServer) => void;
}

export function CustomMcpDialog({
  open,
  onOpenChange,
  server,
  existingIds,
  onSave
}: CustomMcpDialogProps) {
  const { t } = useTranslation(['settings', 'common']);
  const isEditing = server !== null;

  const [formData, setFormData] = useState<CustomMcpServer>({
    id: '',
    name: '',
    type: 'command',
    command: 'npx',
    args: [],
    url: '',
    headers: {},
    description: '',
  });

  const [argsInput, setArgsInput] = useState('');
  const [headerKey, setHeaderKey] = useState('');
  const [headerValue, setHeaderValue] = useState('');
  const [bearerToken, setBearerToken] = useState('');
  const [showAdvancedHeaders, setShowAdvancedHeaders] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Known provider patterns for helpful hints
  const urlHint = useMemo(() => {
    const url = formData.url?.toLowerCase() || '';
    if (url.includes('github')) {
      return {
        provider: 'GitHub',
        icon: Globe,
        message: t('mcp.hints.github'),
        link: 'https://github.com/settings/tokens',
        linkText: t('mcp.hints.createGithubPat'),
      };
    }
    if (url.includes('google') || url.includes('googleapis')) {
      return {
        provider: 'Google',
        icon: Globe,
        message: t('mcp.hints.google'),
        link: 'https://console.cloud.google.com/apis/credentials',
        linkText: t('mcp.hints.createGoogleToken'),
      };
    }
    if (url.includes('anthropic')) {
      return {
        provider: 'Anthropic',
        icon: Globe,
        message: t('mcp.hints.anthropic'),
        link: 'https://console.anthropic.com/settings/keys',
        linkText: t('mcp.hints.createAnthropicKey'),
      };
    }
    if (url.includes('openai')) {
      return {
        provider: 'OpenAI',
        icon: Globe,
        message: t('mcp.hints.openai'),
        link: 'https://platform.openai.com/api-keys',
        linkText: t('mcp.hints.createOpenaiKey'),
      };
    }
    return null;
  }, [formData.url, t]);

  // Reset form when dialog opens/closes or server changes
  useEffect(() => {
    if (open && server) {
      setFormData(server);
      setArgsInput(server.args?.join(' ') || '');
      // Extract bearer token from existing Authorization header
      const authHeader = server.headers?.['Authorization'] || server.headers?.['authorization'] || '';
      if (authHeader.toLowerCase().startsWith('bearer ')) {
        setBearerToken(authHeader.substring(7));
      } else {
        setBearerToken('');
      }
      // Show advanced headers if there are non-Authorization headers
      const hasOtherHeaders = Object.keys(server.headers || {}).some(
        k => k.toLowerCase() !== 'authorization'
      );
      setShowAdvancedHeaders(hasOtherHeaders);
      setError(null);
    } else if (open) {
      setFormData({
        id: '',
        name: '',
        type: 'command',
        command: 'npx',
        args: [],
        url: '',
        headers: {},
        description: '',
      });
      setArgsInput('');
      setBearerToken('');
      setShowAdvancedHeaders(false);
      setError(null);
    }
    setHeaderKey('');
    setHeaderValue('');
  }, [open, server]);

  // Generate ID from name
  const generateId = (name: string): string => {
    return name.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-').replaceAll(/^-|-$/g, '');
  };

  // Validation functions
  const validateForm = (): string | null => {
    if (!formData.name.trim()) {
      return t('mcp.errorNameRequired');
    }

    const generatedId = isEditing ? formData.id : generateId(formData.name);

    // Check for duplicate ID (only when creating new)
    if (!isEditing && existingIds.includes(generatedId)) {
      return t('mcp.errorIdExists');
    }

    if (formData.type === 'command' && !formData.command?.trim()) {
      return t('mcp.errorCommandRequired');
    }

    if (formData.type === 'http' && !formData.url?.trim()) {
      return t('mcp.errorUrlRequired');
    }

    return null;
  };

  // Header processing functions
  const buildHeaders = (): Record<string, string> => {
    if (formData.type !== 'http') {
      return {};
    }

    const finalHeaders: Record<string, string> = {};
    
    // Copy existing headers (excluding old Authorization if we have a new bearer token)
    if (formData.headers) {
      for (const [key, value] of Object.entries(formData.headers)) {
        if (bearerToken && key.toLowerCase() === 'authorization') {
          continue; // Skip old auth header if we have a new bearer token
        }
        finalHeaders[key] = value;
      }
    }
    
    // Add bearer token as Authorization header
    if (bearerToken.trim()) {
      finalHeaders['Authorization'] = `Bearer ${bearerToken.trim()}`;
    }

    return finalHeaders;
  };

  // Server object creation
  const createServerToSave = (generatedId: string): CustomMcpServer => {
    const headers = buildHeaders();
    
    return {
      id: generatedId,
      name: formData.name.trim(),
      type: formData.type,
      description: formData.description?.trim() || undefined,
      ...(formData.type === 'command'
        ? {
            command: formData.command,
            args: argsInput.split(' ').filter(Boolean),
          }
        : {
            url: formData.url,
            headers: Object.keys(headers).length > 0 ? headers : undefined,
          }),
    };
  };

  const handleSave = () => {
    // Validate form
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    const generatedId = isEditing ? formData.id : generateId(formData.name);
    const serverToSave = createServerToSave(generatedId);

    onSave(serverToSave);
    onOpenChange(false);
  };

  const addHeader = () => {
    if (headerKey.trim() && headerValue.trim()) {
      setFormData(prev => ({
        ...prev,
        headers: { ...prev.headers, [headerKey.trim()]: headerValue.trim() },
      }));
      setHeaderKey('');
      setHeaderValue('');
    }
  };

  const removeHeader = (key: string) => {
    setFormData(prev => {
      const newHeaders = { ...prev.headers };
      delete newHeaders[key];
      return { ...prev, headers: newHeaders };
    });
  };

  const isValid = formData.name.trim() && (
    (formData.type === 'command' && formData.command?.trim()) ||
    (formData.type === 'http' && formData.url?.trim())
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? t('mcp.editCustomServer') : t('mcp.addCustomServer')}
          </DialogTitle>
          <DialogDescription>
            {t('mcp.customServerDescription')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Error message */}
          {error && (
            <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded">
              {error}
            </div>
          )}

          {/* Server Type */}
          <div className="space-y-2">
            <Label>{t('mcp.serverType')}</Label>
            <RadioGroup
              value={formData.type}
              onValueChange={(value: 'command' | 'http') =>
                setFormData(prev => ({ ...prev, type: value }))
              }
              className="flex gap-4"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem value="command" id="type-command" />
                <Label htmlFor="type-command" className="flex items-center gap-1.5 cursor-pointer">
                  <Terminal className="h-3.5 w-3.5" />
                  {t('mcp.typeCommand')}
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="http" id="type-http" />
                <Label htmlFor="type-http" className="flex items-center gap-1.5 cursor-pointer">
                  <Globe className="h-3.5 w-3.5" />
                  {t('mcp.typeHttp')}
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">{t('mcp.serverName')}</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => {
                setFormData(prev => ({ ...prev, name: e.target.value }));
                setError(null);
              }}
              placeholder={t('mcp.serverNamePlaceholder')}
            />
            {!isEditing && formData.name && (
              <p className="text-xs text-muted-foreground">
                ID: {generateId(formData.name) || '...'}
              </p>
            )}
          </div>

          {/* Description (optional) */}
          <div className="space-y-2">
            <Label htmlFor="description">
              {t('mcp.serverDescription')} <span className="text-muted-foreground">({t('common:optional')})</span>
            </Label>
            <Input
              id="description"
              value={formData.description || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder={t('mcp.serverDescriptionPlaceholder')}
            />
          </div>

          {/* Command-based fields */}
          {formData.type === 'command' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="command">{t('mcp.command')}</Label>
                <Input
                  id="command"
                  value={formData.command || ''}
                  onChange={(e) => {
                    setFormData(prev => ({ ...prev, command: e.target.value }));
                    setError(null);
                  }}
                  placeholder="npx"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="args">{t('mcp.args')}</Label>
                <Input
                  id="args"
                  value={argsInput}
                  onChange={(e) => setArgsInput(e.target.value)}
                  placeholder="-y @myorg/my-mcp-server"
                />
                <p className="text-xs text-muted-foreground">{t('mcp.argsHint')}</p>
              </div>
            </>
          )}

          {/* HTTP-based fields */}
          {formData.type === 'http' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="url">{t('mcp.url')}</Label>
                <Input
                  id="url"
                  value={formData.url || ''}
                  onChange={(e) => {
                    setFormData(prev => ({ ...prev, url: e.target.value }));
                    setError(null);
                  }}
                  placeholder="https://mcp.example.com/mcp"
                />
              </div>

              {/* URL-based hint for known providers */}
              {urlHint && (
                <div className="flex items-start gap-2 p-3 bg-muted/50 rounded-lg border border-border">
                  <urlHint.icon className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-muted-foreground">{urlHint.message}</p>
                    <a
                      href={urlHint.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-primary hover:underline mt-1"
                      onClick={(e) => {
                        e.preventDefault();
                        globalThis.electronAPI?.openExternal(urlHint.link);
                      }}
                    >
                      {urlHint.linkText}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              )}

              {/* Authentication Token (simplified) */}
              <div className="space-y-2">
                <Label htmlFor="bearerToken">
                  {t('mcp.authToken')} <span className="text-muted-foreground">({t('common:optional')})</span>
                </Label>
                <Input
                  id="bearerToken"
                  value={bearerToken}
                  onChange={(e) => setBearerToken(e.target.value)}
                  placeholder={t('mcp.authTokenPlaceholder')}
                  type="password"
                />
                <p className="text-xs text-muted-foreground">{t('mcp.authTokenHint')}</p>
              </div>

              {/* Advanced Headers (collapsible) */}
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setShowAdvancedHeaders(!showAdvancedHeaders)}
                  className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <span className={`transition-transform ${showAdvancedHeaders ? 'rotate-90' : ''}`}>▶</span>
                  {t('mcp.advancedHeaders')}
                </button>

                {showAdvancedHeaders && (
                  <div className="pl-4 space-y-2">
                    <div className="flex gap-2">
                      <Input
                        value={headerKey}
                        onChange={(e) => setHeaderKey(e.target.value)}
                        placeholder={t('mcp.headerName')}
                        className="flex-1"
                      />
                      <Input
                        value={headerValue}
                        onChange={(e) => setHeaderValue(e.target.value)}
                        placeholder={t('mcp.headerValue')}
                        className="flex-1"
                        type="password"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={addHeader}
                        disabled={!headerKey.trim() || !headerValue.trim()}
                      >
                        {t('common:add')}
                      </Button>
                    </div>
                    {/* Show non-Authorization headers */}
                    {Object.entries(formData.headers || {}).some(([key]) => key.toLowerCase() !== 'authorization') && (
                      <div className="space-y-1 mt-2">
                        {Object.entries(formData.headers || {})
                          .filter(([key]) => key.toLowerCase() !== 'authorization')
                          .map(([key, value]) => (
                            <div key={key} className="flex items-center justify-between text-sm bg-muted px-2 py-1 rounded">
                              <span>
                                <span className="font-medium">{key}:</span>{' '}
                                <span className="text-muted-foreground">
                                  {value.length > 20 ? `${value.substring(0, 20)}...` : value}
                                </span>
                              </span>
                              <button type="button"
                                onClick={() => removeHeader(key)}
                                className="text-muted-foreground hover:text-destructive transition-colors"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common:cancel')}
          </Button>
          <Button onClick={handleSave} disabled={!isValid}>
            {isEditing ? t('common:save') : t('mcp.addServer')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
