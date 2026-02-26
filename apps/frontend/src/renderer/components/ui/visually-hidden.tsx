import * as React from 'react';
import { cn } from '@/lib/utils';

const VisuallyHidden = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement>
>(({ className, ...props }, ref) => (
  <span
    ref={ref}
    className={cn(
      'absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0',
      'sr-only',
      className
    )}
    {...props}
  />
));
VisuallyHidden.displayName = 'VisuallyHidden';

export { VisuallyHidden };
