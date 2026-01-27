#!/usr/bin/env python3
import os
import time
import subprocess
import sys
import re
import glob

# ==========================================
#           KONFIGURASI FILE & PATH
# ==========================================
LOG_DIR = "logs_gsm"
HOME_DIR = "/home/jamal"
# Sesuaikan path ini jika osmo-trx ada di tempat lain
BIN_TRX_UHD = f"{HOME_DIR}/osmo-trx/Transceiver52M/osmo-trx-uhd" 

# File Config
CONF_STP     = "osmo-stp.cfg"
CONF_HLR     = "osmo-hlr.cfg"
CONF_MGW     = "osmo-mgw.cfg"
CONF_MSC_USB = "osmo-msc.cfg"
CONF_BSC_USB = "osmo-bsc.cfg"
CONF_BTS_USB = "osmo-bts-trx.cfg"
CONF_TRX_USB = "osmo-trx-uhd.cfg"
CONF_MSC_LAN = "osmo-msc-lan.cfg"    
CONF_BSC_LAN = "osmo-bsc-lan.cfg"    
CONF_BTS_LAN = "osmo-bts-lan.cfg"
CONF_TRX_LAN = "osmo-trx-lan.cfg"

# ==========================================
#              FUNGSI BANTUAN
# ==========================================
def print_header(text):
    print(f"\n\033[95m{'='*60}")
    print(f"    {text}")
    print(f"{'='*60}\033[0m")

def print_warn(text):
    print(f"    \033[93m[!] {text}\033[0m")

def update_config(filepath, regex_pattern, new_value):
    full_path = os.path.join(HOME_DIR, "gsm", filepath)
    if not os.path.exists(full_path): 
        full_path = filepath
        if not os.path.exists(full_path): return
    
    with open(full_path, 'r') as f: content = f.read()
    
    # Fungsi ini akan mencari pattern dan menggantinya
    # Flags multiline agar ^ mendeteksi awal baris
    new_content, count = re.subn(regex_pattern, f"\\g<1>{new_value}", content, flags=re.MULTILINE)
    
    if count > 0:
        with open(full_path, 'w') as f: f.write(new_content)
        # print(f"        [DEBUG] Updated {filepath}: {new_value}")

def cleanup_and_tune():
    print_header("1. PERSIAPAN: BERSIH-BERSIH SOCKET & TUNING")
    
    # 1. Matikan Proses Lama
    print_warn("Mematikan semua proses Osmocom...")
    os.system("killall -9 osmo-stp osmo-msc osmo-hlr osmo-mgw osmo-bsc osmo-trx-uhd osmo-bts-trx osmo-pcu > /dev/null 2>&1")
    time.sleep(1)

    # 2. HAPUS SOCKET
    print_warn("Menghapus socket /tmp secara paksa...")
    os.system("rm -f /tmp/msc_mncc /tmp/bsc_mncc /tmp/msc_mncc_lan")
    os.system("rm -f /tmp/pcu_bts* /tmp/osmocom_* /tmp/msc_mncc* /tmp/bsc_mncc*")
    print("    [+] Socket bersih! Siap dijalankan.")

    # 3. Tuning Kernel
    print("    [+] Tuning Kernel Buffer (50MB)...")
    os.system("sysctl -w net.core.rmem_max=50000000 > /dev/null")
    os.system("sysctl -w net.core.wmem_max=50000000 > /dev/null")
    os.system("sysctl -w kernel.sched_rt_runtime_us=-1 > /dev/null")
    
    # 4. CPU Performance
    print("    [+] Set CPU ke Performance Mode...")
    cpu_paths = glob.glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor')
    for path in cpu_paths:
        try:
            with open(path, 'w') as f: f.write('performance')
        except: pass
        
    # 5. Reset Logs
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
    os.system(f"rm -f {LOG_DIR}/*.log")
    os.system(f"chmod -R 777 {LOG_DIR}")

def setup_namespace():
    print("    [+] Membangun Network Namespace (bts_lan)...")
    os.system("ip netns del bts_lan >/dev/null 2>&1")
    os.system("ip link del veth-host >/dev/null 2>&1")
    os.system("ip netns add bts_lan")
    os.system("ip netns exec bts_lan ip link set lo up")
    os.system("ip link add veth-host type veth peer name veth-bts")
    os.system("ip link set veth-bts netns bts_lan")
    os.system("ip addr add 10.0.0.1/24 dev veth-host")
    os.system("ip link set veth-host up")
    os.system("ip netns exec bts_lan ip addr add 10.0.0.2/24 dev veth-bts")
    os.system("ip netns exec bts_lan ip link set veth-bts up")
    os.system("ip netns exec bts_lan ip route add default via 10.0.0.1")
    os.system("iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE")
    os.system("sysctl -w net.ipv4.ip_forward=1 >/dev/null")

def run_bg(command_list, log_name, use_namespace=False, realtime=False):
    log_path = os.path.join(LOG_DIR, f"{log_name}.log")
    final_cmd = command_list
    prefix = "[HOST]"
    
    if realtime: final_cmd = ["chrt", "-f", "99"] + final_cmd
    
    if use_namespace: 
        final_cmd = ["ip", "netns", "exec", "bts_lan"] + final_cmd
        prefix = "[LAN ]"
        
    with open(log_path, "w") as f:
        subprocess.Popen(final_cmd, stdout=f, stderr=subprocess.STDOUT)
    print(f"    -> {prefix} Starting {log_name}...")

def get_band_string(input_val):
    """Mengubah input user menjadi format config Osmocom"""
    if "1800" in input_val:
        return "DCS1800"
    elif "1900" in input_val:
        return "PCS1900"
    elif "850" in input_val:
        return "GSM850"
    else:
        return "GSM900" # Default

