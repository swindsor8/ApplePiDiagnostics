#!/usr/bin/env bash
# validate_sd.sh
# Lightweight SD card validation for boot partition presence and basic file checks.
# Usage: sudo ./validate_sd.sh /dev/sdX

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: sudo $0 /dev/sdX"
  exit 2
fi

DEV="$1"
BOOTPART="${DEV}1"

echo "Validating SD device: $DEV"
echo "Checking if device exists..."
if [[ ! -b "$DEV" ]]; then
  echo "Device $DEV not found."
  exit 3
fi

echo "Attempting to mount boot partition $BOOTPART to /mnt/tmpboot"
sudo mkdir -p /mnt/tmpboot
sudo umount /mnt/tmpboot 2>/dev/null || true
if ! sudo mount "$BOOTPART" /mnt/tmpboot; then
  echo "Failed to mount $BOOTPART. Is the partition present and formatted as FAT32?"
  exit 4
fi

echo "Listing /boot-like files on SD card:"
ls -la /mnt/tmpboot || true

echo
echo "Checking for critical files:"
for f in kernel.img vmlinuz start4.elf pieeprom.bin recovery.bin config.txt; do
  if [[ -e /mnt/tmpboot/$f ]]; then
    echo "  FOUND: $f"
  else
    echo "  MISSING: $f"
  fi
done

echo
echo "Unmounting /mnt/tmpboot"
sudo umount /mnt/tmpboot

echo "Validation complete. If critical files are missing, use repair_bootloader.sh to prepare a recovery folder."
