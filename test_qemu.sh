#!/bin/bash

# Wrapper to test the failsafe initramfs in QEMU
# Usage: ./test_qemu.sh [path_to_kernel_image]

PROJECT_ROOT="$(dirname $(dirname $(realpath $0)))"
INITRAMFS="$PROJECT_ROOT/build/initramfs.cpio.gz"
KERNEL="${1:-$PROJECT_ROOT/build/kernel8.img}"

if [ ! -f "$INITRAMFS" ]; then
    echo "Error: Initramfs not found. Run build_failsafe.sh first."
    exit 1
fi

if [ ! -f "$KERNEL" ]; then
    echo "Error: Kernel not found at $KERNEL."
    echo "Usage: $0 <path_to_kernel>"
    exit 1
fi

echo "Starting QEMU (Raspi 3B Emulation)..."
qemu-system-aarch64 \
    -M raspi3b \
    -cpu cortex-a53 \
    -m 1G \
    -kernel "$KERNEL" \
    -initrd "$INITRAMFS" \
    -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init" \
    -nographic \
    -serial mon:stdio