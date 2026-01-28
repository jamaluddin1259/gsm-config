#!/usr/bin/env python3
import sqlite3
import telnetlib
import os
import time
import sys

# --- KONFIGURASI ---
DB_PATH = os.path.expanduser("~/gsm/hlr.db")
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254
DELAY_REFRESH = 1  # Refresh rate 1 detik (Cepat)

def ambil_semua_imsi():
    """Mengambil data IMSI tanpa mengunci database"""
    if not os.path.exists(DB_PATH):
        return []
    try:
        # Mode Read-Only (ro) agar aman
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT imsi, msisdn FROM subscriber")
        data = cursor.fetchall()
        conn.close()
        return data 
    except:
        return []

def main_loop():
    # Bersihkan layar SATU KALI SAJA di awal
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        while True:
            # 1. Pindahkan Kursor ke Pojok Kiri Atas (Tanpa Hapus Layar)
            # \033[H = Home Position
            sys.stdout.write("\033[H")
            
            # 2. Ambil Data
            daftar_pelanggan = ambil_semua_imsi()
            
            # 3. Header Dashboard
            print("\033[96m" + "="*60)
            print(f"    DASHBOARD MONITORING GSM (LIVE)")
            print("="*60 + "\033[0m")
            
            if not daftar_pelanggan:
                print("\n[!] Database Kosong/Tidak Ditemukan.")
            else:
                print(f"{'IMSI':<18} | {'NOMOR HP':<15} | {'STATUS'}")
                print("-" * 60)

                try:
                    # Buka Koneksi Telnet (Cepat)
                    tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=1)
                    tn.read_until(b"> ")
                    tn.write(b"enable\n")
                    tn.read_until(b"# ")
                    
                    online_count = 0
                    total_imsi = len(daftar_pelanggan)

                    for imsi, msisdn in daftar_pelanggan:
                        if not msisdn: msisdn = "-"
                        
                        tn.write(f"show subscriber imsi {imsi}\n".encode('ascii'))
                        output = tn.read_until(b"# ", timeout=0.5).decode('ascii')
                        
                        # Logika Status
                        status_text = ""
                        if "% No subscriber" in output:
                            # Jika ingin menampilkan yang offline, uncomment baris bawah:
                            # status_text = "\033[90m[OFFLINE]\033[0m" 
                            pass # Skip biar rapi, hanya yang online yang muncul
                        else:
                            status_text = "\033[92m[ONLINE]  AKTIF\033[0m" # Hijau
                            print(f"{imsi:<18} | {msisdn:<15} | {status_text}")
                            online_count += 1
                    
                    tn.write(b"exit\n")
                    tn.close()

                    # Footer
                    print("-" * 60)
                    if online_count > 0:
                        print(f"Total Online: \033[92m{online_count}\033[0m / {total_imsi} Perangkat")
                    else:
                        print(f"Total Terdaftar: {total_imsi} | \033[91mTidak ada aktivitas.\033[0m")
                    print("="*60)
                    
                    # 4. Hapus sisa baris di bawah (jika list memendek)
                    # \033[J = Clear Screen from Cursor to End
                    sys.stdout.write("\033[J")

                except Exception:
                    print(f"\n\033[91m[!] Koneksi MSC Terputus.\033[0m")
                    sys.stdout.write("\033[J") # Bersihkan bawah

            # Flush agar tampilan langsung muncul
            sys.stdout.flush()
            
            # Jeda 1 detik
            time.sleep(DELAY_REFRESH)

    except KeyboardInterrupt:
        print("\n[!] Monitoring Stop.")
        sys.exit(0)

if __name__ == "__main__":
    main_loop()
