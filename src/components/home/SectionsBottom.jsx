import { UrlForm } from "@/components/UrlForm";
import { HistoryList } from "@/components/HistoryList";
import { IMG_HISTORY } from "@/components/home/SectionsTop";
import { LOCAL } from "@/lib/api";

const H2 = { fontSize: "clamp(36px,5vw,80px)" };

export const Clarity = () => (
  <section id="teks-rapih" className="relative overflow-hidden bg-[#f3eefc] text-[#0d0b14] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6">
      <p className="disp text-[#0d0b14]/10 leading-none select-none" style={{ fontSize: "clamp(120px,20vw,320px)" }} aria-hidden="true">Rapih.</p>
      <div className="-mt-12 md:-mt-24 grid md:grid-cols-3 gap-8 relative z-10">
        {[["Huruf ala komik", "Tebal, mudah dibaca di layar kecil."],
          ["Ukuran menyesuaikan", "Kalimat panjang mengecil, tidak tumpah keluar balon."],
          ["Latar bersih", "Teks asli dihapus halus sebelum diganti."]].map(([t, d]) => (
          <div key={t}><h3 className="disp text-2xl">{t}</h3><p className="mt-2 leading-[1.6] text-[#3b3346]">{d}</p></div>
        ))}
      </div>
    </div>
  </section>
);

export const PerPage = () => (
  <section id="per-halaman" className="bg-[#17121f] text-[#f3eefc] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-[2fr_3fr] gap-12 items-center">
      <div className="min-w-0">
        <h2 className="disp" style={H2}>Satu halaman, satu terjemahan</h2>
        <p className="mt-6 text-lg leading-[1.6] text-[#cfc6de] max-w-md">Tidak perlu menunggu seluruh chapter. Halaman yang sedang kamu lihat selalu diproses lebih dulu.</p>
      </div>
      <svg viewBox="0 0 600 260" className="w-full" aria-hidden="true">
        <g fill="none" stroke="#f3eefc" strokeOpacity=".25" strokeWidth="2">
          <rect x="10" y="20" width="120" height="220" rx="10" /><rect x="160" y="20" width="120" height="220" rx="10" /><rect x="310" y="20" width="120" height="220" rx="10" /><rect x="460" y="20" width="120" height="220" rx="10" />
        </g>
        <rect x="10" y="20" width="120" height="220" rx="10" fill="#ff3d6e" /><rect x="160" y="20" width="120" height="220" rx="10" fill="#ff3d6e" opacity=".5" />
        <path d="M20 250H580" stroke="#ff3d6e" strokeWidth="3" pathLength="1" className="draw" />
      </svg>
    </div>
  </section>
);

export const History = () => (
  <section id="riwayat" className="bg-[#0d0b14] text-[#f3eefc] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-2 gap-12 items-center">
      <figure className="relative aspect-[4/3] overflow-hidden rounded-3xl order-last md:order-first">
        <img src={IMG_HISTORY} alt="Daftar bacaan di ponsel" loading="lazy" className="absolute inset-0 h-full w-full object-cover" />
      </figure>
      <div className="min-w-0">
        <h2 className="disp" style={H2}>Riwayat bacaan</h2>
        <p className="mt-6 text-lg leading-[1.6] text-[#cfc6de] max-w-md">Setiap chapter yang kamu buka tersimpan di ponsel, lengkap dengan halaman terakhir yang dibaca.</p>
        <HistoryList />
      </div>
    </div>
  </section>
);

export const NextChapter = () => (
  <section id="chapter-berikutnya" className="bg-[#ff3d6e] text-[#0d0b14] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-2 gap-12 items-center">
      <h2 className="disp min-w-0" style={H2}>Habis? Langsung chapter berikutnya.</h2>
      <div className="min-w-0">
        <p className="text-lg leading-[1.6] max-w-md">Tombol di ujung halaman membuka chapter selanjutnya dan langsung menerjemahkannya.</p>
        <div className="mt-8 flex gap-3" aria-hidden="true">
          <span className="rounded-full border-2 border-[#0d0b14] px-6 py-3 font-semibold">← Sebelumnya</span>
          <span className="rounded-full bg-[#0d0b14] text-[#f3eefc] px-6 py-3 font-semibold">Chapter berikutnya →</span>
        </div>
      </div>
    </div>
  </section>
);

