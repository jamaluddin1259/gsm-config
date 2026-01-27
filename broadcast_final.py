#!/usr/bin/env python3
import telnetlib
import re
import sys
import time
import warnings
import smpplib.gsm
import smpplib.client
import smpplib.consts

# Matikan warning agar bersih
warnings.filterwarnings("ignore", category=DeprecationWarning)

# =======================================================
#               KONFIGURASI JARINGAN (FINAL)
# =======================================================
# Berdasarkan keberhasilan tes manual Mas Jamal:
TOWERS = [
    {
        "nama": "TOWER USB (PLMN A)",
        "host": "127.0.0.1",
        "vty_port": 4254,   # Port Intip User
        "smpp_port": 2775   # Port Kirim SMS (USB)
    },
    {
        "nama": "TOWER LAN (AntsDR)",
        "host": "10.0.0.1",
        "vty_port": 4254,   # Port Intip User
        "smpp_port": 2776   # Port Kirim SMS (LAN)
    }
]

SYSTEM_ID = "test"
PASSWORD  = "test"

# =======================================================
#                    FUNGSI RADAR
# =======================================================
def scan_users():
    print("\n" + "="*60)
    print("           RADAR PENCARI PERANGKAT AKTIF")
    print("="*60)
    
    active_users = {} # Format: {'nomor_hp': config_tower}

    for tower in TOWERS:
        print(f"[*] Scanning {tower['nama']} ... ", end='', flush=True)
        try:
            tn = telnetlib.Telnet(tower['host'], tower['vty_port'], timeout=3)
            tn.read_until(b"> ", timeout=1)
            tn.write(b"enable\n")
            tn.read_until(b"# ", timeout=1)
            
            # Perintah sakti untuk melihat subscriber aktif
            tn.write(b"show subscriber cache\n")
            raw_output = tn.read_until(b"# ", timeout=3).decode('ascii')
            tn.close()

            # Ambil semua angka yang terlihat seperti Nomor HP
            # Kita cari angka 3-14 digit (bukan IMSI 15 digit)
            found = re.findall(r'\b\d{3,14}\b', raw_output)
            
            count = 0
            for num in found:
                # Filter angka sampah (port, id, dll)
                if num not in ['4254', '2775', '2776', '0'] and len(num) < 15:
                    active_users[num] = tower
                    count += 1
            
            if count > 0:
                print(f"\033[92m[FOUND {count}]\033[0m")
            else:
                print("\033[93m[KOSONG]\033[0m")

        except Exception as e:
            print(f"\033[91m[ERROR: {e}]\033[0m")

    return active_users

# =======================================================
#                  FUNGSI EKSEKUTOR
# =======================================================
def kirim_pesan(target_list, sender, text):
    print("\n" + "="*60)
    print("              MEMULAI BROADCAST SMS")
    print("="*60)

    # Kirim satu per satu sesuai lokasi tower-nya
    for number, tower in target_list.items():
        print(f"[*] Target: \033[96m{number}\033[0m (via {tower['nama']})")
        
        try:
            # 1. Konek ke SMPP Tower yang sesuai
            client = smpplib.client.Client(tower['host'], tower['smpp_port'])
            client.connect()
            client.bind_transmitter(system_id=SYSTEM_ID, password=PASSWORD)
            
            # 2. Encoding Pesan
            parts, encoding, flag = smpplib.gsm.make_parts(text)
            
            # 3. Tentukan Tipe Pengirim
            if sender.isdigit():
                ton = smpplib.consts.SMPP_TON_INTL
                npi = smpplib.consts.SMPP_NPI_ISDN
            else:
                sender = sender[:11] 
                ton = smpplib.consts.SMPP_TON_ALNUM
                npi = smpplib.consts.SMPP_NPI_UNK

            # 4. Tembak!
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
            
            print("    Status: \033[92m[TERKIRIM KE JARINGAN]\033[0m")
            client.unbind()
            client.disconnect()
            time.sleep(0.5) # Jeda sedikit biar aman

        except Exception as e:
            print(f"    Status: \033[91m[GAGAL: {e}]\033[0m")

# =======================================================
#                     MAIN MENU
# =======================================================
if __name__ == "__main__":
    targets = scan_users()
    
    if not targets:
        print("\n[!] Tidak ada perangkat yang terdeteksi online.")
        print("    Coba toggle Mode Pesawat di HP target lalu scan lagi.")
        sys.exit()

    print("\n" + "-"*60)
    print(f"Total Penerima: {len(targets)} Nomor")
    print("Daftar: " + ", ".join(targets.keys()))
    print("-"*60)

    pengirim = input("\nMasukkan Nama Pengirim : ") or "INFO-PUSAT"
    isi_pesan = input("Masukkan Isi Pesan     : ") or "Tes Broadcast Jaringan Dual PLMN"

    konfirmasi = input(f"Kirim pesan ini? [Y/n]: ")
    if konfirmasi.lower() != 'n':
        kirim_pesan(targets, pengirim, isi_pesan)
        print("\n[+] Selesai.")
    else:
        print("Dibatalkan.")
