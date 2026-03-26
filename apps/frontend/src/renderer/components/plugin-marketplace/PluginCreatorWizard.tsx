import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Bot,
  Plug,
  FileCode,
  Palette,
  MessageSquareText,
  Sparkles,
  Copy,
  FolderOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PluginType } from '@shared/types/plugin-marketplace';

// ============================================
// Types
// ============================================

interface PluginFormData {
  type: PluginType | null;
  id: string;
  name: string;
  description: string;
  version: string;
  // Agent-specific
  systemPrompt: string;
  triggerKeywords: string;
  // Integration-specific
  authType: 'none' | 'apikey' | 'oauth' | 'basic';
  apiEndpoint: string;
  // Theme-specific
  primaryColor: string;
  backgroundColor: string;
  // Spec template / Custom prompt
  templateContent: string;
}

const INITIAL_FORM: PluginFormData = {
  type: null,
  id: '',
  name: '',
  description: '',
  version: '1.0.0',
  systemPrompt: '',
  triggerKeywords: '',
  authType: 'none',
  apiEndpoint: '',
  primaryColor: '#8b5cf6',
  backgroundColor: '#0a0a1a',
  templateContent: '',
};

// ============================================
// Plugin type cards config
// ============================================

const PLUGIN_TYPE_OPTIONS: Array<{
  type: PluginType;
  icon: React.ElementType;
  color: string;
  descKey: string;
}> = [
  { type: 'agent', icon: Bot, color: '#8b5cf6', descKey: 'common:pluginMarketplace.creator.typeDescAgent' },
  { type: 'integration', icon: Plug, color: '#3b82f6', descKey: 'common:pluginMarketplace.creator.typeDescIntegration' },
  { type: 'spec-template', icon: FileCode, color: '#10b981', descKey: 'common:pluginMarketplace.creator.typeDescSpecTemplate' },
  { type: 'theme', icon: Palette, color: '#f97316', descKey: 'common:pluginMarketplace.creator.typeDescTheme' },
  { type: 'custom-prompt', icon: MessageSquareText, color: '#ec4899', descKey: 'common:pluginMarketplace.creator.typeDescCustomPrompt' },
];

// ============================================
// Helpers
// ============================================

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function generateConfigPreview(form: PluginFormData): string {
  const base: Record<string, unknown> = {
    id: form.id || 'my-plugin',
    name: form.name || 'My Plugin',
    type: form.type,
    version: form.version,
    description: form.description || 'A WorkPilot plugin',
  };

  if (form.type === 'agent') {
    base.systemPrompt = form.systemPrompt || 'You are an expert at...';
    if (form.triggerKeywords.trim()) {
      base.triggers = form.triggerKeywords.split(',').map((k) => k.trim()).filter(Boolean);
    }
  } else if (form.type === 'integration') {
    base.authType = form.authType;
    if (form.apiEndpoint) base.apiEndpoint = form.apiEndpoint;
  } else if (form.type === 'theme') {
    base.themeData = {
      '--color-primary': form.primaryColor,
      '--color-background': form.backgroundColor,
    };
  } else if (form.type === 'spec-template' || form.type === 'custom-prompt') {
    base.content = form.templateContent || '# Your content here...';
  }

  const lines = ['// plugin.config.ts', `export default ${JSON.stringify(base, null, 2)};`];
  return lines.join('\n');
}

// ============================================
// Step components
// ============================================

