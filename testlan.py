#!/usr/bin/env python3
import smpplib.gsm
import smpplib.client
import smpplib.consts
import time

# --- KONFIGURASI KERAS (HARDCODED) ---
# Kita paksa tembak ke MSC LAN
IP_TARGET   = "10.0.0.1"
PORT_TARGET = 2776       # Port SMPP LAN
SYSTEM_ID   = "test"
PASSWORD    = "test"

def kirim_paksa():
    print("="*50)
    print("      TEST SMS MANUAL - JALUR LAN")
    print(f"      Target: {IP_TARGET}:{PORT_TARGET}")
    print("="*50)

    # Input Nomor Manual
    nomor_hp = input("Masukkan Nomor HP Target (yg ada di AntsDR): ")
    isi_pesan = "Tes Tembak Langsung LAN"

    try:
        # 1. Konek
        print(f"\n[*] Menghubungkan ke {IP_TARGET}...")
        client = smpplib.client.Client(IP_TARGET, PORT_TARGET)
        client.connect()
        client.bind_transmitter(system_id=SYSTEM_ID, password=PASSWORD)
        print("[+] Login SMPP Berhasil!")

        # 2. Siapkan Pesan
        parts, encoding, flag = smpplib.gsm.make_parts(isi_pesan)

        # 3. Kirim
        print(f"[*] Mengirim ke {nomor_hp}...")
        for part in parts:
            client.send_message(
                source_addr_ton=smpplib.consts.SMPP_TON_ALNUM,
                source_addr_npi=smpplib.consts.SMPP_NPI_UNK,
                source_addr="ADMIN",
                dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
                dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                destination_addr=nomor_hp,
                short_message=part,
                data_coding=encoding,
                esm_class=flag,
                registered_delivery=False,
            )
        
        print("\n\033[92m[SUKSES TERKIRIM DARI SISI PYTHON]\033[0m")
        print("Silakan cek layar HP dan Log MSC LAN.")
        
        time.sleep(1)
        client.unbind()
        client.disconnect()

    except Exception as e:
        print(f"\n\033[91m[GAGAL ERROR]: {e}\033[0m")

if __name__ == "__main__":
    kirim_paksa()
