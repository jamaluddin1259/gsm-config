#!/usr/bin/env python3
import telnetlib
import re
import time
import sys

# --- KONFIGURASI ---
HOST = "127.0.0.1"
PORT = 4241

def konversi_rxlev(rxlev):
    """Mengubah RxLev (0-63) menjadi dBm"""
    try:
        val = int(rxlev)
        # Rumus: -110 + nilai rxlev
        # Contoh: Jika 63 (max), maka -110 + 63 = -47 dBm (Sangat Kuat)
        return -110 + val
    except:
        return -110

def bikin_bar(dbm):
    """Visualisasi Bar Sinyal"""
    try:
        val = int(dbm)
        if val > -60: return "[#####] (Sempurna)"
        elif val > -75: return "[####_] (Bagus)"
        elif val > -85: return "[###__] (Sedang)"
        elif val > -95: return "[##___] (Lemah)"
        else: return "[#____] (Kritis)"
    except:
        return "[.....]"

def monitor_ultimate():
    print(f"[*] Menghubungkan ke BTS ({HOST}:{PORT})...")
    
    try:
        tn = telnetlib.Telnet(HOST, PORT, timeout=5)
        tn.read_until(b"> ")
        
        # AKTIFKAN PENCATATAN (Sesuai temuan di foto)
        commands = [
            b"enable\n",
            b"logging enable\n",
            b"logging filter all 1\n",
            b"logging level meas info\n", 
            b"logging level rsl debug\n"  # Kita butuh level DEBUG untuk lihat 'Send Meas RES'
        ]
        
        for cmd in commands:
            tn.write(cmd)
            time.sleep(0.1)
            
        print("[+] Sukses! Monitoring ULTIMATE aktif...")
        print("="*75)
        print(" UPLINK (HP->BTS)   |   DOWNLINK (BTS->HP)")
        print("="*75)
        
        last_ul_str = "Menunggu..."
        last_dl_str = "Menunggu..."
        
        while True:
            try:
                line = tn.read_until(b"\n").decode('ascii', errors='ignore').strip()
                
                # --- 1. TANGKAP UPLINK (Sinyal HP didengar Tower) ---
                # Pola: RSSI-SUB(- 45dBm)
                if "RSSI-SUB" in line:
                    match_ul = re.search(r'RSSI-SUB\((.*?)dBm\)', line)
                    if match_ul:
                        raw_ul = match_ul.group(1).replace(' ', '')
                        bar_ul = bikin_bar(raw_ul)
                        last_ul_str = f"{raw_ul} dBm {bar_ul}"

                # --- 2. TANGKAP DOWNLINK (Sinyal Tower didengar HP) ---
                # Pola Baru (Sesuai Foto): RXLEV_FULL:63
                # Kita cari baris yang ada 'Send Meas RES' agar akurat
                if "Send Meas RES" in line:
                    match_dl = re.search(r'RXLEV_FULL:(\d+)', line)
                    if match_dl:
                        val_rxlev = match_dl.group(1)
                        val_dbm = konversi_rxlev(val_rxlev)
                        bar_dl = bikin_bar(val_dbm)
                        last_dl_str = f"{val_dbm} dBm {bar_dl}"

                # TAMPILKAN HASIL (Rata Kiri Kanan)
                print(f"\r {last_ul_str:<35} | {last_dl_str}", end="", flush=True)

            except EOFError:
                break
            except Exception:
                continue

    except KeyboardInterrupt:
        print("\n\n[!] Monitoring berhenti.")
        sys.exit()

if __name__ == "__main__":
    monitor_ultimate()
