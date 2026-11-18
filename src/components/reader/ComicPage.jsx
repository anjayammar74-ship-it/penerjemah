import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, RotateCcw, Languages, Pencil } from "lucide-react";
import { BubbleEditor } from "@/components/reader/BubbleEditor";
import { imgSrc, cleanSrc, translateImage, getTranslation, translatePoint, translateLeftovers, enqueue, editBubble, LOCAL, localImageUrl } from "@/lib/api";
import { toast } from "sonner";
import { offlineBlobUrl } from "@/lib/offline";
import { FONTS } from "@/lib/settings";
import { FitText } from "@/components/reader/FitText";
import { applyCorrections, rememberCorrection } from "@/lib/corrections";

const OverlayBubble = ({ b, n, scale, font, pageW, onEdit }) => {
  const f = FONTS[font] || FONTS.comic;
  const timer = useRef(null);
  const pressed = useRef(false);
  const start = () => {
    pressed.current = false;
    timer.current = setTimeout(() => { pressed.current = true; navigator.vibrate?.(30); onEdit(); }, 550);
  };
  const cancel = () => clearTimeout(timer.current);
  // lettering about the size of the original; the slider only changes the letters, never the box
  const cap = b.fs && pageW ? Math.max(11, (b.fs / 100) * pageW * f.cap * 1.15 * scale) : 40 * scale;
  const [showEn, setShowEn] = useState(false);
  return (
    <button type="button" data-testid={`bubble-${n}`}
      onClick={(e) => { e.stopPropagation(); if (!pressed.current) setShowEn((v) => !v); pressed.current = false; }}
      onPointerDown={start} onPointerUp={cancel} onPointerLeave={cancel} onPointerCancel={cancel}
      onContextMenu={(e) => e.preventDefault()}
      title="Ketuk: teks asli · Tekan lama: edit"
      className="absolute rounded-[12px] transition-colors duration-300"
      style={{ left: `${b.x}%`, top: `${b.y}%`, width: `${b.w}%`, height: `${b.h}%`,
        background: showEn ? b.bg : "transparent" }}>
      <FitText text={showEn ? b.en : b.id} color={b.fg} shadow={b.bg} font={f} max={cap} />
    </button>
  );
};

const Marker = ({ b, n }) => (
  <span className="absolute -translate-x-1/2 -translate-y-1/2 h-6 w-6 grid place-items-center rounded-full bg-[#ff3d6e] text-[#0d0b14] text-xs font-bold tn ring-2 ring-[#0d0b14]"
    style={{ left: `${b.x}%`, top: `${b.y}%` }}>{n}</span>
);

const ListCards = ({ bubbles, page, scale, onEdit }) => (
  <ol className="mx-3 my-4 space-y-2" data-testid={`page-${page}-list`}>
    {bubbles.map((b, i) => (
      <li key={i} className="flex gap-3 rounded-2xl bg-[#17121f] border border-white/10 p-4">
        <span className="h-6 w-6 shrink-0 grid place-items-center rounded-full bg-[#ff3d6e] text-[#0d0b14] text-xs font-bold tn">{i + 1}</span>
        <div className="min-w-0 flex-1">
          <p className="leading-snug text-[#f3eefc]" style={{ fontSize: `${17 * scale}px` }}>{b.id}</p>
          <p className="mt-1 leading-snug text-[#9e94b0]" style={{ fontSize: `${13 * scale}px` }}>{b.en}</p>
        </div>
        {onEdit && (
          <button type="button" onClick={() => onEdit(i)} aria-label="Edit terjemahan" data-testid={`page-${page}-edit-${i}`}
            className="h-9 w-9 shrink-0 grid place-items-center rounded-full text-[#9e94b0] hover:text-[#ff3d6e] hover:bg-white/5 transition-colors">
            <Pencil className="h-4 w-4" />
          </button>
        )}
      </li>
    ))}
  </ol>
);

