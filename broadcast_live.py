#!/usr/bin/env python3
import telnetlib
import re
import sys
import time
import smpplib.gsm
import smpplib.client
import smpplib.consts

# --- KONFIGURASI ---
MSC_HOST = "127.0.0.1"
MSC_PORT_VTY = 4254 
MSC_PORT_SMPP = 2775
SYSTEM_ID = "test"
PASSWORD  = "test"

def get_online_users():
    print(f"[*] Menghubungkan ke Radar MSC (VTY)...")
    active_numbers = []

    try:
        tn = telnetlib.Telnet(MSC_HOST, MSC_PORT_VTY, timeout=5)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")
        
        # --- PERBAIKAN DI SINI ---
        # Menggunakan perintah lengkap 'show subscriber cache'
        print("[*] Mengambil data 'show subscriber cache'...")
        tn.write(b"show subscriber cache\n")
        
        # Baca semua output sampai prompt muncul lagi
        raw_output = tn.read_until(b"# ", timeout=3).decode('ascii')
        tn.close()

        # --- DEBUG LOG (PENTING) ---
        # Ini akan menampilkan apa adanya jawaban dari MSC
        print("\n" + "="*20 + " DEBUG RAW OUTPUT " + "="*20)
        print(raw_output.strip())
        print("="*60 + "\n")

        # --- LOGIKA PARSING (REGEX) ---
        # Pola 1: Mencari format "MSISDN: 1001"
        found_labeled = re.findall(r'MSISDN:?\s*(\d+)', raw_output, re.IGNORECASE)
        
        # Pola 2: Mencari format kolom (biasanya IMSI(15) spasi MSISDN(pendek))
        # Kita ambil angka yang panjangnya 3-14 digit (bukan IMSI 15 digit)
        # yang muncul setelah IMSI.
        found_raw_digits = re.findall(r'\b\d{3,14}\b', raw_output)
        
        # Gabungkan hasil temuan
        candidates = found_labeled + found_raw_digits
        
        # Filter: Hapus angka yang sepertinya bukan nomor HP (misal Port, ID, atau IMSI)
        # Biasanya nomor HP itu 4 digit sampai 13 digit.
        final_list = []
        for num in candidates:
            if num not in final_list:
                # Filter tambahan: Jangan ambil angka '4254' (port) atau '2775'
                if num not in ['4254', '2775', '0'] and len(num) >= 3:
                    final_list.append(num)

        active_numbers = sorted(final_list)
        
    except Exception as e:
        print(f"[!] Gagal scan VTY: {e}")
        return []

    return active_numbers

def kirim_smpp(targets, sender, message):
    print(f"\n[*] Menghubungkan ke SMPP ({MSC_HOST}:{MSC_PORT_SMPP})...")
    try:
        client = smpplib.client.Client(MSC_HOST, MSC_PORT_SMPP)
        client.connect()
        client.bind_transmitter(system_id=SYSTEM_ID, password=PASSWORD)
        print("[+] Login SMPP Berhasil!")

        # Tentukan Tipe Pengirim
        if sender.isdigit():
            ton = smpplib.consts.SMPP_TON_INTL
            npi = smpplib.consts.SMPP_NPI_ISDN
            tipe = "NOMOR BIASA"
        else:
            if len(sender) > 11: sender = sender[:11]
            ton = smpplib.consts.SMPP_TON_ALNUM
            npi = smpplib.consts.SMPP_NPI_UNK
            tipe = "HURUF (ALPHANUMERIC)"

        print(f"[*] Pengirim: {sender} ({tipe})")
        print(f"[*] Target: {len(targets)} Nomor")
        print("-" * 50)

        parts, encoding, flag = smpplib.gsm.make_parts(message)

        sukses = 0
        for number in targets:
            print(f" -> Tembak ke \033[96m{number}\033[0m ... ", end='')
            try:
                for part in parts:
                    client.send_message(
                        source_addr_ton=ton,
                        source_addr_npi=npi,
                        source_addr=sender,
                        dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
                        dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                        destination_addr=number,
                        short_message=part,
                        data_coding=encoding,
                        esm_class=flag,
                        registered_delivery=False,
                    )
                print("\033[92m[TERKIRIM]\033[0m")
                sukses += 1
                time.sleep(0.1) 
            except Exception as e:
                print(f"\033[91m[GAGAL: {e}]\033[0m")

        print("="*60)
        print(f"[+] Broadcast Selesai. {sukses} pesan sukses dikirim.")
        client.unbind()
        client.disconnect()

    except Exception as e:
        print(f"[!] Error SMPP: {e}")

if __name__ == "__main__":
    print("=== LIVE RADAR BROADCAST V2 (FIXED COMMAND) ===\n")
    
    # 1. Scan
    online_users = get_online_users()

    # Tampilkan hasil scan
    if not online_users:
        print("\n[!] ZONK: Tidak ada nomor yang terbaca.")
        print("    Cek 'DEBUG RAW OUTPUT' di atas. Apakah ada nomor HP di situ?")
        sys.exit(0)

    print(f"\n[+] Ditemukan {len(online_users)} Target: {', '.join(online_users)}")
    print("-" * 50)

    # 2. Konfirmasi & Kirim
    pengirim = input("Pengirim (Angka/Huruf): ") or "INFO"
    pesan = input("Isi Pesan: ") or "Test Broadcast"

    konfirmasi = input(f"Kirim ke {len(online_users)} nomor ini? [Y/n]: ")
    if konfirmasi.lower() != 'n':
        kirim_smpp(online_users, pengirim, pesan)
    else:
        print("Dibatalkan.")
