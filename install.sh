#!/bin/bash
set -e

# Apple Pi Diagnostics Installation Script
# This script installs all dependencies and sets up the environment

echo "=========================================="
echo "Apple Pi Diagnostics Installation Script"
echo "=========================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please do not run this script as root. Use a regular user account."
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo "Cannot detect OS. This script supports Debian/Ubuntu and derivatives."
    exit 1
fi

echo "Detected OS: $OS $VER"

# Install system dependencies based on OS
if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]] || [[ "$OS" == *"Raspbian"* ]]; then
    echo "Installing system dependencies for Debian/Ubuntu-based system..."
    
    # Update package list
    sudo apt update
    
    # Install required packages
    sudo apt install -y python3 python3-pip python3-venv python3-dev
    sudo apt install -y PyQt5-dev python3-pyqt5 python3-pyqt5.qtsvg
    sudo apt install -y busybox-static cpio gzip
    sudo apt install -y qrencode  # For QR code generation
    sudo apt install -y usbutils  # For USB device detection
    sudo apt install -y lshw       # For hardware information
    sudo apt install -y lm-sensors # For temperature monitoring
    
    # Install optional packages for better functionality
    sudo apt install -y python3-psutil python3-pil python3-reportlab
    
else
    echo "Unsupported OS: $OS"
    echo "Please install the following manually:"
    echo "- Python 3.8+ with pip and venv"
    echo "- PyQt5 development packages"
    echo "- busybox-static"
    echo "- cpio and gzip"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing Python dependencies..."

# Create virtual environment for GUI
cd full-linux-gui
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment and install packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Building failsafe initramfs..."
cd ..
./build_failsafe.sh

echo "Creating desktop entry..."
# Create desktop entry for easy access
cat > ~/.local/share/applications/apple-pi-diagnostics.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Apple Pi Diagnostics
Comment=Complete hardware diagnostic and recovery system for Raspberry Pi
Exec=$SCRIPT_DIR/full-linux-gui/venv/bin/python $SCRIPT_DIR/full-linux-gui/app/main.py
Icon=$SCRIPT_DIR/assets/icon.png
Terminal=false
Categories=System;HardwareSettings;
EOF

# Create symbolic link for easy command line access
mkdir -p ~/.local/bin
ln -sf "$SCRIPT_DIR/full-linux-gui/venv/bin/python" ~/.local/bin/apd-gui 2>/dev/null || true

echo ""
echo "=========================================="
echo "Installation completed successfully!"
echo "=========================================="
echo ""
echo "To run Apple Pi Diagnostics:"
echo "  GUI:    Launch 'Apple Pi Diagnostics' from your application menu"
echo "          or run: $SCRIPT_DIR/full-linux-gui/venv/bin/python $SCRIPT_DIR/full-linux-gui/app/main.py"
echo ""
echo "  Failsafe: The initramfs is built and ready at:"
echo "          $SCRIPT_DIR/build/initramfs.cpio.gz"
echo ""
echo "To test failsafe mode on a Raspberry Pi:"
echo "  1. Copy build/initramfs.cpio.gz to /boot/ on your Pi"
echo "  2. Add 'initramfs initramfs.cpio.gz followkernel' to /boot/config.txt"
echo "  3. Add 'rdinit=/init' to /boot/cmdline.txt"
echo "  4. Reboot the Pi"
echo ""
echo "For more information, see README.md and FAILSAFE_README.md"
