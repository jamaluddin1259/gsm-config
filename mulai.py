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
    new_content, count = re.subn(regex_pattern, f"\\g<1>{new_value}", content, flags=re.MULTILINE)
    if count > 0:
        with open(full_path, 'w') as f: f.write(new_content)

def cleanup_and_tune():
    print_header("1. PERSIAPAN: BERSIH-BERSIH SOCKET & TUNING")
    
    # 1. Matikan Proses Lama (Agar tidak ada zombie process)
    print_warn("Mematikan semua proses Osmocom...")
    os.system("killall -9 osmo-stp osmo-msc osmo-hlr osmo-mgw osmo-bsc osmo-trx-uhd osmo-bts-trx osmo-pcu > /dev/null 2>&1")
    time.sleep(1)

    # ==========================================================
    # 2. HAPUS SOCKET (BAGIAN INI YANG MAS JAMAL MINTA)
    # ==========================================================
    print_warn("Menghapus socket /tmp secara paksa...")
    
    # Hapus Socket MSC USB
    os.system("rm -f /tmp/msc_mncc")
    
    # Hapus Socket BSC USB (Kadang ada sisa bsc_mncc)
    os.system("rm -f /tmp/bsc_mncc")
    
    # Hapus Socket MSC LAN (PENTING UNTUK ANTSDR)
    os.system("rm -f /tmp/msc_mncc_lan")
    
    # Hapus Socket Sisa Lainnya (Wildcard biar bersih total)
    os.system("rm -f /tmp/pcu_bts* /tmp/osmocom_* /tmp/msc_mncc* /tmp/bsc_mncc*")
    
    print("    [+] Socket bersih! Siap dijalankan.")
    # ==========================================================

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

# ==========================================
#                 MAIN PROGRAM
# ==========================================
def main():
    if os.geteuid() != 0:
        print("\033[91mWajib RUN AS ROOT (SUDO)!\033[0m")
        sys.exit(1)

    print_header("OSMOCOM DUAL-PLMN SETUP (ULTIMATE)")

    # --- INPUT IDENTITAS TOWER ---
    print("\033[92m[ TOWER 1: USB (PLMN A) ]\033[0m")
    u_mcc = input("    MCC [510]: ") or "510"
    u_mnc = input("    MNC [01]: ") or "01"
    u_lac = input("    LAC [1]: ") or "1"
    u_cid = input("    CID [1]: ") or "1"
    u_arfcn = input("    ARFCN [871]: ") or "871"

    print("\n\033[96m[ TOWER 2: LAN (PLMN B) ]\033[0m")
    l_mcc = input("    MCC [510]: ") or "510"
    l_mnc = input("    MNC [10]: ") or "10"
    l_lac = input("    LAC [2]: ") or "2"
    l_cid = input("    CID [2]: ") or "2"
    l_arfcn = input("    ARFCN [881]: ") or "881"

    # --- UPDATE CONFIG ---
    print("\n[+] Menulis konfigurasi ke file .cfg...")
    configs = [(CONF_BSC_USB, u_mcc, u_mnc, u_lac, u_cid, u_arfcn),
               (CONF_BSC_LAN, l_mcc, l_mnc, l_lac, l_cid, l_arfcn)]
    
    for cfg, mcc, mnc, lac, cid, arfcn in configs:
        update_config(cfg, r"(^\s*network country code\s+)\d+", mcc)
        update_config(cfg, r"(^\s*mobile network code\s+)\d+", mnc)
        update_config(cfg, r"(^\s*location_area_code\s+)\d+", lac)
        update_config(cfg, r"(^\s*cell_identity\s+)\d+", cid)
        update_config(cfg, r"(^\s*arfcn\s+)\d+", arfcn)

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
    print("Semua proses berjalan di background. Gunakan perintah berikut")
    print("untuk memantau log secara real-time (tail -f):")
    print("-" * 60)
    print("\033[92m[ TOWER 1: USB ]\033[0m")
    print(f"  BTS: tail -f {LOG_DIR}/bts_usb.log")
    print(f"  TRX: tail -f {LOG_DIR}/trx_usb.log")
    print(f"  BSC: tail -f {LOG_DIR}/bsc_usb.log")
    
    print("\n\033[96m[ TOWER 2: LAN ]\033[0m")
    print(f"  BTS: tail -f {LOG_DIR}/bts_lan.log")
    print(f"  TRX: tail -f {LOG_DIR}/trx_lan.log")
    print(f"  BSC: tail -f {LOG_DIR}/bsc_lan.log")
    
    print("\n\033[93m[ CORE NETWORK ]\033[0m")
    print(f"  MSC USB: tail -f {LOG_DIR}/msc_usb.log")
    print(f"  MSC LAN: tail -f {LOG_DIR}/msc_lan.log")
    print(f"  HLR    : tail -f {LOG_DIR}/core_hlr.log")
    print(f"  STP    : tail -f {LOG_DIR}/core_stp.log")
    
    print("\n\033[95m[ GABUNGAN (SEMUA LOG SEKALIGUS) ]\033[0m")
    print(f"  Perintah: tail -f {LOG_DIR}/*.log")
    print("-" * 60)
    print("Selesai.\n")

if __name__ == "__main__":
    main()
