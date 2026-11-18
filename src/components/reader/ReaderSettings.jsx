import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Check, Trash2, RefreshCw, ListOrdered, Users, Loader2, FileDown } from "lucide-react";
import { toast } from "sonner";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Slider } from "@/components/ui/slider";
import { FONTS } from "@/lib/settings";
import { saveChapter, removeOffline, isSaved, onOfflineChange, offlineSupported } from "@/lib/offline";
import { downloadChapter } from "@/lib/exportChapter";
import { TermsEditor } from "@/components/reader/TermsEditor";
import { CorrectionsList } from "@/components/reader/CorrectionsList";
import { BackupPanel } from "@/components/reader/BackupPanel";

const Row = ({ label, children }) => (
  <div className="py-4 border-b border-white/10">
    <p className="lbl text-[#cfc6de] mb-3">{label}</p>
    {children}
  </div>
);

const Seg = ({ value, options, onChange, testid }) => (
  <div className="inline-flex rounded-full border border-white/20 p-1">
    {options.map(([k, l]) => (
      <button key={k} type="button" onClick={() => onChange(k)} data-testid={`${testid}-${k}`}
        className={`rounded-full px-4 py-1.5 text-sm transition-colors ${value === k ? "bg-[#ff3d6e] text-[#0d0b14] font-semibold" : "text-[#cfc6de]"}`}>{l}</button>
    ))}
  </div>
);

