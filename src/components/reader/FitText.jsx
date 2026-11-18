import { useLayoutEffect, useRef } from "react";

// Biggest font that keeps the whole text inside its box, whole words only.
// Words are split mid-way only when even the smallest size cannot hold them.
export const FitText = ({ text, color, shadow, font, max = 40, min = 7, className = "" }) => {
  const box = useRef(null);
  const inner = useRef(null);

  useLayoutEffect(() => {
    const el = box.current;
    const tx = inner.current;
    if (!el || !tx) return undefined;
    const fitsAt = (size) => {
      tx.style.fontSize = `${size}px`;
      return tx.scrollHeight <= el.clientHeight + 1 && tx.scrollWidth <= el.clientWidth + 1;
    };
    const search = (floor = min) => {
      let lo = Math.min(floor, max);
      let hi = Math.max(max, lo);
      if (fitsAt(hi)) return hi;
      while (hi - lo > 0.3) {
        const mid = (lo + hi) / 2;
        if (fitsAt(mid)) lo = mid;
        else hi = mid;
      }
      return lo;
    };
    const fit = () => {
      tx.style.overflowWrap = "normal";
      delete tx.dataset.cut;
      let size = search();
      if (!fitsAt(size)) {
        tx.style.overflowWrap = "anywhere";
        tx.dataset.cut = "1";
        size = search();
      }
      if (!fitsAt(size)) size = search(4); // tiny bubble: smaller letters rather than text outside it
      tx.style.fontSize = `${size}px`;
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    document.fonts?.ready?.then(fit).catch(() => {});
    return () => ro.disconnect();
  }, [text, max, min, font]);

  const halo = shadow ? `0 0 1px ${shadow}, 0 0 2px ${shadow}, 0 0 2px ${shadow}` : undefined;
  return (
    <div ref={box} className={`absolute flex items-center justify-center overflow-hidden ${className}`}
      style={{ inset: "2% 3%" }}>
      <p ref={inner} className="m-0 w-full text-center" lang="id"
        style={{ color, textShadow: halo, fontFamily: font?.family, fontWeight: font?.weight,
          lineHeight: font?.lh || 1.08, letterSpacing: "0.01em", textWrap: "balance",
          textTransform: font?.upper ? "uppercase" : "none", hyphens: "manual", whiteSpace: "normal" }}>
        {String(text || "").split(/(\s+)/).map((w, i) => (/-/.test(w)
          ? <span key={i} className="fit-keep">{w}</span> : w))}
      </p>
    </div>
  );
};
