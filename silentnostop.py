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

def eksekusi_tanpa_stop(msc, msisdn):
    print(f"\n[+] [{get_time()}] 🔥 MODE RAPID FIRE: Hanya START (Tanpa Stop) di {msc['nama']}...")
    print("="*60)
    
    try:
        tn = telnetlib.Telnet(msc['host'], msc['port'], timeout=5)
        tn.read_until(b"> ")
        tn.write(b"enable\n")
        tn.read_until(b"# ")

        # Loop Gila: Kirim START terus menerus
        while True:
            # Bersihkan buffer
            tn.read_very_eager()
            
            # 1. TEMBAK PERINTAH START
            cmd = f"subscriber msisdn {msisdn} silent-call start any speech-fr\n"
            tn.write(cmd.encode('ascii'))
            
            # 2. Baca Respon Cepat (Maks 1 detik)
            output = tn.read_until(b"# ", timeout=1).decode('ascii')

            # 3. Analisis Respon
            if "Success" in output:
                # INI MOMEN KUNCI: Artinya panggilan baru saja masuk!
                print(f"[{get_time()}] ⚡ NEW LOCK! (Sinyal Masuk)")
                # Kita beri napas dikit biar MSC gak keselek
                time.sleep(1) 
            
            elif "busy" in output or "active" in output:
                # Artinya panggilan lama MASIH JALAN.
                # Kita biarkan saja, jangan di-stop.
                # Cek lagi 2 detik kemudian.
                print(".", end='', flush=True)
                time.sleep(2)

            elif "failed" in output:
                 # Jika failed, berarti ada masalah serius (HP hilang/mati)
                 # Baru di sini kita terpaksa pindah tower
                 print(f"\n[{get_time()}] ❌ Target Hilang di {msc['nama']}.")
                 return False
            
            else:
                 time.sleep(1)

    except Exception as e:
        print(f"[!] Error: {e}")
        return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_MSISDN
    print(f"=== SILENT CALL: NO-STOP STRATEGY (Target: {target}) ===")

    while True:
        for msc in MSCS:
            try:
                # Ping Cepat
                tn = telnetlib.Telnet(msc['host'], msc['port'], timeout=1)
                tn.read_until(b"> ")
                tn.write(b"enable\n")
                tn.read_until(b"# ")
                tn.write(f"show subscriber msisdn {target}\n".encode('ascii'))
                res = tn.read_until(b"# ", timeout=1).decode('ascii')
                tn.close()

                if "IMSI" in res:
                    eksekusi_tanpa_stop(msc, target)
            except:
                pass
        
        time.sleep(2)
