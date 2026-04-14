#!/bin/bash
# Apple Pi Diagnostics — Image Build Script
#
# Builds a flashable Raspberry Pi OS image that boots straight into the
# Apple Pi Diagnostics GUI. Produces:
#   apple-pi-diagnostics.img.xz        — compressed image for Pi Imager
#   apple-pi-diagnostics.img.xz.sha256 — checksum file
#
# Requirements (install on a Debian/Ubuntu x86-64 host):
#   sudo apt-get install kpartx qemu-user-static binfmt-support xz-utils \
#                        parted e2fsprogs rsync wget
#
# Usage:
#   sudo ./build-image.sh [--base-image path/to/base.img.xz]
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
MOUNT_BOOT="${BUILD_DIR}/mnt/boot"
MOUNT_ROOT="${BUILD_DIR}/mnt/root"
WORK_IMG="${BUILD_DIR}/apple-pi-diagnostics-work.img"
OUT_IMG="${SCRIPT_DIR}/apple-pi-diagnostics.img"
OUT_XZ="${OUT_IMG}.xz"
OUT_SHA="${OUT_XZ}.sha256"

# Base image — Raspberry Pi OS Lite 64-bit (Bookworm) 2025-05-13
BASE_URL="https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2025-05-13/2025-05-13-raspios-bookworm-arm64-lite.img.xz"
BASE_XZ="${BUILD_DIR}/base-raspios-lite-arm64.img.xz"
# SHA256 is fetched from the Pi servers alongside the image (see Step 1)
# so this script stays correct without manual hash updates on every release bump.

# Extra space to add to the image before chroot.
# X11 + PyQt5 + Python packages add ~600 MB; 3072 MB gives comfortable headroom.
EXTRA_SPACE_MB=3072

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[build-image] $*"; }
die()   { echo "[build-image] ERROR: $*" >&2; exit 1; }

require_root() {
    [ "$(id -u)" -eq 0 ] || die "This script must be run as root (use sudo)."
}

check_deps() {
    local missing=()
    for cmd in losetup kpartx qemu-aarch64-static parted resize2fs rsync wget xz sha256sum; do
        command -v "$cmd" &>/dev/null || missing+=("$cmd")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        die "Missing required tools: ${missing[*]}\n  Install with: sudo apt-get install kpartx qemu-user-static binfmt-support xz-utils parted e2fsprogs rsync wget"
    fi
}

cleanup() {
    info "Cleaning up mounts..."
    # Unmount bind mounts inside chroot
    for fs in dev/pts dev proc sys; do
        umount -lf "${MOUNT_ROOT}/${fs}" 2>/dev/null || true
    done
    # Unmount partitions
    umount -lf "${MOUNT_BOOT}" 2>/dev/null || true
    umount -lf "${MOUNT_ROOT}" 2>/dev/null || true
    # Remove device maps
    kpartx -d "${LOOP_DEV}" 2>/dev/null || true
    losetup -d "${LOOP_DEV}" 2>/dev/null || true
}

LOOP_DEV=""
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-image) BASE_XZ="$2"; shift 2 ;;
        *) die "Unknown argument: $1" ;;
    esac
done

# ---------------------------------------------------------------------------
# Step 0: Preflight
# ---------------------------------------------------------------------------
require_root
check_deps
mkdir -p "${BUILD_DIR}" "${MOUNT_BOOT}" "${MOUNT_ROOT}"

# ---------------------------------------------------------------------------
# Step 1: Download base image
# ---------------------------------------------------------------------------
if [ ! -f "${BASE_XZ}" ]; then
    info "Downloading base Raspberry Pi OS Lite (64-bit)..."
    wget --show-progress -O "${BASE_XZ}" "${BASE_URL}"
else
    info "Base image already cached at ${BASE_XZ}"
fi

info "Verifying base image SHA256 (fetching checksum from Pi servers)..."
wget -q -O "${BASE_XZ}.sha256" "${BASE_URL}.sha256" \
    || die "Failed to download SHA256 file from ${BASE_URL}.sha256"
