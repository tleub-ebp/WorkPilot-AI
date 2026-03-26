import { CheckCircle2, Circle, ExternalLink, Play, TrendingUp } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { Progress } from '../ui/progress';
import { ROADMAP_PRIORITY_COLORS } from '../../../shared/constants';
import type { PhaseCardProps } from './types';
import type { RoadmapFeature } from '../../../shared/types';

export function PhaseCard({
  phase,
  features,
  isFirst: _isFirst,
  onFeatureSelect,
  onConvertToSpec,
  onGoToTask,
}: Readonly<PhaseCardProps>) {
  const completedCount = features.filter((f) => f.status === 'done').length;
  const progress = features.length > 0 ? (completedCount / features.length) * 100 : 0;

  const getStatusClasses = () => {
    if (phase.status === 'completed') {
      return 'bg-success/10 text-success';
    }
    if (phase.status === 'in_progress') {
      return 'bg-primary/10 text-primary';
    }
    return 'bg-muted text-muted-foreground';
  };

  const statusClasses = getStatusClasses();

  const getActionButton = (feature: RoadmapFeature) => {
    if (feature.status === 'done') {
      return <CheckCircle2 className="h-4 w-4 text-success shrink-0" />;
    }
    if (feature.linkedSpecId) {
      return (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2"
          onClick={(e) => {
            e.stopPropagation();
            // biome-ignore lint/style/noNonNullAssertion: value is guaranteed by context
            onGoToTask(feature.linkedSpecId!);
          }}
        >
          <ExternalLink className="h-3 w-3 mr-1" />
          View Task
        </Button>
      );
    }
    return (
      <Button
        variant="ghost"
        size="sm"
        className="h-6 px-2 shrink-0"
        onClick={(e) => {
          e.stopPropagation();
          onConvertToSpec(feature);
        }}
      >
        <Play className="h-3 w-3 mr-1" />
        Build
      </Button>
    );
  };

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${statusClasses}`}
          >
            {phase.status === 'completed' ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <span className="text-sm font-semibold">{phase.order}</span>
            )}
          </div>
          <div>
            <h3 className="font-semibold">{phase.name}</h3>
            <p className="text-sm text-muted-foreground">{phase.description}</p>
          </div>
        </div>
        <Badge variant={phase.status === 'completed' ? 'default' : 'outline'}>
          {phase.status}
        </Badge>
      </div>

      {/* Progress */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-muted-foreground">Progress</span>
          <span>
            {completedCount}/{features.length} features
          </span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Milestones */}
      {phase.milestones.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium mb-2">Milestones</h4>
          <div className="space-y-2">
            {phase.milestones.map((milestone) => (
              <div key={milestone.id} className="flex items-center gap-2 text-sm">
                {milestone.status === 'achieved' ? (
                  <CheckCircle2 className="h-4 w-4 text-success" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground" />
                )}
                <span
                  className={
                    milestone.status === 'achieved' ? 'line-through text-muted-foreground' : ''
                  }
                >
                  {milestone.title}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Features */}
      <div>
        <h4 className="text-sm font-medium mb-2">Features ({features.length})</h4>
        <div className="grid gap-2">
          {features.slice(0, 5).map((feature) => (
            // biome-ignore lint/a11y/noNoninteractiveElementInteractions: interactive handler is intentional
            // biome-ignore lint/a11y/useKeyWithClickEvents: keyboard events handled elsewhere
            <div
              key={feature.id}
              className="flex items-center justify-between p-2 rounded-md bg-muted/50 hover:bg-muted cursor-pointer transition-colors"
              onClick={() => onFeatureSelect(feature)}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <Badge
                  variant="outline"
                  className={`text-xs ${ROADMAP_PRIORITY_COLORS[feature.priority]}`}
                >
                  {feature.priority}
                </Badge>
                <span className="text-sm truncate">{feature.title}</span>
                {feature.competitorInsightIds && feature.competitorInsightIds.length > 0 && (
                  <TrendingUp className="h-3 w-3 text-primary shrink-0" />
                )}
              </div>
              {getActionButton(feature)}
            </div>
          ))}
          {features.length > 5 && (
            <div className="text-sm text-muted-foreground text-center py-1">
              +{features.length - 5} more features
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
