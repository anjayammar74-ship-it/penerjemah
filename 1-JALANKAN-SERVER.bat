@echo off
chcp 65001 >nul
title Penerjemah Reiki - server
cd /d "%~dp0app"

where python >nul 2>nul
if errorlevel 1 (
  echo [!] Python belum terpasang. Buka PANDUAN.txt, ikuti LANGKAH 2.
  pause
  exit /b 1
)

if not exist ".venv\siap.txt" (
  echo Menyiapkan Penerjemah Reiki untuk pertama kali, tunggu 2-5 menit...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt || (echo [!] Gagal memasang. Cek internet lalu jalankan lagi. & pause & exit /b 1)
  echo ok> .venv\siap.txt
) else (
  call .venv\Scripts\activate.bat
)

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo  Penerjemah Reiki sudah jalan.
echo  Buka di komputer ini : http://localhost:8001
echo  Jangan tutup jendela ini selama aplikasi dipakai.
echo.
python -m uvicorn server:app --host 0.0.0.0 --port 8001
pause
