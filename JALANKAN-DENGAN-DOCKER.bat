@echo off
chcp 65001 >nul
title Penerjemah Reiki - Docker
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
  echo [!] Docker Desktop belum terpasang. Lihat PANDUAN.txt CARA B.
  pause
  exit /b 1
)
echo Menyalakan Penerjemah Reiki + database (dan penerjemah sendiri)...
docker compose --profile lokal up -d --build
echo.
echo  Selesai. Buka http://localhost:8001
echo  Penerjemah Reiki akan menyala sendiri setiap Docker Desktop menyala.
pause
