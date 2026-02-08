/**
 * Quality Score Badge Component
 * Displays the code quality grade with a color-coded badge
 */

import { Badge } from './ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { cn } from '../lib/utils';

interface QualityScoreBadgeProps {
  score: number; // 0-100
  grade: string; // A+, A, B, C, D, F
  isPassing: boolean;
  className?: string;
  showTooltip?: boolean;
}

// Color mapping for grades
const GRADE_COLORS: Record<string, string> = {
  'A+': 'bg-emerald-500 hover:bg-emerald-600 text-white',
  'A': 'bg-green-500 hover:bg-green-600 text-white',
  'A-': 'bg-green-400 hover:bg-green-500 text-white',
  'B+': 'bg-lime-500 hover:bg-lime-600 text-white',
  'B': 'bg-yellow-500 hover:bg-yellow-600 text-white',
  'B-': 'bg-yellow-400 hover:bg-yellow-500 text-gray-900',
  'C+': 'bg-orange-400 hover:bg-orange-500 text-white',
  'C': 'bg-orange-500 hover:bg-orange-600 text-white',
  'C-': 'bg-orange-600 hover:bg-orange-700 text-white',
  'D': 'bg-red-500 hover:bg-red-600 text-white',
  'F': 'bg-red-600 hover:bg-red-700 text-white',
};

// Emoji for grades
const GRADE_EMOJI: Record<string, string> = {
  'A+': '🏆',
  'A': '⭐',
  'A-': '✨',
  'B+': '👍',
  'B': '👌',
  'B-': '🙂',
  'C+': '😐',
  'C': '😕',
  'C-': '😟',
  'D': '⚠️',
  'F': '❌',
};

export function QualityScoreBadge({
  score,
  grade,
  isPassing,
  className,
  showTooltip = true,
}: QualityScoreBadgeProps) {
  const colorClass = GRADE_COLORS[grade] || 'bg-gray-500 hover:bg-gray-600 text-white';
  const emoji = GRADE_EMOJI[grade] || '📊';

  const badge = (
    <Badge
      className={cn(
        'font-mono font-bold text-sm px-3 py-1',
        colorClass,
        className
      )}
    >
      {emoji} {grade}
    </Badge>
  );

  if (!showTooltip) {
    return badge;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {badge}
      </TooltipTrigger>
      <TooltipContent>
        <div className="text-sm">
          <div className="font-semibold mb-1">Code Quality Score</div>
          <div>{score.toFixed(1)}/100 (Grade: {grade})</div>
          <div className="text-xs text-muted-foreground mt-1">
            {isPassing ? '✅ Passing' : '❌ Failed'}
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

