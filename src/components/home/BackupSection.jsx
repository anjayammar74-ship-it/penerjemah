import { BackupPanel } from "@/components/reader/BackupPanel";

// Home: move everything you taught the app to a new phone
export const BackupSection = () => (
  <section id="cadangan" className="bg-[#0d0b14] text-[#f3eefc] py-16 md:py-24 border-t border-white/10" data-testid="home-backup">
    <div className="max-w-3xl mx-auto px-6">
      <h2 className="disp text-3xl md:text-5xl">Cadangan koreksi, istilah & nama</h2>
      <p className="mt-4 mb-6 text-base leading-[1.6] text-[#cfc6de]">Ganti HP? Simpan cadangan di HP lama, kirim filenya, lalu tekan Pulihkan di HP baru.</p>
      <BackupPanel />
    </div>
  </section>
);
