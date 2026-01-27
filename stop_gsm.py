import os
import time
import subprocess
import sys

def print_warn(message):
    print(f"\033[93m[!] {message}\033[0m")

def print_step(message):
    print(f"\033[92m[+] {message}\033[0m")

def check_process_running(process_name):
    """Mengecek apakah proses masih ada di background"""
    try:
        # pgrep akan return exit code 0 jika proses ada
        subprocess.check_call(["pgrep", "-f", process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    if os.geteuid() != 0:
        print("ERROR: Jalankan dengan SUDO!")
        sys.exit(1)

    print("==========================================")
    print("   GSM HARD STOP (PEMUSNAHAN TOTAL)       ")
    print("==========================================")

    targets = [
        "osmo-trx-uhd", "osmo-bts-trx", "osmo-bsc", 
        "osmo-msc", "osmo-mgw", "osmo-hlr", "osmo-stp", "osmo-pcu"
    ]

    # 1. TAHAP PERTAMA: SIGTERM (Minta baik-baik)
    print_warn("Mengirim sinyal stop...")
    os.system("killall osmo-trx-uhd osmo-bts-trx > /dev/null 2>&1")
    time.sleep(1)

    # 2. TAHAP KEDUA: SIGKILL (Paksa Mati / Kill -9)
    print_warn("Memastikan proses benar-benar mati...")
    
    # Loop untuk mengecek apakah masih ada yang bandel
    for prog in targets:
        if check_process_running(prog):
            print(f"    -> Membunuh paksa: {prog}")
            # Kita kill berkali-kali untuk memastikan
            os.system(f"killall -9 {prog} > /dev/null 2>&1")
            time.sleep(0.1)
            
            # Cek lagi, kalau masih ada, gunakan pkill (lebih ganas)
            if check_process_running(prog):
                os.system(f"pkill -9 -f {prog} > /dev/null 2>&1")

    # 3. TAHAP KETIGA: MEMBERSIHKAN SOCKET UDP
    # Ini trik untuk memutus aliran UDP di Kernel
    print_warn("Membersihkan Sisa Koneksi & Socket...")
    os.system("rm -f /tmp/pcu_bts /tmp/osmocom_*")
    
    # Opsional: Restart Service Networking ringan untuk flush buffer (TIDAK MEMUTUS SSH)
    # os.system("ip neigh flush all") 

    print("\n" + "="*40)
    print_step("SEMUA PROSES SUDAH HILANG.")
    print("Info: Jika Wireshark masih melihat UDP berjalan,")
    print("      itu adalah sisa traffic dari Radio Hardware.")
    print("      SOLUSI: Cabut USB Radio sekarang.")
    print("==========================================")

if __name__ == "__main__":
    main()
