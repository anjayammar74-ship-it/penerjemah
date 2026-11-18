@echo off
chcp 65001 >nul
title Penerjemah Reiki - penerjemah sendiri (LibreTranslate)
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo [!] Butuh Python 3.11 ^(lihat PANDUAN.txt LANGKAH 7^).
  pause
  exit /b 1
)
if not exist "lt-venv\siap.txt" (
  echo Memasang penerjemah sendiri, butuh 10-20 menit dan sekitar 2 GB ruang...
  py -3.11 -m venv lt-venv
  call lt-venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install libretranslate || (echo [!] Gagal memasang. & pause & exit /b 1)
  echo ok> lt-venv\siap.txt
) else (
  call lt-venv\Scripts\activate.bat
)
echo Penerjemah sendiri jalan di http://localhost:5000 (pertama kali mengunduh bahasa, tunggu sebentar)
libretranslate --host 127.0.0.1 --port 5000 --load-only en,id
pause
