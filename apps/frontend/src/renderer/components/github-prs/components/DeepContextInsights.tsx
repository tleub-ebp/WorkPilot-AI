import { useTranslation } from 'react-i18next';
import {
  Layers,
  AlertTriangle,
  Code2,
  BookOpen,
  Bug,
  ShieldAlert,
  Clock,
} from 'lucide-react';
import { Badge } from '../../ui/badge';
import { CollapsibleCard } from './CollapsibleCard';

interface DeepContextData {
  projectPatterns: Record<string, string>;
  projectConventions: string[];
  relatedCode: Array<{ path: string; reason: string }>;
  historicalInsights: Array<Record<string, unknown>>;
  pastBugsInArea: Array<Record<string, unknown>>;
  regressionRisks: string[];
  architectureStyle: string;
  architectureLayers: Array<{
    name: string;
    patterns: string[];
    allowedImports: string[];
  }>;
  architectureViolations: Array<{
    type: string;
    severity: string;
    file: string;
    description: string;
    suggestion?: string;
  }>;
  gatheringDurationMs: number;
  contextAvailable: boolean;
}

interface DeepContextInsightsProps {
  deepContext: DeepContextData;
}

export function DeepContextInsights({ deepContext }: DeepContextInsightsProps) {
  const { t } = useTranslation('common');

  if (!deepContext.contextAvailable) {
    return null;
  }

  const hasArchitecture =
    deepContext.architectureStyle || deepContext.architectureLayers.length > 0;
  const hasViolations = deepContext.architectureViolations.length > 0;
  const hasPatterns = Object.keys(deepContext.projectPatterns).length > 0;
  const hasConventions = deepContext.projectConventions.length > 0;
  const hasRelatedCode = deepContext.relatedCode.length > 0;
  const hasInsights = deepContext.historicalInsights.length > 0;
  const hasPastBugs = deepContext.pastBugsInArea.length > 0;
  const hasRegressionRisks = deepContext.regressionRisks.length > 0;

  const sectionCount =
    (hasArchitecture ? 1 : 0) +
    (hasViolations ? 1 : 0) +
    (hasPatterns || hasConventions ? 1 : 0) +
    (hasRelatedCode ? 1 : 0) +
    (hasInsights || hasPastBugs || hasRegressionRisks ? 1 : 0);

  return (
    <CollapsibleCard
      title={t('prReview.deepContext.title')}
      icon={<Layers className="h-4 w-4 text-indigo-500" />}
      badge={
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="text-xs bg-indigo-500/10 text-indigo-500 border-indigo-500/30"
          >
            {sectionCount} {sectionCount === 1 ? 'section' : 'sections'}
          </Badge>
          <span className="text-xs text-muted-foreground">
            <Clock className="h-3 w-3 inline mr-1" />
            {t('prReview.deepContext.gatheringTime', {
              ms: deepContext.gatheringDurationMs,
            })}
          </span>
        </div>
      }
      defaultOpen={false}
    >
      <div className="p-4 space-y-4">
        {/* Architecture */}
        {hasArchitecture && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Layers className="h-3.5 w-3.5 text-indigo-500" />
              {t('prReview.deepContext.architecture')}
            </h4>
            {deepContext.architectureStyle && (
              <p className="text-xs text-muted-foreground">
                <span className="font-medium">
                  {t('prReview.deepContext.architectureStyle')}:
                </span>{' '}
                {deepContext.architectureStyle}
              </p>
            )}
            {deepContext.architectureLayers.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">
                  {t('prReview.deepContext.layers')}:
                </p>
                {deepContext.architectureLayers.map((layer) => (
                  <div
                    key={layer.name}
                    className="text-xs pl-3 border-l-2 border-indigo-500/30 py-1"
                  >
                    <span className="font-medium">{layer.name}</span>
                    <span className="text-muted-foreground ml-1">
                      ({layer.patterns.join(', ')})
                    </span>
                    {layer.allowedImports.length > 0 && (
                      <p className="text-muted-foreground mt-0.5">
                        {t('prReview.deepContext.canImportFrom', {
                          imports: layer.allowedImports.join(', '),
                        })}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Architecture Violations */}
        {hasViolations && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-warning" />
              {t('prReview.deepContext.violations')}
            </h4>
            <div className="space-y-1.5">
              {deepContext.architectureViolations.map((v, i) => (
                <div
                  key={`${v.file}-${i}`}
                  className="text-xs p-2 rounded bg-warning/5 border border-warning/20"
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className="text-[10px] px-1.5 py-0"
                    >
                      {v.severity}
                    </Badge>
                    <code className="text-muted-foreground">{v.file}</code>
                  </div>
                  <p className="mt-1 text-muted-foreground">{v.description}</p>
                  {v.suggestion && (
                    <p className="mt-0.5 text-indigo-500/80 italic">
                      {v.suggestion}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Code Patterns & Conventions */}
        {(hasPatterns || hasConventions) && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Code2 className="h-3.5 w-3.5 text-blue-500" />
              {t('prReview.deepContext.patterns')}
            </h4>
            {hasPatterns && (
              <div className="space-y-1.5">
                {Object.entries(deepContext.projectPatterns)
                  .slice(0, 5)
                  .map(([key, snippet]) => (
                    <div key={key} className="text-xs">
                      <span className="font-medium">{key}</span>
                      <pre className="mt-0.5 p-2 rounded bg-muted/50 text-muted-foreground overflow-x-auto max-h-20">
                        {snippet.length > 200
                          ? `${snippet.slice(0, 200)}...`
                          : snippet}
                      </pre>
                    </div>
                  ))}
              </div>
            )}
            {hasConventions && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">
                  {t('prReview.deepContext.conventions')}:
                </p>
                <ul className="text-xs text-muted-foreground space-y-0.5 pl-3">
                  {deepContext.projectConventions.slice(0, 8).map((conv) => (
                    <li key={conv} className="list-disc">
                      {conv}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Related Code */}
        {hasRelatedCode && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <BookOpen className="h-3.5 w-3.5 text-emerald-500" />
              {t('prReview.deepContext.relatedCode')}
            </h4>
            <div className="space-y-1">
              {deepContext.relatedCode.slice(0, 8).map((item) => (
                <div key={item.path} className="text-xs flex items-start gap-2">
                  <code className="text-indigo-500/80 shrink-0 min-w-0 truncate max-w-[200px]">
                    {item.path}
                  </code>
                  <span className="text-muted-foreground">{item.reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Historical Insights & Past Bugs */}
        {(hasInsights || hasPastBugs || hasRegressionRisks) && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Bug className="h-3.5 w-3.5 text-orange-500" />
              {t('prReview.deepContext.historicalInsights')}
            </h4>

            {hasInsights && (
              <ul className="text-xs text-muted-foreground space-y-0.5 pl-3">
                {deepContext.historicalInsights.slice(0, 5).map((hint, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
                  <li key={`insight-${i}`} className="list-disc">
                    {String(
                      (hint as Record<string, unknown>).fact ??
                        (hint as Record<string, unknown>).content ??
                        JSON.stringify(hint)
                    )}
                  </li>
                ))}
              </ul>
            )}

            {hasPastBugs && (
              <div className="mt-2">
                <p className="text-xs font-medium text-muted-foreground mb-1">
                  {t('prReview.deepContext.pastBugs')}:
                </p>
                <ul className="text-xs text-muted-foreground space-y-0.5 pl-3">
                  {deepContext.pastBugsInArea.slice(0, 5).map((bug, i) => (
                    // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
                    <li key={`bug-${i}`} className="list-disc">
                      {String(
                        (bug as Record<string, unknown>).description ??
                          (bug as Record<string, unknown>).fact ??
                          JSON.stringify(bug)
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {hasRegressionRisks && (
              <div className="mt-2">
                <p className="text-xs font-medium flex items-center gap-1 mb-1">
                  <ShieldAlert className="h-3 w-3 text-destructive" />
                  {t('prReview.deepContext.regressionRisks')}:
                </p>
                <ul className="text-xs text-muted-foreground space-y-0.5 pl-3">
                  {deepContext.regressionRisks.slice(0, 5).map((risk, i) => (
                    // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
                    <li key={`risk-${i}`} className="list-disc text-destructive/80">
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </CollapsibleCard>
  );
}
