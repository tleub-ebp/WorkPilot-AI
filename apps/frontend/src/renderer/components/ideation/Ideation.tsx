import { useTranslation } from 'react-i18next';
import { Play } from 'lucide-react';
import { TabsContent } from '../ui/tabs';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { EnvConfigModal } from '../EnvConfigModal';
import { IDEATION_TYPE_DESCRIPTIONS } from '../../../shared/constants';
import { IdeationEmptyState } from './IdeationEmptyState';
import { IdeationHeader } from './IdeationHeader';
import { IdeationFilters } from './IdeationFilters';
import { IdeationDialogs } from './IdeationDialogs';
import { GenerationProgressScreen } from './GenerationProgressScreen';
import { IdeaCard } from './IdeaCard';
import { IdeaDetailPanel } from './IdeaDetailPanel';
import { useIdeation } from './hooks/useIdeation';
import { useViewState } from '../../contexts/ViewStateContext';
import { ALL_IDEATION_TYPES } from './constants';

interface IdeationProps {
  readonly projectId: string;
  readonly onGoToTask?: (taskId: string) => void;
}

export function Ideation({ projectId, onGoToTask }: IdeationProps) {
  const { t } = useTranslation('ideation');
  // Get showArchived from shared context for cross-page sync
  const { showArchived } = useViewState();

  // Pass showArchived directly to the hook to avoid render lag from useEffect sync
  const {
    session,
    generationStatus,
    isGenerating,
    isLoadingSession,
    config,
    logs,
    typeStates,
    selectedIdea,
    activeTab,
    showConfigDialog,
    showDismissed,
    showEnvConfigModal,
    showAddMoreDialog,
    typesToAdd,
    hasToken,
    isCheckingToken,
    summary,
    activeIdeas,
    selectedIds,
    convertingIdeas,
    setSelectedIdea,
    setActiveTab,
    setShowConfigDialog,
    setShowDismissed,
    setShowEnvConfigModal,
    setShowAddMoreDialog,
    setTypesToAdd,
    setConfig,
    handleGenerate,
    handleRefresh,
    handleStop,
    handleDismissAll,
    handleDeleteSelected,
    handleConvertSelectedToTasks,
    handleSelectAll,
    handleEnvConfigured,
    getAvailableTypesToAdd,
    handleAddMoreIdeas,
    toggleTypeToAdd,
    handleConvertToTask,
    handleGoToTask,
    handleDismiss,
    toggleIdeationType,
    toggleSelectIdea,
    clearSelection,
    getIdeasByType
  } = useIdeation(projectId, { onGoToTask, showArchived });

  const getCheckboxState = (selectedCount: number, totalCount: number): boolean | 'indeterminate' => {
    if (selectedCount === totalCount) return true;
    if (selectedCount > 0) return 'indeterminate';
    return false;
  };

  // Show generation progress with streaming ideas (use isGenerating flag for reliable state)
  if (isGenerating) {
    return (
      <GenerationProgressScreen
        generationStatus={generationStatus}
        logs={logs}
        typeStates={typeStates}
        enabledTypes={config.enabledTypes}
        session={session}
        onSelectIdea={setSelectedIdea}
        selectedIdea={selectedIdea}
        onConvert={handleConvertToTask}
        onGoToTask={handleGoToTask}
        onDismiss={handleDismiss}
        onStop={handleStop}
      />
    );
  }

  const showEmptyState = isLoadingSession || !session || session.ideas.length === 0;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {showEmptyState ? (
        <IdeationEmptyState
          config={config}
          hasToken={hasToken}
          isCheckingToken={isCheckingToken || isLoadingSession}
          onGenerate={handleGenerate}
          onOpenConfig={() => setShowConfigDialog(true)}
          onToggleIdeationType={toggleIdeationType}
        />
      ) : (
        <>
          {/* Header */}
          <IdeationHeader
            totalIdeas={summary.totalIdeas}
            ideaCountByType={summary.byType}
            showDismissed={showDismissed}
            selectedCount={selectedIds.size}
            onToggleShowDismissed={() => setShowDismissed(!showDismissed)}
            onOpenConfig={() => setShowConfigDialog(true)}
            onOpenAddMore={() => {
              setTypesToAdd([]);
              setShowAddMoreDialog(true);
            }}
            onDismissAll={handleDismissAll}
            onDeleteSelected={handleDeleteSelected}
            onConvertSelected={handleConvertSelectedToTasks}
            onSelectAll={() => handleSelectAll(activeIdeas)}
            onClearSelection={clearSelection}
            onRefresh={handleRefresh}
            hasActiveIdeas={activeIdeas.length > 0}
            canAddMore={getAvailableTypesToAdd().length > 0}
          />

          {/* Content */}
          <div className="flex-1 overflow-hidden">
            <IdeationFilters activeTab={activeTab} onTabChange={setActiveTab}>
              {/* All Ideas View */}
              <TabsContent value="all" className="flex-1 overflow-auto p-4">
                {activeIdeas.length > 0 && (
                  <div className="flex items-center gap-2 mb-3 pl-4">
                    <Checkbox
                      checked={getCheckboxState(selectedIds.size, activeIdeas.length)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          handleSelectAll(activeIdeas);
                        } else {
                          clearSelection();
                        }
                      }}
                      className="data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                      aria-label={t('header.selectAll')}
                    />
                    <span className="text-sm text-muted-foreground select-none">
                      {t('header.selectAll')}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="ml-auto text-primary hover:bg-primary hover:text-primary-foreground"
                      onClick={async () => {
                        handleSelectAll(activeIdeas);
                        await handleConvertSelectedToTasks();
                      }}
                    >
                      <Play className="h-4 w-4 mr-1" />
                      {t('header.importAll')}
                    </Button>
                  </div>
                )}
                <div className="grid gap-3">
                  {activeIdeas.map((idea) => (
                    <IdeaCard
                      key={idea.id}
                      idea={idea}
                      isSelected={selectedIds.has(idea.id)}
                      onClick={() => setSelectedIdea(selectedIdea?.id === idea.id ? null : idea)}
                      onConvert={handleConvertToTask}
                      onGoToTask={handleGoToTask}
                      onDismiss={handleDismiss}
                      onToggleSelect={toggleSelectIdea}
                    />
                  ))}
                  {activeIdeas.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      {t('noIdeas')}
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Type-specific Views */}
              {ALL_IDEATION_TYPES.map((type) => {
                const typeIdeas = getIdeasByType(type).filter((idea) => {
                  if (!showDismissed && idea.status === 'dismissed') return false;
                  if (!showArchived && idea.status === 'archived') return false;
                  return true;
                });
                return (
                  <TabsContent key={type} value={type} className="flex-1 overflow-auto p-4">
                    <div className="mb-4 p-3 bg-muted/50 rounded-lg">
                      <p className="text-sm text-muted-foreground">
                        {IDEATION_TYPE_DESCRIPTIONS[type]}
                      </p>
                    </div>
                    <div className="grid gap-3">
                      {typeIdeas.map((idea) => (
                        <IdeaCard
                          key={idea.id}
                          idea={idea}
                          isSelected={selectedIds.has(idea.id)}
                          onClick={() => setSelectedIdea(selectedIdea?.id === idea.id ? null : idea)}
                          onConvert={handleConvertToTask}
                          onGoToTask={handleGoToTask}
                          onDismiss={handleDismiss}
                          onToggleSelect={toggleSelectIdea}
                        />
                      ))}
                    </div>
                  </TabsContent>
                );
              })}
            </IdeationFilters>
          </div>

          {/* Idea Detail Panel */}
          {selectedIdea && (
            <IdeaDetailPanel
              idea={selectedIdea}
              onClose={() => setSelectedIdea(null)}
              onConvert={handleConvertToTask}
              onGoToTask={handleGoToTask}
              onDismiss={handleDismiss}
              isConverting={convertingIdeas.has(selectedIdea.id)}
            />
          )}
        </>
      )}

      {/* Dialogs — always rendered so they mount/unmount cleanly without affecting sibling layout */}
      <IdeationDialogs
        showConfigDialog={showConfigDialog}
        showAddMoreDialog={showEmptyState ? false : showAddMoreDialog}
        config={config}
        typesToAdd={showEmptyState ? [] : typesToAdd}
        availableTypesToAdd={showEmptyState ? [] : getAvailableTypesToAdd()}
        onToggleIdeationType={toggleIdeationType}
        onToggleTypeToAdd={showEmptyState ? () => { /* noop */ } : toggleTypeToAdd}
        onSetConfig={setConfig}
        onCloseConfigDialog={() => setShowConfigDialog(false)}
        onCloseAddMoreDialog={() => setShowAddMoreDialog(false)}
        onConfirmAddMore={showEmptyState ? () => { /* noop */ } : handleAddMoreIdeas}
      />

      {/* Environment Configuration Modal */}
      <EnvConfigModal
        open={showEnvConfigModal}
        onOpenChange={setShowEnvConfigModal}
        onConfigured={handleEnvConfigured}
        title={t('auth.title')}
        description={t('auth.description')}
        projectId={projectId}
      />
    </div>
  );
}
