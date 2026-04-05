#!/bin/bash
# Apple Pi Diagnostics — chroot setup script
# Runs INSIDE an ARM64 chroot of the Pi OS root partition.
# Called by build-image.sh after mounting the base image.
set -euo pipefail

APD_ROOT="/opt/apple-pi-diagnostics"

echo "==> [setup-image] Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-pyqt5 \
    python3-pyqt5.qtsvg \
    python3-rpi.gpio \
    xserver-xorg-core \
    xserver-xorg-input-evdev \
    xserver-xorg-video-fbdev \
    xserver-xorg-video-modesetting \
    xinit \
    x11-xserver-utils \
    unclutter \
    busybox-static \
    cpio \
    gzip \
    lm-sensors \
    usbutils \
    lshw \
    libraspberrypi-bin \
    fonts-dejavu-core \
    fonts-liberation

# vcgencmd is provided by libraspberrypi-bin (already installed above).
# reportlab needs TrueType fonts — fonts-dejavu-core and fonts-liberation
# supply them without requiring the full fonts-noto set.

echo "==> [setup-image] Installing Python packages..."
pip3 install --break-system-packages --no-cache-dir \
    psutil \
    reportlab \
    Pillow \
    "qrcode[pil]"

echo "==> [setup-image] Building failsafe initramfs..."
cd "${APD_ROOT}"
bash build_failsafe.sh

echo "==> [setup-image] Configuring auto-login on tty1..."
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I $TERM
EOF

echo "==> [setup-image] Configuring auto-startx for pi user..."
# Create .bash_profile if it does not already exist
if [ ! -f /home/pi/.bash_profile ]; then
    cp /etc/skel/.bash_profile /home/pi/.bash_profile 2>/dev/null || touch /home/pi/.bash_profile
fi
# Append the startx trigger (idempotent — skip if already present)
if ! grep -q "apple-pi-diagnostics" /home/pi/.bash_profile; then
    cat "${APD_ROOT}/deploy/bash_profile_append" >> /home/pi/.bash_profile
fi
chown pi:pi /home/pi/.bash_profile

echo "==> [setup-image] Creating /home/pi/reports directory..."
mkdir -p /home/pi/apd-reports
chown -R pi:pi /home/pi/apd-reports

echo "==> [setup-image] Pointing APD report output at /home/pi/apd-reports..."
# Set an environment variable the app can pick up for the output directory
if ! grep -q "APD_REPORT_DIR" /home/pi/.bash_profile; then
    echo 'export APD_REPORT_DIR="/home/pi/apd-reports"' >> /home/pi/.bash_profile
fi

echo "==> [setup-image] Setting hostname..."
echo "apple-pi-diagnostics" > /etc/hostname
sed -i 's/raspberrypi/apple-pi-diagnostics/g' /etc/hosts 2>/dev/null || true

echo "==> [setup-image] Enabling SSH (useful for report retrieval)..."
systemctl enable ssh 2>/dev/null || true

echo "==> [setup-image] Cleaning up package cache..."
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "==> [setup-image] Done."
