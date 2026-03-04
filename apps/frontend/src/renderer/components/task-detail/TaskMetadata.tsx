import { useState, useRef, useLayoutEffect, useId } from 'react';
import { useTranslation } from 'react-i18next';
import DOMPurify from 'dompurify';
import {
  Target,
  Bug,
  Wrench,
  FileCode,
  Shield,
  Gauge,
  Palette,
  Lightbulb,
  Users,
  GitBranch,
  GitPullRequest,
  ListChecks,
  Clock,
  ExternalLink,
  ChevronDown
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import { Badge } from '../ui/badge';

// Schéma de sanitization personnalisé permettant les styles inline
const customSanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    '*': [
      ...(defaultSchema.attributes?.['*'] || []),
      'style',
      'className',
      'class',
      'dir'
    ],
    a: [
      ...(defaultSchema.attributes?.a || []),
      'href',
      'target',
      'rel'
    ],
    span: ['style', 'className', 'class'],
    div: ['style', 'className', 'class'],
    p: ['style', 'className', 'class', 'dir'],
    b: ['style', 'className', 'class'],
    strong: ['style', 'className', 'class'],
    em: ['style', 'className', 'class'],
    i: ['style', 'className', 'class'],
    u: ['style', 'className', 'class'],
    code: ['style', 'className', 'class'],
    pre: ['style', 'className', 'class'],
  },
  tagNames: [
    ...(defaultSchema.tagNames || []),
    'span',
    'div',
    'br',
    'hr',
  ],
};
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { cn } from '../../lib/utils';
import {
  TASK_CATEGORY_LABELS,
  TASK_CATEGORY_COLORS,
  TASK_COMPLEXITY_LABELS,
  TASK_COMPLEXITY_COLORS,
  TASK_IMPACT_LABELS,
  TASK_IMPACT_COLORS,
  TASK_PRIORITY_LABELS,
  TASK_PRIORITY_COLORS,
  IDEATION_TYPE_LABELS,
  JSON_ERROR_PREFIX
} from '../../../shared/constants';
import type { Task, TaskCategory } from '../../../shared/types';
import {useFormatRelativeTime} from "@/hooks/useFormatRelativeTime";

// Category icon mapping
const CategoryIcon: Record<TaskCategory, typeof Target> = {
  feature: Target,
  bug_fix: Bug,
  refactoring: Wrench,
  documentation: FileCode,
  security: Shield,
  performance: Gauge,
  ui_ux: Palette,
  infrastructure: Wrench,
  testing: FileCode
};

interface TaskMetadataProps {
  readonly task: Task;
}

// Height threshold for collapsing long descriptions (~8 lines)
const COLLAPSED_HEIGHT = 200;

// Custom code component for ReactMarkdown
const CustomCodeComponent = (props: any) => {
  const { children, className, node, ...rest } = props;
  const match = /language-(\w+)/.exec(className || '');
  const isInline = !match;
  
  if (isInline) {
    return (
      <code className={className} {...rest}>
        {children}
      </code>
    );
  }
  return (
    <pre className="overflow-x-auto">
      <code className={className} {...rest}>
        {children}
      </code>
    </pre>
  );
};

// Custom table component for ReactMarkdown
const CustomTableComponent = (props: any) => {
  const { children, ...rest } = props;
  return (
    <div className="overflow-x-auto my-4">
      <table {...rest}>{children}</table>
    </div>
  );
};

