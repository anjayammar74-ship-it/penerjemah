import { UrlForm } from "@/components/UrlForm";
import { ContinueChip } from "@/components/HistoryList";

const IMG_HOME = "/img/home.jpg";
const IMG_OVERLAY = "/img/overlay.jpg";
export const IMG_HISTORY = "/img/history.jpg";

export const BubbleLogo = ({ className = "h-8 w-8" }) => (
  <img src="/icons/logo.png" alt="" aria-hidden="true" className={`${className} rounded-lg`} />
);

const NAV = [["#cara-kerja", "Cara kerja"], ["#mode-tampilan", "Mode"], ["#riwayat", "Riwayat"], ["#faq", "FAQ"]];

export const SiteNav = () => (
  <nav className="sticky top-0 z-50 bg-[#0d0b14]/90 text-[#f3eefc] backdrop-blur border-b border-white/10 safe-top">
    <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <a href="#top" className="flex items-center gap-3" data-testid="nav-logo"><BubbleLogo /><span className="disp text-2xl">Penerjemah Reiki</span></a>
      <div className="hidden md:flex gap-8 text-sm">
        {NAV.map(([h, l]) => <a key={h} href={h} className="ulink" data-testid={`nav-${h.slice(1)}`}>{l}</a>)}
      </div>
      <a href="#tempel" className="rounded-full bg-[#ff3d6e] text-[#0d0b14] px-5 py-2 text-sm font-semibold active:scale-95 transition-transform" data-testid="nav-start-button">Mulai baca</a>
    </div>
  </nav>
);

export const Hero = () => (
  <header id="top" className="relative isolate min-h-[92svh] overflow-hidden flex items-end bg-[#0d0b14] text-[#f3eefc]">
    <div className="gr absolute inset-0 bg-[radial-gradient(ellipse_at_70%_30%,#3a1450,#0d0b14_70%)]">
      <div className="d1-drift absolute inset-0 opacity-25" />
      <svg viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full" aria-hidden="true">
        <g stroke="#ff3d6e" strokeOpacity=".35" strokeWidth="2"><path d="M1040 280L1440 0M1040 280L1440 160M1040 280L1440 330M1040 280L1440 520M1040 280L1300 900M1040 280L700 0M1040 280L880 0" /></g>
        <path d="M860 140h420v240H1020l-70 70v-70h-90z" fill="none" stroke="#f3eefc" strokeOpacity=".5" strokeWidth="3" pathLength="1" className="draw" />
      </svg>
    </div>
    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
    <div className="relative z-10 w-full max-w-7xl mx-auto px-6 pb-24 pt-32 min-w-0">
      <p className="lbl text-[#ff9ab3] fu f1">Pembaca manhwa pribadi untuk Android</p>
      <h1 className="disp mt-6 break-words" style={{ fontSize: "clamp(56px,8vw,148px)", textWrap: "balance" }} data-testid="hero-title">
        <span className="ln"><span>Baca manhwa</span></span>
        <span className="ln"><span>dalam Bahasa</span></span>
        <span className="ln"><span className="text-[#ff3d6e]">Indonesia.</span></span>
      </h1>
      <p className="mt-8 max-w-xl text-lg leading-[1.6] fu f1">Tempel link chapter, lalu teks Indonesia muncul jelas dan rapih langsung di atas balon kata.</p>
      <UrlForm id="hero-url" variant="hero" />
      <ContinueChip />
    </div>
  </header>
);

const MQ = "Tempel link ✦ Terjemah per halaman ✦ Overlay di balon ✦ Daftar terjemahan ✦ Riwayat bacaan ✦ Chapter berikutnya ✦";
export const Marquee = () => (
  <section className="bg-[#ff3d6e] text-[#0d0b14] overflow-hidden py-6" aria-label="Fitur">
    <div className="mq disp text-4xl md:text-6xl whitespace-nowrap"><span className="px-8">{MQ}</span><span className="px-8" aria-hidden="true">{MQ}</span></div>
  </section>
);

