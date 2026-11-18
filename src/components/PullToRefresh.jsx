import { useEffect, useRef, useState } from "react";
import { RotateCw } from "lucide-react";

const TRIGGER = 90;

// Pull down at the very top of the page to reload (installed apps have no browser refresh).
export const PullToRefresh = () => {
  const [pull, setPull] = useState(0);
  const start = useRef(null);
  const pullRef = useRef(0);

  useEffect(() => {
    const down = (e) => {
      start.current = window.scrollY <= 0 && !document.querySelector("[role=dialog]") ? e.touches[0].clientY : null;
    };
    const move = (e) => {
      if (start.current == null) return;
      const dy = Math.max(0, e.touches[0].clientY - start.current);
      pullRef.current = Math.min(dy * 0.5, 130);
      setPull(pullRef.current);
    };
    const up = () => {
      if (pullRef.current >= TRIGGER) window.location.reload();
      start.current = null;
      pullRef.current = 0;
      setPull(0);
    };
    window.addEventListener("touchstart", down, { passive: true });
    window.addEventListener("touchmove", move, { passive: true });
    window.addEventListener("touchend", up);
    return () => {
      window.removeEventListener("touchstart", down);
      window.removeEventListener("touchmove", move);
      window.removeEventListener("touchend", up);
    };
  }, []);

  if (pull < 8) return null;
  const ready = pull >= TRIGGER;
  return (
    <div className="fixed left-1/2 z-[70] -translate-x-1/2 flex items-center gap-2 rounded-full bg-[#0d0b14] px-4 py-2 text-sm text-[#f3eefc] ring-1 ring-[#ff3d6e] shadow-lg"
      style={{ top: `calc(env(safe-area-inset-top) + ${pull * 0.6}px)` }} data-testid="pull-to-refresh">
      <RotateCw className="h-4 w-4 text-[#ff3d6e]" style={{ transform: `rotate(${pull * 3}deg)` }} />
      {ready ? "Lepas untuk muat ulang" : "Tarik untuk muat ulang"}
    </div>
  );
};
