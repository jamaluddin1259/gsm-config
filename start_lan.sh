#!/bin/bash

# ==========================================
# SCRIPT FINAL: TRX & BTS DALAM SATU NAMESPACE
# Solusi Anti-Bentrok Port & Tanpa Socat
# ==========================================

# 1. BERSIH-BERSIH
echo "=== 1. Membersihkan Sistem ==="
sudo killall -9 osmo-bts-trx osmo-trx-uhd 2>/dev/null
sudo ip netns del bts_lan 2>/dev/null
sudo ip link del veth-host 2>/dev/null
sudo rm /tmp/pcu_bts_lan 2>/dev/null

# 2. BUAT KAMAR ISOLASI
echo "=== 2. Menyiapkan Namespace ==="
sudo ip netns add bts_lan
sudo ip netns exec bts_lan ip link set lo up

# 3. KABEL VIRTUAL & IP
echo "=== 3. Setting Network Bridge ==="
sudo ip link add veth-host type veth peer name veth-bts
sudo ip link set veth-bts netns bts_lan

# IP Laptop (Gerbang Luar)
sudo ip addr add 10.0.0.1/24 dev veth-host
sudo ip link set veth-host up

# IP Namespace (Dalam Kamar)
sudo ip netns exec bts_lan ip addr add 10.0.0.2/24 dev veth-bts
sudo ip netns exec bts_lan ip link set veth-bts up

# 4. ROUTING & NAT (Supaya TRX bisa kontak AntsDR di 192.168.1.10)
echo "=== 4. Mengaktifkan NAT ==="
sudo ip netns exec bts_lan ip route add default via 10.0.0.1
sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE
sudo sysctl -w net.ipv4.ip_forward=1 > /dev/null

# 5. JALANKAN TRX (RADIO) DI DALAM NAMESPACE (Background)
echo "=== 5. Menyalakan Radio (osmo-trx-uhd) ==="
# Kita jalankan di background (&) agar script lanjut ke BTS
sudo ip netns exec bts_lan /home/jamal/osmo-trx/Transceiver52M/osmo-trx-uhd -C /home/jamal/gsm/osmo-trx-lan.cfg > /home/jamal/gsm/logs_gsm/trx_lan.log 2>&1 &

echo "   -> Menunggu Radio panas (5 detik)..."
sleep 5

# 6. JALANKAN BTS DI DALAM NAMESPACE (Foreground)
echo "=== 6. Menyalakan BTS Software ==="
sudo ip netns exec bts_lan osmo-bts-trx -c /home/jamal/gsm/osmo-bts-lan.cfg
