import { Button } from '../ui/button';
import { Loader2, LogIn, Users, CheckCircle } from 'lucide-react';
import { AuthTerminal } from './AuthTerminal';

interface AuthTerminalState {
  terminalId: string;
  configDir: string;
  profileName: string;
}

interface WindsurfAccountInfo {
  userName?: string;
  planName?: string;
  usageInfo?: { 
    usedMessages: number; 
    totalMessages: number; 
    usedFlowActions: number; 
    totalFlowActions: number; 
  };
}

interface OAuthAuthContentProps {
  readonly providerId: string;
  readonly providerName: string;
  readonly isAuthenticating: boolean;
  readonly authTerminal: AuthTerminalState | null;
  readonly windsurfAccountInfo: WindsurfAccountInfo | null;
  readonly windsurfSsoToken: string;
  readonly testResult: { success: boolean; message: string } | null;
  readonly t: any;
  readonly onOAuthAuth: () => void;
  readonly onAuthTerminalClose: () => void;
  readonly onAuthTerminalSuccess: (email?: string) => void;
  readonly onAuthTerminalError: (error: string) => void;
  readonly onWindsurfDetect: () => void;
  readonly onWindsurfSave: () => void;
}

export function OAuthAuthContent({
  providerId,
  providerName,
  isAuthenticating,
  authTerminal,
  windsurfAccountInfo,
  windsurfSsoToken,
  testResult,
  t,
  onOAuthAuth,
  onAuthTerminalClose,
  onAuthTerminalSuccess,
  onAuthTerminalError,
  onWindsurfDetect,
  onWindsurfSave
}: OAuthAuthContentProps) {
  if (providerId === 'windsurf') {
    return (
      <div className="space-y-4">
        {/* Windsurf account info card */}
        {windsurfAccountInfo && (windsurfAccountInfo.userName || windsurfAccountInfo.planName) && (
          <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Users className="w-4 h-4 text-primary" />
              {t('sections.accounts.providerConfig.windsurfAuth.accountInfo')}
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              {windsurfAccountInfo.userName && (
                <>
                  <span className="text-muted-foreground">{t('sections.accounts.providerConfig.windsurfAuth.accountName')}</span>
                  <span className="font-medium">{windsurfAccountInfo.userName}</span>
                </>
              )}
              {windsurfAccountInfo.planName && (
                <>
                  <span className="text-muted-foreground">{t('sections.accounts.providerConfig.windsurfAuth.accountPlan')}</span>
                  <span className="font-medium">{windsurfAccountInfo.planName}</span>
                </>
              )}
              {windsurfAccountInfo.usageInfo && windsurfAccountInfo.usageInfo.totalMessages > 0 && (
                <>
                  <span className="text-muted-foreground">{t('sections.accounts.providerConfig.windsurfAuth.accountCredits')}</span>
                  <span className="font-medium">
                    {Math.round(windsurfAccountInfo.usageInfo.usedMessages / 100)}/{Math.round(windsurfAccountInfo.usageInfo.totalMessages / 100)}
                  </span>
                </>
              )}
              {windsurfAccountInfo.usageInfo && windsurfAccountInfo.usageInfo.totalFlowActions > 0 && (
                <>
                  <span className="text-muted-foreground">{t('sections.accounts.providerConfig.windsurfAuth.accountFlowActions')}</span>
                  <span className="font-medium">
                    {Math.round(windsurfAccountInfo.usageInfo.usedFlowActions / 100).toLocaleString()}/{Math.round(windsurfAccountInfo.usageInfo.totalFlowActions / 100).toLocaleString()}
                  </span>
                </>
              )}
            </div>
          </div>
        )}

        {/* Auto-detect from local Windsurf IDE */}
        <Button
          variant="outline"
          className="w-full"
          disabled={isAuthenticating}
          onClick={onWindsurfDetect}
        >
          {isAuthenticating ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              {t('sections.accounts.providerConfig.windsurfAuth.detecting')}
            </>
          ) : (
            <>
              <LogIn className="w-4 h-4 mr-2" />
              {t('sections.accounts.providerConfig.windsurfAuth.detectFromIDE')}
            </>
          )}
        </Button>

        {/* Or open Windsurf login manually */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{t('sections.accounts.providerConfig.windsurfAuth.orManual')}</span>
          <button
            type="button"
            className="text-primary underline hover:no-underline"
            onClick={() => window.open('https://windsurf.com/account', '_blank')}
          >
            {t('sections.accounts.providerConfig.windsurfAuth.openWindsurfLogin')}
          </button>
        </div>

        {/* Auth Content */}
        <WindsurfAuthContent
          windsurfSsoToken={windsurfSsoToken}
          authTerminal={authTerminal}
          isAuthenticating={isAuthenticating}
          onOAuthAuth={onOAuthAuth}
          onAuthTerminalClose={onAuthTerminalClose}
          onAuthTerminalSuccess={onAuthTerminalSuccess}
          onAuthTerminalError={onAuthTerminalError}
          onWindsurfSave={onWindsurfSave}
          t={t}
        />
      </div>
    );
  }

  // Anthropic/Claude OAuth
  return (
    <div className="space-y-4">
      <ClaudeAuthContent
        authTerminal={authTerminal}
        isAuthenticating={isAuthenticating}
        onOAuthAuth={onOAuthAuth}
        onAuthTerminalClose={onAuthTerminalClose}
        onAuthTerminalSuccess={onAuthTerminalSuccess}
        onAuthTerminalError={onAuthTerminalError}
        t={t}
      />
    </div>
  );
}

