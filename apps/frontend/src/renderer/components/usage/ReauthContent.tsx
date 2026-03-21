import React from 'react';
import { AlertCircle, LogIn } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ReauthContentProps {
  readonly onOpenAccounts: (e: React.MouseEvent) => void;
}

export function ReauthContent({ onOpenAccounts }: ReauthContentProps) {
  const { t } = useTranslation(['common']);

  return (
    <div className="py-2 space-y-3">
      <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-destructive/10 border border-destructive/20">
        <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-xs font-medium text-destructive">
            {t('common:usage.reauthRequired')}
          </p>
          <p className="text-[10px] text-muted-foreground leading-relaxed">
            {t('common:usage.reauthRequiredDescription')}
          </p>
        </div>
      </div>
      <button
          type="button"
          onClick={onOpenAccounts}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors text-xs font-medium"
      >
        <LogIn className="h-3.5 w-3.5" />
        {t('common:usage.reauthButton')}
      </button>
    </div>
  );
}
