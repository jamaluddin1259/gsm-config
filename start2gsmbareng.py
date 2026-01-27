import os
import time
import subprocess
import sys
import re

# ==========================================
#          KONFIGURASI FILE & PATH
# ==========================================
LOG_DIR = "logs_gsm"
BIN_TRX = "/home/jamal/osmo-trx/Transceiver52M/osmo-trx-uhd"

# --- CORE NETWORK ---
CONF_STP = "osmo-stp.cfg"
CONF_MSC = "osmo-msc.cfg"
CONF_HLR = "osmo-hlr.cfg"
CONF_MGW = "osmo-mgw.cfg"

# --- TOWER 1: USB (HOST - PLMN A) ---
CONF_BSC_USB = "osmo-bsc.cfg"       # Config BSC Utama
CONF_BTS_USB = "osmo-bts-trx.cfg"
CONF_TRX_USB = "osmo-trx-uhd.cfg"

# --- TOWER 2: LAN (NAMESPACE - PLMN B) ---
CONF_BSC_LAN = "osmo-bsc-lan.cfg"   # Config BSC Kedua (AntsDR)
CONF_BTS_LAN = "osmo-bts-lan.cfg"
CONF_TRX_LAN = "osmo-trx-lan.cfg"

# ==========================================
#              FUNGSI BANTUAN
# ==========================================
def print_header(text):
    print(f"\n\033[95m{'='*60}")
    print(f"   {text}")
    print(f"{'='*60}\033[0m")

def update_config(filepath, regex_pattern, new_value):
    if not os.path.exists(filepath): 
        print(f"   \033[91m[!] Config not found: {filepath}\033[0m")
        return
    with open(filepath, 'r') as f: content = f.read()
    new_content, count = re.subn(regex_pattern, f"\\g<1>{new_value}", content, flags=re.MULTILINE)
    if count > 0:
        with open(filepath, 'w') as f: f.write(new_content)
        # print(f"   [OK] Updated {filepath}")

def setup_cleanup():
    """Membersihkan Socket & Izin Database agar MSC tidak Error"""
    print("   [+] Cleaning up sockets & fixing permissions...")
    os.system("killall -9 osmo-stp osmo-msc osmo-hlr osmo-mgw osmo-bsc osmo-trx-uhd osmo-bts-trx >/dev/null 2>&1")
    os.system("rm -f /tmp/msc_mncc /tmp/pcu_bts*") # Hapus socket nyangkut
    os.system("chmod 777 ~/gsm/*.db* 2>/dev/null") # Fix database locked
    
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
    os.system(f"chmod -R 777 {LOG_DIR}") # Izin folder log

def setup_namespace():
    print("   [+] Building Isolation Room (Namespace)...")
    cmds = [
        "ip netns del bts_lan >/dev/null 2>&1",
        "ip link del veth-host >/dev/null 2>&1",
        "ip netns add bts_lan",
        "ip netns exec bts_lan ip link set lo up",
        "ip link add veth-host type veth peer name veth-bts",
        "ip link set veth-bts netns bts_lan",
        "ip addr add 10.0.0.1/24 dev veth-host",
        "ip link set veth-host up",
        "ip netns exec bts_lan ip addr add 10.0.0.2/24 dev veth-bts",
        "ip netns exec bts_lan ip link set veth-bts up",
        "ip netns exec bts_lan ip route add default via 10.0.0.1",
        "iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE",
        "sysctl -w net.ipv4.ip_forward=1 >/dev/null"
    ]
    for cmd in cmds:
        os.system(cmd)

def run_bg(command_list, log_name, use_namespace=False):
    log_path = os.path.join(LOG_DIR, f"{log_name}.log")
    final_cmd = command_list
    prefix = "[HOST]"
    
    if use_namespace:
        final_cmd = ["ip", "netns", "exec", "bts_lan"] + command_list
        prefix = "[LAN ]"
        
    with open(log_path, "w") as f:
        subprocess.Popen(final_cmd, stdout=f, stderr=subprocess.STDOUT)
    print(f"   -> {prefix} {log_name} running...")

