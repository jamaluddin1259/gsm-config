#!/usr/bin/env python3
import telnetlib
import time
import sys
from datetime import datetime

# --- KONFIGURASI ---
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254
TARGET_MSISDN = "1001" 

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def loop_silent_call(target_msisdn):
    print(f"[*] [{get_time()}] Menghubungkan ke MSC...")
    
    try:
        tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=5)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")
        
        print(f"[+] [{get_time()}] Mode: SPEECH-FR (Deteksi Alat Aktif)")
        print(f"[*] Target: {target_msisdn}")
        print("="*60)

        while True:
            # 1. Kirim perintah Start dengan mode Suara (Speech)
            # Ini yang bikin alat Anda berbunyi/mendeteksi trafik
            cmd_start = f"subscriber msisdn {target_msisdn} silent-call start any speech-fr\n"
            tn.write(cmd_start.encode('ascii'))
            
            # Baca respon
            output = tn.read_until(b"# ", timeout=1.0).decode('ascii')
            
            if "Success" in output:
                print(f"[{get_time()}] ➤ SINYAL SUARA AKTIF! (Cek Alat Anda)")
                # Beri waktu 10-15 detik agar sinyal stabil terpancar sebelum cek lagi
                time.sleep(10) 
                
            elif "busy" in output or "active" in output:
                # Jika masih aktif, jangan diganggu. Tidur sebentar.
                time.sleep(5) 
                
            else:
                # Jika mati/error (Log: MS not responding, dsb)
                print(f"[{get_time()}] ⚠ Sinyal Hilang. Membersihkan Kanal...")
                
                # WAJIB: Kirim STOP untuk reset status di MSC/BSC
                tn.write(f"subscriber msisdn {target_msisdn} silent-call stop\n".encode('ascii'))
                tn.read_until(b"# ", timeout=0.5)
                
                # Jeda istirahat agar hardware AntsDR tidak overload (penting!)
                time.sleep(2)
                
                print(f"[{get_time()}] ↻ Mencoba Sambung Ulang...")

    except KeyboardInterrupt:
        print(f"\n[{get_time()}] STOP.")
        tn.close()
        sys.exit()
    except Exception as e:
        print(f"\n[!] Error: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_MSISDN
    loop_silent_call(target)
