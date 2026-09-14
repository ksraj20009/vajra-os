#!/bin/bash
# Vajra OS Tor Transparent Proxy Setup
set -e
echo "◆ Vajra OS Tor Proxy Setup"
if [[ $EUID -ne 0 ]]; then echo "Run as root"; exit 1; fi
if ! command -v tor &>/dev/null; then apt-get update && apt-get install -y tor; fi
cp /opt/vajra/privacy/torrc /etc/tor/torrc 2>/dev/null || true
systemctl enable tor && systemctl start tor
sleep 3
TOR_UID=$(id -u debian-tor 2>/dev/null || id -u tor 2>/dev/null || echo 0)
iptables -F && iptables -t nat -F && iptables -t mangle -F
iptables -t nat -A OUTPUT -o lo -p udp --dport 53 -j REDIRECT --to-ports 5353
iptables -t nat -A OUTPUT -o lo -p tcp --dport 53 -j REDIRECT --to-ports 5353
iptables -t nat -A OUTPUT -o lo -j RETURN
iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports 9040
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT
iptables -A OUTPUT -p udp --dport 5353 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 9040 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 9050 -j ACCEPT
iptables -A OUTPUT -j DROP
iptables -A INPUT -j DROP
iptables -P INPUT DROP && iptables -P FORWARD DROP && iptables -P OUTPUT DROP
echo "nameserver 127.0.0.1" > /etc/resolv.conf
mkdir -p /etc/vajra && iptables-save > /etc/vajra/iptables.rules
echo "◆ Tor Transparent Proxy Active!"