# ==========================================
#                MAIN PROGRAM
# ==========================================
def main():
    if os.geteuid() != 0:
        print("ERROR: Wajib RUN AS ROOT (SUDO)!")
        sys.exit(1)

    print_header("OSMOCOM DUAL-BSC LAUNCHER (2 OPERATORS)")
    
    # --- INPUT TOWER 1 (USB) ---
    print("\n\033[92m[ SETTING TOWER 1: USB (HOST) ]\033[0m")
    u_mcc   = input("   MCC [510]: ") or "510"
    u_mnc   = input("   MNC [01]: ") or "01"
    u_lac   = input("   LAC [1]: ") or "1"
    u_cid   = input("   CID [1]: ") or "1"
    u_band  = input("   BAND [GSM900]: ") or "GSM900"
    u_arfcn = input("   ARFCN [1]: ") or "1"

    # --- INPUT TOWER 2 (LAN) ---
    print("\n\033[96m[ SETTING TOWER 2: LAN (NAMESPACE) ]\033[0m")
    l_mcc   = input("   MCC [510]: ") or "510"
    l_mnc   = input("   MNC [10]: ") or "10"
    l_lac   = input("   LAC [2]: ") or "2"
    l_cid   = input("   CID [2]: ") or "2"
    l_band  = input("   BAND [GSM900]: ") or "GSM900"
    l_arfcn = input("   ARFCN [10]: ") or "10"

    # --- UPDATE CONFIG FILES ---
    print("\n[+] Updating Configuration Files...")
    
    # 1. Update BSC USB (osmo-bsc.cfg)
    update_config(CONF_BSC_USB, r"(^\s*network country code\s+)\d+", u_mcc)
    update_config(CONF_BSC_USB, r"(^\s*mobile network code\s+)\d+", u_mnc)
    update_config(CONF_BSC_USB, r"(^\s*location_area_code\s+)\d+", u_lac)
    update_config(CONF_BSC_USB, r"(^\s*cell_identity\s+)\d+", u_cid)
    update_config(CONF_BSC_USB, r"(^\s*band\s+)[A-Z0-9]+", u_band)
    update_config(CONF_BSC_USB, r"(^\s*arfcn\s+)\d+", u_arfcn)

    # 2. Update BSC LAN (osmo-bsc-lan.cfg)
    update_config(CONF_BSC_LAN, r"(^\s*network country code\s+)\d+", l_mcc)
    update_config(CONF_BSC_LAN, r"(^\s*mobile network code\s+)\d+", l_mnc)
    update_config(CONF_BSC_LAN, r"(^\s*location_area_code\s+)\d+", l_lac)
    update_config(CONF_BSC_LAN, r"(^\s*cell_identity\s+)\d+", l_cid)
    update_config(CONF_BSC_LAN, r"(^\s*band\s+)[A-Z0-9]+", l_band)
    update_config(CONF_BSC_LAN, r"(^\s*arfcn\s+)\d+", l_arfcn)
    
    # 3. Update MSC (Supaya match dgn MCC/MNC USB sebagai default)
    update_config(CONF_MSC, r"(^\s*network country code\s+)\d+", u_mcc)
    update_config(CONF_MSC, r"(^\s*mobile network code\s+)\d+", u_mnc)

    # --- EKSEKUSI ---
    setup_cleanup()
    setup_namespace()

    # 1. Launch Core Network (Shared)
    print_header("1. STARTING CORE NETWORK")
    run_bg(["osmo-stp", "-c", CONF_STP], "core_stp")
    time.sleep(1)
    run_bg(["osmo-hlr", "-c", CONF_HLR], "core_hlr")
    run_bg(["osmo-msc", "-c", CONF_MSC], "core_msc")
    run_bg(["osmo-mgw", "-c", CONF_MGW], "core_mgw")
    time.sleep(2)

    # 2. Launch Tower USB (HOST)
    print_header("2. STARTING TOWER 1 (USB/HOST)")
    run_bg(["osmo-bsc", "-c", CONF_BSC_USB], "bsc_usb")
    time.sleep(2)
    run_bg(["chrt", "-f", "99", BIN_TRX, "-C", CONF_TRX_USB], "trx_usb")
    time.sleep(2)
    run_bg(["osmo-bts-trx", "-c", CONF_BTS_USB], "bts_usb")

    # 3. Launch Tower LAN (NAMESPACE)
    print_header("3. STARTING TOWER 2 (LAN/NAMESPACE)")
    # Jalankan BSC kedua di dalam namespace
    run_bg(["osmo-bsc", "-c", CONF_BSC_LAN], "bsc_lan", use_namespace=True)
    time.sleep(2)
    # Jalankan TRX & BTS kedua di dalam namespace
    run_bg([BIN_TRX, "-C", CONF_TRX_LAN], "trx_lan", use_namespace=True)
    time.sleep(5)
    run_bg(["osmo-bts-trx", "-c", CONF_BTS_LAN], "bts_lan", use_namespace=True)

    print("\n\033[92m" + "="*60)
    print("   SUCCESS: DUAL OPERATOR NETWORK IS LIVE!")
    print("="*60 + "\033[0m")
    print(f"Log USB: tail -f {LOG_DIR}/bsc_usb.log")
    print(f"Log LAN: tail -f {LOG_DIR}/bsc_lan.log")

if __name__ == "__main__":
    main()
