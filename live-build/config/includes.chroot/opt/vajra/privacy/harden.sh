#!/bin/bash
# Vajra OS Privacy Hardening
set -e
echo "◆ Vajra OS Privacy Hardening"
if [[ $EUID -ne 0 ]]; then echo "Run as root"; exit 1; fi

# Telemetry off
mkdir -p /etc/firefox/syspref.js.d
cat > /etc/firefox/syspref.js.d/vajra.js << 'EOF'
pref("datareporting.policy.dataSubmissionEnabled", false);
pref("toolkit.telemetry.enabled", false);
pref("browser.privatebrowsing.autostart", true);
pref("privacy.resistFingerprinting", true);
pref("privacy.trackingprotection.enabled", true);
pref("network.dns.disablePrefetch", true);
pref("media.peerconnection.enabled", false);
EOF

# Kernel hardening
cat > /etc/sysctl.d/99-vajra.conf << 'EOF'
net.ipv6.conf.all.use_tempaddr = 2
net.ipv4.ip_forward = 0
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.tcp_syncookies = 1
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
fs.suid_dumpable = 0
kernel.randomize_va_space = 2
kernel.unprivileged_bpf_disabled = 1
EOF
sysctl --system > /dev/null 2>&1

# MAC randomization
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/vajra-mac.conf << 'EOF'
[device]
wifi.scan-rand-mac-address=yes
[connection]
wifi.cloned-mac-address=random
ethernet.cloned-mac-address=random
EOF
systemctl restart NetworkManager 2>/dev/null || true

# Firewall
systemctl enable firewalld 2>/dev/null || true
systemctl start firewalld 2>/dev/null || true
firewall-cmd --permanent --set-default-zone=drop 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true

# Disable services
for svc in avahi-daemon cups bluetooth; do systemctl disable $svc 2>/dev/null || true; done

# SSH hardening
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/vajra.conf << 'EOF'
PermitRootLogin no
PasswordAuthentication no
MaxAuthTries 3
AllowUsers vajra
EOF

# Encrypted DNS
cat > /etc/systemd/resolved.conf << 'EOF'
[Resolve]
DNS=127.0.0.1:5353
FallbackDNS=1.1.1.1 9.9.9.9
DNSOverTLS=yes
DNSSEC=yes
LLMNR=no
MulticastDNS=no
EOF
systemctl restart systemd-resolved 2>/dev/null || true

echo "◆ Privacy hardening complete!"
