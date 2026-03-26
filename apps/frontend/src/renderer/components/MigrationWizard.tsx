import React, { useState, } from 'react';
import {
  ChevronRight,
  Check,
  AlertCircle,
  Loader2,
  GitBranch,
  FileCode,
  Shield,
  Zap,
} from 'lucide-react';
import { Card, } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Checkbox } from './ui/checkbox';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { useTranslation } from 'react-i18next';
import { useProjectStore } from '../stores/project-store';

interface MigrationStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  icon: React.ReactNode;
}

interface MigrationConfig {
  sourceFramework: string;
  targetFramework: string;
  projectPath: string;
  enableLLM: boolean;
  autoFix: boolean;
  backupEnabled: boolean;
}

export const MigrationWizard: React.FC = () => {
  const { t } = useTranslation('migrationWizard');
  const selectedProject = useProjectStore((state) => state.getSelectedProject?.());
  const defaultProjectPath = selectedProject?.path || t('defaultProjectPath', { defaultValue: './' });
  const [currentStep, setCurrentStep] = useState(0);
  const [_migrationId, setMigrationId] = useState<string | null>(null);
  const [config, setConfig] = useState<MigrationConfig>({
    sourceFramework: '',
    targetFramework: '',
    projectPath: defaultProjectPath,
    enableLLM: true,
    autoFix: true,
    backupEnabled: true,
  });
  const [_migrating, setMigrating] = useState(false);
  const [progress, setProgress] = useState(0);
  // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
  const [transformations, setTransformations] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const steps: MigrationStep[] = [
    {
      id: 'configure',
      title: t('steps.configure'),
      description: t('descriptions.configure'),
      status: currentStep > 0 ? 'completed' : currentStep === 0 ? 'in_progress' : 'pending',
      icon: <FileCode className="w-5 h-5" />,
    },
    {
      id: 'analyze',
      title: t('steps.analyze'),
      description: t('descriptions.analyze'),
      status: currentStep > 1 ? 'completed' : currentStep === 1 ? 'in_progress' : 'pending',
      icon: <GitBranch className="w-5 h-5" />,
    },
    {
      id: 'transform',
      title: t('steps.transform'),
      description: t('descriptions.transform'),
      status: currentStep > 2 ? 'completed' : currentStep === 2 ? 'in_progress' : 'pending',
      icon: <Zap className="w-5 h-5" />,
    },
    {
      id: 'validate',
      title: t('steps.validate'),
      description: t('descriptions.validate'),
      status: currentStep > 3 ? 'completed' : currentStep === 3 ? 'in_progress' : 'pending',
      icon: <Shield className="w-5 h-5" />,
    },
  ];

  const supportedMigrations = [
    // Frontend
    { source: 'react', target: 'vue', label: 'React → Vue 3', complexity: 'medium', category: 'frontend' },
    { source: 'vue', target: 'react', label: 'Vue 3 → React', complexity: 'medium', category: 'frontend' },
    { source: 'react', target: 'angular', label: 'React → Angular', complexity: 'high', category: 'frontend' },
    { source: 'angular', target: 'react', label: 'Angular → React', complexity: 'high', category: 'frontend' },
    { source: 'react', target: 'svelte', label: 'React → Svelte', complexity: 'medium', category: 'frontend' },
    { source: 'svelte', target: 'react', label: 'Svelte → React', complexity: 'medium', category: 'frontend' },
    
    // Databases
    { source: 'mysql', target: 'postgresql', label: 'MySQL → PostgreSQL', complexity: 'medium', category: 'database' },
    { source: 'postgresql', target: 'mysql', label: 'PostgreSQL → MySQL', complexity: 'medium', category: 'database' },
    { source: 'mysql', target: 'mongodb', label: 'MySQL → MongoDB', complexity: 'high', category: 'database' },
    { source: 'mongodb', target: 'postgresql', label: 'MongoDB → PostgreSQL', complexity: 'high', category: 'database' },
    { source: 'sqlite', target: 'postgresql', label: 'SQLite → PostgreSQL', complexity: 'low', category: 'database' },
    
    // Languages
    { source: 'python2', target: 'python3', label: 'Python 2 → Python 3', complexity: 'medium', category: 'language' },
    { source: 'javascript', target: 'typescript', label: 'JavaScript → TypeScript', complexity: 'low', category: 'language' },
    { source: 'typescript', target: 'javascript', label: 'TypeScript → JavaScript', complexity: 'low', category: 'language' },
    { source: 'javascript', target: 'python', label: 'JavaScript → Python', complexity: 'high', category: 'language' },
    { source: 'python', target: 'javascript', label: 'Python → JavaScript', complexity: 'high', category: 'language' },
    { source: 'java', target: 'kotlin', label: 'Java → Kotlin', complexity: 'medium', category: 'language' },
    
    // API
    { source: 'rest', target: 'graphql', label: 'REST → GraphQL', complexity: 'high', category: 'api' },
    { source: 'graphql', target: 'rest', label: 'GraphQL → REST', complexity: 'high', category: 'api' },
    { source: 'rest', target: 'grpc', label: 'REST → gRPC', complexity: 'high', category: 'api' },
    
    // Backend
    { source: 'express', target: 'fastify', label: 'Express → Fastify', complexity: 'medium', category: 'backend' },
    { source: 'django', target: 'fastapi', label: 'Django → FastAPI', complexity: 'high', category: 'backend' },
    { source: 'flask', target: 'fastapi', label: 'Flask → FastAPI', complexity: 'medium', category: 'backend' },
    
    // Build Tools
    { source: 'webpack', target: 'vite', label: 'Webpack → Vite', complexity: 'medium', category: 'build' },
    { source: 'webpack', target: 'rollup', label: 'Webpack → Rollup', complexity: 'medium', category: 'build' },
    
    // Testing
    { source: 'jest', target: 'vitest', label: 'Jest → Vitest', complexity: 'low', category: 'testing' },
    { source: 'mocha', target: 'jest', label: 'Mocha → Jest', complexity: 'medium', category: 'testing' },
    { source: 'unittest', target: 'pytest', label: 'unittest → pytest', complexity: 'medium', category: 'testing' },
    
    // Mobile
    { source: 'reactnative', target: 'flutter', label: 'React Native → Flutter', complexity: 'very_high', category: 'mobile' },
    { source: 'flutter', target: 'reactnative', label: 'Flutter → React Native', complexity: 'very_high', category: 'mobile' },
    
    // Package Managers
    { source: 'npm', target: 'yarn', label: 'npm → Yarn', complexity: 'low', category: 'package' },
    { source: 'yarn', target: 'pnpm', label: 'Yarn → pnpm', complexity: 'low', category: 'package' },
    { source: 'pip', target: 'poetry', label: 'pip → Poetry', complexity: 'low', category: 'package' },
  ];

  const categories = [
    { value: 'all', label: t('categories.all'), icon: '🌐' },
    { value: 'frontend', label: t('categories.frontend'), icon: '⚛️' },
    { value: 'backend', label: t('categories.backend'), icon: '🔧' },
    { value: 'database', label: t('categories.database'), icon: '🗄️' },
    { value: 'language', label: t('categories.language'), icon: '💻' },
    { value: 'api', label: t('categories.api'), icon: '🔌' },
    { value: 'build', label: t('categories.build'), icon: '⚙️' },
    { value: 'testing', label: t('categories.testing'), icon: '🧪' },
    { value: 'mobile', label: t('categories.mobile'), icon: '📱' },
    { value: 'package', label: t('categories.package'), icon: '📦' },
  ];

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'low': return 'bg-green-100 text-green-700';
      case 'medium': return 'bg-yellow-100 text-yellow-700';
      case 'high': return 'bg-orange-100 text-orange-700';
      case 'very_high': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const filteredMigrations = supportedMigrations.filter((m) => {
    const matchesSearch = m.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         m.source.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         m.target.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || m.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const startMigration = async () => {
    setMigrating(true);
    
    try {
      // Call backend to start migration
      // TODO: Connect to backend migration API when available
      // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
      const response = await (window as any).electronAPI?.startMigration?.({
        projectPath: config.projectPath,
        targetFramework: config.targetFramework,
        enableLLM: config.enableLLM,
        autoFix: config.autoFix,
      }) ?? { migrationId: `migration-${Date.now()}` };

      setMigrationId(response.migrationId);
      setCurrentStep(1);
      
      // Start polling for progress
      pollMigrationStatus(response.migrationId);
    } catch (error) {
      console.error('Migration start error:', error);
    }
  };

  const pollMigrationStatus = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        // TODO: Connect to backend migration API when available
        // biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
        const status = await (window as any).electronAPI?.getMigrationStatus?.(id) ?? { progress: 100, state: 'complete', currentPhase: 'validation', transformations: [] };
        
        // Update progress
        setProgress(status.progress);
        
        // Update step based on phase
        if (status.currentPhase === 'analysis') setCurrentStep(1);
        else if (status.currentPhase === 'transformation') setCurrentStep(2);
        else if (status.currentPhase === 'validation') setCurrentStep(3);
        
        // Update transformations
        if (status.transformations) {
          setTransformations(status.transformations);
        }
        
        // Check if complete
        if (status.state === 'complete' || status.state === 'failed') {
          clearInterval(interval);
          setMigrating(false);
          if (status.state === 'complete') {
            setCurrentStep(4);
          }
        }
      } catch (error) {
        console.error('Status polling error:', error);
        clearInterval(interval);
      }
    }, 2000);
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <div>
              <Label className="block text-sm font-medium mb-2">{t('fields.projectPath')}</Label>
              <Input
                type="text"
                value={config.projectPath}
                onChange={(e) => setConfig({ ...config, projectPath: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder={t('fields.projectPath')}
              />
            </div>

            <div>
              <Label className="block text-sm font-medium mb-2">{t('fields.selectMigrationType')}</Label>
              
              {/* Search Bar */}
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('fields.search')}
                className="w-full px-4 py-2 border rounded-lg mb-3 focus:ring-2 focus:ring-blue-500"
              />
              
              {/* Category Filter */}
              <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
                {categories.map((cat) => (
                  <Button
                    key={cat.value}
                    onClick={() => setSelectedCategory(cat.value)}
                    variant={selectedCategory === cat.value ? 'default' : 'outline'}
                    className="px-3 py-1.5 rounded-full text-sm whitespace-nowrap"
                  >
                    <span className="mr-1">{cat.icon}</span>
                    {cat.label}
                  </Button>
                ))}
              </div>
              
              {/* Migration Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto">
                {filteredMigrations.map((m) => (
                  <Card
                    key={`${m.source}-${m.target}`}
                    onClick={() => {
                      setConfig({ ...config, sourceFramework: m.source, targetFramework: m.target });
                    }}
                    className={`p-4 border rounded-lg text-left cursor-pointer transition-colors ${
                      config.sourceFramework === m.source && config.targetFramework === m.target
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{m.label}</span>
                      <Badge className={getComplexityColor(m.complexity)}>
                        {m.complexity.replace('_', ' ')}
                      </Badge>
                    </div>
                    <div className="text-xs text-gray-500">
                      {categories.find((c) => c.value === m.category)?.icon}{' '}
                      {categories.find((c) => c.value === m.category)?.label}
                    </div>
                  </Card>
                ))}
              </div>
              
              {filteredMigrations.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  {t('noMigrations', { search: searchQuery })}
                </div>
              )}
            </div>

            <div className="space-y-4">
              // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
              <label className="flex items-center space-x-3">
                <Checkbox
                  checked={config.enableLLM}
                  onCheckedChange={(checked) => setConfig({ ...config, enableLLM: !!checked })}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <div>
                  <div className="font-medium">{t('options.llmEnhancement.title')}</div>
                  <div className="text-sm text-gray-500">
                    {t('options.llmEnhancement.description')}
                  </div>
                </div>
              </label>

              // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
              <label className="flex items-center space-x-3">
                <Checkbox
                  checked={config.autoFix}
                  onCheckedChange={(checked) => setConfig({ ...config, autoFix: !!checked })}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <div>
                  <div className="font-medium">{t('options.autoFixLoop.title')}</div>
                  <div className="text-sm text-gray-500">
                    {t('options.autoFixLoop.description')}
                  </div>
                </div>
              </label>

              // biome-ignore lint/a11y/noLabelWithoutControl: label association is implicit
{/* biome-ignore lint/a11y/noLabelWithoutControl: intentional  */}
              <label className="flex items-center space-x-3">
                <Checkbox
                  checked={config.backupEnabled}
                  onCheckedChange={(checked) => setConfig({ ...config, backupEnabled: !!checked })}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <div>
                  <div className="font-medium">{t('options.createBackup.title')}</div>
                  <div className="text-sm text-gray-500">
                    {t('options.createBackup.description')}
                  </div>
                </div>
              </label>
            </div>

            <Button
              onClick={startMigration}
              disabled={!config.projectPath || !config.targetFramework}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              <span>{t('actions.start')}</span>
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>
        );

      case 1:
        return (
          <div className="space-y-4">
            <div className="flex items-center space-x-3 text-blue-600">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span className="font-medium">{t('statuses.analyzing')}</span>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">
                {t('statuses.analyzingDescription')}
              </div>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3 text-blue-600">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="font-medium">{t('statuses.transforming')}</span>
              </div>
              <span className="text-sm text-gray-500">{progress}% {t('common.complete')}</span>
            </div>

            <Progress value={progress} className="h-2 rounded-full" />

            {transformations.length > 0 && (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {transformations.map((t, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
                <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div className="flex items-center space-x-2">
                      {t.llm_enhanced && (
                        <Zap className="w-4 h-4 text-yellow-500" />
                      )}
                      <span className="text-sm">{t.file}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-gray-500">{t.changes} {t('changes')}</span>
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                        {Math.round(t.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <div className="flex items-center space-x-3 text-blue-600">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span className="font-medium">{t('statuses.validating')}</span>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">
                {t('statuses.validatingDescription')}
              </div>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            <div className="flex items-center space-x-3 text-green-600">
              <Check className="w-8 h-8" />
              <span className="text-xl font-semibold">{t('migrationComplete')}</span>
            </div>
            
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="text-sm text-green-800">
                {t('migrationSuccess', { source: config.sourceFramework, target: config.targetFramework })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{transformations.length}</div>
                <div className="text-sm text-gray-600">{t('filesTransformed')}</div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {transformations.filter((t) => t.llm_enhanced).length}
                </div>
                <div className="text-sm text-gray-600">{t('llmEnhanced')}</div>
              </div>
            </div>

            <div className="flex space-x-3">
              <Button className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700">
                {t('actions.viewReport')}
              </Button>
              <Button className="flex-1 border border-gray-300 py-2 rounded-lg hover:bg-gray-50">
                {t('actions.startNewMigration')}
              </Button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // Ajout d'une scrollbar sur la frame principale
  return (
    <div className="h-full overflow-y-auto bg-card rounded-xl shadow border border-border px-4 pt-8 pb-8 w-full">
      <h1 className="text-2xl font-bold mb-2">{t('title')}</h1>
      <p className="text-muted-foreground mb-8">{steps[0].description}</p>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <React.Fragment key={step.id}>
              <div className="flex flex-col items-center">
                <div
                  className={`
                    w-12 h-12 rounded-full flex items-center justify-center mb-2
                    ${
                      step.status === 'completed'
                        ? 'bg-green-500 text-white'
                        : step.status === 'in_progress'
                        ? 'bg-blue-500 text-white'
                        : step.status === 'failed'
                        ? 'bg-red-500 text-white'
                        : 'bg-gray-200 text-gray-500'
                    }
                  `}
                >
                  {step.status === 'completed' ? (
                    <Check className="w-6 h-6" />
                  ) : step.status === 'in_progress' ? (
                    <Loader2 className="w-6 h-6 animate-spin" />
                  ) : step.status === 'failed' ? (
                    <AlertCircle className="w-6 h-6" />
                  ) : (
                    step.icon
                  )}
                </div>
                <div className="text-sm font-medium text-center">{step.title}</div>
                <div className="text-xs text-gray-500 text-center max-w-32">
                  {step.description}
                </div>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`flex-1 h-1 mx-4 ${
                    currentStep > index ? 'bg-green-500' : 'bg-gray-200'
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Step Content */}
      {renderStepContent()}
    </div>
  );
};