EXPECTED_SHA256=$(awk '{print $1}' "${BASE_XZ}.sha256")
echo "${EXPECTED_SHA256}  ${BASE_XZ}" | sha256sum -c - || {
    info "WARNING: SHA256 mismatch — re-downloading base image..."
    rm -f "${BASE_XZ}"
    wget --show-progress -O "${BASE_XZ}" "${BASE_URL}"
    echo "${EXPECTED_SHA256}  ${BASE_XZ}" | sha256sum -c - \
        || die "Base image SHA256 verification failed after re-download."
}
rm -f "${BASE_XZ}.sha256"

# ---------------------------------------------------------------------------
# Step 2: Decompress to working image
# ---------------------------------------------------------------------------
info "Decompressing base image..."
rm -f "${WORK_IMG}"
xz -dk --stdout "${BASE_XZ}" > "${WORK_IMG}"

# ---------------------------------------------------------------------------
# Step 3: Expand image to make room for our packages
# ---------------------------------------------------------------------------
info "Expanding image by ${EXTRA_SPACE_MB} MB..."
truncate -s "+${EXTRA_SPACE_MB}M" "${WORK_IMG}"

# Extend the root partition to fill the new space
parted -s "${WORK_IMG}" resizepart 2 -- -1s

# ---------------------------------------------------------------------------
# Step 4: Set up loop device and partition maps
# ---------------------------------------------------------------------------
info "Attaching loop device..."
LOOP_DEV=$(losetup -fP --show "${WORK_IMG}")
kpartx -av "${LOOP_DEV}"

# Give udev a moment to create the device nodes
sleep 1

LOOP_BASE=$(basename "${LOOP_DEV}")
PART_BOOT="/dev/mapper/${LOOP_BASE}p1"
PART_ROOT="/dev/mapper/${LOOP_BASE}p2"

# Resize the root filesystem to fill the new partition
info "Resizing root filesystem..."
e2fsck -fy "${PART_ROOT}" || true
resize2fs "${PART_ROOT}"

# ---------------------------------------------------------------------------
# Step 5: Mount partitions
# ---------------------------------------------------------------------------
info "Mounting partitions..."
mount "${PART_ROOT}" "${MOUNT_ROOT}"
mount "${PART_BOOT}" "${MOUNT_BOOT}"
# Bind-mount the boot partition at its in-OS location too
mkdir -p "${MOUNT_ROOT}/boot/firmware"
mount --bind "${MOUNT_BOOT}" "${MOUNT_ROOT}/boot/firmware"

# ---------------------------------------------------------------------------
# Step 6: Set up QEMU for ARM64 emulation
# ---------------------------------------------------------------------------
info "Copying qemu-aarch64-static for chroot emulation..."
cp "$(command -v qemu-aarch64-static)" "${MOUNT_ROOT}/usr/bin/qemu-aarch64-static"

# Bind-mount kernel filesystems into chroot
for fs in proc sys dev dev/pts; do
    mount --bind "/${fs}" "${MOUNT_ROOT}/${fs}"
done

# ---------------------------------------------------------------------------
# Step 7: Copy Apple Pi Diagnostics into the image
# ---------------------------------------------------------------------------
info "Copying Apple Pi Diagnostics source..."
mkdir -p "${MOUNT_ROOT}/opt/apple-pi-diagnostics"
rsync -a --exclude='.git' \
         --exclude='venv' \
         --exclude='build' \
         --exclude='*.img' \
         --exclude='*.img.xz' \
         --exclude='*.sha256' \
         --exclude='full-linux-gui/reports' \
         --exclude='__pycache__' \
         --exclude='*.py[cod]' \
         --exclude='.pytest_cache' \
         --exclude='coverage.xml' \
         --exclude='htmlcov' \
         --exclude='.coverage' \
         --exclude='full-linux-gui/app/tests' \
         "${SCRIPT_DIR}/" \
         "${MOUNT_ROOT}/opt/apple-pi-diagnostics/"

# Make scripts executable
chmod +x "${MOUNT_ROOT}/opt/apple-pi-diagnostics/deploy/setup-image.sh"
chmod +x "${MOUNT_ROOT}/opt/apple-pi-diagnostics/build_failsafe.sh"
chmod +x "${MOUNT_ROOT}/opt/apple-pi-diagnostics/deploy/xinitrc"

