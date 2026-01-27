#!/usr/bin/env python3
import sqlite3
import telnetlib
import os
import time
import warnings

# Matikan warning agar tampilan bersih
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- KONFIGURASI DATABASE ---
DB_PATH = os.path.expanduser("~/gsm/hlr.db")

# --- KONFIGURASI TARGET (SESUAI HASIL NETSTAT) ---
MSC_LIST = [
    # TOWER USB (Localhost) - Port 4254
    {"nama": "TOWER USB (PLMN A)", "host": "127.0.0.1", "port": 4254},
    
    # TOWER LAN (AntsDR) - Port 4254
    {"nama": "TOWER LAN (PLMN B)", "host": "10.0.0.1",  "port": 4254}
]

def ambil_semua_imsi():
    if not os.path.exists(DB_PATH): 
        print(f"[ERROR] Database tidak ditemukan di {DB_PATH}")
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT imsi, msisdn FROM subscriber")
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        return []

def monitoring_realtime():
    daftar = ambil_semua_imsi()
    if not daftar:
        print("[!] Database HLR kosong.")
        return

    print("="*85)
    print(f"   MONITORING DUAL NETWORK (USB & LAN)")
    print("="*85)
    print(f"{'IMSI':<18} | {'NOMOR HP':<15} | {'LOKASI TOWER':<22} | {'STATUS'}")
    print("-" * 85)

    online_total = 0

    for imsi, msisdn in daftar:
        if not msisdn: msisdn = "NoNum"
        
        lokasi_ditemukan = None
        
        # Cek ke setiap MSC
        for msc in MSC_LIST:
            try:
                # Koneksi Telnet
                tn = telnetlib.Telnet(msc['host'], msc['port'], timeout=2)
                
                # Mantra Login (Sesuai skrip lama Mas)
                tn.read_until(b"> ", timeout=1)
                tn.write(b"enable\n")
                tn.read_until(b"# ", timeout=1)
                
                # Cek Subscriber
                cmd = f"show subscriber imsi {imsi}\n"
                tn.write(cmd.encode('ascii'))
                
                # Baca Output
                output = tn.read_until(b"# ", timeout=2).decode('ascii')
                tn.write(b"exit\n")
                tn.close()

                # Analisis: Jika MSC memberikan detail (bukan error), berarti ONLINE
                if "% No subscriber" not in output and "No subscriber found" not in output:
                    lokasi_ditemukan = msc['nama']
                    break # Ketemu! Gak perlu cek tower sebelah
            except:
                continue # Lanjut cek tower sebelah jika error

        # Tampilkan Hasil
        if lokasi_ditemukan:
            print(f"{imsi:<18} | {msisdn:<15} | {lokasi_ditemukan:<22} | [\033[92mONLINE\033[0m]")
            online_total += 1
        # else:
        #    print(f"{imsi:<18} | {msisdn:<15} | {'-':<22} | [OFFLINE]")

    print("-" * 85)
    if online_total == 0:
        print("   Tidak ada perangkat yang terhubung.")
    else:
        print(f"   Total Perangkat Aktif: {online_total}")
    print("="*85)

if __name__ == "__main__":
    monitoring_realtime()
