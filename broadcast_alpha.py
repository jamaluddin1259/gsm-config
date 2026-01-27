#!/usr/bin/env python3
import sqlite3
import smpplib
import smpplib.gsm
import smpplib.consts
import os
import sys
import time

# --- KONFIGURASI ---
# Menggunakan database hlr.db sesuai sistem Anda
DB_PATH = os.path.expanduser("~/gsm/hlr.db")
MSC_IP = '127.0.0.1'
MSC_PORT = 2775  # Port SMPP (Wajib ini supaya bisa pakai Huruf)

def ambil_target_dari_db():
    """Mengambil semua nomor HP dari database hlr.db"""
    if not os.path.exists(DB_PATH):
        print(f"[!] Database {DB_PATH} tidak ditemukan.")
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Ambil msisdn yang tidak kosong
        cursor.execute("SELECT msisdn FROM subscriber WHERE msisdn IS NOT NULL AND msisdn != ''")
        data = [item[0] for item in cursor.fetchall()]
        conn.close()
        return data
    except Exception as e:
        print(f"[!] Gagal baca DB: {e}")
        return []

def kirim_via_smpp(daftar_target, nama_pengirim, isi_pesan):
    """Mengirim SMS dengan Header Alphanumeric"""
    print(f"\n[*] Menghubungkan ke SMPP ({MSC_IP}:{MSC_PORT})...")
    
    try:
        # 1. Setup Koneksi
        client = smpplib.client.Client(MSC_IP, MSC_PORT)
        
        # 2. Login SMPP (Default OsmoMSC biasanya user/pass bebas)
        client.connect()
        client.bind_transceiver(system_id='test', password='test')
        print("[+] Login SMPP Berhasil.")

        sukses = 0
        print(f"[*] Mengirim pesan dari '{nama_pengirim}'...")

        for target in daftar_target:
            print(f" -> Sending to {target}...", end=' ')
            
            # 3. RAKIT PESAN (RAHASIANYA DI SINI)
            # Memecah pesan panjang jika perlu
            parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(isi_pesan)
            
            for part in parts:
                client.send_message(
                    source_addr_ton=smpplib.consts.SMPP_TON_ALNUM, # <--- INI KUNCINYA (ALPHANUMERIC)
                    source_addr_npi=smpplib.consts.SMPP_NPI_UNKNOWN,
                    source_addr=nama_pengirim, # Nama Huruf masuk sini
                    
                    dest_addr_ton=smpplib.consts.SMPP_TON_INTERNATIONAL,
                    dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                    destination_addr=target,
                    
                    short_message=part,
                    data_coding=encoding_flag,
                    esm_class=msg_type_flag,
                    registered_delivery=0,
                )
            print("[OK]")
            sukses += 1
            time.sleep(0.2) # Jeda sedikit agar stabil

        print(f"\n[+] SELESAI! {sukses} Pesan terkirim.")
        client.unbind()
        client.disconnect()

    except Exception as e:
        print(f"\n[!] GAGAL SMPP: {e}")
        print("    Tips: Pastikan layanan OsmoMSC berjalan normal.")

if __name__ == "__main__":
    print("=== BROADCAST SMS SENDER HURUF (SMPP) ===\n")
    
    # Input Pengirim (Bebas Huruf)
    sender = input("Masukkan NAMA Pengirim (Maks 11 Huruf): ")
    if not sender: sender = "DRAGON-OS"
    
    # Potong jika kepanjangan (Aturan GSM maks 11 karakter untuk nama)
    if len(sender) > 11:
        sender = sender[:11]
        print(f"[*] Nama dipotong menjadi: {sender} (Maks 11 char)")

    msg = input("Isi Pesan: ")
    if not msg: sys.exit("[!] Pesan kosong!")
