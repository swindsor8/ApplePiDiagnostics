#!/bin/bash

# Test script for running failsafe diagnostics on actual Raspberry Pi
# This script helps test the initramfs on real hardware

PROJECT_ROOT="$(dirname $(dirname $(realpath $0)))"
INITRAMFS="$PROJECT_ROOT/build/initramfs.cpio.gz"

if [ ! -f "$INITRAMFS" ]; then
    echo "Error: Initramfs not found. Run build_failsafe.sh first."
    exit 1
fi

echo "=========================================="
echo "Raspberry Pi Failsafe Test Instructions"
echo "=========================================="
echo ""
echo "To test the failsafe initramfs on a Raspberry Pi:"
echo ""
echo "1. Copy the initramfs to your Pi's boot partition:"
echo "   scp $INITRAMFS pi@<pi-ip>:/boot/initramfs.cpio.gz"
echo ""
echo "2. On the Pi, edit /boot/config.txt and add:"
echo "   initramfs initramfs.cpio.gz followkernel"
echo ""
echo "3. Edit /boot/cmdline.txt and ensure it includes:"
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

