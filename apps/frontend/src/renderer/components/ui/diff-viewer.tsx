
import { FileText } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useTranslation } from 'react-i18next';

interface DiffViewerProps {
  patch?: string;
  className?: string;
}

interface DiffLine {
  content: string;
  type: 'context' | 'added' | 'removed' | 'hunk';
  lineNumber?: number;
  oldLineNumber?: number;
  newLineNumber?: number;
}

export function DiffViewer({ patch, className }: DiffViewerProps) {
  const { t } = useTranslation(['common']);
  
  if (!patch || patch.trim() === '') {
    return (
      <div className={cn("p-4 text-center text-muted-foreground", className)}>
        <div className="flex flex-col items-center gap-2">
          <FileText className="h-8 w-8 opacity-50" />
          <span>{t('common:diffViewer.noContent')}</span>
          <span className="text-xs">{t('common:diffViewer.noContentHint')}</span>
        </div>
      </div>
    );
  }

  const lines = parseDiff(patch);

  return (
    <div className={cn("diff-viewer font-mono text-xs", className)}>
      <div className="diff-content">
        {lines.map((line, index) => (
          <div
            key={index}
            className={cn(
              "flex diff-line",
              line.type === 'added' && "bg-green-500/20",
              line.type === 'removed' && "bg-red-500/20",
              line.type === 'hunk' && "bg-blue-500/20",
              line.type === 'context' && "bg-transparent"
            )}
          >
            <div className={cn(
              "diff-line-numbers flex shrink-0 select-none",
              "w-20 border-r border-border"
            )}>
              <div className={cn(
                "w-10 text-right pr-2",
                line.type === 'added' && "text-green-400 font-medium",
                line.type === 'removed' && "text-red-400 font-medium",
                line.type === 'context' && "text-muted-foreground",
                line.type === 'hunk' && "text-blue-400 font-medium"
              )}>
                {line.newLineNumber || ''}
              </div>
              <div className={cn(
                "w-10 text-right pr-2 border-l border-border",
                line.type === 'added' && "text-green-400 font-medium",
                line.type === 'removed' && "text-red-400 font-medium",
                line.type === 'context' && "text-muted-foreground",
                line.type === 'hunk' && "text-blue-400 font-medium"
              )}>
                {line.oldLineNumber || ''}
              </div>
            </div>
            <div className={cn(
              "flex-1 px-2 py-0.5 whitespace-pre overflow-x-auto",
              line.type === 'added' && "text-green-400 font-medium",
              line.type === 'removed' && "text-red-400 font-medium",
              line.type === 'hunk' && "text-blue-400 font-medium",
              line.type === 'context' && "text-foreground"
            )}>
              {line.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function parseDiff(patch: string): DiffLine[] {
  const lines = patch.split('\n');
  const result: DiffLine[] = [];
  let oldLineNumber = 0;
  let newLineNumber = 0;

  for (const line of lines) {
    let diffLine: DiffLine;

    if (line.startsWith('@@')) {
      // Hunk header - extract line numbers
      const match = line.match(/@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/);
      if (match) {
        oldLineNumber = parseInt(match[1], 10) - 1;
        newLineNumber = parseInt(match[3], 10) - 1;
      }
      diffLine = {
        content: line,
        type: 'hunk',
      };
    } else if (line.startsWith('+')) {
      // Added line
      newLineNumber++;
      diffLine = {
        content: line.substring(1),
        type: 'added',
        newLineNumber,
      };
    } else if (line.startsWith('-')) {
      // Removed line
      oldLineNumber++;
      diffLine = {
        content: line.substring(1),
        type: 'removed',
        oldLineNumber,
      };
    } else if (line.startsWith(' ')) {
      // Context line
      oldLineNumber++;
      newLineNumber++;
      diffLine = {
        content: line.substring(1),
        type: 'context',
        oldLineNumber,
        newLineNumber,
      };
    } else {
      // Other lines (file headers, etc.)
      diffLine = {
        content: line,
        type: 'context',
      };
    }

    result.push(diffLine);
  }

  return result;
}

export default DiffViewer;
