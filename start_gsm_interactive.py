import os
import time
import subprocess
import sys
import re

# ==========================================
#         KONFIGURASI SYSTEM
# ==========================================
LOG_DIR = "logs_gsm"

# --- TIMING (SESUAI PERMINTAAN) ---
DELAY_CORE  = 10  # Jeda antar komponen Core (STP, HLR, MSC, dll)
DELAY_FINAL = 5   # Jeda singkat setelah BTS

def print_step(message):
    print(f"\033[92m[+] {message}\033[0m")

def print_warn(message):
    print(f"\033[93m[!] {message}\033[0m")

def print_error(message):
    print(f"\033[91m[X] {message}\033[0m")

def get_user_input(prompt, default_val):
    """
    Meminta input user. Jika user langsung tekan ENTER, pakai nilai default.
    """
    user_val = input(f"   {prompt} [\033[96m{default_val}\033[0m]: ")
    if user_val.strip() == "":
        return default_val
    return user_val.strip()

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

    # 1. Identitas
    update_config_file("osmo-bsc.cfg", r"(^\s*network country code\s+)\d+", f"\\g<1>{mcc}")
    update_config_file("osmo-bsc.cfg", r"(^\s*mobile network code\s+)\d+", f"\\g<1>{mnc}")
    update_config_file("osmo-bsc.cfg", r"(^\s*location_area_code\s+)\d+", f"\\g<1>{lac}")
    update_config_file("osmo-bsc.cfg", r"(^\s*cell_identity\s+)\d+", f"\\g<1>{cid}")
    
    update_config_file("osmo-msc.cfg", r"(^\s*network country code\s+)\d+", f"\\g<1>{mcc}")
    update_config_file("osmo-msc.cfg", r"(^\s*mobile network code\s+)\d+", f"\\g<1>{mnc}")

    # 2. Frekuensi
    update_config_file("osmo-bsc.cfg", r"(^\s*band\s+)[A-Z0-9]+", f"\\g<1>{band}")
    update_config_file("osmo-bsc.cfg", r"(^\s*arfcn\s+)\d+", f"\\g<1>{arfcn}")
    update_config_file("osmo-bts-trx.cfg", r"(^\s*band\s+)[A-Z0-9]+", f"\\g<1>{band}")

def run_background(command_list, log_name):
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    log_path = os.path.join(LOG_DIR, f"{log_name}.log")
    with open(log_path, "w") as f:
        subprocess.Popen(command_list, stdout=f, stderr=subprocess.STDOUT)
    print(f"    -> {log_name} berjalan (Log: {log_path})")

def countdown(seconds, message):
    """Fungsi hitung mundur"""
    for i in range(seconds, 0, -1):
        print(f"    {message} {i} detik...   ", end="\r")
        time.sleep(1)
    print(" " * 60, end="\r") # Hapus baris hitungan

def main():
    if os.geteuid() != 0:
        print("ERROR: Jalankan dengan SUDO!")
        sys.exit(1)

    print("==========================================")
    print("   GSM NETWORK LAUNCHER (OPTIMIZED)")
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

    # 1. PERSIAPAN BERSIH-BERSIH
    print_warn("Membersihkan proses lama & Tuning Kernel...")
    os.system("killall -9 osmo-stp osmo-msc osmo-hlr osmo-mgw osmo-bsc osmo-trx-uhd osmo-bts-trx osmo-pcu > /dev/null 2>&1")
    os.system("rm -f /tmp/pcu_bts /tmp/osmocom_*")
    
    os.system("sysctl -w net.core.rmem_max=50000000 > /dev/null")
    os.system("sysctl -w net.core.wmem_max=50000000 > /dev/null")
    
    apply_gsm_settings(my_mcc, my_mnc, my_lac, my_cid, my_band, my_arfcn)
    time.sleep(1)

    print("\n" + "="*50)
    print("   MEMULAI EKSEKUSI (ANTENA DULUAN -> CORE)")
    print("="*50)

    # 2. START ANTENA (TRX) - LANGSUNG JALAN DI AWAL
    # Tujuannya agar dia punya waktu 'warming up' selagi kita menyalakan Core
    print_step("Menyalakan DRIVER ANTENA (TRX)...")
    run_background(["chrt", "-f", "99", "osmo-trx-uhd", "-C", "osmo-trx-uhd.cfg"], "trx")
    print("    (Antena dibiarkan loading di background...)")
    
    # 3. START CORE NETWORK (BERTAHAP 10 DETIK)
    # Total waktu loading core ini sekitar 50 detik, 
    # cukup bagi Antena untuk stabil sebelum BTS dinyalakan.

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

    # 4. START BTS (TERAKHIR)
    # Di titik ini, TRX sudah nyala >50 detik, harusnya sangat stabil.
    print_step("Menyalakan BTS (Radio Unit)...")
    run_background(["osmo-bts-trx", "-c", "osmo-bts-trx.cfg"], "bts")
    
    countdown(DELAY_FINAL, "Finalisasi System:")

    print("\n" + "="*40)
    print("STATUS: SEMUA SERVICE BERJALAN.")
    print("Cek Log Realtime: tail -f logs_gsm/bts.log")
    print("==========================================")

if __name__ == "__main__":
    main()
