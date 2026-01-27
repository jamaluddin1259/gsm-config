#!/usr/bin/env python3
import os
import time
import subprocess
import sys
import re

# ==========================================
#          KONFIGURASI SYSTEM
# ==========================================
LOG_DIR = "logs_gsm"

# --- TIMING (OPTIMIZED) ---
DELAY_CORE  = 10  # Jeda antar komponen Core
DELAY_FINAL = 5   # Jeda sebelum final

def print_step(message):
    print(f"\033[92m[+] {message}\033[0m")

def print_warn(message):
    print(f"\033[93m[!] {message}\033[0m")

def print_error(message):
    print(f"\033[91m[X] {message}\033[0m")

def get_user_input(prompt, default_val):
    user_val = input(f"   {prompt} [\033[96m{default_val}\033[0m]: ")
    if user_val.strip() == "":
        return default_val
    return user_val.strip()

def enable_performance_mode():
    """
    Mengaktifkan Mode POWERFUL untuk CPU dan USB
    agar sinkronisasi radio tidak putus-putus.
    """
    print("\n" + "="*50)
    print("   AKTIVASI HARDWARE: PERFORMANCE MODE")
    print("="*50)
    
    try:
        # 1. CPU ke Performance Mode
        print_step("Set CPU Governor -> Performance")
        os.system("echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null")
        
        # 2. Matikan USB Autosuspend (Global)
        print_step("Disable USB Autosuspend (Kernel)")
        os.system("echo -1 | tee /sys/module/usbcore/parameters/autosuspend > /dev/null")
        
        # 3. Paksa USB Port ON (Individual)
        print_step("Force USB Ports -> Always ON")
        # Menggunakan shell=True agar wildcard (*) terbaca
        subprocess.run("for i in /sys/bus/usb/devices/*/power/control; do echo on > $i; done", shell=True)
        
        print("   [OK] Hardware siap tempur!")
    except Exception as e:
        print_error(f"Gagal set performance: {e}")

def update_config_file(filepath, pattern_regex, new_value):
    if not os.path.exists(filepath):
        print_error(f"File config tidak ditemukan: {filepath}")
        return

    with open(filepath, 'r') as f:
        content = f.read()

    new_content, count = re.subn(pattern_regex, new_value, content, flags=re.MULTILINE)

    if count > 0:
        with open(filepath, 'w') as f:
            f.write(new_content)
    else:
        pass

def apply_gsm_settings(mcc, mnc, lac, cid, band, arfcn):
    print_step(f"Menerapkan Config: MCC={mcc} MNC={mnc} ARFCN={arfcn}...")

    # PERBAIKAN: Menggunakan rf"..." agar kompatibel Python 3.12+
    # 1. Identitas
    update_config_file("osmo-bsc.cfg", r"(^\s*network country code\s+)\d+", rf"\g<1>{mcc}")
    update_config_file("osmo-bsc.cfg", r"(^\s*mobile network code\s+)\d+", rf"\g<1>{mnc}")
    update_config_file("osmo-bsc.cfg", r"(^\s*location_area_code\s+)\d+", rf"\g<1>{lac}")
    update_config_file("osmo-bsc.cfg", r"(^\s*cell_identity\s+)\d+", rf"\g<1>{cid}")
    
    update_config_file("osmo-msc.cfg", r"(^\s*network country code\s+)\d+", rf"\g<1>{mcc}")
    update_config_file("osmo-msc.cfg", r"(^\s*mobile network code\s+)\d+", rf"\g<1>{mnc}")

    # 2. Frekuensi
    update_config_file("osmo-bsc.cfg", r"(^\s*band\s+)[A-Z0-9]+", rf"\g<1>{band}")
    update_config_file("osmo-bsc.cfg", r"(^\s*arfcn\s+)\d+", rf"\g<1>{arfcn}")
    update_config_file("osmo-bts-trx.cfg", r"(^\s*band\s+)[A-Z0-9]+", rf"\g<1>{band}")
    # Update ARFCN di BTS juga jika ada
    update_config_file("osmo-bts-trx.cfg", r"(^\s*arfcn\s+)\d+", rf"\g<1>{arfcn}")

def run_background(command_list, log_name):
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    log_path = os.path.join(LOG_DIR, f"{log_name}.log")
    with open(log_path, "w") as f:
        # Menggunakan 'nice -n -5' agar prioritas proses tinggi
        cmd_with_priority = ["nice", "-n", "-5"] + command_list
        subprocess.Popen(cmd_with_priority, stdout=f, stderr=subprocess.STDOUT)
    print(f"    -> {log_name} berjalan (Log: {log_path})")

