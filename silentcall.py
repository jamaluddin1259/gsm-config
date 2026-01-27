#!/usr/bin/env python3
import telnetlib
import time
import sys

# --- KONFIGURASI ---
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254  # Port Telnet OsmoMSC

def loop_silent_call(target_msisdn):
    print(f"[*] Menghubungkan ke MSC ({MSC_HOST}:{MSC_PORT})...")
    
    try:
        # Masuk ke Telnet
        tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=5)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")
        
        print(f"[+] Terhubung! Memulai Auto-Reconnect Silent Call ke: {target_msisdn}")
        print("="*50)
        print("   TEKAN CTRL+C UNTUK BERHENTI (STOP)")
        print("="*50)

        counter = 1
        while True:
            # Kirim Perintah Silent Call
            # Format: subscriber msisdn [NOMOR] silent-call start
            cmd = f"subscriber msisdn {target_msisdn} silent-call start any speech-fr\n"
            tn.write(cmd.encode('ascii'))
            
            # Baca respon dari MSC (biar buffer tidak penuh)
            # Kita set timeout cepat (0.5 detik) karena kita buru-buru
            output = tn.read_until(b"# ", timeout=0.5).decode('ascii')
            
            # Cek status sederhana
            if "Success" in output:
                print(f"[{counter}] RE-DIALING... (Panggilan Baru Dimulai)")
            elif "busy" in output or "active" in output:
                # Jika MSC bilang sibuk, berarti panggilan msh jalan. Kita diam aja.
                # print(f"[{counter}] Masih Nyambung...", end='\r')
                pass
            else:
                # Respon lain (mungkin error atau putus)
                print(f"[{counter}] Memastikan sambungan...")
            
            counter += 1
            
            # TUNGGU SEBENTAR
            # Jeda ini penting. Jika terlalu cepat, CPU naik. 
            # Jika terlalu lama, ada jeda kosong saat putus.
            # 3 detik adalah angka ideal.
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n\n[!] DIBERHENTIKAN OLEH USER (CTRL+C).")
        print("[*] Mematikan panggilan terakhir...")
        
        # Kirim perintah STOP bersih-bersih sebelum keluar
        try:
            tn.write(f"subscriber msisdn {target_msisdn} silent-call stop\n".encode('ascii'))
            time.sleep(1)
        except:
            pass
            
        tn.close()
        print("[+] Selesai. Bye!")
        sys.exit()

    except Exception as e:
        print(f"\n[!] Error Koneksi: {e}")
        print("    Pastikan osmo-msc jalan!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Cara Pakai: python3 auto_silent_call.py <NOMOR_HP>")
        print("Contoh    : python3 auto_silent_call.py 88888")
        sys.exit(1)
        
    target = sys.argv[1]
    loop_silent_call(target)