function StepTypeSelection({
  selected,
  onSelect,
  t,
}: {
  selected: PluginType | null;
  onSelect: (type: PluginType) => void;
  t: (key: string) => string;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t('common:pluginMarketplace.creator.selectTypeDesc')}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {PLUGIN_TYPE_OPTIONS.map(({ type, icon: Icon, color, descKey }) => (
          <button
            key={type}
            type="button"
            onClick={() => onSelect(type)}
            className={cn(
              'flex items-start gap-3 p-4 rounded-xl border-2 text-left transition-all',
              selected === type
                ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                : 'border-border hover:border-primary/40 hover:bg-accent/50'
            )}
          >
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
              style={{ backgroundColor: `${color}20` }}
            >
              <Icon className="h-5 w-5" style={{ color }} />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold">{type}</p>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                {t(descKey)}
              </p>
            </div>
            {selected === type && (
              <Check className="h-4 w-4 text-primary shrink-0 mt-0.5 ml-auto" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function StepDetails({
  form,
  onChange,
  t,
}: {
  form: PluginFormData;
  onChange: (updates: Partial<PluginFormData>) => void;
  t: (key: string) => string;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t('common:pluginMarketplace.creator.detailsDesc')}
      </p>

      {/* Name → auto-generates id */}
      <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
        <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldName')}</label>
        <input
          type="text"
          value={form.name}
          onChange={(e) =>
            onChange({ name: e.target.value, id: slugify(e.target.value) })
          }
          placeholder="My Awesome Plugin"
          className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </div>

      <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
        <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldId')}</label>
        <input
          type="text"
          value={form.id}
          onChange={(e) => onChange({ id: e.target.value })}
          placeholder="my-awesome-plugin"
          className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
        <p className="text-[10px] text-muted-foreground">
          {t('common:pluginMarketplace.creator.fieldIdHint')}
        </p>
      </div>

      <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
        <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldDescription')}</label>
        <textarea
          value={form.description}
          onChange={(e) => onChange({ description: e.target.value })}
          placeholder={t('common:pluginMarketplace.creator.fieldDescriptionPlaceholder')}
          rows={2}
          className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
        />
      </div>

      <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
        <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldVersion')}</label>
        <input
          type="text"
          value={form.version}
          onChange={(e) => onChange({ version: e.target.value })}
          placeholder="1.0.0"
          className="w-48 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </div>

      {/* Type-specific fields */}
      {form.type === 'agent' && (
        <>
          <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
            <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldSystemPrompt')}</label>
            <textarea
              value={form.systemPrompt}
              onChange={(e) => onChange({ systemPrompt: e.target.value })}
              placeholder={t('common:pluginMarketplace.creator.fieldSystemPromptPlaceholder')}
              rows={4}
              className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
            />
          </div>
          <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
            <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldTriggers')}</label>
            <input
              type="text"
              value={form.triggerKeywords}
              onChange={(e) => onChange({ triggerKeywords: e.target.value })}
              placeholder={t('common:pluginMarketplace.creator.fieldTriggersPlaceholder')}
              className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <p className="text-[10px] text-muted-foreground">
              {t('common:pluginMarketplace.creator.fieldTriggersHint')}
            </p>
          </div>
        </>
      )}

      {form.type === 'integration' && (
        <>
          <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
            <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldAuthType')}</label>
            <select
              value={form.authType}
              onChange={(e) => onChange({ authType: e.target.value as PluginFormData['authType'] })}
              className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value="none">{t('common:pluginMarketplace.creator.authNone')}</option>
              <option value="apikey">{t('common:pluginMarketplace.creator.authApiKey')}</option>
              <option value="oauth">OAuth</option>
              <option value="basic">{t('common:pluginMarketplace.creator.authBasic')}</option>
            </select>
          </div>
          <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
            <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldApiEndpoint')}</label>
            <input
              type="text"
              value={form.apiEndpoint}
              onChange={(e) => onChange({ apiEndpoint: e.target.value })}
              placeholder="https://api.example.com"
              className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>
        </>
      )}

      {form.type === 'theme' && (
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
            <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldPrimaryColor')}</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={form.primaryColor}
                onChange={(e) => onChange({ primaryColor: e.target.value })}
                className="h-8 w-8 rounded border border-border cursor-pointer"
              />
              <input
                type="text"
                value={form.primaryColor}
                onChange={(e) => onChange({ primaryColor: e.target.value })}
                className="flex-1 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
          </div>
          <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
            <label className="text-xs font-medium">{t('common:pluginMarketplace.creator.fieldBackgroundColor')}</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={form.backgroundColor}
                onChange={(e) => onChange({ backgroundColor: e.target.value })}
                className="h-8 w-8 rounded border border-border cursor-pointer"
              />
              <input
                type="text"
                value={form.backgroundColor}
                onChange={(e) => onChange({ backgroundColor: e.target.value })}
                className="flex-1 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
          </div>
        </div>
      )}

      {(form.type === 'spec-template' || form.type === 'custom-prompt') && (
        <div className="space-y-1.5">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
          <label className="text-xs font-medium">
            {form.type === 'spec-template'
              ? t('common:pluginMarketplace.creator.fieldTemplateContent')
              : t('common:pluginMarketplace.creator.fieldPromptContent')}
          </label>
          <textarea
            value={form.templateContent}
            onChange={(e) => onChange({ templateContent: e.target.value })}
            placeholder={
              form.type === 'spec-template'
                ? '# Spec Template\n\n## Requirements\n...'
                : 'You are an expert at...'
            }
            rows={6}
            className="w-full rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
          />
        </div>
      )}
    </div>
  );
}

function StepPreview({
  form,
  onCopy,
  copied,
  t,
}: {
  form: PluginFormData;
  onCopy: () => void;
  copied: boolean;
  t: (key: string) => string;
}) {
  const configPreview = generateConfigPreview(form);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t('common:pluginMarketplace.creator.previewDesc')}
      </p>

      {/* Summary */}
      <div className="rounded-xl border border-border bg-card p-4 space-y-2">
        <div className="flex items-center gap-2">
          <div
            className="h-3 w-3 rounded-full"
            style={{
              backgroundColor:
                PLUGIN_TYPE_OPTIONS.find((o) => o.type === form.type)?.color || '#888',
            }}
          />
          <span className="text-sm font-semibold">{form.name || 'Untitled'}</span>
          <span className="text-xs font-mono text-muted-foreground ml-auto">
            v{form.version}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">{form.description || '—'}</p>
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className="font-mono bg-muted/60 px-1.5 py-0.5 rounded">{form.type}</span>
          <span className="font-mono bg-muted/60 px-1.5 py-0.5 rounded">{form.id}</span>
        </div>
      </div>

      {/* Generated config */}
      <div className="relative">
        <button
          type="button"
          onClick={onCopy}
          className="absolute top-2 right-2 flex items-center gap-1 rounded-md bg-muted/80 px-2 py-1 text-[10px] font-medium hover:bg-muted transition-colors"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          {copied ? t('common:pluginMarketplace.creator.copied') : t('common:pluginMarketplace.creator.copyConfig')}
        </button>
        <pre
          className={cn(
            'rounded-lg bg-muted/60 p-3 pt-8 text-xs font-mono overflow-x-auto',
            'border border-border/50 text-foreground/80 leading-relaxed'
          )}
        >
          {configPreview}
        </pre>
      </div>
    </div>
  );
}

// ============================================
// Main wizard
// ============================================

interface PluginCreatorWizardProps {
  onClose: () => void;
}

export function PluginCreatorWizard({ onClose }: PluginCreatorWizardProps) {
  const { t } = useTranslation(['common']);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<PluginFormData>({ ...INITIAL_FORM });
  const [copied, setCopied] = useState(false);
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState(false);
  const [createdPath, setCreatedPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const STEPS = [
    { labelKey: 'common:pluginMarketplace.creator.stepType' },
    { labelKey: 'common:pluginMarketplace.creator.stepDetails' },
    { labelKey: 'common:pluginMarketplace.creator.stepPreview' },
  ];

  const updateForm = useCallback((updates: Partial<PluginFormData>) => {
    setForm((prev) => ({ ...prev, ...updates }));
  }, []);

  const canAdvance = step === 0 ? form.type !== null : step === 1 ? form.name.trim() !== '' : true;

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(generateConfigPreview(form));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [form]);

  const handleCreate = useCallback(async () => {
    setCreating(true);
    setError(null);
    try {
      const result = await globalThis.electronAPI?.invoke('pluginMarketplace:create', {
        type: form.type,
        id: form.id || slugify(form.name),
        name: form.name,
        description: form.description,
        version: form.version,
        systemPrompt: form.systemPrompt,
        triggerKeywords: form.triggerKeywords,
        authType: form.authType,
        apiEndpoint: form.apiEndpoint,
        primaryColor: form.primaryColor,
        backgroundColor: form.backgroundColor,
        templateContent: form.templateContent,
      });
      if (result?.success) {
        setCreated(true);
        setCreatedPath(result.data?.path || null);
      } else {
        setError(result?.error || 'Failed to create plugin');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create plugin');
    } finally {
      setCreating(false);
    }
  }, [form]);

  const handleOpenFolder = useCallback(() => {
    if (createdPath) {
      globalThis.electronAPI?.invoke('shell:openPath', createdPath);
    }
  }, [createdPath]);

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="shrink-0 border-b border-border bg-gradient-to-b from-primary/5 to-transparent px-6 py-5">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-accent transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Sparkles className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-bold">{t('common:pluginMarketplace.creator.title')}</h2>
            <p className="text-xs text-muted-foreground">
              {t('common:pluginMarketplace.creator.subtitle')}
            </p>
          </div>
        </div>

        {/* Step indicator */}
        {!created && (
          <div className="flex items-center gap-2 mt-4">
            {STEPS.map((s, i) => (
              <div key={s.labelKey} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => i < step && setStep(i)}
                  disabled={i > step}
                  className={cn(
                    'flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors',
                    i === step
                      ? 'bg-primary text-primary-foreground'
                      : i < step
                        ? 'bg-primary/10 text-primary cursor-pointer hover:bg-primary/20'
                        : 'bg-muted text-muted-foreground'
                  )}
                >
                  <span className="flex h-4 w-4 items-center justify-center rounded-full text-[10px]">
                    {i < step ? <Check className="h-3 w-3" /> : i + 1}
                  </span>
                  {t(s.labelKey)}
                </button>
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      'h-px w-6',
                      i < step ? 'bg-primary/40' : 'bg-border'
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 px-6 py-6 max-w-2xl">
        {created ? (
          <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-green-500/10">
              <Check className="h-8 w-8 text-green-500" />
            </div>
            <h3 className="text-lg font-bold">{t('common:pluginMarketplace.creator.successTitle')}</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              {t('common:pluginMarketplace.creator.successDesc', { name: form.name })}
            </p>
            {createdPath && (
              <p className="text-xs font-mono text-muted-foreground bg-muted/60 px-3 py-1.5 rounded-lg">
                {createdPath}
              </p>
            )}
            <div className="flex gap-3 mt-4">
              {createdPath && (
                <button
                  type="button"
                  onClick={handleOpenFolder}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border px-4 py-2 text-xs font-medium hover:bg-accent transition-colors"
                >
                  <FolderOpen className="h-3.5 w-3.5" />
                  {t('common:pluginMarketplace.creator.openFolder')}
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                {t('common:pluginMarketplace.creator.done')}
              </button>
            </div>
          </div>
        ) : (
          <>
            {step === 0 && (
              <StepTypeSelection
                selected={form.type}
                onSelect={(type) => updateForm({ type })}
                t={t}
              />
            )}
            {step === 1 && <StepDetails form={form} onChange={updateForm} t={t} />}
            {step === 2 && (
              <StepPreview form={form} onCopy={handleCopy} copied={copied} t={t} />
            )}
          </>
        )}
      </div>

      {/* Footer with navigation */}
      {!created && (
        <div className="shrink-0 border-t border-border px-6 py-3 flex items-center justify-between">
          <button
            type="button"
            onClick={() => (step === 0 ? onClose() : setStep(step - 1))}
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-4 py-2 text-xs font-medium hover:bg-accent transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {step === 0
              ? t('common:pluginMarketplace.creator.cancel')
              : t('common:pluginMarketplace.creator.back')}
          </button>

          {error && (
            <p className="text-xs text-destructive">{error}</p>
          )}

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={() => setStep(step + 1)}
              disabled={!canAdvance}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md px-4 py-2 text-xs font-medium transition-colors',
                canAdvance
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              )}
            >
              {t('common:pluginMarketplace.creator.next')}
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleCreate}
              disabled={creating}
              className="inline-flex items-center gap-1.5 rounded-md bg-green-600 px-4 py-2 text-xs font-medium text-white hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {creating ? (
                <>
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  {t('common:pluginMarketplace.creator.creating')}
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" />
                  {t('common:pluginMarketplace.creator.createPlugin')}
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}



