#!/usr/bin/env python3
import sqlite3
import os
import sys
import time
import smpplib.gsm
import smpplib.client
import smpplib.consts

# --- KONFIGURASI ---
# Database
DB_PATH = os.path.expanduser("~/gsm/hlr.db")

# Koneksi SMPP
SMPP_HOST = "127.0.0.1"
SMPP_PORT = 2775
SYSTEM_ID = "test"
PASSWORD  = "test"

def ambil_msisdn_dari_db():
    print(f"[*] Membaca database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"[!] ERROR: File {DB_PATH} tidak ditemukan!")
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Mengambil MSISDN yang valid
        cursor.execute("SELECT msisdn FROM subscriber WHERE msisdn IS NOT NULL AND msisdn != ''")
        data = cursor.fetchall()
        conn.close()
        
        # Rapikan data
        hasil_bersih = [item[0] for item in data]
        return hasil_bersih

    except Exception as e:
        print(f"[!] Gagal membaca SQL: {e}")
        return []

def kirim_broadcast_smpp(daftar_target, pengirim, pesan):
    if not daftar_target:
        print("[!] Tidak ada target untuk dikirim.")
        return

    print(f"\n[*] Menghubungkan ke SMPP ({SMPP_HOST}:{SMPP_PORT})...")
    
    try:
        client = smpplib.client.Client(SMPP_HOST, SMPP_PORT)
        client.connect()
        client.bind_transmitter(system_id=SYSTEM_ID, password=PASSWORD)
        print("[+] Login SMPP Berhasil!")

        # --- LOGIKA PINTAR: MENENTUKAN TIPE PENGIRIM ---
        if pengirim.isdigit():
            # Jika Angka Semua (081234)
            ton = smpplib.consts.SMPP_TON_INTL
            npi = smpplib.consts.SMPP_NPI_ISDN
            tipe_kirim = "NOMOR BIASA"
        else:
            # Jika ada Huruf (POLDA) -> ALPHANUMERIC
            if len(pengirim) > 11:
                pengirim = pengirim[:11]
                print(f"[!] Info: Nama dipotong jadi '{pengirim}' (Max 11 Char)")
            
            ton = smpplib.consts.SMPP_TON_ALNUM
            # PERBAIKAN DI SINI: Menggunakan .SMPP_NPI_UNK
            npi = smpplib.consts.SMPP_NPI_UNK 
            tipe_kirim = "ALPHANUMERIC (HURUF)"

        print(f"[*] Mode Pengiriman: {tipe_kirim}")
        print(f"[*] Memulai Broadcast ke {len(daftar_target)} nomor...")
        print("="*60)

        # Encoding pesan
        parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(pesan)

        sukses = 0
        for target in daftar_target:
            print(f" -> Mengirim ke {target}...", end=' ')
            try:
                for part in parts:
                    client.send_message(
                        source_addr_ton=ton,
                        source_addr_npi=npi,
                        source_addr=pengirim,
                        
                        dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
                        dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                        destination_addr=target,
                        
                        short_message=part,
                        data_coding=encoding_flag,
                        esm_class=msg_type_flag,
                        registered_delivery=False,
                    )
                print("\033[92m[OK]\033[0m") 
                sukses += 1
                time.sleep(0.1) 
                
            except Exception as e:
                print(f"\033[91m[GAGAL: {e}]\033[0m")

        print("="*60)
        print(f"[+] SELESAI! {sukses} SMS berhasil ditembakkan.")
        
        client.unbind()
        client.disconnect()

    except Exception as e:
        print(f"\n[!] ERROR SMPP: {e}")
        print("    Pastikan fitur SMPP di osmo-msc.cfg sudah aktif!")

if __name__ == "__main__":
    print("=== BROADCAST SMS HYBRID (DATABASE + SMPP) ===\n")
    
    sender = input("Masukkan PENGIRIM (Bisa Angka '081xxx' atau Huruf 'POLDA'): ")
    if not sender: sender = "INFO" 
    
    msg = input("Isi Pesan: ")
    if not msg: sys.exit("[!] Pesan tidak boleh kosong!")

    targets = ambil_msisdn_dari_db()
    
    if targets:
        print(f"[+] Ditemukan {len(targets)} Nomor Aktif: {', '.join(targets)}")
        tanya = input("Lanjut kirim broadcast? (y/n): ")
        if tanya.lower() == 'y':
            kirim_broadcast_smpp(targets, sender, msg)
        else:
            print("[-] Dibatalkan.")
    else:
        print("[!] Database hlr.db kosong. Pastikan HLR sudah berjalan dan ada subscriber.")
