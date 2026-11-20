#!/bin/sh
echo "[STORAGE] Checking block devices..."
FOUND=0
for dev in /dev/mmcblk0 /dev/nvme0n1 /dev/sda; do
    if [ -b "$dev" ]; then
        echo "  Found block device: $dev"
        if dd if="$dev" of=/dev/null bs=512 count=1 2>/dev/null; then
            echo "  Read test OK: $dev"
            FOUND=1
        else
            echo "  FAIL: Read test failed on $dev"
        fi
    fi
done

if [ "$FOUND" -eq 0 ]; then
    echo "  FAIL: No readable storage device detected"
    exit 1
fi
echo "Storage check: OK"
exit 0