const TapSpinner = ({ tap }) => (
  <span className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-1/2 flex items-center gap-2 rounded-full bg-[#0d0b14]/90 px-3 py-2 text-xs text-[#f3eefc] ring-2 ring-[#ff3d6e] animate-in zoom-in-50"
    style={{ left: `${tap.x}%`, top: `${tap.y}%` }} data-testid="tap-translating">
    <Loader2 className="h-4 w-4 animate-spin text-[#ff3d6e]" /> Menerjemahkan…
  </span>
);

const StatusChip = ({ state, onRetry, page, message, stage }) => {
  if (state === "loading")
    return (
      <div className="pointer-events-none absolute inset-x-0 top-0 z-10" data-testid={`page-${page}-loading`}>
        <div className="h-1 scan-shimmer" />
        <div className="mx-auto mt-3 w-max flex items-center gap-2 rounded-full bg-[#0d0b14]/90 backdrop-blur px-4 py-2 text-sm text-[#f3eefc] border border-white/10">
          <Loader2 className="h-4 w-4 animate-spin text-[#ff3d6e]" /> {stage === "ocr" ? `Membaca teks halaman ${page}…` : `Menerjemahkan halaman ${page}…`}
        </div>
      </div>
    );
  if (state === "error")
    return (
      <div className="sticky top-16 z-10 h-0 flex justify-center px-4">
        <button type="button" onClick={onRetry} data-testid={`page-${page}-retry-button`}
          className="flex items-center gap-2 rounded-full bg-[#ff3d6e] text-[#0d0b14] px-4 py-2 text-sm font-semibold active:scale-95 transition-transform">
          <RotateCcw className="h-4 w-4 shrink-0" /> <span className="text-left">{message || "Gagal."} Ketuk untuk coba lagi</span>
        </button>
      </div>
    );
  return null;
};

// Online: API urls. Offline-saved chapter: blob urls from Cache Storage. APK: blob urls from the phone's own store.
function useLocalSources(src, chapterUrl, version) {
  const [s, setS] = useState({ orig: "", clean: "" });
  useEffect(() => {
    if (!LOCAL) return undefined;
    let alive = true;
    let urls = [];
    Promise.all([localImageUrl(src, chapterUrl), version ? localImageUrl(src, chapterUrl, true) : ""])
      .then(([orig, clean]) => { urls = [orig, clean].filter(Boolean); if (alive) setS({ orig, clean }); })
      .catch(() => {});
    return () => { alive = false; urls.forEach((u) => URL.revokeObjectURL(u)); };
  }, [src, chapterUrl, version]);
  return s;
}

function useSources(src, chapterUrl, saved, engine) {
  const online = { orig: imgSrc(src, chapterUrl), clean: cleanSrc(src, engine) };
  const [blobs, setBlobs] = useState(null);
  useEffect(() => {
    if (!saved) return undefined;
    let urls = [];
    Promise.all([offlineBlobUrl(online.orig), offlineBlobUrl(online.clean)]).then(([o, c]) => {
      urls = [o, c].filter(Boolean);
      setBlobs({ orig: o || online.orig, clean: c || online.clean });
    });
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saved, src, engine]);
  return saved ? blobs || { orig: "", clean: "" } : online;
}

export const ComicPage = ({ src, chapterUrl, page, settings, onVisible, saved, forceToken }) => {
  const ref = useRef(null);
  const [near, setNear] = useState(false);
  const [state, setState] = useState(saved ? "done" : "idle");
  const [data, setData] = useState(saved || null);
  const [attempt, setAttempt] = useState(0);
  const [cleanReady, setCleanReady] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [tap, setTap] = useState(null);
  const [stage, setStage] = useState("");
  const [editing, setEditing] = useState(null);
  const [fixes, setFixes] = useState(0);
  useEffect(() => {
    const bump = () => setFixes((n) => n + 1);
    window.addEventListener("reiki-corrections", bump);
    return () => window.removeEventListener("reiki-corrections", bump);
  }, []);
  const saver = !!settings.saver;
  const saveEdit = async (text) => {
    try {
      const en = bubbles[editing]?.en;
      const d = await editBubble(src, engine, editing, text);
      setData((old) => ({ ...d, verified: old?.verified ?? d.verified }));
      // remembered: the same English line gets this sentence in every chapter from now on
      if (en) rememberCorrection(en, text);
      toast.success("Terjemahan diperbarui dan diingat untuk semua chapter");
      setEditing(null);
    } catch (e) {
      toast.error(e.message);
    }
  };
  const { mode, scale, font } = settings;
  const engine = saved?.engine || settings.engine || "free";
  const serverImgs = useSources(src, chapterUrl, !!saved && !LOCAL, engine);
  const localImgs = useLocalSources(src, chapterUrl, LOCAL ? (data?.updated_at || data?.created_at || "") : null);
  const imgs = LOCAL ? localImgs : serverImgs;
  const [pageW, setPageW] = useState(0);

  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setPageW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const el = ref.current;
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setNear(true),
      { rootMargin: saver ? "0px" : "0px 0px 1200px 0px" });
    const vis = new IntersectionObserver(([e]) => e.isIntersecting && onVisible(page), { rootMargin: "-45% 0px -45% 0px" });
    io.observe(el);
    vis.observe(el);
    return () => { io.disconnect(); vis.disconnect(); };
  }, [page, onVisible, saver]);

  useEffect(() => {
    if (!near || (saved && !forceToken && !attempt)) return undefined;
    let alive = true;
    setState("loading");
    setCleanReady(false);
    setStage("");
    translateImage(src, chapterUrl, attempt > 0 || forceToken > 0, engine, page, (st) => alive && setStage(st))
      .then((d) => { if (alive) { setData(d); setState("done"); } })
      .catch((e) => { if (alive) { setErrMsg(e.message); setState("error"); } });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [near, src, chapterUrl, attempt, forceToken, saved, engine]);

  // the server double-checks each page for leftover English; pick up its additions
  // free engine: the phone takes a second look at the cleaned page for leftover English
  useEffect(() => {
    if (saver || engine !== "free" || saved || state !== "done" || !data || data.verified) return undefined;
    let alive = true;
    enqueue(page + 40, () => translateLeftovers(src, chapterUrl, null, true))
      .then((d) => alive && setData(d))
      .catch(() => {});
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, saved, state, data?.verified, src, saver]);

  useEffect(() => {
    if (engine !== "ai" || saved || state !== "done" || !data || data.verified) return undefined;
    let n = 0;
    const t = setInterval(async () => {
      n += 1;
      try {
        const d = await getTranslation(src, engine);
        if (d.verified || n > 30) clearInterval(t);
        if (d.updated_at !== data.updated_at || d.verified) setData(d);
      } catch { if (n > 30) clearInterval(t); }
    }, 5000);
    return () => clearInterval(t);
  }, [state, data, src, saved, engine]);

  const onTap = async (e) => {
    if (mode !== "overlay" || state !== "done" || saved || tap) return;
    const r = e.currentTarget.getBoundingClientRect();
    const point = { x: ((e.clientX - r.left) / r.width) * 100, y: ((e.clientY - r.top) / r.height) * 100 };
    setTap(point);
    try {
      const py = (point.y / 100) * (data?.height || 0);
      const d = engine === "free"
        ? await translateLeftovers(src, chapterUrl, { y0: py - 650, y1: py + 650 }, false)
        : await translatePoint(src, chapterUrl, point.x, point.y, engine);
      if (d.added) { setData(d); toast.success(`${d.added} balon diterjemahkan`); }
      else toast("Tidak ada teks Inggris di bagian ini");
    } catch (err) {
      toast.error(err.message);
    }
    setTap(null);
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const bubbles = useMemo(() => applyCorrections(data?.bubbles), [data, fixes]);
  const overlay = mode === "overlay" && state === "done";
  // reserve the page's real shape before the picture loads, so bubbles are laid out right away
  const ratio = data?.width && data?.height ? { aspectRatio: `${data.width} / ${data.height}` } : undefined;
  return (
    <section ref={ref} id={`page-${page}`} data-testid={`comic-page-${page}`} className="relative">
      <div className="relative" style={ratio} onClick={onTap} data-testid={`page-${page}-tap-area`}>
        {imgs.orig && (
          <img src={imgs.orig} alt={`Halaman ${page}`} loading={page <= 2 ? "eager" : "lazy"}
            className={`block w-full h-auto select-none bg-[#17121f] ${ratio ? "" : "min-h-[60vh]"}`} draggable="false"
            onLoad={(e) => { e.currentTarget.style.minHeight = "0"; }} />
        )}
        {overlay && imgs.clean && (
          <img src={LOCAL ? imgs.clean : `${imgs.clean}${saved || !data?.created_at ? "" : `&t=${encodeURIComponent(data.updated_at || data.created_at)}`}`}
            alt="" aria-hidden="true" draggable="false" onLoad={() => setCleanReady(true)}
            className={`absolute inset-0 h-full w-full select-none transition-opacity duration-500 ${cleanReady ? "opacity-100" : "opacity-0"}`} />
        )}
        {overlay && cleanReady && bubbles.map((b, i) => <OverlayBubble key={i} b={b} n={`${page}-${i}`} scale={scale} font={font} pageW={pageW} onEdit={() => !saved && setEditing(i)} />)}
        {mode === "list" && bubbles.map((b, i) => <Marker key={i} b={b} n={i + 1} />)}
        {tap && <TapSpinner tap={tap} />}
        <StatusChip state={state} page={page} message={errMsg} stage={stage} onRetry={() => setAttempt((a) => a + 1)} />
      </div>
      {mode === "list" && state === "done" && (bubbles.length
        ? <ListCards bubbles={bubbles} page={page} scale={scale} onEdit={saved ? null : setEditing} />
        : <p className="mx-3 my-4 flex items-center gap-2 text-sm text-[#9e94b0]"><Languages className="h-4 w-4" /> Tidak ada teks di halaman {page}.</p>)}
      <BubbleEditor bubble={editing != null ? bubbles[editing] : null} onClose={() => setEditing(null)} onSave={saveEdit} />
    </section>
  );
};
