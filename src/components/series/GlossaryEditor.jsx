import { useEffect, useState } from "react";
import { Plus, Trash2, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { getGlossary, saveGlossary } from "@/lib/api";

export const GlossaryEditor = ({ seriesKey }) => {
  const [terms, setTerms] = useState(null);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    getGlossary(seriesKey).then(setTerms).catch(() => setTerms([]));
  }, [seriesKey]);

  const edit = (i, patch) => { setTerms((t) => t.map((x, j) => (j === i ? { ...x, ...patch } : x))); setDirty(true); };
  const add = () => { setTerms((t) => [{ en: "", id: "" }, ...t]); setDirty(true); };
  const del = (i) => { setTerms((t) => t.filter((_, j) => j !== i)); setDirty(true); };
  const save = async () => {
    setBusy(true);
    try {
      setTerms(await saveGlossary(seriesKey, terms.filter((t) => t.en.trim())));
      setDirty(false);
      toast.success("Daftar nama disimpan. Berlaku untuk halaman yang diterjemahkan berikutnya.");
    } catch {
      toast.error("Gagal menyimpan daftar nama");
    }
    setBusy(false);
  };

  if (!terms) return <div className="py-8 grid place-items-center"><Loader2 className="h-6 w-6 animate-spin text-[#ff3d6e]" /></div>;

  return (
    <div data-testid="glossary-editor">
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={add} data-testid="glossary-add-button"
          className="flex items-center gap-2 rounded-full border border-white/20 px-4 h-11 text-sm hover:border-[#ff3d6e] transition-colors"><Plus className="h-4 w-4" /> Tambah nama</button>
        <button type="button" onClick={save} disabled={!dirty || busy} data-testid="glossary-save-button"
          className="flex items-center gap-2 rounded-full bg-[#ff3d6e] text-[#0d0b14] px-5 h-11 text-sm font-semibold disabled:opacity-40 active:scale-95 transition-transform">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Simpan
        </button>
      </div>
      {!terms.length && <p className="mt-6 text-[#9e94b0]">Belum ada nama. Nama tokoh akan tercatat otomatis saat chapter diterjemahkan, atau tambahkan sendiri.</p>}
      <ul className="mt-6 space-y-2">
        {terms.map((t, i) => (
          <li key={i} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-center" data-testid={`glossary-row-${i}`}>
            <input value={t.en} onChange={(e) => edit(i, { en: e.target.value })} placeholder="Nama di teks Inggris"
              aria-label="Nama Inggris" data-testid={`glossary-en-${i}`}
              className="min-w-0 rounded-xl bg-white/5 border border-white/15 px-3 h-11 focus:outline-none focus:border-[#ff3d6e]" />
            <input value={t.id} onChange={(e) => edit(i, { id: e.target.value })} placeholder="Tulis sebagai"
              aria-label="Ejaan terkunci" data-testid={`glossary-id-${i}`}
              className="min-w-0 rounded-xl bg-white/5 border border-white/15 px-3 h-11 focus:outline-none focus:border-[#ff3d6e]" />
            <button type="button" onClick={() => del(i)} aria-label="Hapus nama" data-testid={`glossary-delete-${i}`}
              className="h-11 w-11 grid place-items-center rounded-full text-[#9e94b0] hover:text-[#ff3d6e] transition-colors"><Trash2 className="h-4 w-4" /></button>
          </li>
        ))}
      </ul>
    </div>
  );
};
