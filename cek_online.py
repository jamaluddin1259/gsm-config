#!/usr/bin/env python3
import sqlite3
import telnetlib
import os
import time
import sys
import select
import tty
import termios

# --- KONFIGURASI ---
DB_PATH = os.path.expanduser("~/gsm/hlr.db")
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254
MAX_ROWS = 7       # Jumlah baris per halaman
DELAY_LOOP = 0.5   # Kecepatan loop (detik)

def is_data_ready():
    """Cek apakah ada tombol keyboard ditekan (Non-blocking)"""
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

def get_key():
    """Membaca satu karakter dari keyboard tanpa tekan Enter"""
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        if is_data_ready():
            return sys.stdin.read(1)
        return None
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def ambil_semua_imsi_terbaru():
    """Mengambil data IMSI diurutkan dari yang TERBARU (ID DESC)"""
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        # ORDER BY id DESC agar yang paling baru masuk paling atas
        cursor.execute("SELECT imsi, msisdn FROM subscriber ORDER BY id DESC")
        data = cursor.fetchall()
        conn.close()
        return data 
    except:
        return []

def get_online_devices(imsi_list, tn_session):
    """Filter status online lewat sesi Telnet yang sudah terbuka"""
    online_list = []
    try:
        # Trik cepat: Ambil semua data HLR subscriber sekaligus jika memungkinkan
        # Tapi biar akurat, kita loop show subscriber
        # Agar tidak lambat, kita set timeout sangat kecil
        for imsi, msisdn in imsi_list:
            if not msisdn: msisdn = "-"
            tn_session.write(f"show subscriber imsi {imsi}\n".encode('ascii'))
            output = tn_session.read_until(b"# ", timeout=0.1).decode('ascii')
            
            if "% No subscriber" not in output:
                online_list.append((imsi, msisdn))
    except:
        pass
    return online_list

def main_loop():
    os.system('cls' if os.name == 'nt' else 'clear')
    current_page = 1
    last_check_time = 0
    cached_online_list = []
    
    # Pesan instruksi
    instruksi = "Navigasi: [n] Next Page | [p] Prev Page | [q] Quit"

    try:
        while True:
            # --- 1. DETEKSI INPUT KEYBOARD (Tanpa Pause) ---
            key = get_key()
            if key == 'n':
                current_page += 1
            elif key == 'p':
                if current_page > 1:
                    current_page -= 1
            elif key == 'q':
                print("\nKeluar.")
                break

            # --- 2. UPDATE DATA (Setiap 2 detik agar tidak spamming Telnet) ---
            now = time.time()
            if now - last_check_time > 2.0:
                try:
                    all_subs = ambil_semua_imsi_terbaru()
                    
                    # Buka Telnet sekali untuk batch check
                    tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=1)
                    tn.read_until(b"> ")
                    tn.write(b"enable\n")
                    tn.read_until(b"# ")
                    
                    # Update list online
                    cached_online_list = get_online_devices(all_subs, tn)
                    
                    tn.write(b"exit\n")
                    tn.close()
                    last_check_time = now
                except:
                    pass # Abaikan error koneksi sesaat

            # --- 3. LOGIKA PAGINATION ---
            total_online = len(cached_online_list)
            total_pages = (total_online + MAX_ROWS - 1) // MAX_ROWS
            if total_pages < 1: total_pages = 1
            
            # Koreksi halaman jika out of bound
            if current_page > total_pages: current_page = total_pages
            if current_page < 1: current_page = 1

            # Slice data untuk halaman saat ini
            start_idx = (current_page - 1) * MAX_ROWS
            end_idx = start_idx + MAX_ROWS
            page_data = cached_online_list[start_idx:end_idx]

            # --- 4. TAMPILKAN DASHBOARD ---
            sys.stdout.write("\033[H") # Reset Kursor ke atas
            
            print("\033[96m" + "="*60)
            print(f"    MONITOR GSM TERBARU (Halaman {current_page}/{total_pages})")
            print("="*60 + "\033[0m")
            
            if total_online == 0:
                print(f"\n\033[91m[!] Tidak ada perangkat online.\033[0m")
                print("    Menunggu koneksi...")
            else:
                print(f"{'IMSI (Terbaru)':<18} | {'NOMOR HP':<15} | {'STATUS'}")
                print("-" * 60)
                
                for imsi, msisdn in page_data:
                    print(f"{imsi:<18} | {msisdn:<15} | \033[92m[ONLINE] AKTIF\033[0m")
                
                # Isi baris kosong jika data di halaman ini sedikit (agar tinggi layar tetap)
                sisa_baris = MAX_ROWS - len(page_data)
                for _ in range(sisa_baris):
                    print(" " * 60)

            print("-" * 60)
            print(f"Total Online: \033[92m{total_online}\033[0m Perangkat")
            print(f"\033[93m{instruksi}\033[0m")
            print("="*60)
            
            sys.stdout.write("\033[J") # Bersihkan sisa bawah
            sys.stdout.flush()
            
            time.sleep(DELAY_LOOP) # Loop cepat untuk respons keyboard

    except KeyboardInterrupt:
        print("\nStop.")
        sys.exit(0)

if __name__ == "__main__":
    main_loop()
