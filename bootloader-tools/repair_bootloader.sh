#!/usr/bin/env bash
# repair_bootloader.sh
# PREPARES a recovery folder that you can copy to a FAT32 partition for Raspberry Pi EEPROM recovery.
# THIS SCRIPT DOES NOT FLASH EEPROM AUTOMATICALLY.
# Steps:
#  1) Download official pieeprom.bin and recovery.bin from the Raspberry Pi Foundation
#  2) Place them under bootloader-tools/rpi-eeprom-tools/
#  3) Run this script to assemble a recovery FAT folder in bootloader-tools/recovery_sd/
#  4) Copy the contents of recovery_sd/ to a FAT32-formatted SD card boot partition and try booting the Pi

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
EERP_DIR="$BASE_DIR/rpi-eeprom-tools"
OUT_DIR="$BASE_DIR/recovery_sd"

mkdir -p "$OUT_DIR"

echo "Preparing recovery folder at: $OUT_DIR"

# Required files that must be provided by user (download from upstream)
REQUIRED_FILES=("pieeprom.bin" "recovery.bin" "recovery.conf" "bootconf.txt")

MISSING=()
for f in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "$EERP_DIR/$f" ]]; then
    MISSING+=("$f")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "The following required files are missing in $EERP_DIR:"
  for m in "${MISSING[@]}"; do
    echo "  - $m"
  done
  echo
  echo "Please download official EEPROM recovery files from the Raspberry Pi Foundation and place them in:"
  echo "  $EERP_DIR"
  echo "Refer to: https://www.raspberrypi.com/documentation/computers/raspberry-pi-4-uefi/ (or the official Pi EEPROM recovery docs)."
  exit 1
fi

# Copy files into the recovery folder
cp -v "$EERP_DIR/"{pieeprom.bin,recovery.bin,bootconf.txt,recovery.conf} "$OUT_DIR"/ || true

echo
echo "Recovery folder prepared. To create a bootable recovery SD card:"
cat <<INSTR

1) Format an SD card's first partition as FAT32 (BE CAREFUL: this will erase the partition).
   Example (replace /dev/sdX with your device):
     sudo mkfs.vfat -F32 /dev/sdX1

2) Mount the partition and copy the contents of:
     $OUT_DIR/* 
   to the root of the FAT32 partition.

3) Insert the SD card into the Raspberry Pi and power on. The Pi will attempt EEPROM recovery
   and indicate status via HDMI splash or LED codes.

IMPORTANT: This script does not attempt to flash EEPROM automatically. Review the files and the official docs before proceeding.
INSTR

echo
echo "repair_bootloader.sh finished."
