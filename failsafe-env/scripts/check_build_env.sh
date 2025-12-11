#!/usr/bin/env bash
echo "=== Checking build environment for Apple Pi Diagnostics ==="

echo -n "Checking for dracut... "
command -v dracut && echo OK || echo MISSING

echo -n "Checking for cpio... "
command -v cpio && echo OK || echo MISSING

echo -n "Checking for mkinitrd... "
command -v mkinitrd && echo OK || echo MISSING

echo -n "Checking for gzip... "
command -v gzip && echo OK || echo MISSING

echo -n "Checking for mkfs tools... "
command -v mkfs.vfat && echo OK || echo MISSING
