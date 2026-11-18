import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { loadCorrections, removeCorrection } from "@/lib/corrections";

// Sentences you fixed by hand; each one is reused whenever the same English line appears again.
export const CorrectionsList = () => {
  const [rows, setRows] = useState(loadCorrections);
  const [q, setQ] = useState("");
  useEffect(() => {
    const sync = () => setRows([...loadCorrections()]);
    window.addEventListener("reiki-corrections", sync);
    return () => window.removeEventListener("reiki-corrections", sync);
  }, []);
  const shown = rows.filter((c) => !q || `${c.en} ${c.id}`.toLowerCase().includes(q.toLowerCase())).slice(0, 50);
  if (!rows.length) {
    return (
      <p data-testid="corrections-empty" className="text-xs text-[#cfc6de]">
        Belum ada. Tekan lama sebuah balon, perbaiki kalimatnya, lalu simpan: kalimat itu dipakai lagi di semua chapter.
      </p>
    );
  }
  return (
    <div data-testid="corrections-list" className="space-y-2">
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Cari di ${rows.length} koreksi`} data-testid="corrections-search"
        className="h-10 w-full rounded-lg bg-[#1a1524] border border-white/15 px-2 text-sm text-[#f3eefc] placeholder:text-[#8f86a3] focus:border-[#ff3d6e] outline-none" />
      <ul className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {shown.map((c, i) => (
          <li key={c.en} data-testid={`correction-${i}`} className="flex gap-2 items-start rounded-lg border border-white/10 p-2">
            <div className="min-w-0 flex-1">
              <p className="text-xs text-[#a99fbd] break-words">{c.en}</p>
              <p className="text-sm text-[#f3eefc] break-words">{c.id}</p>
            </div>
            <button type="button" aria-label="Hapus koreksi" data-testid={`correction-remove-${i}`} onClick={() => setRows([...removeCorrection(c.en)])}
              className="h-9 w-9 shrink-0 grid place-items-center rounded-lg border border-white/15 text-[#cfc6de] hover:border-[#ff3d6e]"><Trash2 className="h-4 w-4" /></button>
          </li>
        ))}
      </ul>
    </div>
  );
};
