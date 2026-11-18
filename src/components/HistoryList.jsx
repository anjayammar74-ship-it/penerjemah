import { Link } from "react-router-dom";
import { Trash2, ListOrdered, Download } from "lucide-react";
import { useEffect, useState } from "react";
import { offlineIndex, onOfflineChange } from "@/lib/offline";
import { useHistory, splitTitle } from "@/lib/history";
import { useOpenChapter } from "@/components/UrlForm";

const EXAMPLE = "https://en-thunderscans.com/the-general-fighting-legend-chapter-23/";

const readUrl = (h) => `/read?url=${encodeURIComponent(h.url)}${h.lastPage ? `&page=${h.lastPage}` : ""}`;

export const HistoryList = () => {
  const { items, remove } = useHistory();
  const open = useOpenChapter();
  const [offline, setOffline] = useState(offlineIndex);
  useEffect(() => onOfflineChange(() => setOffline(offlineIndex())), []);
  const saved = new Set(offline.map((o) => o.url));

  if (!items.length) {
    return (
      <div className="mt-8 rounded-2xl border border-dashed border-white/15 p-6" data-testid="history-empty">
        <p className="text-[#cfc6de]">Belum ada chapter yang dibaca. Coba dengan contoh link:</p>
        <button type="button" onClick={() => open(EXAMPLE)} data-testid="history-example-button"
          className="mt-4 w-full text-left py-3 flex justify-between gap-4 border-t border-white/10 hover:text-[#ff9ab3] transition-colors">
          <span>The General Fighting Legend</span><span className="tn text-[#ff9ab3]">Ch. 23 →</span>
        </button>
      </div>
    );
  }

  return (
    <ul className="mt-8 divide-y divide-white/10" data-testid="history-list">
      {items.slice(0, 12).map((h, i) => {
        const { series, chapter } = splitTitle(h.title);
        return (
          <li key={h.url} className="py-4 flex items-center gap-3" data-testid={`history-item-${i}`}>
            <Link to={readUrl(h)} className="min-w-0 flex-1 group" data-testid={`history-open-${i}`}>
              <span className="flex items-center gap-1.5 truncate group-hover:text-[#ff9ab3] transition-colors">
                {saved.has(h.url) && <Download className="h-3.5 w-3.5 shrink-0 text-[#9ff0c4]" aria-label="Tersimpan offline" />}
                <span className="truncate">{series}</span>
              </span>
              <span className="lbl text-[#9e94b0]">
                {h.lastPage ? `Lanjut hlm ${h.lastPage}/${h.total || "?"}` : "Belum dibuka"}
              </span>
            </Link>
            {chapter && <span className="tn text-[#ff9ab3] shrink-0">Ch. {chapter}</span>}
            <Link to={`/series?url=${encodeURIComponent(h.url)}`} aria-label="Semua chapter" data-testid={`history-series-${i}`}
              className="h-11 w-11 grid place-items-center rounded-full text-[#9e94b0] hover:text-[#ff9ab3] hover:bg-white/5 transition-colors">
              <ListOrdered className="h-4 w-4" />
            </Link>
            <button type="button" onClick={() => remove(h.url)} aria-label="Hapus dari riwayat"
              data-testid={`history-remove-${i}`}
              className="h-11 w-11 grid place-items-center rounded-full text-[#9e94b0] hover:text-[#ff3d6e] hover:bg-white/5 transition-colors">
              <Trash2 className="h-4 w-4" />
            </button>
          </li>
        );
      })}
    </ul>
  );
};

export const ContinueChip = () => {
  const { items } = useHistory();
  const h = items[0];
  if (!h) return null;
  const { series, chapter } = splitTitle(h.title);
  return (
    <Link to={readUrl(h)} data-testid="hero-continue-link"
      className="mt-5 inline-flex max-w-full items-center gap-3 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-[#ff3d6e] transition-colors fu f3">
      <span className="lbl text-[#ff9ab3] shrink-0">Lanjutkan</span>
      <span className="truncate">{series}{chapter ? ` · Ch. ${chapter}` : ""}</span>
      <span className="text-[#ff9ab3]">→</span>
    </Link>
  );
};
