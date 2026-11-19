#!/bin/bash

# Test script for running failsafe diagnostics on actual Raspberry Pi
# This script helps test the initramfs on real hardware

PROJECT_ROOT="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
INITRAMFS="$PROJECT_ROOT/build/initramfs.cpio.gz"

if [ ! -f "$INITRAMFS" ]; then
    echo "Error: Initramfs not found. Run build_failsafe.sh first."
    exit 1
fi

echo "=========================================="
echo "Raspberry Pi Failsafe Test Instructions"
echo "=========================================="
echo ""
echo "Note: Raspberry Pi OS Bookworm mounts the boot partition at /boot/firmware"
echo "      (older Bullseye/Buster releases use /boot)."
echo ""
echo "To test the failsafe initramfs on a Raspberry Pi (build it on ARM64 / Pi):"
echo ""
echo "1. Copy the initramfs to your Pi's boot partition:"
echo "   scp $INITRAMFS pi@<pi-ip>:/tmp/initramfs.cpio.gz"
echo "   ssh pi@<pi-ip> 'sudo mv /tmp/initramfs.cpio.gz /boot/firmware/initramfs.cpio.gz'"
echo ""
echo "2. On the Pi, edit /boot/firmware/config.txt and add:"
echo "   initramfs initramfs.cpio.gz followkernel"
echo ""
echo "3. Edit /boot/firmware/cmdline.txt and ensure it includes:"
echo "   rdinit=/init"
echo ""
echo "4. Reboot the Pi:"
echo "   sudo reboot"
echo ""
echo "Expected Behavior:"
echo "  - LED will blink patterns based on diagnostics"
echo "  - Console will show diagnostic messages"
echo "  - On success: double blink, then boot to full system"
echo "  - On failure: rapid blink, stays in failsafe console"
echo ""
echo "Failure Mode Tests:"
echo "  - Remove SD card: Should detect failure and blink rapidly"
echo "  - Corrupt rootfs: Should detect and enter failsafe"
echo "  - Under-voltage: Should show warning with slow blink"
echo ""

