import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { loadTerms, saveTerms } from "@/lib/terms";

const input = "h-10 min-w-0 rounded-lg bg-[#1a1524] border border-white/15 px-2 text-sm text-[#f3eefc] placeholder:text-[#8f86a3] focus:border-[#ff3d6e] outline-none";

// Your own dictionary for every series: Hyung -> Kak, or skill names that must stay as names.
export const TermsEditor = () => {
  const [rows, setRows] = useState(loadTerms);
  const set = (i, patch) => setRows((r) => r.map((x, k) => (k === i ? { ...x, ...patch } : x)));
  const save = () => { setRows(saveTerms(rows)); toast.success("Kamus istilah tersimpan. Berlaku untuk halaman yang diterjemahkan berikutnya."); };
  return (
    <div data-testid="terms-editor" className="space-y-2">
      {rows.map((t, i) => (
        <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-center">
          <input className={input} value={t.en} placeholder="Inggris (Hyung)" data-testid={`term-en-${i}`}
            onChange={(e) => set(i, { en: e.target.value })} />
          <input className={input} value={t.id} placeholder={t.kind === "skill" ? "Nama tampil" : "Indonesia (Kak)"} data-testid={`term-id-${i}`}
            onChange={(e) => set(i, { id: e.target.value })} />
          <button type="button" aria-label="Hapus" data-testid={`term-remove-${i}`} onClick={() => setRows((r) => r.filter((_, k) => k !== i))}
            className="h-10 w-10 grid place-items-center rounded-lg border border-white/15 text-[#cfc6de] hover:border-[#ff3d6e]"><Trash2 className="h-4 w-4" /></button>
          <label className="col-span-3 -mt-1 flex items-center gap-2 text-xs text-[#cfc6de]">
            <input type="checkbox" checked={t.kind === "skill"} data-testid={`term-skill-${i}`}
              onChange={(e) => set(i, { kind: e.target.checked ? "skill" : "term" })} className="accent-[#ff3d6e]" />
            Nama teknik/skill: jangan diterjemahkan, tampil sebagai [Nama]
          </label>
        </div>
      ))}
      <div className="flex gap-2">
        <button type="button" data-testid="term-add" onClick={() => setRows((r) => [...r, { en: "", id: "", kind: "term" }])}
          className="flex-1 h-10 rounded-lg border border-white/20 text-sm flex items-center justify-center gap-1 hover:border-[#ff3d6e]"><Plus className="h-4 w-4" /> Tambah</button>
        <button type="button" data-testid="term-save" onClick={save}
          className="flex-1 h-10 rounded-lg bg-[#ff3d6e] text-[#0d0b14] text-sm font-semibold active:scale-[0.98] transition-transform">Simpan</button>
      </div>
    </div>
  );
};
