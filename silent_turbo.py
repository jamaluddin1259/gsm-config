#!/usr/bin/env python3
import telnetlib
import time
import sys
from datetime import datetime

# --- KONFIGURASI HYPER ---
MSC_HOST = "127.0.0.1"
MSC_PORT = 4254
TARGET_MSISDN = "1001" 
DURASI_ON = 13.0  # Detik ke-13 matikan

def get_time():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def run_hyper_loop(target_msisdn):
    print(f"[*] [{get_time()}] HYPER MODE: ON")
    
    try:
        tn = telnetlib.Telnet(MSC_HOST, MSC_PORT, timeout=3)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")
        
        print(f"[+] [{get_time()}] Target: {target_msisdn}. Siap Spamming!")
        print("="*60)

        # START AWAL
        tn.write(f"subscriber msisdn {target_msisdn} silent-call start any speech-fr\n".encode('ascii'))
        tn.read_until(b"# ", timeout=1)

        while True:
            # 1. TAHAN SELAMA 13 DETIK
            # Kita pakai time.sleep murni biar CPU istirahat saat sinyal ON
            print(f"[{get_time()}] ➤ [ON] Menahan Sinyal {DURASI_ON}s...")
            time.sleep(DURASI_ON)

            # 2. PROSES RESET SUPER CEPAT
            # print(f"[{get_time()}] ↻ RECONNECTING...") # Print dimatikan biar lebih cepat
            
            # A. Kirim STOP
            tn.write(f"subscriber msisdn {target_msisdn} silent-call stop\n".encode('ascii'))
            
            # B. BACA RESPON STOP (Cepat)
            # Kita harus baca output biar buffer telnet kosong, tapi timeout super ketat
            tn.read_until(b"# ", timeout=0.1)

            # C. LOOPING START SAMPAI NYANTOL (Tanpa Sleep)
            # Ini kuncinya: Terus kirim START sampai diterima. 
            # Tidak ada jeda istirahat. Hardware dipaksa kerja.
            while True:
                tn.write(f"subscriber msisdn {target_msisdn} silent-call start any speech-fr\n".encode('ascii'))
                
                # Baca respon secepat mungkin
                output = tn.read_until(b"# ", timeout=0.1).decode('ascii')
                
                if "Success" in output:
                    # BERHASIL! Keluar dari loop reconnect, kembali ke loop utama (menahan 13 detik)
                    # print(f"[{get_time()}] ✓ Connected!") 
                    break 
                
                elif "busy" in output:
                    # Kalau busy, berarti perintah STOP tadi belum selesai diproses di radio.
                    # JANGAN SLEEP. Langsung coba lagi di putaran while berikutnya (milidetik).
                    pass
                
                else:
                    # Error lain, coba lagi terus.
                    pass

    except KeyboardInterrupt:
        print("\nSTOP.")
        try:
            tn.write(f"subscriber msisdn {target_msisdn} silent-call stop\n".encode('ascii'))
        except:
            pass
        tn.close()
        sys.exit()

if __name__ == "__main__":
    msisdn = sys.argv[1] if len(sys.argv) > 1 else TARGET_MSISDN
    run_hyper_loop(msisdn)
