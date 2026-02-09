/**
 * Streaming Session Button - Launch streaming mode for a task
 */

import { useState } from 'react';
import { Film } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';
import { Dialog, DialogContent } from '../ui/dialog';
import { StreamingSession } from './StreamingSession';

interface StreamingSessionButtonProps {
  taskId: string;
  projectPath: string;
}

export function StreamingSessionButton({ taskId, projectPath }: StreamingSessionButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation(['tasks']);

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(true)}
        className="gap-2"
      >
        <Film className="w-4 h-4" />
        {t('tasks:modal.actions.watchLive')}
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-[95vw] h-[95vh] p-0">
          <StreamingSession
            sessionId={taskId}
            projectPath={projectPath}
            onClose={() => setIsOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}