def countdown(seconds, message):
    for i in range(seconds, 0, -1):
        print(f"    {message} {i} detik...    ", end="\r")
        time.sleep(1)
    print(" " * 60, end="\r") 

def main():
    if os.geteuid() != 0:
        print("ERROR: Jalankan dengan SUDO!")
        print("Usage: sudo python3 start_gsm_turbo.py")
        sys.exit(1)

    print("==========================================")
    print("   GSM NETWORK LAUNCHER (TURBO MODE)")
    print("==========================================")

    # --- INPUT USER ---
    try:
        my_mcc   = get_user_input("MCC (Negara)", "510")
        my_mnc   = get_user_input("MNC (Operator)", "01")
        my_lac   = get_user_input("LAC (Area)", "1000")
        my_cid   = get_user_input("CID (Cell ID)", "2000")
        my_band  = get_user_input("BAND (GSM900/DCS1800)", "DCS1800")
        my_arfcn = get_user_input("ARFCN (Channel)", "875")
    except KeyboardInterrupt:
        sys.exit(0)

    print("\n------------------------------------------")
    print(f"Konfigurasi: {my_band} (ARFCN {my_arfcn}) | PLMN {my_mcc}-{my_mnc}")
    print("------------------------------------------")
    
    confirm = input("Lanjut jalankan server? [Y/n]: ")
    if confirm.lower() == 'n':
        print("Dibatalkan.")
        sys.exit(0)

    # 1. AKTIVASI MODE POWERFUL (Wajib di awal)
    enable_performance_mode()

    # 2. PERSIAPAN BERSIH-BERSIH
    print_warn("Membersihkan proses lama & Tuning Kernel...")
    os.system("killall -9 osmo-stp osmo-msc osmo-hlr osmo-mgw osmo-bsc osmo-trx-uhd osmo-bts-trx osmo-pcu > /dev/null 2>&1")
    os.system("rm -f /tmp/pcu_bts /tmp/osmocom_*")
    
    # Tuning Buffer TCP/IP agar tidak bottleneck
    os.system("sysctl -w net.core.rmem_max=50000000 > /dev/null")
    os.system("sysctl -w net.core.wmem_max=50000000 > /dev/null")
    
    apply_gsm_settings(my_mcc, my_mnc, my_lac, my_cid, my_band, my_arfcn)
    time.sleep(1)

    print("\n" + "="*50)
    print("   MEMULAI EKSEKUSI (ANTENA DULUAN -> CORE)")
    print("="*50)

    # 3. START ANTENA (TRX) - PRIORITY REALTIME
    print_step("Menyalakan DRIVER ANTENA (TRX)...")
    # chrt -f 99 membuat proses ini menjadi Real Time Priority (Sangat Penting)
    run_background(["chrt", "-f", "99", "osmo-trx-uhd", "-C", "osmo-trx-uhd.cfg"], "trx")
    print("    (Antena sedang warming up...)")
    
    # 4. START CORE NETWORK
    print_step("Menyalakan STP (Signaling)...")
    run_background(["osmo-stp", "-c", "osmo-stp.cfg"], "stp")
    countdown(DELAY_CORE, "Menunggu STP stabil:")

    print_step("Menyalakan HLR (Database)...")
    run_background(["osmo-hlr", "-c", "osmo-hlr.cfg"], "hlr")
    countdown(DELAY_CORE, "Menunggu HLR stabil:")

    print_step("Menyalakan MSC (Switching)...")
    run_background(["osmo-msc", "-c", "osmo-msc.cfg"], "msc")
    countdown(DELAY_CORE, "Menunggu MSC stabil:")

    print_step("Menyalakan MGW (Media Gateway)...")
    run_background(["osmo-mgw", "-c", "osmo-mgw.cfg"], "mgw")
    countdown(DELAY_CORE, "Menunggu MGW stabil:")
    
    print_step("Menyalakan BSC (Controller)...")
    run_background(["osmo-bsc", "-c", "osmo-bsc.cfg"], "bsc")
    countdown(DELAY_CORE, "Menunggu BSC connect ke MSC:")

    # 5. START BTS (TERAKHIR)
    print_step("Menyalakan BTS (Radio Unit)...")
    # BTS juga kita kasih prioritas tinggi
    run_background(["chrt", "-f", "50", "osmo-bts-trx", "-c", "osmo-bts-trx.cfg"], "bts")
    
    countdown(DELAY_FINAL, "Finalisasi System:")

    print("\n" + "="*40)
    print("STATUS: SEMUA SERVICE BERJALAN (PERFORMANCE MODE).")
    print("Cek Log Realtime: tail -f logs_gsm/bts.log")
    print("==========================================")

if __name__ == "__main__":
    main()
