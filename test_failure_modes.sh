#!/bin/bash

# Test script for different failure modes in QEMU
# Tests the failsafe initramfs with various failure scenarios

PROJECT_ROOT="$(dirname $(dirname $(realpath $0)))"
INITRAMFS="$PROJECT_ROOT/build/initramfs.cpio.gz"
KERNEL="${1:-$PROJECT_ROOT/build/kernel8.img}"
QEMU_CMD="qemu-system-aarch64"

if [ ! -f "$INITRAMFS" ]; then
    echo "Error: Initramfs not found. Run build_failsafe.sh first."
    exit 1
fi

if [ ! -f "$KERNEL" ]; then
    echo "Error: Kernel not found at $KERNEL"
    echo "Usage: $0 <path_to_kernel>"
    exit 1
fi

echo "=========================================="
echo "Apple Pi Diagnostics - Failure Mode Tests"
echo "=========================================="
echo ""

test_normal_boot() {
    echo "Test 1: Normal Boot (should succeed)"
    echo "-----------------------------------"
    $QEMU_CMD \
        -M raspi3b \
        -cpu cortex-a53 \
        -m 1G \
        -kernel "$KERNEL" \
        -initrd "$INITRAMFS" \
        -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init" \
        -drive file=/dev/zero,format=raw,if=sd,id=sd0 \
        -nographic \
        -serial mon:stdio &
    QEMU_PID=$!
    sleep 5
    kill $QEMU_PID 2>/dev/null || true
    wait $QEMU_PID 2>/dev/null || true
    echo ""
}

test_no_storage() {
    echo "Test 2: No Storage Device (should fail with LED blink)"
    echo "------------------------------------------------------"
    $QEMU_CMD \
        -M raspi3b \
        -cpu cortex-a53 \
        -m 1G \
        -kernel "$KERNEL" \
        -initrd "$INITRAMFS" \
        -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init" \
        -nographic \
        -serial mon:stdio &
    QEMU_PID=$!
    sleep 5
    kill $QEMU_PID 2>/dev/null || true
    wait $QEMU_PID 2>/dev/null || true
    echo ""
}

test_corrupt_root() {
    echo "Test 3: Corrupt Root Filesystem (should enter failsafe)"
    echo "-------------------------------------------------------"
    # Create a dummy corrupt filesystem
    TEMP_IMG=$(mktemp)
    dd if=/dev/zero of="$TEMP_IMG" bs=1M count=100 2>/dev/null
    
    $QEMU_CMD \
        -M raspi3b \
        -cpu cortex-a53 \
        -m 1G \
        -kernel "$KERNEL" \
        -initrd "$INITRAMFS" \
        -append "console=ttyAMA0 root=/dev/ram0 rdinit=/init" \
        -drive file="$TEMP_IMG",format=raw,if=sd,id=sd0 \
        -nographic \
        -serial mon:stdio &
    QEMU_PID=$!
    sleep 5
    kill $QEMU_PID 2>/dev/null || true
    wait $QEMU_PID 2>/dev/null || true
    rm -f "$TEMP_IMG"
    echo ""
}

# Menu
echo "Select test mode:"
echo "  1) Normal Boot"
echo "  2) No Storage Device"
echo "  3) Corrupt Root Filesystem"
echo "  4) Run All Tests"
echo ""
read -p "Choice [1-4]: " choice

case "$choice" in
    1)
        test_normal_boot
        ;;
    2)
        test_no_storage
        ;;
    3)
        test_corrupt_root
        ;;
    4)
        test_normal_boot
        test_no_storage
        test_corrupt_root
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo "Tests complete!"

