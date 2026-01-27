#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime

# Lokasi Database
DB_PATH = os.path.expanduser("~/gsm/hlr.db")

def cek_semua_pelanggan():
    if not os.path.exists(DB_PATH):
        print(f"[!] Database {DB_PATH} tidak ditemukan.")
        return

    try:
        # Buka Database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ambil data: ID, IMSI, MSISDN, dan Tanggal Dibuat (jika ada)
        # Kita ambil semua, baik yang punya nomor atau belum
        cursor.execute("SELECT id, imsi, msisdn FROM subscriber")
        data = cursor.fetchall()
        conn.close()

        print("="*50)
        print(f"   ISI DATABASE HLR ({len(data)} Pelanggan)")
        print("="*50)
        print(f"{'ID':<5} | {'IMSI':<18} | {'NOMOR HP (MSISDN)':<15}")
        print("-" * 50)

        for row in data:
            id_sub = row[0]
            imsi = row[1]
            msisdn = row[2]
            
            # Jika msisdn kosong, tulis 'Belum Ada'
            if msisdn is None or msisdn == "":
                msisdn = "[KOSONG]"
            
            print(f"{id_sub:<5} | {imsi:<18} | {msisdn:<15}")

        print("-" * 50)
        print(f"Total: {len(data)} kartu SIM terdaftar.")
        print("="*50)

    except Exception as e:
        print(f"[!] Error membaca database: {e}")

if __name__ == "__main__":
    cek_semua_pelanggan()
