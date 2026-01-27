#!/usr/bin/env python3
import telnetlib
import re
import time
import sys

# --- KONFIGURASI ---
HOST = "127.0.0.1"
PORT = 4241

def konversi_rxlev(rxlev):
    try:
        val = int(rxlev)
        return -110 + val
    except:
        return -110

def monitor_debug():
    print(f"[*] Menghubungkan ke BTS ({HOST}:{PORT})...")
    
    try:
        tn = telnetlib.Telnet(HOST, PORT, timeout=5)
        tn.read_until(b"> ")
        
        # KITA UBAH LEVEL LOG JADI DEBUG (Lebih Cerewet)
        commands = [
            b"enable\n",
            b"logging enable\n",
            b"logging filter all 1\n",
            b"logging level meas debug\n",  # <-- KUNCI RAHASIANYA DISINI
            b"logging level rsl info\n"
        ]
        
        for cmd in commands:
            tn.write(cmd)
            time.sleep(0.1)
            
        print("[+] Mode DEBUG Aktif! Menunggu data sinyal...")
        print("="*70)
        
        last_ul = "..."
        last_dl = "..."
        
        while True:
            try:
                line = tn.read_until(b"\n").decode('ascii', errors='ignore').strip()
                
                # 1. TANGKAP UPLINK (Sinyal HP diterima Tower)
                if "RSSI-SUB" in line:
                    match_ul = re.search(r'RSSI-SUB\((.*?)dBm\)', line)
                    if match_ul:
                        raw_ul = match_ul.group(1).replace(' ', '')
                        last_ul = f"{raw_ul} dBm"

                # 2. TANGKAP DOWNLINK (Sinyal Tower diterima HP)
                # Kita cari baris yang ada 'rxlev' tapi BUKAN 'UL MEAS' (milik Uplink)
                if "rxlev" in line.lower() and "UL MEAS" not in line:
                    
                    # Coba baca format standar: "rxlev_full=60" atau "rxlev: 60"
                    match_dl = re.search(r'rxlev[a-z_]*[=:]\s*(\d+)', line.lower())
                    
                    if match_dl:
                        rxlev_val = match_dl.group(1)
                        dbm_val = konversi_rxlev(rxlev_val)
                        last_dl = f"{dbm_val} dBm"
                    else:
                        # JIKA FORMATNYA ANEH, TAMPILKAN MENTAHNYA (Untuk Diagosa)
                        # Ini supaya kita tahu format aslinya seperti apa
                        print(f"\n[?] FORMAT ASING: {line}\n")

                # TAMPILKAN MONITOR
                print(f"\r UPLINK: {last_ul}   <==>   DOWNLINK: {last_dl}      ", end="", flush=True)

            except EOFError:
                break
            except Exception:
                continue

    except KeyboardInterrupt:
        print("\n\n[!] Monitoring berhenti.")
        sys.exit()

if __name__ == "__main__":
    monitor_debug()