# ==========================================
#                 MAIN PROGRAM
# ==========================================
def main():
    if os.geteuid() != 0:
        print("\033[91mWajib RUN AS ROOT (SUDO)!\033[0m")
        sys.exit(1)

    print_header("OSMOCOM DUAL-PLMN SETUP (ULTIMATE - BAND SELECT)")

    # --- INPUT IDENTITAS TOWER 1 (USB) ---
    print("\033[92m[ TOWER 1: USB (PLMN A) ]\033[0m")
    u_band_in = input("    BAND [900/1800]: ") or "900"
    u_mcc = input("    MCC [510]: ") or "510"
    u_mnc = input("    MNC [01]: ") or "01"
    u_lac = input("    LAC [1]: ") or "1"
    u_cid = input("    CID [1]: ") or "1"
    
    # Tentukan Default ARFCN berdasarkan Band
    def_arfcn = "871" if "1800" in u_band_in else "50"
    u_arfcn = input(f"    ARFCN [{def_arfcn}]: ") or def_arfcn
    
    u_band_cfg = get_band_string(u_band_in)

    # --- INPUT IDENTITAS TOWER 2 (LAN) ---
    print("\n\033[96m[ TOWER 2: LAN (PLMN B) ]\033[0m")
    l_band_in = input("    BAND [900/1800]: ") or "900"
    l_mcc = input("    MCC [510]: ") or "510"
    l_mnc = input("    MNC [10]: ") or "10"
    l_lac = input("    LAC [2]: ") or "2"
    l_cid = input("    CID [2]: ") or "2"
    
    def_arfcn_lan = "881" if "1800" in l_band_in else "60"
    l_arfcn = input(f"    ARFCN [{def_arfcn_lan}]: ") or def_arfcn_lan

    l_band_cfg = get_band_string(l_band_in)

    # --- UPDATE CONFIG ---
    print(f"\n[+] Mengupdate Konfigurasi (Band T1: {u_band_cfg}, Band T2: {l_band_cfg})...")
    
    # List config yang akan diupdate: (File BSC, File BTS, Data)
    # Kita update BTS config juga karena parameter 'band' biasanya ada di BTS
    target_updates = [
        (CONF_BSC_USB, CONF_BTS_USB, u_band_cfg, u_mcc, u_mnc, u_lac, u_cid, u_arfcn),
        (CONF_BSC_LAN, CONF_BTS_LAN, l_band_cfg, l_mcc, l_mnc, l_lac, l_cid, l_arfcn)
    ]
    
    for bsc_file, bts_file, band, mcc, mnc, lac, cid, arfcn in target_updates:
        # Update BSC File
        update_config(bsc_file, r"(^\s*network country code\s+)\d+", mcc)
        update_config(bsc_file, r"(^\s*mobile network code\s+)\d+", mnc)
        update_config(bsc_file, r"(^\s*location_area_code\s+)\d+", lac)
        update_config(bsc_file, r"(^\s*cell_identity\s+)\d+", cid)
        
        # Update BTS File (Band & ARFCN biasanya di sini juga penting)
        # Update 'band' di BTS config (phy 0 section)
        update_config(bts_file, r"(^\s*band\s+)\w+", band)
        # Jika ada setting band di BSC (network section), update juga
        update_config(bsc_file, r"(^\s*band\s+)\w+", band)
        
        # Update ARFCN (Bisa ada di BSC atau BTS, kita coba update dua-duanya jika ketemu)
        update_config(bsc_file, r"(^\s*arfcn\s+)\d+", arfcn)
        update_config(bts_file, r"(^\s*arfcn\s+)\d+", arfcn)

    # --- EKSEKUSI ---
    cleanup_and_tune()
    setup_namespace()

    print_header("2. MENJALANKAN PROSES GSM")
    
    # Core Network
    run_bg(["osmo-stp", "-c", CONF_STP], "core_stp")
    run_bg(["osmo-hlr", "-c", CONF_HLR], "core_hlr")
    run_bg(["osmo-mgw", "-c", CONF_MGW], "core_mgw")
    
    # Dual MSC
    run_bg(["osmo-msc", "-c", CONF_MSC_USB], "msc_usb")
    run_bg(["osmo-msc", "-c", CONF_MSC_LAN], "msc_lan")
    time.sleep(2)

    # Tower 1 (USB)
    run_bg(["osmo-bsc", "-c", CONF_BSC_USB], "bsc_usb")
    run_bg(["osmo-trx-uhd", "-C", CONF_TRX_USB], "trx_usb", realtime=True)
    time.sleep(2)
    run_bg(["osmo-bts-trx", "-c", CONF_BTS_USB], "bts_usb")

    # Tower 2 (LAN)
    run_bg(["osmo-bsc", "-c", CONF_BSC_LAN], "bsc_lan")
    run_bg([BIN_TRX_UHD, "-C", CONF_TRX_LAN], "trx_lan", use_namespace=True, realtime=True)
    time.sleep(4)
    run_bg(["osmo-bts-trx", "-c", CONF_BTS_LAN], "bts_lan", use_namespace=True)

    # --- RINGKASAN LOG ---
    print_header("3. EKSEKUSI BERHASIL!")
    print("Semua proses berjalan. Cek log dengan:")
    print("-" * 60)
    print("\033[92m[ TOWER 1: USB ]\033[0m")
    print(f"  ALL: tail -f {LOG_DIR}/*usb.log")
    print("\n\033[96m[ TOWER 2: LAN ]\033[0m")
    print(f"  ALL: tail -f {LOG_DIR}/*lan.log")
    print("-" * 60)
    print("Selesai.\n")

if __name__ == "__main__":
    main()
