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
    xserver-xorg-core \
    xserver-xorg-legacy \
    xserver-xorg-input-libinput \
    xserver-xorg-video-fbdev \
    libgl1-mesa-dri \
    libegl1 \
    libgles2 \
    xinit \
    xauth \
    x11-xserver-utils \
    xfonts-base \
    openbox \
    dbus-x11 \
    unclutter \
    busybox-static \
    cpio \
    gzip \
    lm-sensors \
    usbutils \
    lshw \
    fonts-dejavu-core \
    fonts-liberation

# Install vcgencmd (raspi-utils on Bookworm; fall back to libraspberrypi-bin)
apt-get install -y --no-install-recommends raspi-utils \
    || apt-get install -y --no-install-recommends libraspberrypi-bin \
    || true

# Install GPIO libraries (python3-rpi-lgpio + gpiozero work on both Pi 4 & Pi 5)
apt-get install -y --no-install-recommends python3-gpiozero python3-rpi-lgpio \
    || apt-get install -y --no-install-recommends python3-rpi.gpio \
    || true

# Allow non-root startx on tty1 to open the console/DRM cleanly
mkdir -p /etc/X11 /etc/X11/xorg.conf.d
cat > /etc/X11/Xwrapper.config <<'EOF'
allowed_users=anybody
needs_root_rights=auto
EOF

# Ensure Xorg binds to the Pi 4/5 VC4 KMS display controller (not render-only v3d)
cat > /etc/X11/xorg.conf.d/99-vc4.conf <<'EOF'
Section "OutputClass"
    Identifier "vc4"
    MatchDriver "vc4"
    Driver "modesetting"
    Option "PrimaryGPU" "true"
EndSection
EOF

echo "==> [setup-image] Installing Python packages..."
pip3 install --break-system-packages --no-cache-dir \
    psutil \
    reportlab \
    Pillow \
    "qrcode[pil]"

echo "==> [setup-image] Building failsafe initramfs..."
cd "${APD_ROOT}"
bash build_failsafe.sh

# Copy ARM64 failsafe initramfs onto the boot partition so it is available
# immediately if failsafe mode is enabled in /boot/firmware/config.txt.
if [ -d /boot/firmware ] && [ -f "${APD_ROOT}/build/initramfs.cpio.gz" ]; then
    cp "${APD_ROOT}/build/initramfs.cpio.gz" /boot/firmware/apd-failsafe-initramfs.cpio.gz
fi

echo "==> [setup-image] Ensuring pi user exists and disabling first-boot wizard..."
if ! id -u pi >/dev/null 2>&1; then
    useradd -m -s /bin/bash pi
fi
# Ensure the pi account is not expired so agetty --autologin pi always succeeds
chage -d 19000 -E -1 pi 2>/dev/null || true
# Add pi to hardware/display/input groups if they exist on the image
for grp in video render input tty audio plugdev netdev dialout gpio i2c spi sudo; do
    if getent group "$grp" >/dev/null 2>&1; then
        usermod -aG "$grp" pi
    fi
done

# Disable Raspberry Pi OS Bookworm's interactive user-creation wizard so it
# never hijacks tty1 or renames the pi user out from under autologin.
# Note: userconf-pi ships with getty@tty1.service DISABLED until userconfig
# finishes, so we MUST explicitly unmask and enable getty@tty1.service below.
systemctl disable userconfig.service 2>/dev/null || true
systemctl mask userconfig.service 2>/dev/null || true
rm -f /etc/systemd/system/multi-user.target.wants/userconfig.service 2>/dev/null || true
systemctl disable piwiz.service 2>/dev/null || true

echo "==> [setup-image] Configuring and enabling auto-login on tty1..."
rm -f /etc/systemd/system/getty@tty1.service.d/*userconf* 2>/dev/null || true
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I $TERM
EOF

# Re-enable getty@tty1.service (disabled by default in Bookworm Lite by userconf-pi)
systemctl unmask getty@tty1.service 2>/dev/null || true
systemctl enable getty@tty1.service
if [ ! -L /etc/systemd/system/getty.target.wants/getty@tty1.service ]; then
    echo "ERROR: getty@tty1.service is not enabled in getty.target.wants!" >&2
    exit 1
fi

echo "==> [setup-image] Configuring auto-startx for pi user..."
mkdir -p /home/pi
if [ ! -f /home/pi/.bash_profile ]; then
    if [ -f /etc/skel/.profile ]; then
        cp /etc/skel/.profile /home/pi/.bash_profile
    else
        touch /home/pi/.bash_profile
    fi
fi
# Append the startx trigger (idempotent — skip if already present)
if ! grep -q "apple-pi-diagnostics" /home/pi/.bash_profile; then
    cat "${APD_ROOT}/deploy/bash_profile_append" >> /home/pi/.bash_profile
fi
chown pi:pi /home/pi/.bash_profile

echo "==> [setup-image] Creating /home/pi/apd-reports directory..."
mkdir -p /home/pi/apd-reports
chown -R pi:pi /home/pi/apd-reports

echo "==> [setup-image] Setting hostname..."
echo "apple-pi-diagnostics" > /etc/hostname
sed -i 's/raspberrypi/apple-pi-diagnostics/g' /etc/hosts 2>/dev/null || true

echo "==> [setup-image] Enabling SSH (useful for report retrieval)..."
systemctl enable ssh 2>/dev/null || true

echo "==> [setup-image] Running build-time smoke check..."
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "/opt/apple-pi-diagnostics/full-linux-gui/app")
import PyQt5.QtWidgets
import PyQt5.QtSvg
import psutil
import reportlab
import PIL
import qrcode
import config
from diagnostics.cpu.cpu_test import run_cpu_quick_test
from diagnostics.ram.ram_test import run_ram_quick_test
from diagnostics.storage.storage_test import run_storage_quick_test
from diagnostics.network.network_test import run_network_quick_test
from diagnostics.usb.usb_test import run_usb_quick_test
from diagnostics.hdmi.hdmi_test import run_hdmi_quick_test
from diagnostics.gpio.gpio_test import run_gpio_quick_test
print("All Python and diagnostic module imports OK.")
PYEOF

echo "==> [setup-image] Cleaning up package cache..."
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "==> [setup-image] Done."