export function TaskMetadata({ task }: TaskMetadataProps) {
  const { t } = useTranslation(['tasks', 'errors']);
  const formatRelativeTime = useFormatRelativeTime();
  const [isExpanded, setIsExpanded] = useState(true); // Start expanded by default
  const [hasOverflow, setHasOverflow] = useState(false);
  const [userManuallyExpanded, setUserManuallyExpanded] = useState(false); // Track user's manual choice
  const contentRef = useRef<HTMLDivElement>(null);
  const contentId = useId();

  // Handle JSON error description with i18n
  const displayDescription = (() => {
    if (!task.description) return null;
    if (task.description.startsWith(JSON_ERROR_PREFIX)) {
      const errorMessage = task.description.slice(JSON_ERROR_PREFIX.length);
      return t('errors:task.jsonError.description', { error: errorMessage });
    }
    return task.description;
  })();

  // Détecter si le contenu est du HTML pur (commence par une balise HTML)
  const isHtmlContent = displayDescription?.trim().startsWith('<') || false;

  // Transformer le HTML pour appliquer les styles du thème
  const transformHtmlStyles = (html: string): string => {
    if (!html) return '';
    
    // Utiliser DOMParser pour manipuler le HTML de manière sécurisée
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // Fonction récursive pour traiter tous les éléments
    const processElement = (element: Element) => {
      // Conserver le style pour certaines propriétés mais adapter les couleurs
      const style = element.getAttribute('style');
      if (style) {
        let newStyle = style;
        
        // Remplacer les couleurs noires par la couleur du texte du thème
        newStyle = newStyle.replaceAll(/color:\s*#000000?/gi, 'color: hsl(var(--foreground))');
        newStyle = newStyle.replaceAll(/color:\s*rgb\(0,\s*0,\s*0\)/gi, 'color: hsl(var(--foreground))');
        newStyle = newStyle.replaceAll(/color:\s*black/gi, 'color: hsl(var(--foreground))');
        
        // Remplacer les backgrounds blancs par transparent ou muted
        newStyle = newStyle.replaceAll(/background-color:\s*#ffffff?/gi, 'background-color: transparent');
        newStyle = newStyle.replaceAll(/background-color:\s*rgb\(255,\s*255,\s*255\)/gi, 'background-color: transparent');
        newStyle = newStyle.replaceAll(/background-color:\s*white/gi, 'background-color: transparent');
        
        // Simplifier les margins et paddings excessifs
        newStyle = newStyle.replaceAll(/margin-top:\s*\d+pt/gi, 'margin-top: 0.75rem');
        newStyle = newStyle.replaceAll(/margin-bottom:\s*\d+pt/gi, 'margin-bottom: 0.75rem');
        
        element.setAttribute('style', newStyle);
      }
      
      // Ajouter des classes CSS pour améliorer le rendu
      const tagName = element.tagName.toLowerCase();
      const existingClass = element.getAttribute('class') || '';
      
      switch (tagName) {
        case 'p':
          element.setAttribute('class', `${existingClass} my-2 leading-relaxed text-foreground`.trim());
          break;
        case 'b':
        case 'strong':
          element.setAttribute('class', `${existingClass} font-semibold text-foreground`.trim());
          break;
        case 'em':
        case 'i':
          element.setAttribute('class', `${existingClass} italic text-foreground/90`.trim());
          break;
        case 'u':
          element.setAttribute('class', `${existingClass} underline decoration-foreground/50`.trim());
          break;
        case 'span':
          // Conserver les spans avec style inline mais ajouter classe pour couleur par défaut
          if (!style?.includes('color')) {
            element.setAttribute('class', `${existingClass} text-foreground`.trim());
          }
          break;
        case 'a':
          element.setAttribute('class', `${existingClass} text-info hover:text-info/80 underline transition-colors`.trim());
          break;
        case 'ul':
        case 'ol':
          element.setAttribute('class', `${existingClass} my-3 pl-6 space-y-1 list-disc`.trim());
          break;
        case 'li':
          element.setAttribute('class', `${existingClass} text-foreground leading-relaxed ml-2`.trim());
          break;
        case 'div':
          // Éviter d'ajouter trop de marges aux divs
          if (!existingClass && !style) {
            element.setAttribute('class', 'my-1');
          }
          break;
        case 'br':
          // Conserver les breaks mais sans style particulier
          break;
      }
      
      // Traiter les enfants récursivement
      Array.from(element.children).forEach(child => processElement(child));
    };
    
    // Traiter tous les éléments du body
    Array.from(doc.body.children).forEach(child => processElement(child));
    
    return doc.body.innerHTML;
  };

  // Detect if content overflows the collapsed height
  // Re-check when description changes (content height depends on rendered description)
  // Start expanded, but auto-collapse if content exceeds threshold
  // biome-ignore lint/correctness/useExhaustiveDependencies: task.description triggers re-render which changes content height
  useLayoutEffect(() => {
    const checkOverflow = () => {
      const element = contentRef.current;
      if (element) {
        // Temporarily remove max-height to get natural height
        const originalMaxHeight = element.style.maxHeight;
        element.style.maxHeight = 'none';
        
        // Force a reflow to get accurate measurements
        element.getBoundingClientRect();
        
        const scrollHeight = element.scrollHeight;
        const clientHeight = element.clientHeight;
        const hasContentOverflow = scrollHeight > COLLAPSED_HEIGHT;
        
        // Restore original max-height
        element.style.maxHeight = originalMaxHeight;
        
        console.log('[TaskMetadata] Overflow check:', {
          scrollHeight,
          clientHeight,
          COLLAPSED_HEIGHT,
          hasContentOverflow,
          userManuallyExpanded,
          taskId: task.id
        });
        
        setHasOverflow(hasContentOverflow);
        
        // Only auto-collapse if user hasn't manually expanded
        if (!userManuallyExpanded) {
          setIsExpanded(!hasContentOverflow);
        }
      }
    };

    // Initial check
    checkOverflow();

    // Re-check after a short delay to ensure content is fully rendered
    const timeoutId = setTimeout(checkOverflow, 100);

    // Additional check after images and other elements might have loaded
    const timeoutId2 = setTimeout(checkOverflow, 500);

    // Set up ResizeObserver to detect content size changes, but with debouncing
    let resizeObserver: ResizeObserver | null = null;
    let resizeTimeout: NodeJS.Timeout | null = null;
    
    if (contentRef.current && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => {
        // Debounce resize events to prevent immediate re-collapse
        if (resizeTimeout) {
          clearTimeout(resizeTimeout);
        }
        resizeTimeout = setTimeout(checkOverflow, 50);
      });
      resizeObserver.observe(contentRef.current);
    }

    return () => {
      clearTimeout(timeoutId);
      clearTimeout(timeoutId2);
      if (resizeTimeout) {
        clearTimeout(resizeTimeout);
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
    };
  }, [task.id, task.description, userManuallyExpanded]);

  const hasClassification = task.metadata && (
    task.metadata.category ||
    task.metadata.priority ||
    task.metadata.complexity ||
    task.metadata.impact ||
    task.metadata.securitySeverity ||
    task.metadata.sourceType
  );

  return (
    <div className="space-y-5">
      {/* Compact Metadata Bar: Classification + Timeline */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-border">
        {/* Classification Badges - Left */}
        {hasClassification && (
          <div className="flex flex-wrap items-center gap-1.5">
            {/* Category */}
            {task.metadata?.category && (
              <Badge
                variant="outline"
                className={cn('text-xs', TASK_CATEGORY_COLORS[task.metadata.category])}
              >
                {CategoryIcon[task.metadata.category] && (() => {
                  const Icon = CategoryIcon[task.metadata.category];
                  return <Icon className="h-3 w-3 mr-1" />;
                })()}
                {TASK_CATEGORY_LABELS[task.metadata.category]}
              </Badge>
            )}
            {/* Priority */}
            {task.metadata?.priority && (
              <Badge
                variant="outline"
                className={cn('text-xs', TASK_PRIORITY_COLORS[task.metadata.priority])}
              >
                {TASK_PRIORITY_LABELS[task.metadata.priority]}
              </Badge>
            )}
            {/* Complexity */}
            {task.metadata?.complexity && (
              <Badge
                variant="outline"
                className={cn('text-xs', TASK_COMPLEXITY_COLORS[task.metadata.complexity])}
              >
                {TASK_COMPLEXITY_LABELS[task.metadata.complexity]}
              </Badge>
            )}
            {/* Impact */}
            {task.metadata?.impact && (
              <Badge
                variant="outline"
                className={cn('text-xs', TASK_IMPACT_COLORS[task.metadata.impact])}
              >
                {TASK_IMPACT_LABELS[task.metadata.impact]}
              </Badge>
            )}
            {/* Security Severity */}
            {task.metadata?.securitySeverity && (
              <Badge
                variant="outline"
                className={cn('text-xs', TASK_IMPACT_COLORS[task.metadata.securitySeverity])}
              >
                <Shield className="h-3 w-3 mr-1" />
                {task.metadata.securitySeverity}
              </Badge>
            )}
            {/* Source Type */}
            {task.metadata?.sourceType && (
              <Badge variant="secondary" className="text-xs">
                {task.metadata.sourceType === 'ideation' && task.metadata.ideationType
                  ? IDEATION_TYPE_LABELS[task.metadata.ideationType] || task.metadata.ideationType
                  : task.metadata.sourceType}
              </Badge>
            )}
          </div>
        )}

        {/* Timeline - Right */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Clock className="h-3 w-3" />
            {t('tasks:metadata.created')} {formatRelativeTime(task.createdAt)}
          </span>
          <span className="text-border">•</span>
          <span>{t('tasks:metadata.updated')} {formatRelativeTime(task.updatedAt)}</span>
        </div>
      </div>

      {/* Description - Primary Content */}
      {displayDescription && (
        <div className="bg-muted/30 rounded-lg px-4 py-3 border border-border/50 overflow-hidden max-w-full">
          {/* Content container with conditional max-height */}
          <div className="relative">
            <div
              ref={contentRef}
              id={contentId}
              className={cn(
                'prose prose-sm dark:prose-invert max-w-none overflow-hidden',
                // Texte et paragraphes
                'prose-p:text-foreground/90 prose-p:leading-relaxed prose-p:my-3',
                // En-têtes
                'prose-headings:text-foreground prose-headings:font-semibold prose-headings:tracking-tight',
                'prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-h4:text-sm',
                'prose-h1:mb-4 prose-h2:mb-3 prose-h3:mb-2 prose-h4:mb-2',
                // Texte fort et emphase
                'prose-strong:text-foreground prose-strong:font-semibold',
                'prose-em:text-foreground/90 prose-em:italic',
                // Listes avec meilleure indentation
                'prose-ul:my-3 prose-ul:pl-6 prose-ul:space-y-1',
                'prose-ol:my-3 prose-ol:pl-6 prose-ol:space-y-1',
                'prose-li:text-foreground/90 prose-li:my-1 prose-li:leading-relaxed',
                'prose-li:pl-2',
                // Listes imbriquées
                '[&_ul_ul]:my-1 [&_ol_ol]:my-1 [&_ul_ol]:my-1 [&_ol_ul]:my-1',
                '[&_ul_ul]:pl-4 [&_ol_ol]:pl-4 [&_ul_ol]:pl-4 [&_ol_ul]:pl-4',
                // Liens
                'prose-a:text-info prose-a:underline prose-a:wrap-break-word',
                'hover:prose-a:text-info/80',
                // Blocs de code
                'prose-pre:bg-muted/50 prose-pre:border prose-pre:border-border',
                'prose-pre:rounded-md prose-pre:p-4 prose-pre:my-4',
                'prose-pre:overflow-x-auto prose-pre:text-sm',
                'prose-code:text-foreground prose-code:bg-muted/50',
                'prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded',
                'prose-code:text-sm prose-code:font-mono',
                'prose-code:before:content-none prose-code:after:content-none',
                // Tableaux
                'prose-table:w-full prose-table:my-4',
                'prose-table:border-collapse prose-table:border prose-table:border-border',
                'prose-th:bg-muted/50 prose-th:p-2 prose-th:text-left prose-th:font-semibold',
                'prose-th:border prose-th:border-border',
                'prose-td:p-2 prose-td:border prose-td:border-border',
                // Citations
                'prose-blockquote:border-l-4 prose-blockquote:border-muted-foreground/30',
                'prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-foreground/80',
                'prose-blockquote:my-4',
                // Images
                'prose-img:max-w-full prose-img:h-auto prose-img:rounded-md',
                'prose-img:border prose-img:border-border prose-img:my-4',
                // Règles horizontales
                'prose-hr:border-border prose-hr:my-6',
                // Limite de largeur et gestion du débordement
                '**:max-w-full **:overflow-x-auto',
                !isExpanded && hasOverflow && 'max-h-[200px]'
              )}
              style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}
            >
              {isHtmlContent ? (
                // Rendu HTML pur avec DOMPurify et transformation des styles
                <div
                  className="html-content"
                  dangerouslySetInnerHTML={{
                    __html: DOMPurify.sanitize(
                      transformHtmlStyles(displayDescription || ''),
                      {
                        ADD_TAGS: ['span', 'div', 'br', 'hr', 'p', 'b', 'strong', 'em', 'i', 'u', 'a', 'ul', 'ol', 'li'],
                        ADD_ATTR: ['style', 'class', 'dir', 'href', 'target', 'rel'],
                        ALLOW_DATA_ATTR: false,
                      }
                    ),
                  }}
                />
              ) : (
                // Rendu Markdown avec ReactMarkdown
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw, [rehypeSanitize, customSanitizeSchema]]}
                  components={{
                    // Personnaliser le rendu des blocs de code
                    code: CustomCodeComponent,
                    // Améliorer le rendu des tableaux
                    table: CustomTableComponent,
                  }}
                >
                  {displayDescription}
                </ReactMarkdown>
              )}
            </div>

            {/* Gradient overlay when collapsed and has overflow */}
            {!isExpanded && hasOverflow && (
              <div className="absolute bottom-0 left-0 right-0 h-16 bg-linear-to-t from-muted/80 to-transparent pointer-events-none" />
            )}
          </div>

          {/* Expand/Collapse button */}
          {hasOverflow && !isExpanded && (
            <div className="flex justify-center mt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setIsExpanded(true);
                  setUserManuallyExpanded(true);
                }}
                className="text-muted-foreground hover:text-foreground"
                aria-expanded={isExpanded}
                aria-controls={contentId}
              >
                <ChevronDown className="h-4 w-4 mr-1" aria-hidden="true" />
                {t('tasks:metadata.showMore')}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Secondary Details */}
      {task.metadata && (
        <div className="space-y-4 pt-2">
          {/* Rationale */}
          {task.metadata.rationale && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                <Lightbulb className="h-3 w-3 text-warning" />
                {t('tasks:metadata.rationale')}
              </h3>
              <p className="text-sm text-foreground/80">{task.metadata.rationale}</p>
            </div>
          )}

          {/* Problem Solved */}
          {task.metadata.problemSolved && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                <Target className="h-3 w-3 text-success" />
                {t('tasks:metadata.problemSolved')}
              </h3>
              <p className="text-sm text-foreground/80">{task.metadata.problemSolved}</p>
            </div>
          )}

          {/* Target Audience */}
          {task.metadata.targetAudience && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                <Users className="h-3 w-3 text-info" />
                {t('tasks:metadata.targetAudience')}
              </h3>
              <p className="text-sm text-foreground/80">{task.metadata.targetAudience}</p>
            </div>
          )}

          {/* Dependencies */}
          {task.metadata.dependencies && task.metadata.dependencies.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                <GitBranch className="h-3 w-3 text-purple-400" />
                {t('tasks:metadata.dependencies')}
              </h3>
              <ul className="text-sm text-foreground/80 list-disc list-inside space-y-0.5">
                {task.metadata.dependencies.map((dep) => (
                  <li key={dep}>{dep}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Pull Request */}
          {task.metadata.prUrl && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                <GitPullRequest className="h-3 w-3 text-info" />
                {t('tasks:metadata.pullRequest')}
              </h3>
              <button
                type="button"
                onClick={() => {
                  if (task.metadata?.prUrl) {
                    globalThis.electronAPI.openExternal(task.metadata.prUrl);
                  }
                }}
                className="text-sm text-info hover:underline flex items-center gap-1.5 bg-transparent border-none cursor-pointer p-0 text-left"
              >
                {task.metadata.prUrl}
                <ExternalLink className="h-3 w-3" />
              </button>
            </div>
          )}

          {/* Acceptance Criteria */}
          {task.metadata.acceptanceCriteria && task.metadata.acceptanceCriteria.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                <ListChecks className="h-3 w-3 text-success" />
                {t('tasks:metadata.acceptanceCriteria')}
              </h3>
              <ul className="text-sm text-foreground/80 list-disc list-inside space-y-0.5">
                {task.metadata.acceptanceCriteria.map((criteria) => (
                  <li key={criteria.trim()}>{criteria}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Affected Files */}
          {task.metadata.affectedFiles && task.metadata.affectedFiles.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                <FileCode className="h-3 w-3" />
                {t('tasks:metadata.affectedFiles')}
              </h3>
              <div className="flex flex-wrap gap-1">
                {task.metadata.affectedFiles.map((file) => (
                  <Tooltip key={file}>
                    <TooltipTrigger asChild>
                      <Badge variant="secondary" className="text-xs font-mono cursor-help">
                        {file.split('/').pop()}
                      </Badge>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="font-mono text-xs">
                      {file}
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
