import { useTranslation } from 'react-i18next';
import type { BreakingChange } from '@shared/types';

interface BreakingChangeBannerProps {
  breakingChanges: BreakingChange[];
}

/**
 * BreakingChangeBanner - Alert banner for detected cross-repo breaking changes
 */
export function BreakingChangeBanner({ breakingChanges }: BreakingChangeBannerProps) {
  const { t } = useTranslation(['multiRepo']);

  if (breakingChanges.length === 0) return null;

  const errors = breakingChanges.filter((bc) => bc.severity === 'error');
  const warnings = breakingChanges.filter((bc) => bc.severity === 'warning');

  return (
    <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 p-4 space-y-3">
      <div className="flex items-center gap-2">
        {/* biome-ignore lint/a11y/noSvgWithoutTitle: SVG is decorative, intentional */}
        <svg className="h-5 w-5 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
        </svg>
        <h4 className="text-sm font-medium text-amber-600 dark:text-amber-400">
          {t('multiRepo:breakingChanges.title')} ({breakingChanges.length})
        </h4>
      </div>

      <div className="space-y-2">
        {errors.map((bc, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
          <div key={`err-${i}`} className="flex items-start gap-2 text-sm">
            <span className="shrink-0 rounded-full bg-destructive/20 px-1.5 py-0.5 text-xs font-medium text-destructive">
              {t('multiRepo:breakingChanges.severity.error')}
            </span>
            <div className="min-w-0">
              <p className="text-foreground">
                <span className="font-medium">{bc.sourceRepo}</span>
                {' → '}
                <span className="font-medium">{bc.targetRepo}</span>
                {': '}
                {bc.description}
              </p>
              {bc.suggestion && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {bc.suggestion}
                </p>
              )}
            </div>
          </div>
        ))}

        {warnings.map((bc, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
          <div key={`warn-${i}`} className="flex items-start gap-2 text-sm">
            <span className="shrink-0 rounded-full bg-amber-500/20 px-1.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
              {t('multiRepo:breakingChanges.severity.warning')}
            </span>
            <div className="min-w-0">
              <p className="text-foreground">
                <span className="font-medium">{bc.sourceRepo}</span>
                {' → '}
                <span className="font-medium">{bc.targetRepo}</span>
                {': '}
                {bc.description}
              </p>
              {bc.suggestion && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {bc.suggestion}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
