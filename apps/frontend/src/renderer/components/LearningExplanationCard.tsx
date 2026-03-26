import { useState } from 'react';
import { ChevronDown, ChevronUp, Lightbulb, Code, BookOpen, Layers, CheckCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { cn } from '../lib/utils';
import type { LearningExplanation } from '../../shared/types';

interface LearningExplanationCardProps {
  explanation: LearningExplanation;
  defaultExpanded?: boolean;
}

const CATEGORY_ICONS = {
  tool_use: Code,
  decision: Lightbulb,
  code: Code,
  pattern: Layers,
  best_practice: CheckCircle
};

const CATEGORY_LABELS = {
  tool_use: '?? Utilisation d\'outil',
  decision: '?? D�cision',
  code: '?? Code',
  pattern: '?? Pattern de conception',
  best_practice: '? Bonne pratique'
};

const CATEGORY_COLORS = {
  tool_use: 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20',
  decision: 'bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/20',
  code: 'bg-green-500/10 text-green-700 dark:text-green-300 border-green-500/20',
  pattern: 'bg-orange-500/10 text-orange-700 dark:text-orange-300 border-orange-500/20',
  best_practice: 'bg-pink-500/10 text-pink-700 dark:text-pink-300 border-pink-500/20'
};

export function LearningExplanationCard({ explanation, defaultExpanded = false }: LearningExplanationCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const Icon = CATEGORY_ICONS[explanation.category] || BookOpen;
  const categoryLabel = CATEGORY_LABELS[explanation.category] || explanation.category;
  const categoryColor = CATEGORY_COLORS[explanation.category] || 'bg-gray-500/10 text-gray-700 dark:text-gray-300';

  return (
    <Card className={cn('border-l-4 transition-all', categoryColor)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <div className={cn('p-2 rounded-lg', categoryColor)}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1">
              <CardTitle className="text-sm font-medium mb-1">
                {explanation.title}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">
                  {categoryLabel}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  Niveau: {explanation.difficulty}
                </Badge>
              </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="shrink-0"
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0 space-y-4">
          {/* Explanation text */}
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {explanation.explanation}
            </ReactMarkdown>
          </div>

          {/* Code snippet */}
          {explanation.code_snippet && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">
                Exemple de code:
              </div>
              <pre className="bg-muted p-3 rounded-md overflow-x-auto text-xs">
                <code>{explanation.code_snippet}</code>
              </pre>
            </div>
          )}

          {/* Diagram */}
          {explanation.diagram && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">
                Diagramme:
              </div>
              <pre className="bg-muted p-3 rounded-md overflow-x-auto text-xs">
                <code>{explanation.diagram}</code>
              </pre>
            </div>
          )}

          {/* Alternative approaches */}
          {explanation.alternative_approaches && explanation.alternative_approaches.length > 0 && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">
                Approches alternatives:
              </div>
              <div className="space-y-2">
                {explanation.alternative_approaches.map((alt, idx) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
                  <div key={idx} className="bg-muted/50 p-3 rounded-md text-xs">
                    <div className="font-medium mb-1">{alt.name}</div>
                    {alt.description && (
                      <div className="text-muted-foreground mb-1">{alt.description}</div>
                    )}
                    {alt.pros && (
                      <div className="text-green-600 dark:text-green-400">+ {alt.pros}</div>
                    )}
                    {alt.cons && (
                      <div className="text-red-600 dark:text-red-400">- {alt.cons}</div>
                    )}
                    {alt.reason_rejected && (
                      <div className="text-muted-foreground italic mt-1">
                        Pourquoi pas choisi: {alt.reason_rejected}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* References */}
          {explanation.references && explanation.references.length > 0 && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">
                Pour en savoir plus:
              </div>
              <div className="space-y-1">
                {explanation.references.map((ref, idx) => (
                  <a
                    // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
                    key={idx}
                    href={ref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs text-primary hover:underline"
                  >
                    {ref}
                  </a>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}




