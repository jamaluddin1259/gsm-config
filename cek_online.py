#!/usr/bin/env python3
import sqlite3
import telnetlib
import os
import time
import re

# --- KONFIGURASI ---
DB_PATH = os.path.expanduser("~/gsm/hlr.db")
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254  # Port MSC (Pengelola Sinyal/Traffic)

def ambil_semua_imsi():
    """Mengambil semua IMSI dari database untuk diabsen"""
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT imsi, msisdn FROM subscriber")
        data = cursor.fetchall()
        conn.close()
        return data # List of (imsi, msisdn)
    except:
        return []

def cek_status_online():
    daftar_pelanggan = ambil_semua_imsi()
    if not daftar_pelanggan:
        print("[!] Database kosong.")
        return

    print("="*60)
    print(f"   STATUS REAL-TIME (Hanya yang ON / Ada Sinyal)")
    print("="*60)
    print(f"{'IMSI':<18} | {'NOMOR HP':<15} | {'STATUS'}")
    print("-" * 60)

    try:
        # Masuk ke OsmoMSC
        tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=5)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")
        
        online_count = 0

        # Kita absen satu per satu
        for imsi, msisdn in daftar_pelanggan:
            if not msisdn: msisdn = "Tanpa No"
            
            # Perintah cek status spesifik ke MSC
            cmd = f"show subscriber imsi {imsi}\n"
            tn.write(cmd.encode('ascii'))
            
            # Baca respon MSC
            # Jika user online, MSC akan memberi detail panjang.
            # Jika offline, MSC biasanya bilang "% No subscriber found"
            output = tn.read_until(b"# ").decode('ascii')
            
            # Cek tanda-tanda kehidupan
            if "% No subscriber" in output:
                # User Offline / Tidak ada di VLR
                pass 
            else:
                # User Online (Ada data LAC/CID dsb)
                print(f"{imsi:<18} | {msisdn:<15} | [ONLINE] \033[92mAKTIF\033[0m")
                online_count += 1
        
        tn.write(b"exit\n")
        tn.close()

        print("-" * 60)
        if online_count == 0:
            print("Tidak ada HP yang tersambung saat ini.")
        else:
            print(f"Total: {online_count} HP sedang Online.")
        print("="*60)

    except Exception as e:
        print(f"[!] Gagal koneksi ke MSC: {e}")
        print("    Pastikan osmo-msc sedang berjalan.")

if __name__ == "__main__":
    cek_status_online()