export const PasteSection = () => (
  <section id="tempel" className="bg-[#0d0b14] text-[#f3eefc] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-2 gap-12 items-center">
      <div className="min-w-0">
        <p className="lbl text-[#ff9ab3]">Layar utama</p>
        <h2 className="disp mt-4" style={{ fontSize: "clamp(36px,5vw,80px)" }}>Satu kotak. Satu link.</h2>
        <p className="mt-6 text-lg leading-[1.6] max-w-md text-[#cfc6de]">Salin link chapter dari browser, tempel di sini, dan pembaca langsung terbuka. Tanpa akun, tanpa menu berlapis.</p>
        <UrlForm id="paste-url" variant="stack" />
      </div>
      <figure className="relative aspect-[4/5] overflow-hidden rounded-3xl">
        <img src={IMG_HOME} alt="Ponsel di tangan" className="absolute inset-0 h-full w-full object-cover" loading="lazy" />
      </figure>
    </div>
  </section>
);

const STEPS = [
  ["Tempel link", "Link chapter dari situs scanlation favoritmu, dibuka lewat link aplikasi.", "f2"],
  ["Gulir halaman", "Setiap gambar diterjemahkan satu per satu tepat saat kamu menggulirnya.", "f3"],
  ["Baca dengan tenang", "Teks Indonesia menempel di balon kata, ukurannya pas, hurufnya bersih.", "f4"],
];
export const HowItWorks = () => (
  <section id="cara-kerja" className="bg-[#17121f] text-[#f3eefc] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6">
      <h2 className="disp" style={{ fontSize: "clamp(36px,5vw,80px)" }}>Cara kerjanya</h2>
      <ol className="mt-12 divide-y divide-white/10">
        {STEPS.map(([t, d, f]) => (
          <li key={t} className={`grid md:grid-cols-[1fr_2fr] gap-6 py-10 items-baseline fu ${f}`}>
            <div><h3 className="disp text-3xl">{t}</h3><p className="mt-3 text-lg leading-[1.6] text-[#cfc6de] max-w-lg">{d}</p></div>
          </li>
        ))}
      </ol>
    </div>
  </section>
);

export const Modes = () => (
  <section id="mode-tampilan" className="bg-[#0d0b14] text-[#f3eefc] py-24 md:py-36">
    <div className="max-w-7xl mx-auto px-6">
      <p className="lbl text-[#ff9ab3]">Dua cara membaca</p>
      <h2 className="disp mt-4 max-w-3xl" style={{ fontSize: "clamp(36px,5vw,80px)" }}>Ganti mode kapan saja</h2>
      <div className="mt-16 grid md:grid-cols-2 gap-12 items-center">
        <figure className="group relative aspect-[3/4] overflow-hidden rounded-3xl">
          <img src={IMG_OVERLAY} alt="Panel komik" loading="lazy" className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" />
        </figure>
        <div className="min-w-0 space-y-10">
          <div><h3 className="disp text-4xl">Overlay di balon</h3><p className="mt-3 text-lg leading-[1.6] text-[#cfc6de] max-w-md">Teks Inggris ditutup rapi, diganti kalimat Indonesia yang mengikuti bentuk balonnya.</p></div>
          <div><h3 className="disp text-4xl">Daftar di bawah gambar</h3><p className="mt-3 text-lg leading-[1.6] text-[#cfc6de] max-w-md">Gambar asli tetap utuh, terjemahan tersusun berurutan di bawahnya per balon.</p></div>
          <div className="inline-flex rounded-full border border-white/20 p-1" aria-hidden="true">
            <span className="rounded-full bg-[#ff3d6e] text-[#0d0b14] px-5 py-2 text-sm font-semibold">Overlay</span><span className="px-5 py-2 text-sm">Daftar</span>
          </div>
        </div>
      </div>
    </div>
  </section>
);
