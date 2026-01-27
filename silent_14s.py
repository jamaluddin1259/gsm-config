#!/usr/bin/env python3
import telnetlib
import time
import sys
from datetime import datetime

# --- KONFIGURASI ---
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254
TARGET_MSISDN = "1001" 
DURASI_TAHAN = 14.0  # Menahan sinyal selama 14 detik pas

def get_time():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def run_fast_reconnect(target_msisdn):
    print(f"[*] [{get_time()}] Menghubungkan ke MSC...")
    
    try:
        # Buka Koneksi Telnet
        tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=3)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")
        
        print(f"[+] [{get_time()}] Target: {target_msisdn}")
        print(f"[-] Mode: Tahan {DURASI_TAHAN} Detik -> Reconnect Kilat")
        print("="*60)

        # Pancingan Awal (Start Pertama)
        tn.write(f"subscriber msisdn {target_msisdn} silent-call start any speech-fr\n".encode('ascii'))
        tn.read_until(b"# ", timeout=1)

        while True:
            # 1. TAHAN SINYAL (HOLD)
            # Biarkan sinyal memancar stabil selama 14 detik
            print(f"[{get_time()}] ➤ [ON] Memancar {DURASI_TAHAN}s...")
            time.sleep(DURASI_TAHAN)

            # 2. PUTUS & SAMBUNG (ZERO DELAY LOGIC)
            # print(f"[{get_time()}] ⚡ Refreshing...")
            
            # A. Kirim Perintah STOP
            tn.write(f"subscriber msisdn {target_msisdn} silent-call stop\n".encode('ascii'))
            
            # B. Baca respon STOP (Cepat, 0.1s max)
            # Kita cuma butuh memastikan buffer kosong, gak perlu nunggu lama
            tn.read_until(b"# ", timeout=0.1)

            # C. SPAM START SAMPAI NYANTOL
            # Terus kirim perintah START tanpa jeda tidur (sleep)
            while True:
                tn.write(f"subscriber msisdn {target_msisdn} silent-call start any speech-fr\n".encode('ascii'))
                
                # Baca output secepat mungkin
                output = tn.read_until(b"# ", timeout=0.1).decode('ascii')
                
                if "Success" in output:
                    # Sukses nyambung lagi! Keluar dari loop spam, balik ke loop tahan
                    break 
                
                # Jika output "busy" atau kosong, loop akan otomatis ulang seketika
                # Tidak ada 'else' atau 'sleep' di sini agar brutal

    except KeyboardInterrupt:
        print(f"\n[{get_time()}] STOP.")
        try:
            tn.write(f"subscriber msisdn {target_msisdn} silent-call stop\n".encode('ascii'))
        except:
            pass
        tn.close()
        sys.exit()

if __name__ == "__main__":
    msisdn = sys.argv[1] if len(sys.argv) > 1 else TARGET_MSISDN
    run_fast_reconnect(msisdn)
