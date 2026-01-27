#!/usr/bin/env python3
import telnetlib
import time

# --- KONFIGURASI ---
HOST = "127.0.0.1"
PORT = 4254  # Port MSC untuk SMS
DAFTAR_NOMOR = ["1001", "1003"]  # Masukkan semua nomor target di sini
PESAN = "PENGUMUMAN: Server GSM sedang online. Harap lapor jika terima pesan ini."
# -------------------

def kirim_sms():
    try:
        print(f"[*] Menghubungkan ke MSC ({HOST}:{PORT})...")
        tn = telnetlib.Telnet(HOST, PORT)

        # 1. Tunggu prompt awal (OsmoMSC>)
        tn.read_until(b"> ")
        
        # 2. Masuk mode Enable (agar bisa kirim SMS)
        tn.write(b"enable\n")
        tn.read_until(b"# ")
        print("[+] Berhasil login ke MSC.")

        # 3. Looping kirim ke semua nomor
        for nomor in DAFTAR_NOMOR:
            print(f" -> Mengirim SMS ke {nomor}...")
            
            # Format perintah: subscriber msisdn <NOMOR> sms <PESAN>
            perintah = f"subscriber msisdn {nomor} sms {PESAN}\n"
            tn.write(perintah.encode('ascii'))
            
            # Beri jeda 1 detik agar tidak spamming error
            time.sleep(1)

        print("[*] Selesai! Semua pesan telah dikirim.")
        tn.write(b"exit\n")
        tn.close()

    except ConnectionRefusedError:
        print("[!] GAGAL: Tidak bisa connect ke MSC.")
        print("    Pastikan 'osmo-msc' sudah berjalan!")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    kirim_sms()
