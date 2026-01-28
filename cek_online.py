#!/usr/bin/env python3
import sqlite3
import telnetlib
import os
import time
import sys

# --- KONFIGURASI ---
DB_PATH = os.path.expanduser("~/gsm/hlr.db")
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254  # Port MSC
DELAY_REFRESH = 3 # Detik (Waktu jeda antar refresh)

def clear_screen():
    """Membersihkan layar terminal agar terlihat seperti dashboard"""
    os.system('cls' if os.name == 'nt' else 'clear')

def ambil_semua_imsi():
    """Mengambil semua IMSI dari database untuk diabsen"""
    if not os.path.exists(DB_PATH):
        return []
    try:
        # Buka database dengan mode Read-Only agar tidak mengunci file
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT imsi, msisdn FROM subscriber")
        data = cursor.fetchall()
        conn.close()
        return data 
    except:
        return []

def cek_status_online():
    # 1. Bersihkan layar dulu
    clear_screen()

    daftar_pelanggan = ambil_semua_imsi()
    
    print("\033[96m="*60) # Warna Cyan
    print(f"    STATUS JARINGAN REAL-TIME (Auto-Refresh {DELAY_REFRESH}s)")
    print("="*60 + "\033[0m")
    
    if not daftar_pelanggan:
        print("\n[!] Database HLR kosong atau tidak ditemukan.")
        return

    print(f"{'IMSI':<18} | {'NOMOR HP':<15} | {'STATUS'}")
    print("-" * 60)

    try:
        # Masuk ke OsmoMSC
        tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=3)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")
        
        online_count = 0
        total_imsi = len(daftar_pelanggan)

        # Kita absen satu per satu
        for imsi, msisdn in daftar_pelanggan:
            if not msisdn: msisdn = "Tanpa No"
            
            # Perintah cek status spesifik ke MSC
            cmd = f"show subscriber imsi {imsi}\n"
            tn.write(cmd.encode('ascii'))
            
            # Baca respon
            output = tn.read_until(b"# ", timeout=1).decode('ascii')
            
            # Cek tanda-tanda kehidupan
            if "% No subscriber" in output:
                # User Offline -> Tidak perlu ditampilkan (biar rapi)
                # Atau aktifkan baris bawah ini jika ingin melihat yang offline juga:
                # print(f"{imsi:<18} | {msisdn:<15} | [OFF] Offline")
                pass 
            else:
                # User Online (Ada data LAC/CID dsb)
                print(f"{imsi:<18} | {msisdn:<15} | \033[92m[ONLINE] TERHUBUNG\033[0m")
                online_count += 1
        
        tn.write(b"exit\n")
        tn.close()

        print("-" * 60)
        if online_count == 0:
            print(f"Total Terdaftar: {total_imsi} | \033[91mTidak ada HP aktif saat ini.\033[0m")
        else:
            print(f"Total Terdaftar: {total_imsi} | \033[92mTotal Online: {online_count} HP\033[0m")
        print("="*60)
        print("\n[i] Tekan Ctrl+C untuk STOP.")

    except ConnectionRefusedError:
        print("\n\033[91m[!] GAGAL KONEKSI KE MSC!\033[0m")
        print("    Pastikan 'osmo-msc' sudah berjalan.")
    except Exception as e:
        print(f"\n[!] Error: {e}")

# --- LOOPING UTAMA ---
if __name__ == "__main__":
    try:
        while True:
            cek_status_online()
            # Jeda waktu sebelum refresh ulang
            time.sleep(DELAY_REFRESH)
            
    except KeyboardInterrupt:
        print("\n\n[!] Monitoring Dihentikan.")
        sys.exit(0)
