#!/bin/bash
set -e

# Configuration
PROJECT_ROOT="$(dirname $(dirname $(realpath $0)))"
FAILSAFE_DIR="$PROJECT_ROOT/failsafe-env"
BUILD_DIR="$PROJECT_ROOT/build/failsafe_root"
OUTPUT_IMG="$PROJECT_ROOT/build/initramfs.cpio.gz"

echo "Building Failsafe Initramfs..."

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{bin,sbin,etc,proc,sys,dev,tmp,newroot}

# Install Busybox
# Attempts to use static busybox from host
if [ -f "/usr/bin/busybox-static" ]; then
    cp /usr/bin/busybox-static "$BUILD_DIR/bin/busybox"
elif command -v busybox >/dev/null; then
    echo "Warning: Using system busybox. Ensure it is statically linked."
    cp $(command -v busybox) "$BUILD_DIR/bin/busybox"
else
    echo "Error: Busybox not found. Please install busybox-static."
    exit 1
fi

# Create symlinks for busybox tools
chmod +x "$BUILD_DIR/bin/busybox"
pushd "$BUILD_DIR/bin" > /dev/null
./busybox --install -s .
popd > /dev/null

# Install Init Script
if [ -f "$PROJECT_ROOT/init" ]; then
    cp "$PROJECT_ROOT/init" "$BUILD_DIR/init"
    chmod +x "$BUILD_DIR/init"
else
    echo "Error: Init script not found at $PROJECT_ROOT/init"
    exit 1
fi

# Copy failsafe environment
# -r: recursive, -p: preserve permissions, -v: verbose
cp -rpv "$FAILSAFE_DIR/"* "$BUILD_DIR/"


# Create CPIO Archive
pushd "$BUILD_DIR" > /dev/null
find . -print0 | cpio --null -ov --format=newc | gzip -9 > "$OUTPUT_IMG"
popd > /dev/null

echo "Success! Initramfs created at $OUTPUT_IMG"