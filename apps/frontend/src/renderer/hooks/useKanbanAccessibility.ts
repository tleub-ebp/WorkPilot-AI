import { useState, useCallback, useRef, useEffect } from 'react';
import type { DragStartEvent, DragEndEvent, DragOverEvent } from '@dnd-kit/core';

/**
 * Custom hook that provides screen reader announcements for Kanban drag-and-drop.
 * Uses an aria-live region to announce drag state changes to assistive technology.
 */
export function useKanbanAccessibility() {
  const [announcement, setAnnouncement] = useState('');
  const announcementTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const announce = useCallback((message: string) => {
    // Clear previous timeout
    if (announcementTimeoutRef.current) {
      clearTimeout(announcementTimeoutRef.current);
    }
    setAnnouncement(message);
    // Clear after 3s so it doesn't linger
    announcementTimeoutRef.current = setTimeout(() => {
      setAnnouncement('');
    }, 3000);
  }, []);

  const onDragStartAnnounce = useCallback(
    (event: DragStartEvent, getTaskTitle: (id: string) => string | undefined) => {
      const title = getTaskTitle(event.active.id as string);
      if (title) {
        announce(`Picked up task: ${title}. Use arrow keys to move, Enter to drop, Escape to cancel.`);
      }
    },
    [announce]
  );

  const onDragOverAnnounce = useCallback(
    (
      event: DragOverEvent,
      getColumnLabel: (id: string) => string | undefined
    ) => {
      if (!event.over) return;
      const label = getColumnLabel(event.over.id as string);
      if (label) {
        announce(`Over column: ${label}`);
      }
    },
    [announce]
  );

  const onDragEndAnnounce = useCallback(
    (
      event: DragEndEvent,
      getTaskTitle: (id: string) => string | undefined,
      getColumnLabel: (id: string) => string | undefined
    ) => {
      if (!event.over) {
        announce('Drop cancelled.');
        return;
      }
      const title = getTaskTitle(event.active.id as string);
      const column = getColumnLabel(event.over.id as string);
      if (title && column) {
        announce(`Dropped task "${title}" into ${column}.`);
      } else if (title) {
        announce(`Dropped task "${title}".`);
      }
    },
    [announce]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (announcementTimeoutRef.current) {
        clearTimeout(announcementTimeoutRef.current);
      }
    };
  }, []);

  return {
    announcement,
    announce,
    onDragStartAnnounce,
    onDragOverAnnounce,
    onDragEndAnnounce,
  };
}
