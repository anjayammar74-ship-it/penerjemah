#!/data/data/com.termux/files/usr/bin/bash
# Link https sementara untuk Penerjemah Reiki yang jalan di HP ini. Jalankan di sesi Termux kedua.
echo "Cari baris https://....trycloudflare.com lalu buka di Chrome."
cloudflared tunnel --url http://localhost:8001
