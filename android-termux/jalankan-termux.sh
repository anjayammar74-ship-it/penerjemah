#!/data/data/com.termux/files/usr/bin/bash
# Penerjemah Reiki di HP Android (Termux). Jalankan:  bash jalankan-termux.sh
set -e
cd "$(dirname "$0")/../app"

if [ ! -f .siap ]; then
  echo "Menyiapkan Penerjemah Reiki untuk pertama kali (bisa 15-30 menit)..."
  pkg update -y && pkg upgrade -y
  pkg install -y python python-numpy python-scipy python-pillow rust binutils cloudflared
  pip install fastapi==0.110.1 starlette==0.37.2 uvicorn==0.25.0 motor==3.7.1 "pymongo>=4.6,<5" \
    httpx==0.28.1 "pydantic>=2.6,<3" "python-dotenv>=1.0" wordninja==2.0.0
  touch .siap
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo
  echo "PENTING: isi MONGO_URL di file app/.env dengan link MongoDB Atlas kamu (PANDUAN.txt CARA C)."
  echo "Edit dengan:  nano $(pwd)/.env   lalu jalankan skrip ini lagi."
  exit 0
fi

termux-wake-lock 2>/dev/null || true
echo "Penerjemah Reiki jalan di http://localhost:8001  (biarkan Termux terbuka)"
python -m uvicorn server:app --host 0.0.0.0 --port 8001
