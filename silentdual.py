#!/usr/bin/env python3
import telnetlib
import time
import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", category=DeprecationWarning)

TARGET_MSISDN = "1001" 
MSCS = [
    {"nama": "TOWER USB", "host": "127.0.0.1", "port": 4254},
    {"nama": "TOWER LAN", "host": "10.0.0.1",  "port": 4254}
]

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def eksekusi_silent_call(msc, msisdn):
    print(f"\n[+] [{get_time()}] 🎯 Mencoba Silent Call di {msc['nama']}...")
    print("="*60)

    try:
        tn = telnetlib.Telnet(msc['host'], msc['port'], timeout=5)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")

        # Loop Panggilan
        while True:
            # Bersihkan buffer dulu biar output bersih
            tn.read_very_eager()
            
            cmd = f"subscriber msisdn {msisdn} silent-call start any speech-fr\n"
            tn.write(cmd.encode('ascii'))
            
            # Baca respon pelan-pelan
            output = tn.read_until(b"# ", timeout=3).decode('ascii')

            if "Success" in output:
                print(f"[{get_time()}] \033[92m➤ SINYAL AKTIF! (OK)\033[0m")
                time.sleep(10) # Tahan sinyal 10 detik
            
            elif "busy" in output or "active" in output:
                print(f"[{get_time()}] . (Sinyal sedang memancar...)")
                time.sleep(5)

            elif "failed" in output or "Failure" in output:
                print(f"[{get_time()}] \033[91m⚠ GAGAL: Target tidak merespon di {msc['nama']}.\033[0m")
                tn.close()
                return False # RETURN FALSE AGAR PINDAH TOWER

            else:
                # Menangkap echo command (biasanya baris pertama output)
                lines = output.strip().splitlines()
                status = lines[-1] if lines else "Unknown"
                if "silent-call start" in status: status = "Mencoba menghubungkan..."
                print(f"[{get_time()}] ℹ Info: {status}")
                time.sleep(1)

    except Exception as e:
        print(f"[!] Error koneksi: {e}")
        return False

# --- MAIN LOGIC ---
if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_MSISDN
    print(f"=== SILENT CALLER ULTIMATE (Target: {target}) ===")

    try:
        while True:
            target_found = False
            
            # Loop cek semua tower
            for msc in MSCS:
                # Cek apakah subscriber ada di cache MSC ini
                try:
                    tn = telnetlib.Telnet(msc['host'], msc['port'], timeout=2)
                    tn.read_until(b"> ")
                    tn.write(b"enable\n")
                    tn.read_until(b"# ")
                    tn.write(f"show subscriber msisdn {target}\n".encode('ascii'))
                    res = tn.read_until(b"# ", timeout=2).decode('ascii')
                    tn.close()

                    if "IMSI" in res:
                        # Jika ada datanya, COBA SILENT CALL
                        result = eksekusi_silent_call(msc, target)
                        if result:
                            # Jika sukses loop selamanya di dalam fungsi eksekusi
                            pass 
                        else:
                            # Jika return False (Gagal), lanjut ke tower berikutnya
                            print(f"[*] Pindah mencari ke tower lain...\n")
                            continue
                except:
                    pass
            
            print(f"[{get_time()}] ⏳ Target tidak ditemukan/gagal di semua tower. Re-scan 3d...", end='\r')
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n[STOP] Selesai.")
