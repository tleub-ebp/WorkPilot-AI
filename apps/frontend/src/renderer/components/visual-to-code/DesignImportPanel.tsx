import { useCallback, useRef, useState, type DragEvent, type ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Image as ImageIcon,
  Upload,
  X,
  Loader2,
  Check,
  AlertTriangle,
  Code,
  Palette,
  TestTube,
  FileCode2,
  Eye,
  Copy,
  ChevronRight,
  Sparkles,
  Layout,
  Monitor,
  Smartphone,
  Tablet,
  Settings2,
  Play,
  RotateCcw,
} from 'lucide-react';

import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

import {
  useDesignToCodeStore,
  runDesignToCodePipeline,
  type FrameworkType,
  type DesignSourceType,
  type PipelinePhase,
} from '../../stores/design-to-code-store';

// Phase metadata for UI display
const PHASE_CONFIG: Record<PipelinePhase, { icon: React.ElementType; labelKey: string; color: string }> = {
  idle: { icon: Play, labelKey: 'phases.idle', color: 'text-muted-foreground' },
  analyzing: { icon: Eye, labelKey: 'phases.analyzing', color: 'text-blue-500' },
  spec_generation: { icon: Layout, labelKey: 'phases.spec_generation', color: 'text-purple-500' },
  code_generation: { icon: Code, labelKey: 'phases.code_generation', color: 'text-green-500' },
  design_token_integration: { icon: Palette, labelKey: 'phases.design_token_integration', color: 'text-amber-500' },
  visual_test_generation: { icon: TestTube, labelKey: 'phases.visual_test_generation', color: 'text-cyan-500' },
  figma_sync: { icon: Palette, labelKey: 'phases.figma_sync', color: 'text-violet-500' },
  complete: { icon: Check, labelKey: 'phases.complete', color: 'text-green-600' },
  error: { icon: AlertTriangle, labelKey: 'phases.error', color: 'text-red-500' },
};

const FRAMEWORK_OPTIONS: { value: FrameworkType; labelKey: string; icon: string }[] = [
  { value: 'react', labelKey: 'frameworks.react', icon: '⚛️' },
  { value: 'angular', labelKey: 'frameworks.angular', icon: '🅰️' },
  { value: 'vue', labelKey: 'frameworks.vue', icon: '💚' },
  { value: 'nextjs', labelKey: 'frameworks.nextjs', icon: '▲' },
  { value: 'nuxt', labelKey: 'frameworks.nuxt', icon: '💚' },
  { value: 'svelte', labelKey: 'frameworks.svelte', icon: '🔥' },
];

const SOURCE_TYPE_OPTIONS: { value: DesignSourceType; labelKey: string; icon: string }[] = [
  { value: 'screenshot', labelKey: 'sourceTypes.screenshot', icon: '📸' },
  { value: 'figma', labelKey: 'sourceTypes.figma', icon: '🎨' },
  { value: 'wireframe', labelKey: 'sourceTypes.wireframe', icon: '📐' },
  { value: 'whiteboard', labelKey: 'sourceTypes.whiteboard', icon: '📋' },
  { value: 'photo', labelKey: 'sourceTypes.photo', icon: '📷' },
];

const LANGUAGE_COLORS: Record<string, string> = {
  tsx: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  jsx: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  ts: 'bg-blue-600/10 text-blue-800 dark:text-blue-300',
  js: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400',
  css: 'bg-purple-500/10 text-purple-700 dark:text-purple-400',
  scss: 'bg-pink-500/10 text-pink-700 dark:text-pink-400',
  vue: 'bg-green-500/10 text-green-700 dark:text-green-400',
  svelte: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
  html: 'bg-red-500/10 text-red-700 dark:text-red-400',
  text: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
};

/**
 * DesignImportPanel — Design-to-Code Pipeline UI (inline page version).
 *
 * Upload a design (screenshot, Figma, wireframe, whiteboard photo) and
 * generate production-ready code with visual tests in one click.
 */