# ---------------------------------------------------------------------------
# Step 8: Run chroot setup
# ---------------------------------------------------------------------------
info "Running setup-image.sh inside chroot..."
chroot "${MOUNT_ROOT}" /opt/apple-pi-diagnostics/deploy/setup-image.sh

# ---------------------------------------------------------------------------
# Step 9: First-boot flag — Pi OS expands filesystem on first boot; we skip that
# ---------------------------------------------------------------------------
# Remove the init_resize service so the image boots faster on first flash
rm -f "${MOUNT_ROOT}/etc/init.d/resize2fs_once" 2>/dev/null || true
systemctl --root="${MOUNT_ROOT}" disable resize2fs_once 2>/dev/null || true

# ---------------------------------------------------------------------------
# Step 10: Unmount
# ---------------------------------------------------------------------------
info "Unmounting..."
cleanup
trap - EXIT  # Cleanup already ran; disable the trap

# ---------------------------------------------------------------------------
# Step 11: Shrink image with PiShrink (download if not present)
# ---------------------------------------------------------------------------
PISHRINK="${BUILD_DIR}/pishrink.sh"
# Pin PiShrink to a specific commit to prevent supply-chain attacks via mutable
# 'master' branch.  Update PISHRINK_COMMIT and PISHRINK_SHA256 together whenever
# you intentionally upgrade PiShrink:
#   1. Pick a commit from https://github.com/Drewsif/PiShrink/commits/master
#   2. Download it: curl -fsSL "https://raw.githubusercontent.com/Drewsif/PiShrink/<commit>/pishrink.sh" | sha256sum
#   3. Set both variables below.
PISHRINK_COMMIT="a5f9463c01607ab07402c7e75c9cfd4bb3a0e886"
PISHRINK_SHA256="71026f0c02ac099e588a3eb8f70760c1b680aa8ea3acde61a0141fbaeb68c777"
PISHRINK_URL="https://raw.githubusercontent.com/Drewsif/PiShrink/${PISHRINK_COMMIT}/pishrink.sh"

if [ ! -f "${PISHRINK}" ]; then
    info "Downloading PiShrink (commit ${PISHRINK_COMMIT})..."
    wget -q -O "${PISHRINK}" "${PISHRINK_URL}"
fi

info "Verifying PiShrink integrity..."
ACTUAL_SHA256="$(sha256sum "${PISHRINK}" | awk '{print $1}')"
if [ "${ACTUAL_SHA256}" != "${PISHRINK_SHA256}" ]; then
    die "PiShrink checksum mismatch — expected ${PISHRINK_SHA256}, got ${ACTUAL_SHA256}. Delete ${PISHRINK} and re-run after updating PISHRINK_COMMIT and PISHRINK_SHA256."
fi
chmod +x "${PISHRINK}"

info "Shrinking image..."
cp "${WORK_IMG}" "${OUT_IMG}"
bash "${PISHRINK}" "${OUT_IMG}" || info "PiShrink encountered a non-fatal issue; continuing."

# ---------------------------------------------------------------------------
# Step 12: Compress and checksum
# ---------------------------------------------------------------------------
info "Compressing image (this takes a few minutes)..."
rm -f "${OUT_XZ}"
xz -T0 -9 --keep "${OUT_IMG}"
mv "${OUT_IMG}.xz" "${OUT_XZ}" 2>/dev/null || true

info "Generating SHA256 checksum..."
sha256sum "${OUT_XZ}" > "${OUT_SHA}"

# Print final sizes for os_list.json
XZ_SIZE=$(stat -c%s "${OUT_XZ}")
RAW_SIZE=$(stat -c%s "${OUT_IMG}")
SHA256=$(awk '{print $1}' "${OUT_SHA}")

info "============================================"
info "Build complete!"
info "  Image:            ${OUT_XZ}"
info "  Compressed size:  ${XZ_SIZE} bytes"
info "  Extracted size:   ${RAW_SIZE} bytes"
info "  SHA256:           ${SHA256}"
info "============================================"
info "Update os_list.json with the above values before publishing."
