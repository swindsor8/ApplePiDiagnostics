#!/bin/bash

# Wrapper to test the failsafe initramfs in QEMU
# Usage: ./test_qemu.sh [path_to_kernel_image] [options]

PROJECT_ROOT="$(dirname $(dirname $(realpath $0)))"
INITRAMFS="$PROJECT_ROOT/build/initramfs.cpio.gz"
KERNEL="${1:-$PROJECT_ROOT/build/kernel8.img}"
GRAPHIC="${2:-nographic}"

if [ ! -f "$INITRAMFS" ]; then
    echo "Error: Initramfs not found. Run build_failsafe.sh first."
    echo ""
    echo "To build the initramfs, run:"
    echo "  ./ApplePiDiagnostics/build_failsafe.sh"
    exit 1
fi

if [ ! -f "$KERNEL" ]; then
    echo "Error: Kernel not found at $KERNEL."
    echo ""
    echo "Usage: $0 <path_to_kernel> [graphic|nographic]"
    echo ""
    echo "You can download a Raspberry Pi kernel from:"
    echo "  https://github.com/raspberrypi/firmware/tree/master/boot"
    echo "  (Look for kernel8.img for Pi 3/4)"
    exit 1
fi

echo "=========================================="
echo "Testing Failsafe Initramfs in QEMU"
echo "=========================================="
echo "Kernel:  $KERNEL"
echo "Initramfs: $INITRAMFS"
echo "Mode:    $GRAPHIC"
echo ""
echo "Starting QEMU (Raspi 3B Emulation)..."
echo "Press Ctrl+A then X to exit QEMU"
echo ""

if [ "$GRAPHIC" = "graphic" ]; then
    qemu-system-aarch64 \
        -M raspi3b \
        -cpu cortex-a53 \
        -m 1G \
        -kernel "$KERNEL" \
        -initrd "$INITRAMFS" \
        -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init" \
        -serial stdio \
        -display gtk
else
    qemu-system-aarch64 \
        -M raspi3b \
        -cpu cortex-a53 \
        -m 1G \
        -kernel "$KERNEL" \
        -initrd "$INITRAMFS" \
        -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init" \
        -nographic \
        -serial mon:stdio
fi