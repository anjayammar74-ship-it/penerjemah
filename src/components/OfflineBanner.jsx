import { useEffect, useState } from "react";

export function OfflineBanner() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  if (online) return null;
  return (
    <div className="fixed left-1/2 -translate-x-1/2 bottom-24 z-[60] rounded-full bg-[#ff9ab3] px-4 py-2 text-center text-sm text-[#0d0b14] shadow-lg w-max max-w-[92vw]" data-testid="offline-banner">
      Offline · chapter yang disimpan tetap bisa dibaca
    </div>
  );
}
