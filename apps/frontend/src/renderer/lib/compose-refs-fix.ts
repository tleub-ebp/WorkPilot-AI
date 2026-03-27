/**
 * Fixed version of @radix-ui/react-compose-refs for React 19 compatibility.
 *
 * Bug in Radix UI 1.x: components like Switch, Select, RadioGroup, and ScrollArea
 * use `useComposedRefs(forwardedRef, (node) => setState(node))` with inline arrow
 * functions. Because the arrow function is recreated on every render, `useCallback`
 * sees a changed dependency and returns a NEW composed ref. React 19's synchronous
 * `flushSpawnedWork` then immediately flushes the `setState(null)` call that occurs
 * during ref detach, causing an infinite render loop.
 *
 * Fix: store refs in a `useRef` so the composed callback is always the same function
 * (empty dependency array). The latest refs are captured at call-time, so attachments
 * and cleanups still reach the correct targets.
 */
import * as React from 'react';

type PossibleRef<T> = React.Ref<T> | undefined;

function setRef<T>(ref: PossibleRef<T>, value: T) {
  if (typeof ref === 'function') {
    return ref(value);
  } else if (ref !== null && ref !== undefined) {
    (ref as React.MutableRefObject<T>).current = value;
  }
}

export function composeRefs<T>(...refs: PossibleRef<T>[]) {
  return (node: T) => {
    let hasCleanup = false;
    const cleanups = refs.map((ref) => {
      const cleanup = setRef(ref, node);
      if (!hasCleanup && typeof cleanup === 'function') {
        hasCleanup = true;
      }
      return cleanup;
    });
    if (hasCleanup) {
      return () => {
        for (let i = 0; i < refs.length; i++) {
          const cleanup = cleanups[i];
          if (typeof cleanup === 'function') {
            (cleanup as () => void)();
          } else {
            setRef(refs[i], null as unknown as T);
          }
        }
      };
    }
  };
}

export function useComposedRefs<T>(...refs: PossibleRef<T>[]) {
  // Keep a ref to the latest refs array so the callback never needs to be
  // recreated when an inline function identity changes between renders.
  const refsRef = React.useRef(refs);
  refsRef.current = refs;

  return React.useCallback(
    (node: T) => {
      // Capture the current refs at attachment time.
      const currentRefs = refsRef.current;
      let hasCleanup = false;
      const cleanups = currentRefs.map((ref) => {
        const cleanup = setRef(ref, node);
        if (!hasCleanup && typeof cleanup === 'function') {
          hasCleanup = true;
        }
        return cleanup;
      });
      if (hasCleanup) {
        return () => {
          for (let i = 0; i < currentRefs.length; i++) {
            const cleanup = cleanups[i];
            if (typeof cleanup === 'function') {
              (cleanup as () => void)();
            } else {
              setRef(currentRefs[i], null as unknown as T);
            }
          }
        };
      }
    },
    [] // eslint-disable-line react-hooks/exhaustive-deps — intentionally stable
  );
}