function WindsurfAuthContent({
  windsurfSsoToken,
  authTerminal,
  isAuthenticating,
  onOAuthAuth,
  onAuthTerminalClose,
  onAuthTerminalSuccess,
  onAuthTerminalError,
  onWindsurfSave,
  t
}: {
  readonly windsurfSsoToken: string;
  readonly authTerminal: AuthTerminalState | null;
  readonly isAuthenticating: boolean;
  readonly onOAuthAuth: () => void;
  readonly onAuthTerminalClose: () => void;
  readonly onAuthTerminalSuccess: (email?: string) => void;
  readonly onAuthTerminalError: (error: string) => void;
  readonly onWindsurfSave: () => void;
  readonly t: any;
}) {
  // Show save form when SSO token is available
  if (windsurfSsoToken) {
    return (
      <div className="space-y-4">
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800">
            {t('sections.accounts.providerConfig.windsurfAuth.tokenReceived')}
          </p>
          <p className="text-xs text-green-600 mt-1 font-mono break-all">
            {windsurfSsoToken.substring(0, 20)}...
          </p>
        </div>
        <Button
          className="w-full"
          disabled={!windsurfSsoToken.trim()}
          onClick={onWindsurfSave}
        >
          <CheckCircle className="w-4 h-4 mr-2" />
          {t('sections.accounts.providerConfig.windsurfAuth.saveAndConnect')}
        </Button>
      </div>
    );
  }

  // Show auth terminal when active
  if (authTerminal) {
    return (
      <div className="rounded-lg border border-primary/30 overflow-hidden" style={{ height: '320px' }}>
        <AuthTerminal
          terminalId={authTerminal.terminalId}
          configDir={authTerminal.configDir}
          profileName={authTerminal.profileName}
          onClose={onAuthTerminalClose}
          onAuthSuccess={onAuthTerminalSuccess}
          onAuthError={onAuthTerminalError}
        />
      </div>
    );
  }

  // Show default auth options
  return (
    <div className="space-y-4">
      <Button
        onClick={onOAuthAuth}
        disabled={isAuthenticating}
        className="w-full"
      >
        {isAuthenticating ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            {t('sections.accounts.providerConfig.windsurfAuth.authenticating')}
          </>
        ) : (
          <>
            <LogIn className="w-4 h-4 mr-2" />
            {t('sections.accounts.providerConfig.windsurfAuth.connectWithClaude')}
          </>
        )}
      </Button>
      
      <div className="text-xs text-muted-foreground">
        <p>{t('sections.accounts.providerConfig.windsurfAuth.terminalInstructions')}</p>
      </div>
    </div>
  );
}

function ClaudeAuthContent({
  authTerminal,
  isAuthenticating,
  onOAuthAuth,
  onAuthTerminalClose,
  onAuthTerminalSuccess,
  onAuthTerminalError,
  t
}: {
  readonly authTerminal: AuthTerminalState | null;
  readonly isAuthenticating: boolean;
  readonly onOAuthAuth: () => void;
  readonly onAuthTerminalClose: () => void;
  readonly onAuthTerminalSuccess: (email?: string) => void;
  readonly onAuthTerminalError: (error: string) => void;
  readonly t: any;
}) {
  // Show auth terminal when active
  if (authTerminal) {
    return (
      <div className="rounded-lg border border-primary/30 overflow-hidden" style={{ height: '320px' }}>
        <AuthTerminal
          terminalId={authTerminal.terminalId}
          configDir={authTerminal.configDir}
          profileName={authTerminal.profileName}
          onClose={onAuthTerminalClose}
          onAuthSuccess={onAuthTerminalSuccess}
          onAuthError={onAuthTerminalError}
        />
      </div>
    );
  }

  // Show default auth button
  return (
    <div className="space-y-4">
      <Button
        onClick={onOAuthAuth}
        disabled={isAuthenticating}
        className="w-full"
      >
        {isAuthenticating ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            {t('sections.accounts.providerConfig.windsurfAuth.authenticating')}
          </>
        ) : (
          <>
            <LogIn className="w-4 h-4 mr-2" />
            {t('sections.accounts.providerConfig.windsurfAuth.connectWithClaude')}
          </>
        )}
      </Button>
      
      <div className="text-xs text-muted-foreground">
        <p>{t('sections.accounts.providerConfig.windsurfAuth.terminalInstructions')}</p>
      </div>
    </div>
  );
}
