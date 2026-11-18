@echo off
chcp 65001 >nul
title Penerjemah Reiki - link https sementara
where cloudflared >nul 2>nul
if errorlevel 1 (
  echo Memasang cloudflared dari Microsoft winget...
  winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
  echo Selesai. Tutup jendela ini lalu jalankan file ini sekali lagi.
  pause
  exit /b
)
echo.
echo  Cari baris berisi  https://....trycloudflare.com  di bawah ini.
echo  Buka link itu di Chrome HP kamu. Link berganti tiap kali file ini dijalankan ulang.
echo  Mau link tetap (domain sendiri)? Lihat PANDUAN.txt LANGKAH 6.
echo.
cloudflared tunnel --url http://localhost:8001
pause
