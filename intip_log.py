#!/usr/bin/env python3
import telnetlib
import time
import sys

# KONFIGURASI
HOST = "127.0.0.1"
PORT = 4241

def spy_mode():
    print(f"[*] Menghubungkan ke BTS ({HOST}:{PORT})...")
    
    try:
        tn = telnetlib.Telnet(HOST, PORT, timeout=5)
        tn.read_until(b"> ")
        
        # KITA NYALAKAN SEMUA LAMPU SOROT
        commands = [
            b"enable\n",
            b"logging enable\n",
            b"logging filter all 1\n",
            b"logging level meas debug\n", # Cek pengukuran
            b"logging level rsl debug\n",  # Cek laporan HP (PENTING!)
            b"logging level lchan debug\n" # Cek kanal radio
        ]
        
        for cmd in commands:
            tn.write(cmd)
            time.sleep(0.1)
            
        print("[+] MODE MATA-MATA AKTIF! (Tekan Ctrl+C untuk stop)")
        print("="*60)
        
        while True:
            try:
                # BACA SEMUA TANPA FILTER
                line = tn.read_until(b"\n").decode('ascii', errors='ignore').strip()
                
                # Hanya print yang ada angkanya supaya tidak pusing
                if any(char.isdigit() for char in line):
                    print(line)
                    
            except KeyboardInterrupt:
                sys.exit()
            except Exception:
                continue

    except KeyboardInterrupt:
        print("\n[!] Berhenti.")
        sys.exit()

if __name__ == "__main__":
    spy_mode()
