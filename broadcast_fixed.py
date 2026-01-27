#!/usr/bin/env python3
import sqlite3
import telnetlib
import os
import sys
import time

# --- KONFIGURASI YANG SUDAH DIPERBAIKI ---
# Mengarah ke file 'hlr.db' sesuai screenshot Anda
DB_PATH = os.path.expanduser("~/gsm/hlr.db")
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254

def ambil_msisdn_dari_db():
    print(f"[*] Membaca database: {DB_PATH}")
    
    # Cek apakah file benar-benar ada
    if not os.path.exists(DB_PATH):
        print(f"[!] ERROR: File {DB_PATH} tidak ditemukan!")
        return []

    try:
        # Koneksi ke SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query mengambil nomor pelanggan
        # (Mengambil MSISDN yang tidak kosong)
        cursor.execute("SELECT msisdn FROM subscriber WHERE msisdn IS NOT NULL AND msisdn != ''")
        data = cursor.fetchall()
        conn.close()
        
        # Rapikan data tuple [('1001',), ('1003',)] menjadi list ['1001', '1003']
        hasil_bersih = [item[0] for item in data]
        return hasil_bersih

    except Exception as e:
        print(f"[!] Gagal membaca SQL: {e}")
        return []

def kirim_broadcast(daftar_target, pengirim, pesan):
    if not daftar_target:
        print("[!] Tidak ada target untuk dikirim.")
        return

    print(f"\n[*] Memulai Broadcast ke {len(daftar_target)} nomor...")
    
    try:
        tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=10)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")

        sukses = 0
        for target in daftar_target:
            print(f" -> Mengirim ke {target}...", end=' ')
            
            # FORMAT PERINTAH FINAL (Sesuai tes manual kita yang berhasil)
            # subscriber msisdn [TARGET] sms sender msisdn [PENGIRIM] send [PESAN]
            cmd = f"subscriber msisdn {target} sms sender msisdn {pengirim} send {pesan}\n"
            
            tn.write(cmd.encode('ascii'))
            
            # Beri jeda 0.5 detik per SMS agar stabil
            time.sleep(0.5) 
            print("[OK]")
            sukses += 1
            
        tn.write(b"exit\n")
        tn.close()
        print(f"\n[+] SELESAI! {sukses} SMS berhasil dikirim ke antrian jaringan.")

    except ConnectionRefusedError:
        print(f"\n[!] GAGAL: Tidak bisa connect ke MSC (Port 4254).")
        print("    Pastikan 'osmo-msc' sudah berjalan!")
    except Exception as e:
        print(f"\n[!] Error: {e}")

if __name__ == "__main__":
    print("=== BROADCAST SMS OTOMATIS (OSMO-HLR DB) ===\n")
    
    # 1. Input Data
    sender = input("Masukkan Nomor Pengirim (Cth: 8888): ")
    if not sender: sender = "8888"
    
    msg = input("Isi Pesan: ")
    if not msg: sys.exit("[!] Pesan tidak boleh kosong!")

    # 2. Ambil Data dari hlr.db
    targets = ambil_msisdn_dari_db()
    
    # 3. Eksekusi
    if targets:
        print(f"[+] Ditemukan {len(targets)} Nomor Aktif: {', '.join(targets)}")
        tanya = input("Lanjut kirim broadcast? (y/n): ")
        if tanya.lower() == 'y':
            kirim_broadcast(targets, sender, msg)
        else:
            print("[-] Dibatalkan.")
    else:
        print("[!] Database hlr.db kosong atau belum ada pelanggan yang punya nomor.")
