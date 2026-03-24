import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Settings,
  Key,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
  Zap,
  Globe,
  Shield,
  Bot,
  Cloud,
  Star
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader } from '../ui/card';
import { Switch } from '../ui/switch';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '../ui/tooltip';

interface ProviderCardProps {
  provider: {
    id: string;
    name: string;
    category: string;
    description?: string;
    isConfigured: boolean;
    isWorking?: boolean;
    lastTested?: string;
    usageCount?: number;
    isPremium?: boolean;
    icon?: React.ElementType;
  };
  onConfigure: (providerId: string) => void;
  onTest: (providerId: string) => void;
  onToggle: (providerId: string, enabled: boolean) => void;
  onRemove?: (providerId: string) => void;
  className?: string;
}

const providerIcons: Record<string, React.ElementType> = {
  'openai': Bot,
  'gemini': Star,
  'meta-llama': Shield,
  'mistral': Zap,
  'deepseek': Globe,
  'grok': Cloud,
  'google': Star,
  'meta': Shield,
  'windsurf': Bot,
  'cursor': Bot,
  'azure-openai': Cloud,
};

const providerCategories: Record<string, { label: string; color: string }> = {
  'openai': { label: 'OpenAI', color: 'bg-green-500' },
  'google': { label: 'Google', color: 'bg-blue-500' },
  'meta': { label: 'Meta', color: 'bg-purple-500' },
  'independent': { label: 'Indépendant', color: 'bg-orange-500' },
  'microsoft': { label: 'Microsoft', color: 'bg-cyan-500' },
};

export function ProviderCard({
  provider,
  onConfigure,
  onTest,
  onToggle,
  onRemove,
  className
}: ProviderCardProps) {
  const { t } = useTranslation('settings');
  const [isExpanded, setIsExpanded] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [_apiKey, _setApiKey] = useState('');

  const Icon = providerIcons[provider.id] || Bot;
  const category = providerCategories[provider.category] || providerCategories['independent'];

  const getStatusBadge = () => {
    if (!provider.isConfigured) {
      return (
        <Badge variant="outline" className="text-gray-500 border-gray-300">
          <XCircle className="w-3 h-3 mr-1" />
          Non configuré
        </Badge>
      );
    }

    if (provider.isWorking === false) {
      return (
        <Badge variant="destructive">
          <AlertCircle className="w-3 h-3 mr-1" />
          Erreur
        </Badge>
      );
    }

    return (
      <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
        <CheckCircle className="w-3 h-3 mr-1" />
        Actif
      </Badge>
    );
  };

  return (
    <TooltipProvider>
      <Card className={cn(
        'transition-all duration-200 hover:shadow-md',
        !provider.isConfigured && 'opacity-75 border-dashed',
        provider.isWorking === false && 'border-red-200 bg-red-50/50',
        className
      )}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Icon className="w-8 h-8 text-muted-foreground" />
                {provider.isPremium && (
                  <Star className="w-3 h-3 text-yellow-500 absolute -top-1 -right-1 fill-current" />
                )}
              </div>
              <div>
                <h3 className="font-semibold text-lg">{provider.name}</h3>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className={cn('text-xs', category.color)}>
                    {category.label}
                  </Badge>
                  {getStatusBadge()}
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {provider.isConfigured && (
                <Switch
                  checked={provider.isWorking !== false}
                  onCheckedChange={(checked) => onToggle(provider.id, checked)}
                />
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="h-8 w-8 p-0"
              >
                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          {provider.description && (
            <p className="text-sm text-muted-foreground mb-4">{provider.description}</p>
          )}

          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              {!provider.isConfigured ? (
                <Button
                  onClick={() => onConfigure(provider.id)}
                  className="flex items-center gap-2"
                  size="sm"
                >
                  <Key className="w-4 h-4" />
                  Configurer
                </Button>
              ) : (
                <>
                  <Button
                    onClick={() => onTest(provider.id)}
                    variant="outline"
                    size="sm"
                    className="flex items-center gap-2"
                  >
                    <Zap className="w-4 h-4" />
                    Tester
                  </Button>
                  <Button
                    onClick={() => onConfigure(provider.id)}
                    variant="outline"
                    size="sm"
                    className="flex items-center gap-2"
                  >
                    <Settings className="w-4 h-4" />
                    Modifier
                  </Button>
                </>
              )}
              
              {onRemove && provider.isConfigured && (
                <Button
                  onClick={() => onRemove(provider.id)}
                  variant="outline"
                  size="sm"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  Supprimer
                </Button>
              )}
            </div>

            {provider.usageCount && (
              <Tooltip>
                <TooltipTrigger>
                  <div className="text-xs text-muted-foreground">
                    {provider.usageCount} utilisations
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Nombre d'utilisations ce mois-ci</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>

          {isExpanded && provider.isConfigured && (
            <div className="mt-4 pt-4 border-t space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">Clé API</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type={showApiKey ? 'text' : 'password'}
                    value="sk-...••••••••••••••••••••••••••••••••"
                    disabled
                    className="text-xs font-mono max-w-xs"
                    readOnly
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="h-8 w-8 p-0"
                  >
                    {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </Button>
                </div>
              </div>

              {provider.lastTested && (
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Dernier test</span>
                  <span>{new Date(provider.lastTested).toLocaleDateString()}</span>
                </div>
              )}

              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Statut</span>
                <span className={cn(
                  'font-medium',
                  provider.isWorking === false ? 'text-red-600' : 'text-green-600'
                )}>
                  {provider.isWorking === false ? 'Inactif' : 'Opérationnel'}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}
