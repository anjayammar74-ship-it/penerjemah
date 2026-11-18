import { useRef, useState } from "react";
import { Download, Upload, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { downloadBackup, restoreBackup } from "@/lib/backup";

// Save / restore everything you taught the app (corrections, terms, character names) in one file.
export const BackupPanel = ({ onRestored }) => {
  const pick = useRef(null);
  const [busy, setBusy] = useState("");
  const save = async () => {
    setBusy("save");
    try { toast.success(`Cadangan tersimpan: ${await downloadBackup()}`); } catch (e) { toast.error(e.message); }
    setBusy("");
  };
  const restore = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy("restore");
    try {
      const r = await restoreBackup(file);
      toast.success(`Dipulihkan: ${r.corrections} koreksi, ${r.terms} istilah, nama karakter ${r.series} serial.`);
      onRestored?.();
    } catch (err) { toast.error(err.message); }
    setBusy("");
  };
  const btn = "flex-1 h-11 rounded-lg text-sm flex items-center justify-center gap-2 active:scale-[0.98] transition-transform disabled:opacity-60";
  return (
    <div data-testid="backup-panel" className="space-y-2">
      <p className="text-xs text-[#cfc6de]">Satu file berisi koreksi teringat, kamus istilah dan daftar nama karakter semua serial. Pulihkan di HP baru, tidak ada yang hilang.</p>
      <div className="flex gap-2">
        <button type="button" onClick={save} disabled={!!busy} data-testid="backup-save" className={`${btn} bg-[#ff3d6e] text-[#0d0b14] font-semibold`}>
          {busy === "save" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} Simpan cadangan
        </button>
        <button type="button" onClick={() => pick.current?.click()} disabled={!!busy} data-testid="backup-restore" className={`${btn} border border-white/20 hover:border-[#ff3d6e]`}>
          {busy === "restore" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />} Pulihkan
        </button>
      </div>
      <input ref={pick} type="file" accept=".json,application/json" className="hidden" onChange={restore} data-testid="backup-file-input" />
    </div>
  );
};
