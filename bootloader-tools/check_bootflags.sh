#!/usr/bin/env bash
# check_bootflags.sh
# Non-destructive health checks for the SD/boot area.
# Usage: sudo ./check_bootflags.sh [device]
# If device is omitted, performs local filesystem checks.

set -euo pipefail

echo "=== Apple Pi Diagnostics: bootloader-tools/check_bootflags.sh ==="
DEVICE="${1:-}"

if [[ -n "$DEVICE" ]]; then
  echo "Checking device: $DEVICE"
  echo "Partition layout (fdisk):"
  sudo fdisk -l "$DEVICE" || true
  echo
  echo "Block devices (lsblk):"
  lsblk "$DEVICE" || true
else
  BOOT_DIR="/boot"
  if [[ -d /boot/firmware ]]; then
    BOOT_DIR="/boot/firmware"
  fi
  echo "No device specified. Inspecting local ${BOOT_DIR} and root filesystem."
  echo
  echo "Listing ${BOOT_DIR} contents:"
  ls -la "$BOOT_DIR" || echo "${BOOT_DIR} not mounted or not present."
  echo
  echo "Looking for common boot files:"
  for f in kernel8.img kernel.img vmlinuz bcm2711-rpi-4-b.dtb start4.elf config.txt cmdline.txt pieeprom.bin recovery.bin; do
    if [[ -e "${BOOT_DIR}/$f" ]]; then
      echo "  OK: ${BOOT_DIR}/$f"
    else
      echo "  MISSING: ${BOOT_DIR}/$f"
    fi
  done
fi

echo
echo "Checking for typical errors in system logs (last 200 lines of dmesg):"
dmesg | tail -n 200 || true

echo
echo "Check complete. For a deeper repair, run repair_bootloader.sh after placing official pieeprom files in bootloader-tools/rpi-eeprom-tools/."
