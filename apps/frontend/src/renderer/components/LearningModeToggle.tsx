import { useState } from 'react';
import { GraduationCap, Settings } from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';
import type { ExplanationLevel, LearningModeConfig } from '../../shared/types';

interface LearningModeToggleProps {
  config?: LearningModeConfig;
  onConfigChange: (config: LearningModeConfig) => void;
  disabled?: boolean;
}

const EXPLANATION_LEVELS: Array<{ value: ExplanationLevel; label: string; description: string }> = [
  {
    value: 'beginner',
    label: 'Débutant',
    description: 'Explications très détaillées, sans présupposé de connaissances'
  },
  {
    value: 'intermediate',
    label: 'Intermédiaire',
    description: 'Détails modérés, avec connaissances de base'
  },
  {
    value: 'advanced',
    label: 'Avancé',
    description: 'Concis, focus sur le "pourquoi" pas le "quoi"'
  },
  {
    value: 'expert',
    label: 'Expert',
    description: 'Minimal, seulement les insights clés'
  }
];

export function LearningModeToggle({ config, onConfigChange, disabled }: LearningModeToggleProps) {
  const [isOpen, setIsOpen] = useState(false);
  
  const currentConfig: LearningModeConfig = config || {
    enabled: false,
    explanationLevel: 'intermediate',
    explainTools: true,
    explainDecisions: true,
    explainCode: true,
    explainPatterns: true,
    explainBestPractices: true,
    preferVisualDiagrams: false,
    preferExamples: true,
    preferComparisons: true
  };

  const handleToggle = () => {
    onConfigChange({
      ...currentConfig,
      enabled: !currentConfig.enabled
    });
  };

  const handleLevelChange = (level: ExplanationLevel) => {
    onConfigChange({
      ...currentConfig,
      explanationLevel: level
    });
    setIsOpen(false);
  };

  const currentLevel = EXPLANATION_LEVELS.find(l => l.value === currentConfig.explanationLevel);

  return (
    <div className="flex items-center gap-2">
      <Button
        variant={currentConfig.enabled ? 'default' : 'outline'}
        size="sm"
        onClick={handleToggle}
        disabled={disabled}
        className={cn(
          'transition-all',
          currentConfig.enabled && 'bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600'
        )}
      >
        <GraduationCap className="mr-2 h-4 w-4" />
        Mode Apprentissage
      </Button>

      {currentConfig.enabled && (
        <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" disabled={disabled}>
              <Settings className="mr-2 h-3 w-3" />
              <Badge variant="secondary" className="text-xs">
                {currentLevel?.label}
              </Badge>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel>Niveau d'explication</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {EXPLANATION_LEVELS.map((level) => (
              <DropdownMenuItem
                key={level.value}
                onClick={() => handleLevelChange(level.value)}
                className={cn(
                  'cursor-pointer flex-col items-start py-3',
                  currentConfig.explanationLevel === level.value && 'bg-accent'
                )}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="font-medium">{level.label}</span>
                  {currentConfig.explanationLevel === level.value && (
                    <Badge variant="default" className="text-xs">
                      Actif
                    </Badge>
                  )}
                </div>
                <span className="text-xs text-muted-foreground mt-1">
                  {level.description}
                </span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}

