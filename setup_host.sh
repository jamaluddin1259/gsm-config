#!/bin/bash
# Skrip Persiapan Host untuk USRP B210 & Docker Osmogrgsm

echo "=== Memulai Setup Host Ubuntu 24.04 ==="

# 1. Update dan Install Paket Dasar
sudo apt update
sudo apt install -y uhd-host libuhd-dev gnuradio docker.io git

# 2. Tambahkan User ke Grup Docker
sudo usermod -aG docker $USER

# 3. Download Firmware UHD
echo "--- Mendownload Firmware UHD (B210) ---"
sudo uhd_images_downloader

# 4. Konfigurasi Udev Rules (Izin USB)
echo "--- Mengatur Izin USB (Udev Rules) ---"
# Mencari lokasi file rules secara dinamis agar tidak error No Such File
RULES_PATH=$(find /usr/lib -name "uhd-usrp.rules" | head -n 1)

if [ -z "$RULES_PATH" ]; then
    echo "Error: File uhd-usrp.rules tidak ditemukan!"
else
    sudo cp "$RULES_PATH" /etc/udev/rules.d/
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "Berhasil menyalin rules dari: $RULES_PATH"
fi

echo "=== Setup Selesai! ==="
echo "PENTING: Silakan cabut dan colok kembali SDR ."
echo "PENTING: Silakan LOGOUT dan LOGIN kembali agar grup Docker aktif."