export function DesignImportPanel() {
  const { t } = useTranslation('designToCode');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  const {
    phase,
    status,
    result,
    error,
    framework,
    sourceType,
    designSystemPath,
    figmaUrl,
    generateTests,
    customInstructions,
    imageData,
    imagePreview,
    imageName,
    selectedFileIndex,
    activeTab,
    setFramework,
    setSourceType,
    setDesignSystemPath,
    setFigmaUrl,
    setGenerateTests,
    setCustomInstructions,
    setImageData,
    clearImage,
    resetPipeline,
    setSelectedFileIndex,
    setActiveTab,
  } = useDesignToCodeStore();

  const isRunning = ['analyzing', 'spec_generation', 'code_generation', 'design_token_integration', 'visual_test_generation', 'figma_sync'].includes(phase);

  // =========================================================================
  // Image handling
  // =========================================================================

  const handleFileSelect = useCallback(async (file: File) => {
    const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml'];
    if (!validTypes.includes(file.type)) {
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setImageData(dataUrl, dataUrl, file.name);
    };
    reader.readAsDataURL(file);
  }, [setImageData]);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  // =========================================================================
  // Pipeline control
  // =========================================================================

  const handleRunPipeline = useCallback(() => {
    runDesignToCodePipeline();
  }, []);

  const handleReset = useCallback(() => {
    resetPipeline();
    clearImage();
  }, [resetPipeline, clearImage]);

  const handleCopyCode = useCallback((content: string, path: string) => {
    navigator.clipboard.writeText(content);
    setCopiedFile(path);
    setTimeout(() => setCopiedFile(null), 2000);
  }, []);

  // =========================================================================
  // Phase progress
  // =========================================================================

  const phaseOrder: PipelinePhase[] = [
    'analyzing',
    'spec_generation',
    'code_generation',
    'design_token_integration',
    'visual_test_generation',
    'figma_sync',
    'complete',
  ];

  const currentPhaseIndex = phaseOrder.indexOf(phase);

  // =========================================================================
  // Render
  // =========================================================================

  return (
    <div className="flex flex-col h-full p-6 gap-2">
      {/* Header */}
      <div className="pb-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Sparkles className="h-5 w-5 text-violet-500" />
          {t('title')}
        </h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          {t('description')}
        </p>
      </div>

      {/* Pipeline Progress Bar */}
      {phase !== 'idle' && (
        <div className="flex items-center gap-1 px-1 py-2">
          {phaseOrder.slice(0, -1).map((p, i) => {
            const config = PHASE_CONFIG[p];
            const Icon = config.icon;
            const isActive = phase === p;
            const isDone = currentPhaseIndex > i;

            let phaseStatusClass: string;
            if (isActive) {
              phaseStatusClass = `${config.color} bg-current/5 ring-1 ring-current/20`;
            } else if (isDone) {
              phaseStatusClass = 'text-green-600 bg-green-500/5';
            } else {
              phaseStatusClass = 'text-muted-foreground/50';
            }

            let phaseIconElement: React.ReactElement;
            if (isActive && isRunning) {
              phaseIconElement = <Loader2 className="h-3 w-3 animate-spin" />;
            } else if (isDone) {
              phaseIconElement = <Check className="h-3 w-3" />;
            } else {
              phaseIconElement = <Icon className="h-3 w-3" />;
            }

            const connectorClass = isDone ? 'bg-green-500/40' : 'bg-border';

            return (
              <div key={p} className="flex items-center flex-1">
                <div className={`flex items-center gap-1.5 text-xs font-medium rounded-full px-2 py-1 transition-all ${phaseStatusClass}`}>
                  {phaseIconElement}
                  <span className="hidden sm:inline truncate">{t(config.labelKey).replace('...', '')}</span>
                </div>
                {i < phaseOrder.length - 2 && (
                  <div className={`flex-1 h-px mx-1 ${connectorClass}`} />
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Main content with tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)} className="flex-1 overflow-hidden flex flex-col min-h-0">
        <TabsList className="grid grid-cols-5 w-full shrink-0">
          <TabsTrigger value="upload" className="text-xs gap-1">
            <Upload className="h-3.5 w-3.5" />
            {t('tabs.upload')}
          </TabsTrigger>
          <TabsTrigger value="spec" className="text-xs gap-1" disabled={!result?.design_spec}>
            <Layout className="h-3.5 w-3.5" />
            {t('tabs.spec')}
          </TabsTrigger>
          <TabsTrigger value="code" className="text-xs gap-1" disabled={!result?.generated_files?.length}>
            <Code className="h-3.5 w-3.5" />
            {t('tabs.code')} ({result?.generated_files?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="tests" className="text-xs gap-1" disabled={!result?.visual_tests?.length}>
            <TestTube className="h-3.5 w-3.5" />
            {t('tabs.tests')} ({result?.visual_tests?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="tokens" className="text-xs gap-1" disabled={!result?.design_tokens_used?.length}>
            <Palette className="h-3.5 w-3.5" />
            {t('tabs.tokens')} ({result?.design_tokens_used?.length || 0})
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-hidden mt-3 min-h-0">
          {/* ============ UPLOAD TAB ============ */}
          <TabsContent value="upload" className="h-full m-0">
            <ScrollArea className="h-full">
              <div className="space-y-4 pr-4">
                {/* Image Upload Zone */}
{/* biome-ignore lint/a11y/noNoninteractiveElementInteractions lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: interactive handler is intentional */}
                <div
                  className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                    isDragging
                      ? 'border-violet-500 bg-violet-500/5'
                      : imagePreview
                        ? 'border-green-500/50 bg-green-500/5'
                        : 'border-border hover:border-violet-500/50 hover:bg-accent/50'
                  }`}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml"
                    className="hidden"
                    onChange={handleInputChange}
                  />

                  {imagePreview ? (
                    <div className="space-y-3">
                      <div className="relative inline-block">
                        <img
                          src={imagePreview}
                          alt="Design preview"
                          className="max-h-48 rounded-lg shadow-md mx-auto"
                        />
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); clearImage(); }}
                          className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 transition-colors"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                      <p className="text-sm text-muted-foreground">{imageName}</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="mx-auto w-16 h-16 rounded-2xl bg-violet-500/10 flex items-center justify-center">
                        <ImageIcon className="h-8 w-8 text-violet-500" />
                      </div>
                      <div>
                        <p className="text-base font-medium">{t('upload.dropDesign')}</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          {t('upload.dropDescription')}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {t('upload.dropFormats')}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Figma URL Input */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="figma-url-input"
                    className="text-sm font-medium flex items-center gap-1.5"
                  >
                    <Palette className="h-4 w-4" />
                    {t('upload.figmaUrl')}
                  </label>
                  <input
                    id="figma-url-input"
                    type="text"
                    placeholder={t('upload.figmaUrlPlaceholder')}
                    value={figmaUrl}
                    onChange={(e) => setFigmaUrl(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('upload.figmaUrlHelp')}
                  </p>
                </div>

                {/* Framework Selection */}
                <div className="space-y-1.5">
                  <div className="text-sm font-medium">
                    {t('upload.targetFramework')}
                  </div>
                  <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                    {FRAMEWORK_OPTIONS.map((fw) => (
                      <button
                        key={fw.value}
                        type="button"
                        onClick={() => setFramework(fw.value)}
                        className={`flex flex-col items-center gap-1 px-3 py-2.5 rounded-lg border text-xs font-medium transition-all ${
                          framework === fw.value
                            ? 'border-violet-500 bg-violet-500/10 text-violet-700 dark:text-violet-300 ring-1 ring-violet-500/30'
                            : 'border-border hover:bg-accent/50'
                        }`}
                      >
                        <span className="text-lg">{fw.icon}</span>
                        {t(fw.labelKey)}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Source Type */}
                <div className="space-y-1.5">
                  <div className="text-sm font-medium">
                    {t('upload.sourceType')}
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {SOURCE_TYPE_OPTIONS.map((st) => (
                      <button
                        key={st.value}
                        type="button"
                        onClick={() => setSourceType(st.value)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                          sourceType === st.value
                            ? 'bg-violet-500/10 text-violet-700 dark:text-violet-300 ring-1 ring-violet-500/30'
                            : 'bg-accent/50 hover:bg-accent'
                        }`}
                      >
                        <span>{st.icon}</span>
                        {t(st.labelKey)}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Advanced Settings */}
                <div>
                  <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <Settings2 className="h-4 w-4" />
                    {t('upload.advancedSettings')}
                    <ChevronRight className={`h-3 w-3 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} />
                  </button>

                  {showAdvanced && (
                    <div className="mt-3 space-y-3 pl-6 border-l-2 border-border">
                      {/* Design System Path */}
                      <div className="space-y-1">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
                        <label className="text-xs font-medium">{t('upload.designSystemPath')}</label>
                        <input
                          type="text"
                          placeholder={t('upload.designSystemPathPlaceholder')}
                          value={designSystemPath}
                          onChange={(e) => setDesignSystemPath(e.target.value)}
                          className="w-full px-3 py-1.5 text-sm rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                        />
                      </div>

                      {/* Visual Tests Toggle */}
                      <div className="flex items-center justify-between">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
                        <label className="text-xs font-medium">{t('upload.generateVisualTests')}</label>
                        <button
                          type="button"
                          onClick={() => setGenerateTests(!generateTests)}
                          className={`relative w-10 h-5 rounded-full transition-colors ${
                            generateTests ? 'bg-violet-500' : 'bg-muted-foreground/30'
                          }`}
                        >
                          <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                            generateTests ? '-translate-x-5' : 'translate-x-0.5'
                          }`} />
                        </button>
                      </div>

                      {/* Custom Instructions */}
                      <div className="space-y-1">
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional */}
                        <label className="text-xs font-medium">{t('upload.customInstructions')}</label>
                        <textarea
                          placeholder={t('upload.customInstructionsPlaceholder')}
                          value={customInstructions}
                          onChange={(e) => setCustomInstructions(e.target.value)}
                          rows={3}
                          className="w-full px-3 py-1.5 text-sm rounded-md border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Error display */}
                {error && (
                  <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 text-red-700 dark:text-red-400 text-sm">
                    <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                    <p>{error}</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* ============ SPEC TAB ============ */}
          <TabsContent value="spec" className="h-full m-0">
            <ScrollArea className="h-full">
              {result?.design_spec ? (
                <div className="space-y-4 pr-4">
                  {/* Components */}
                  <div>
                    <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                      <Layout className="h-4 w-4 text-violet-500" />
                      {t('spec.components')} ({result.design_spec.components.length})
                    </h3>
                    <div className="space-y-2">
                      {result.design_spec.components.map((comp, i) => (
                        <div key={`${comp.type}-${comp.name}-${i}`} className="p-3 rounded-lg border bg-card">
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="text-xs">{comp.type}</Badge>
                            <span className="text-sm font-medium">{comp.name}</span>
                          </div>
                          {comp.description && (
                            <p className="text-xs text-muted-foreground mt-1">{comp.description}</p>
                          )}
                          {comp.children.length > 0 && (
                            <div className="mt-2 pl-4 border-l-2 border-border space-y-1">
                              {comp.children.map((child, j) => (
                                <div key={`${child.type}-${child.name}-${j}`} className="flex items-center gap-1.5 text-xs">
                                  <ChevronRight className="h-3 w-3 text-muted-foreground" />
                                  <Badge variant="outline" className="text-[10px]">{child.type}</Badge>
                                  <span>{child.name}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Color Palette */}
                  {Object.keys(result.design_spec.color_palette).length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                        <Palette className="h-4 w-4 text-amber-500" />
                        {t('spec.colorPalette')}
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(result.design_spec.color_palette).map(([name, value]) => (
                          <div key={name} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-card">
                            <div
                              className="w-5 h-5 rounded-md border shadow-sm"
                              style={{ backgroundColor: value.startsWith('var(') ? '#888' : value }}
                            />
                            <div>
                              <p className="text-xs font-medium">{name}</p>
                              <p className="text-[10px] text-muted-foreground font-mono">{value}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Typography */}
                  {Object.keys(result.design_spec.typography).length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold mb-2">{t('spec.typography')}</h3>
                      <div className="space-y-1">
                        {Object.entries(result.design_spec.typography).map(([name, props]) => (
                          <div key={name} className="flex items-center gap-3 px-3 py-1.5 rounded-lg border bg-card text-xs">
                            <span className="font-medium w-20">{name}</span>
                            {Object.entries(props).map(([k, v]) => (
                              <span key={k} className="text-muted-foreground">
                                {k}: <span className="font-mono">{v}</span>
                              </span>
                            ))}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  {t('spec.emptyState')}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* ============ CODE TAB ============ */}
          <TabsContent value="code" className="h-full m-0">
            {result?.generated_files?.length ? (
              <div className="flex gap-3 h-full">
                {/* File list */}
                <div className="w-56 shrink-0 border rounded-lg overflow-hidden">
                  <ScrollArea className="h-full">
                    <div className="p-1 space-y-0.5">
                      {result.generated_files.map((file, i) => (
                        <button
                          key={file.path}
                          type="button"
                          onClick={() => setSelectedFileIndex(i)}
                          className={`w-full text-left px-2.5 py-2 rounded-md text-xs transition-colors ${
                            selectedFileIndex === i
                              ? 'bg-violet-500/10 text-violet-700 dark:text-violet-300'
                              : 'hover:bg-accent/50'
                          }`}
                        >
                          <div className="flex items-center gap-1.5">
                            <FileCode2 className="h-3.5 w-3.5 shrink-0" />
                            <span className="truncate font-medium">{file.path.split('/').pop()}</span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-1 pl-5">
                            <Badge className={`text-[10px] px-1 py-0 ${LANGUAGE_COLORS[file.language] || LANGUAGE_COLORS.text}`}>
                              {file.language}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground truncate">{file.description}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </ScrollArea>
                </div>

                {/* Code preview */}
                <div className="flex-1 border rounded-lg overflow-hidden flex flex-col">
                  {result.generated_files[selectedFileIndex] && (
                    <>
                      <div className="flex items-center justify-between px-3 py-1.5 bg-muted/50 border-b text-xs">
                        <span className="font-mono text-muted-foreground truncate">
                          {result.generated_files[selectedFileIndex].path}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs"
                          onClick={() => handleCopyCode(
                            result.generated_files[selectedFileIndex].content,
                            result.generated_files[selectedFileIndex].path,
                          )}
                        >
                          {copiedFile === result.generated_files[selectedFileIndex].path ? (
                            <><Check className="h-3 w-3 mr-1" /> {t('code.copied')}</>
                          ) : (
                            <><Copy className="h-3 w-3 mr-1" /> {t('code.copy')}</>
                          )}
                        </Button>
                      </div>
                      <ScrollArea className="flex-1">
                        <pre className="p-3 text-xs font-mono whitespace-pre-wrap overflow-wrap-break-word">
                          {result.generated_files[selectedFileIndex].content}
                        </pre>
                      </ScrollArea>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                {t('code.emptyState')}
              </div>
            )}
          </TabsContent>

          {/* ============ TESTS TAB ============ */}
          <TabsContent value="tests" className="h-full m-0">
            <ScrollArea className="h-full">
              {result?.visual_tests?.length ? (
                <div className="space-y-3 pr-4">
                  <div className="flex items-center gap-2 mb-2">
                    <TestTube className="h-4 w-4 text-cyan-500" />
                    <span className="text-sm font-semibold">
                      {t('tests.visualRegressionTests')} ({result.visual_tests.length})
                    </span>
                    <Badge variant="secondary" className="text-[10px]">Playwright</Badge>
                  </div>

                  <div className="flex gap-2 mb-3">
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Monitor className="h-3.5 w-3.5" /> {t('tests.desktop')}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Tablet className="h-3.5 w-3.5" /> {t('tests.tablet')}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Smartphone className="h-3.5 w-3.5" /> {t('tests.mobile')}
                    </div>
                  </div>

                  {result.visual_tests.map((test) => (
                    <div key={test.name} className="border rounded-lg overflow-hidden">
                      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b">
                        <div className="flex items-center gap-2">
                          <TestTube className="h-3.5 w-3.5 text-cyan-500" />
                          <span className="text-xs font-medium">{test.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-[10px]">
                            {t('tests.threshold')}: {(test.threshold * 100).toFixed(0)}%
                          </Badge>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs"
                            onClick={() => handleCopyCode(test.test_code, test.name)}
                          >
                            {copiedFile === test.name ? (
                              <><Check className="h-3 w-3 mr-1" /> {t('tests.copied')}</>
                            ) : (
                              <><Copy className="h-3 w-3 mr-1" /> {t('tests.copy')}</>
                            )}
                          </Button>
                        </div>
                      </div>
                      <pre className="p-3 text-xs font-mono whitespace-pre-wrap overflow-wrap-break-word max-h-64 overflow-auto">
                        {test.test_code}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  {t('tests.emptyState')}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          {/* ============ TOKENS TAB ============ */}
          <TabsContent value="tokens" className="h-full m-0">
            <ScrollArea className="h-full">
              {result?.design_tokens_used?.length ? (
                <div className="space-y-3 pr-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Palette className="h-4 w-4 text-amber-500" />
                    <span className="text-sm font-semibold">
                      {t('tokens.designTokensIntegrated')} ({result.design_tokens_used.length})
                    </span>
                  </div>

                  {/* Group tokens by category */}
                  {Object.entries(
                    result.design_tokens_used.reduce<Record<string, typeof result.design_tokens_used>>(
                      (acc, token) => {
                        // biome-ignore lint/suspicious/noAssignInExpressions: intentional assignment
                        const categoryTokens = acc[token.category] ??= [];
                        categoryTokens.push(token);
                        return acc;
                      },
                      {},
                    ),
                  ).map(([category, tokens]) => (
                    <div key={category}>
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
                        {category}
                      </h4>
                      <div className="grid grid-cols-2 gap-1.5">
                        {tokens.map((token) => (
                          <div key={token.name} className="flex items-center gap-2 px-2.5 py-1.5 rounded-md border bg-card text-xs">
                            {token.category === 'color' && (
                              <div
                                className="w-4 h-4 rounded border"
                                style={{ backgroundColor: token.value }}
                              />
                            )}
                            <div className="min-w-0 flex-1">
                              <span className="font-mono truncate block">{token.name}</span>
                              <span className="text-muted-foreground truncate block">{token.value}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  {t('tokens.emptyState')}
                </div>
              )}
            </ScrollArea>
          </TabsContent>
        </div>
      </Tabs>

      {/* Footer with actions */}
      <div className="flex items-center justify-between gap-3 pt-2 border-t mt-auto shrink-0">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {phase === 'complete' && result && (
            <>
              <Check className="h-3.5 w-3.5 text-green-500" />
              <span>
                {result.generated_files.length} {t('footer.files')} • {result.visual_tests.length} {t('footer.tests')} • {result.duration_seconds.toFixed(1)}s
              </span>
            </>
          )}
          {isRunning && (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>{status}</span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {phase !== 'idle' && (
            <Button variant="outline" size="sm" onClick={handleReset} disabled={isRunning}>
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
              {t('footer.reset')}
            </Button>
          )}
          <Button
            onClick={handleRunPipeline}
            disabled={isRunning || (!imageData && !figmaUrl)}
            className="bg-violet-600 hover:bg-violet-700 text-white"
            size="sm"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                {t('footer.processing')}
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                {t('footer.generateCode')}
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}