const Odo = ({ d, label }) => (
  <div>
    <p className="disp tn text-[#ff3d6e]" style={{ fontSize: "clamp(64px,9vw,140px)" }}>
      <span className="odo"><span className="reel" style={{ "--d": d }}>{[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => <span key={n} className="block">{n}</span>)}</span></span>
    </p>
    <p className="mt-2 lbl text-[#cfc6de]">{label}</p>
  </div>
);

export const Numbers = () => (
  <section id="angka" className="bg-[#17121f] text-[#f3eefc] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-3 gap-12">
      <Odo d={1} label="link untuk mulai" /><Odo d={2} label="mode tampilan" /><Odo d={0} label="akun yang perlu dibuat" />
    </div>
  </section>
);

export const Install = () => (
  <section id="pasang" className="bg-[#0d0b14] text-[#f3eefc] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-[3fr_2fr] gap-12 items-center">
      <div className="min-w-0">
        <h2 className="disp" style={H2}>Pasang di HP Android</h2>
        <p className="mt-6 text-lg leading-[1.6] text-[#cfc6de] max-w-md">Unduh file APK Penerjemah Reiki lalu pasang seperti aplikasi biasa. Semua proses berjalan di HP kamu: tanpa server, tanpa kredit, tanpa biaya. Bisa juga lewat Chrome: ketuk “Tambahkan ke layar utama”.</p>
        {!LOCAL && (
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="/download/penerjemah-reiki.apk" data-testid="install-apk-link"
              className="inline-flex items-center gap-2 rounded-full bg-[#ff3d6e] text-[#0d0b14] px-6 h-12 font-semibold hover:bg-[#ff9ab3] transition-colors">Unduh APK Android</a>
            <a href="/download/penerjemah-reiki-kode.zip" data-testid="download-code-link"
              className="inline-flex items-center gap-2 rounded-full border border-white/25 px-6 h-12 font-semibold hover:border-[#ff3d6e] transition-colors">Unduh kode mentah (ZIP)</a>
          </div>
        )}
      </div>
      <img src="/icons/icon-512.png" alt="Logo Penerjemah Reiki" className="w-full max-w-xs mx-auto rounded-[22%] shadow-2xl" />
    </div>
  </section>
);

const FAQ = [
  ["Situs apa saja yang bisa dibuka?", "Halaman chapter yang menampilkan gambar komik berurutan, seperti contoh link yang kamu tempel."],
  ["Apakah gambar asli berubah?", "Tidak. Terjemahan hanya tampil di ponselmu, dan mode daftar menyisakan gambar asli."],
  ["Kalau terjemahan kurang pas?", "Ketuk balon untuk melihat teks Inggrisnya, atau pindah ke mode daftar untuk membandingkan setiap balon."],
];
export const Faq = () => (
  <section id="faq" className="bg-[#17121f] text-[#f3eefc] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-[1fr_2fr] gap-12">
      <h2 className="disp" style={H2}>Tanya jawab</h2>
      <div className="divide-y divide-white/10">
        {FAQ.map(([q, a], i) => (
          <details key={q} className="py-6" open={i === 0} data-testid={`faq-item-${i}`}>
            <summary className="disp text-2xl cursor-pointer">{q}</summary>
            <p className="mt-3 leading-[1.6] text-[#cfc6de] max-w-xl">{a}</p>
          </details>
        ))}
      </div>
    </div>
  </section>
);

export const FinalCta = () => (
  <section id="mulai" className="relative overflow-hidden bg-[#3a1450] text-[#f3eefc] py-24 md:py-36">
    <div className="d1-drift absolute inset-0 opacity-20" aria-hidden="true" />
    <div className="relative z-10 max-w-7xl mx-auto px-6 text-center">
      <h2 className="disp mx-auto max-w-4xl" style={H2}>Chapter berikutnya menunggu.</h2>
      <UrlForm id="cta-url" variant="cta" />
    </div>
  </section>
);

export const Footer = () => (
  <footer className="bg-[#0d0b14] text-[#cfc6de] border-t border-white/10 safe-bottom">
    <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col md:flex-row justify-between gap-6 text-sm">
      <span className="disp text-xl text-[#f3eefc]">Penerjemah Reiki</span>
      <span>Pembaca manhwa berbahasa Indonesia, untuk dipakai sendiri.</span>
      <a href="#top" data-testid="footer-top-link">Kembali ke atas ↑</a>
    </div>
  </footer>
);