const OfflineButton = ({ ch, engine }) => {
  const [saved, setSaved] = useState(() => isSaved(ch.url));
  const [progress, setProgress] = useState(null);
  useEffect(() => onOfflineChange(() => setSaved(isSaved(ch.url))), [ch.url]);
  if (!offlineSupported()) return <p className="text-sm text-[#9e94b0]">Browser ini tidak mendukung simpan offline.</p>;
  const save = async () => {
    setProgress([0, ch.images.length]);
    try {
      await saveChapter(ch, (d, t) => setProgress([d, t]), engine);
      toast.success("Chapter tersimpan. Bisa dibaca tanpa internet.");
    } catch (e) {
      toast.error(e.message || "Gagal menyimpan offline");
    }
    setProgress(null);
  };
  if (progress)
    return (
      <div data-testid="offline-progress">
        <div className="flex items-center gap-2 text-sm"><Loader2 className="h-4 w-4 animate-spin text-[#ff3d6e]" /> Menyimpan halaman {progress[0]}/{progress[1]}…</div>
        <div className="mt-3 h-1.5 rounded-full bg-white/10 overflow-hidden"><div className="h-full bg-[#ff3d6e] transition-[width]" style={{ width: `${(progress[0] / progress[1]) * 100}%` }} /></div>
      </div>
    );
  return saved ? (
    <div className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2 text-sm text-[#9ff0c4]"><Check className="h-4 w-4" /> Tersimpan offline</span>
      <button type="button" onClick={() => removeOffline(ch.url)} data-testid="offline-remove-button"
        className="flex items-center gap-2 rounded-full border border-white/20 px-4 h-10 text-sm hover:border-[#ff3d6e] transition-colors"><Trash2 className="h-4 w-4" /> Hapus</button>
    </div>
  ) : (
    <button type="button" onClick={save} data-testid="offline-save-button"
      className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#ff3d6e] text-[#0d0b14] h-12 font-semibold active:scale-[0.98] transition-transform">
      <Download className="h-4 w-4" /> Simpan chapter ini offline
    </button>
  );
};

const TRANSLATORS = {
  v1: "Cepat: Google gratis per balon.",
  v2: "Lebih natural: satu halaman diterjemahkan sekaligus supaya nyambung, istilah manhwa dan tanda baca dijaga.",
  v3: "Paling akurat: membandingkan 3 penerjemah (2 Google + AI offline di HP) lalu memilih hasil terbaik per balon. Lebih lambat.",
  v4: "Seperti penerjemah manusia: Super Canggih lalu ditulis ulang gaya scanlator (kubilang, pakai, tak akan, kau), nama Korea dirapikan (Mo-Mun).",
};

const OfflineModel = () => {
  const [state, setState] = useState("cek");
  const [pct, setPct] = useState(0);
  useEffect(() => {
    let alive = true;
    import("@/lib/local/offlineMT").then((m) => m.offlineReady()).then((ok) => { if (alive) setState(ok ? "siap" : "belum"); });
    return () => { alive = false; };
  }, []);
  const install = async () => {
    setState("unduh");
    const m = await import("@/lib/local/offlineMT");
    const off = m.onOfflineProgress((p) => setPct(p));
    try {
      await m.prepareOfflineModel();
      setState("siap");
      toast.success("Penerjemah AI offline siap dipakai");
    } catch (e) {
      setState("belum");
      toast.error(`Gagal memasang: ${e.message}`);
    }
    off();
  };
  if (state === "siap") return <p data-testid="offline-model-ready" className="text-sm text-[#7ee2a8] flex items-center gap-2"><Check className="h-4 w-4" /> AI offline terpasang di HP ini</p>;
  if (state === "unduh") return <p data-testid="offline-model-progress" className="text-sm flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin text-[#ff3d6e]" /> Mengunduh AI offline… {pct}%</p>;
  return (
    <button type="button" onClick={install} disabled={state === "cek"} data-testid="offline-model-install"
      className="w-full rounded-xl border border-white/20 h-11 text-sm font-semibold hover:border-[#ff3d6e] transition-colors">
      Pasang AI offline (sekitar 105 MB, sekali saja)
    </button>
  );
};

const DownloadButton = ({ ch, settings }) => {
  const [progress, setProgress] = useState(null);
  const run = async () => {
    setProgress([0, ch.images.length]);
    try {
      const where = await downloadChapter(ch, settings, (d, t) => setProgress([d, t]));
      toast.success(`Chapter tersimpan di ${where}`);
    } catch (e) {
      toast.error(e.message || "Gagal mengunduh chapter");
    }
    setProgress(null);
  };
  if (progress)
    return (
      <div data-testid="download-progress" className="flex items-center gap-2 text-sm">
        <Loader2 className="h-4 w-4 animate-spin text-[#ff3d6e]" /> Menyiapkan halaman {progress[0]}/{progress[1]}…
      </div>
    );
  return (
    <button type="button" onClick={run} data-testid="download-chapter-button"
      className="w-full flex items-center justify-center gap-2 rounded-xl border border-[#ff3d6e] text-[#ff9ab3] h-12 font-semibold active:scale-[0.98] transition-transform">
      <FileDown className="h-4 w-4" /> Unduh chapter ke folder (JPG)
    </button>
  );
};

export const ReaderSettings = ({ open, onOpenChange, settings, update, ch, onRetranslate }) => {
  const seriesLink = ch ? `/series?url=${encodeURIComponent(ch.url)}` : "/";
  const [restored, setRestored] = useState(0);
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="bg-[#0d0b14] text-[#f3eefc] border-white/10 rounded-t-3xl max-h-[85dvh] overflow-y-auto safe-bottom" data-testid="reader-settings">
        <SheetHeader className="text-left">
          <SheetTitle className="disp text-3xl text-[#f3eefc]">Pengaturan baca</SheetTitle>
          <SheetDescription className="text-[#9e94b0]">Tersimpan otomatis di ponsel ini.</SheetDescription>
        </SheetHeader>
        <Row label={`Ukuran huruf · ${Math.round(settings.scale * 100)}%`}>
          <div className="balona-slider flex items-center gap-4">
            <span className="text-sm">A</span>
            <Slider data-testid="font-scale-slider" min={0.8} max={1.5} step={0.05} value={[settings.scale]}
              onValueChange={([v]) => update({ scale: v })} />
            <span className="text-xl font-bold">A</span>
          </div>
          <p className="mt-3 text-[#f3eefc]" data-testid="font-preview" style={{ fontFamily: (FONTS[settings.font] || FONTS.comic).family, fontWeight: (FONTS[settings.font] || FONTS.comic).weight,
            textTransform: (FONTS[settings.font] || FONTS.comic).upper ? "uppercase" : "none", fontSize: `${16 * settings.scale}px` }}>
            Contoh: Dengan kekuatan seperti itu, dia tak akan menang.
          </p>
        </Row>
        <Row label="Jenis huruf">
          <Seg value={settings.font} onChange={(v) => update({ font: v })} testid="font"
            options={Object.entries(FONTS).map(([k, f]) => [k, f.label])} />
        </Row>
        <Row label="Mode tampilan">
          <Seg value={settings.mode} onChange={(v) => update({ mode: v })} testid="settings-mode"
            options={[["overlay", "Overlay"], ["list", "Daftar"]]} />
        </Row>
        <Row label="Versi penerjemah (semua gratis)">
          <div className="grid grid-cols-2 gap-2" data-testid="settings-translator">
            {[["v1", "Normal"], ["v2", "Super"], ["v3", "Super Canggih"], ["v4", "Terbaik"]].map(([k, l]) => (
              <button key={k} type="button" onClick={() => update({ translator: k })} data-testid={`settings-translator-${k}`}
                className={`h-11 rounded-xl text-sm font-semibold transition-colors ${(settings.translator || "v2") === k ? "bg-[#ff3d6e] text-[#0d0b14]" : "border border-white/15 text-[#cfc6de]"}`}>{l}</button>
            ))}
          </div>
          <p data-testid="translator-desc" className="mt-2 text-xs text-[#b9b0c9]">{TRANSLATORS[settings.translator || "v2"]} Berlaku untuk halaman baru; ketuk “Terjemahkan ulang” untuk halaman lama.</p>
          <div className="mt-3"><OfflineModel /></div>
        </Row>
        <Row label="Kamus istilahku (semua serial)">
          <TermsEditor key={`terms-${restored}`} />
        </Row>
        <Row label="Koreksi teringat (semua chapter)">
          <CorrectionsList />
        </Row>
        <Row label="Cadangan koreksi, istilah & nama">
          <BackupPanel onRestored={() => setRestored((n) => n + 1)} />
        </Row>
        <Row label="Mode hemat baterai">
          <Seg value={settings.saver ? "on" : "off"} onChange={(v) => update({ saver: v === "on" })} testid="settings-saver"
            options={[["off", "Mati"], ["on", "Nyala"]]} />
          <p className="mt-2 text-xs text-[#b9b0c9]">Nyala: hanya halaman yang sedang kamu lihat yang diterjemahkan.</p>
        </Row>
        {ch && <Row label="Simpan offline"><OfflineButton ch={ch} engine={settings.engine} /></Row>}
        {ch && (
          <Row label="Unduh ke file manager">
            <DownloadButton ch={ch} settings={settings} />
            <p className="mt-2 text-xs text-[#b9b0c9]">Setiap halaman disimpan sebagai gambar berbahasa Indonesia.</p>
          </Row>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-4">
          <Link to={seriesLink} data-testid="settings-series-link" className="flex items-center gap-2 rounded-xl border border-white/15 px-4 h-12 hover:border-[#ff3d6e] transition-colors"><ListOrdered className="h-4 w-4 text-[#ff9ab3]" /> Semua chapter</Link>
          <Link to={`${seriesLink}#nama`} data-testid="settings-glossary-link" className="flex items-center gap-2 rounded-xl border border-white/15 px-4 h-12 hover:border-[#ff3d6e] transition-colors"><Users className="h-4 w-4 text-[#ff9ab3]" /> Nama karakter</Link>
          <button type="button" onClick={onRetranslate} data-testid="settings-retranslate-button" className="flex items-center gap-2 rounded-xl border border-white/15 px-4 h-12 hover:border-[#ff3d6e] transition-colors"><RefreshCw className="h-4 w-4 text-[#ff9ab3]" /> Terjemahkan ulang</button>
        </div>
      </SheetContent>
    </Sheet>
  );
};
