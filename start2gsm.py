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

CONF_TRX_USB = "osmo-trx-uhd.cfg"
CONF_BTS_USB = "osmo-bts-trx.cfg"
CONF_TRX_LAN = "osmo-trx-lan.cfg"
CONF_BTS_LAN = "osmo-bts-lan.cfg"
CONF_BSC     = "osmo-bsc.cfg"
CONF_MSC     = "osmo-msc.cfg"

# ==========================================
#              FUNGSI BANTUAN
# ==========================================
def update_config(filepath, regex_pattern, new_value):
    if not os.path.exists(filepath): 
        print(f"   [!] Gagal update: {filepath} tidak ada")
        return
    with open(filepath, 'r') as f: content = f.read()
    new_content, count = re.subn(regex_pattern, f"\\g<1>{new_value}", content, flags=re.MULTILINE)
    if count > 0:
        with open(filepath, 'w') as f: f.write(new_content)

def setup_namespace():
    print("   [+] Setting up Network Namespace & NAT...")
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

def run_bg(command_list, log_name, use_namespace=False):
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
    os.system(f"chmod -R 777 {LOG_DIR}")
    log_path = os.path.join(LOG_DIR, f"{log_name}.log")
    final_cmd = command_list
    if use_namespace:
        final_cmd = ["ip", "netns", "exec", "bts_lan"] + command_list
    with open(log_path, "w") as f:
        subprocess.Popen(final_cmd, stdout=f, stderr=subprocess.STDOUT)
    print(f"   -> {'[LAN]' if use_namespace else '[USB]'} {log_name} running")

# ==========================================
#                MAIN PROGRAM
# ==========================================
def main():
    if os.geteuid() != 0:
        print("ERROR: Wajib RUN AS ROOT (SUDO)!")
        sys.exit(1)

    print("\n\033[95m" + "="*60)
    print("      OSMOCOM DUAL TOWER - PROFESSIONAL LAUNCHER")
    print("="*60 + "\033[0m")
    
    # --- KONFIGURASI TOWER 1 (USB) ---
    print("\n\033[92m[ SETTING TOWER 1: USB / HOST ]\033[0m")
    u_mcc   = input("   MCC [510]: ") or "510"
    u_mnc   = input("   MNC [01]: ") or "01"
    u_lac   = input("   LAC [1]: ") or "1"
    u_cid   = input("   CID [1]: ") or "1"
    u_band  = input("   BAND (GSM900/DCS1800) [GSM900]: ") or "GSM900"
    u_arfcn = input("   ARFCN [1]: ") or "1"

    # --- KONFIGURASI TOWER 2 (LAN) ---
    print("\n\033[96m[ SETTING TOWER 2: LAN / ANTSDR ]\033[0m")
    l_mcc   = input("   MCC [510]: ") or "510"
    l_mnc   = input("   MNC [10]: ") or "10"
    l_lac   = input("   LAC [2]: ") or "2"
    l_cid   = input("   CID [2]: ") or "2"
    l_band  = input("   BAND (GSM900/DCS1800) [GSM900]: ") or "GSM900"
    l_arfcn = input("   ARFCN [10]: ") or "10"

    # --- UPDATE CONFIG FILES ---
    print("\n[+] Updating Configuration Files...")
    
    # Global BSC settings (biasanya ikut bts 0)
    update_config(CONF_BSC, r"(^\s*network country code\s+)\d+", u_mcc)
    update_config(CONF_BSC, r"(^\s*mobile network code\s+)\d+", u_mnc)
    
    # Tower USB (BTS 0) - Pastikan di bsc.cfg ada bts 0
    # Kita asumsikan urutan bts 0 dulu baru bts 1 di file config
    # Note: Regex ini akan mengganti kemunculan pertama (bts 0)
    update_config(CONF_BTS_USB, r"(^\s*band\s+)[A-Z0-9]+", u_band)
    update_config(CONF_BTS_USB, r"(^\s*arfcn\s+)\d+", u_arfcn)
    
    # Tower LAN (BTS 1)
    update_config(CONF_BTS_LAN, r"(^\s*band\s+)[A-Z0-9]+", l_band)
    update_config(CONF_BTS_LAN, r"(^\s*arfcn\s+)\d+", l_arfcn)

    # --- EKSEKUSI ---
    print("\n\033[93m[!] Cleaning system & Preparing services...\033[0m")
    os.system("killall -9 osmo-stp osmo-msc osmo-hlr osmo-mgw osmo-bsc osmo-trx-uhd osmo-bts-trx >/dev/null 2>&1")
    os.system("rm -f /tmp/pcu_bts*")
    os.system("chmod -R 777 ~/gsm/")
    
    setup_namespace()

    # Launch Core
    run_bg(["osmo-stp", "-c", "osmo-stp.cfg"], "core_stp")
    time.sleep(1)
    run_bg(["osmo-hlr", "-c", "osmo-hlr.cfg"], "core_hlr")
    run_bg(["osmo-msc", "-c", "osmo-msc.cfg"], "core_msc")
    run_bg(["osmo-mgw", "-c", "osmo-mgw.cfg"], "core_mgw")
    time.sleep(2)
    run_bg(["osmo-bsc", "-c", CONF_BSC], "core_bsc")
    time.sleep(5)

    # Launch USB
    run_bg(["chrt", "-f", "99", BIN_TRX, "-C", CONF_TRX_USB], "trx_usb")
    time.sleep(2)
    run_bg(["osmo-bts-trx", "-c", CONF_BTS_USB], "bts_usb")

    # Launch LAN
    run_bg([BIN_TRX, "-C", CONF_TRX_LAN], "trx_lan", use_namespace=True)
    time.sleep(5)
    run_bg(["osmo-bts-trx", "-c", CONF_BTS_LAN], "bts_lan", use_namespace=True)

    print("\n\033[92m" + "="*60)
    print("   SUCCESS: DUAL TOWER IS NOW BROADCASTING!")
    print("="*60 + "\033[0m")
    print(f"Check logs in: {os.getcwd()}/{LOG_DIR}")

if __name__ == "__main__":
    main()
