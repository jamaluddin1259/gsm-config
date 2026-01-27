#!/usr/bin/env python3
import telnetlib
import re
import sys
import time
import warnings
import smpplib.gsm
import smpplib.client
import smpplib.consts

# Matikan warning deprecation agar tampilan bersih
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ==========================================
#        KONFIGURASI DUAL TOWER
# ==========================================
# Kita sesuaikan dengan hasil NETSTAT Mas Jamal:
# VTY Port  : 4254 (Untuk Cek Online)
# SMPP Port : 2775 (USB) & 2776 (LAN) (Untuk Kirim SMS)

TOWERS = [
    {
        "nama": "TOWER USB (PLMN A)",
        "host": "127.0.0.1",
        "vty_port": 4254,   # Port Intip User
        "smpp_port": 2775   # Port Kirim SMS USB
    },
    {
        "nama": "TOWER LAN (AntsDR)",
        "host": "10.0.0.1",
        "vty_port": 4254,   # Port Intip User
        "smpp_port": 2776   # Port Kirim SMS LAN
    }
]

SYSTEM_ID = "test"
PASSWORD  = "test"

# ==========================================
#              LOGIKA SCANNING
# ==========================================
def scan_network():
    print(f"[*] Memulai Radar Scanning pada {len(TOWERS)} Tower...")
    
    # Dictionary untuk menyimpan target: { 'nomor_hp': config_tower }
    target_map = {} 

    for tower in TOWERS:
        print(f"    -> Scanning {tower['nama']} ({tower['host']}:{tower['vty_port']})... ", end='', flush=True)
        try:
            tn = telnetlib.Telnet(tower['host'], tower['vty_port'], timeout=3)
            tn.read_until(b"> ", timeout=1)
            tn.write(b"enable\n")
            tn.read_until(b"# ", timeout=1)
            
            # Ambil data subscriber
            tn.write(b"show subscriber cache\n")
            raw_output = tn.read_until(b"# ", timeout=3).decode('ascii')
            tn.close()

            # Parsing Nomor HP
            # Pola 1: Format standar Osmo "MSISDN: 12345"
            found = re.findall(r'MSISDN:?\s*(\d+)', raw_output, re.IGNORECASE)
            
            # Pola 2: Format tabel (biasanya kolom kedua/ketiga)
            # Ambil angka 3-14 digit yang berdiri sendiri
            raw_digits = re.findall(r'\b\d{3,14}\b', raw_output)
            candidates = found + raw_digits
            
            count_tower = 0
            for num in candidates:
                # Filter angka sampah (port, id, imsi panjang)
                if num not in ['4254', '2775', '2776', '0'] and len(num) >= 3 and len(num) < 15:
                    if num not in target_map:
                        target_map[num] = tower # Simpan info tower untuk nomor ini
                        count_tower += 1
            
            if count_tower > 0:
                print(f"\033[92m[DAPAT {count_tower} NOMOR]\033[0m")
            else:
                print("\033[93m[KOSONG]\033[0m")
                
        except Exception as e:
            print(f"\033[91m[ERROR: {e}]\033[0m")

    return target_map

# ==========================================
#              LOGIKA PENGIRIMAN
# ==========================================
def kirim_broadcast(target_map, sender, message):
    if not target_map:
        return

    print("\n" + "="*60)
    print("       MEMULAI PENGIRIMAN SMS (SMART ROUTING)")
    print("="*60)

    # Kelompokkan nomor berdasarkan Tower SMPP-nya agar efisien
    # Format: { '2775': ['081', '082'], '2776': ['083'] }
    grouped_targets = {}
    for num, tower_conf in target_map.items():
        port = tower_conf['smpp_port']
        host = tower_conf['host']
        key = (host, port) # Jadikan (IP, Port) sebagai kunci
        
        if key not in grouped_targets:
            grouped_targets[key] = []
        grouped_targets[key].append(num)

    # Loop per Tower (Konek sekali, kirim banyak)
    for (host, port), numbers in grouped_targets.items():
        print(f"\n[*] Menghubungkan ke SMPP {host}:{port} ...")
        
        try:
            client = smpplib.client.Client(host, port)
            client.connect()
            client.bind_transmitter(system_id=SYSTEM_ID, password=PASSWORD)
            
            # Setup Encoding
            parts, encoding, flag = smpplib.gsm.make_parts(message)
            
            # Tentukan Tipe Pengirim
            if sender.isdigit():
                ton = smpplib.consts.SMPP_TON_INTL
                npi = smpplib.consts.SMPP_NPI_ISDN
            else:
                sender = sender[:11] # Max 11 char for alphanum
                ton = smpplib.consts.SMPP_TON_ALNUM
                npi = smpplib.consts.SMPP_NPI_UNK

            for num in numbers:
                print(f"    -> Mengirim ke \033[96m{num}\033[0m ... ", end='')
                try:
                    for part in parts:
                        client.send_message(
                            source_addr_ton=ton,
                            source_addr_npi=npi,
                            source_addr=sender,
                            dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
                            dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                            destination_addr=num,
                            short_message=part,
                            data_coding=encoding,
                            esm_class=flag,
                            registered_delivery=False,
                        )
                    print("\033[92m[SUKSES]\033[0m")
                except Exception as e:
                    print(f"\033[91m[GAGAL: {e}]\033[0m")
                time.sleep(0.1)

            client.unbind()
            client.disconnect()
            
        except Exception as e:
            print(f"[!] Gagal konek SMPP {host}:{port} -> {e}")

# ==========================================
#               MAIN PROGRAM
# ==========================================
if __name__ == "__main__":
    print("\n=== DUAL-PLMN BROADCAST SYSTEM ===")
    
    # 1. Scan Otomatis
    hasil_scan = scan_network()
    
    daftar_nomor = list(hasil_scan.keys())
    
    if not daftar_nomor:
        print("\n[!] Tidak ada user online di kedua tower.")
        sys.exit(0)

    print("-" * 50)
    print(f"Total Target: {len(daftar_nomor)} Nomor")
    print(f"List: {', '.join(daftar_nomor)}")
    print("-" * 50)

    # 2. Input Pesan
    pengirim = input("Pengirim (Nama/Angka): ") or "INFO"
    pesan = input("Isi Pesan: ") or "Tes Broadcast Jaringan"
    
    print("\n")
    if input("Lanjutkan kirim? [Y/n]: ").lower() != 'n':
        kirim_broadcast(hasil_scan, pengirim, pesan)
        print("\n[+] Selesai.")
    else:
        print("Dibatalkan.")
