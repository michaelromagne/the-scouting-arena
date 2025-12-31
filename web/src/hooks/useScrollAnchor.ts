import { useRef } from "react";

export function useScrollAnchor() {
  const anchorRef = useRef<HTMLDivElement>(null);
  const preTopRef = useRef<number | null>(null);

  const snapshotAnchor = () => {
    const el = anchorRef.current;
    if (el) preTopRef.current = el.getBoundingClientRect().top;
  };

  const restoreToAnchor = () => {
    const el = anchorRef.current;
    if (!el || preTopRef.current === null) return;
    const after = el.getBoundingClientRect().top;
    const delta = after - preTopRef.current;
    if (delta !== 0) window.scrollBy(0, delta);
    preTopRef.current = null;
  };

  return { anchorRef, snapshotAnchor, restoreToAnchor };
}
