#!/usr/bin/env python3
import smpplib.gsm
import smpplib.client
import smpplib.consts
import sys

# --- KONFIGURASI SMPP (Sesuai osmo-msc.cfg) ---
IP = '127.0.0.1'
PORT = 2775
SYSTEM_ID = 'test'
PASSWORD = 'test'

def send_sms(target_number, sender_name, text_message):
    print(f"[*] Menghubungkan ke SMSC ({IP}:{PORT})...")
    
    # 1. Koneksi ke MSC
    client = smpplib.client.Client(IP, PORT)
    
    # 2. Login (Bind)
    try:
        client.connect()
        client.bind_transmitter(system_id=SYSTEM_ID, password=PASSWORD)
        print("[+] Login SMPP Berhasil!")
    except Exception as e:
        print(f"[!] Gagal Login SMPP: {e}")
        return

    # 3. Encoding Pesan
    # Kita pakai encoding default GSM 7-bit agar kompatibel semua HP
    parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(text_message)

    print(f"[*] Mengirim '{text_message}' dari '{sender_name}' ke '{target_number}'...")

    # 4. Kirim Pesan
    try:
        for part in parts:
            pdu = client.send_message(
                source_addr_ton=smpplib.consts.SMPP_TON_ALNUM, # Penting: ALPHANUMERIC
                source_addr_npi=smpplib.consts.SMPP_NPI_UNK,
                source_addr=sender_name,
                
                dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
                dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
                destination_addr=target_number,
                
                short_message=part,
                data_coding=encoding_flag,
                esm_class=msg_type_flag,
                registered_delivery=True,
            )
            # print(f"    -> PDU Terkirim (ID: {pdu.message_id})")
        
        print("[+] SUKSES! Pesan telah dikirim ke jaringan.")

    except Exception as e:
        print(f"[!] Error Pengiriman: {e}")
    finally:
        client.unbind()
        client.disconnect()

if __name__ == "__main__":
    print("=========================================")
    print("   SMPP BROADCAST TOOL (ALPHANUMERIC)")
    print("=========================================")
    
    if len(sys.argv) < 4:
        # Mode Interaktif
        tgt = input("Nomor Target (Contoh: 1001): ")
        snd = input("Nama Pengirim (Max 11 Huruf): ")
        msg = input("Isi Pesan: ")
    else:
        # Mode Command Line (Bisa dipanggil skrip lain)
        tgt = sys.argv[1]
        snd = sys.argv[2]
        msg = " ".join(sys.argv[3:])

    # Validasi Nama
    if len(snd) > 11:
        print("[!] Warning: Nama dipotong jadi 11 karakter!")
        snd = snd[:11]
    
    send_sms(tgt, snd, msg)
