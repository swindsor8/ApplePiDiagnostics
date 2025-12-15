#!/bin/bash
set -e

# Configuration
PROJECT_ROOT="$(dirname $(dirname $(realpath $0)))"
FAILSAFE_DIR="$PROJECT_ROOT/ApplePiDiagnostics/failsafe-env"
BUILD_DIR="$PROJECT_ROOT/build/failsafe_root"
OUTPUT_IMG="$PROJECT_ROOT/build/initramfs.cpio.gz"
INIT_SCRIPT="$PROJECT_ROOT/ApplePiDiagnostics/init"

echo "=========================================="
echo "Building Failsafe Initramfs"
echo "=========================================="
echo "Project Root: $PROJECT_ROOT"
echo "Build Dir:   $BUILD_DIR"
echo "Output:      $OUTPUT_IMG"
echo ""

# Clean previous build
echo "Cleaning previous build..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{bin,sbin,etc,proc,sys,dev,tmp,newroot,run,diagnostics/{basic,hardware,network,storage},init,scripts}

# Install Busybox
echo "Installing Busybox..."
if [ -f "/usr/bin/busybox-static" ]; then
    cp /usr/bin/busybox-static "$BUILD_DIR/bin/busybox"
    echo "  Using busybox-static from /usr/bin"
elif command -v busybox >/dev/null; then
    BUSYBOX_PATH=$(command -v busybox)
    # Check if it's static
    if ldd "$BUSYBOX_PATH" 2>/dev/null | grep -q "not a dynamic"; then
        cp "$BUSYBOX_PATH" "$BUILD_DIR/bin/busybox"
        echo "  Using static busybox from $BUSYBOX_PATH"
    else
        echo "  WARNING: Using system busybox. It may not be statically linked."
        echo "  For best results, install busybox-static package."
        cp "$BUSYBOX_PATH" "$BUILD_DIR/bin/busybox"
    fi
else
    echo "ERROR: Busybox not found. Please install busybox-static."
    echo "  On Debian/Ubuntu: sudo apt-get install busybox-static"
    echo "  On Fedora: sudo dnf install busybox"
    exit 1
fi

# Create symlinks for busybox tools
chmod +x "$BUILD_DIR/bin/busybox"
echo "Creating busybox symlinks..."
pushd "$BUILD_DIR/bin" > /dev/null
./busybox --install -s . 2>/dev/null || {
    # Fallback: create essential symlinks manually
    for cmd in sh mount umount mkdir rmdir ls cp mv rm cat echo sleep dd grep switch_root; do
        ln -sf busybox "$cmd" 2>/dev/null || true
    done
}
popd > /dev/null

# Install Init Script
echo "Installing init script..."
if [ -f "$INIT_SCRIPT" ]; then
    cp "$INIT_SCRIPT" "$BUILD_DIR/init"
    chmod +x "$BUILD_DIR/init"
    echo "  Init script installed"
else
    echo "ERROR: Init script not found at $INIT_SCRIPT"
    exit 1
fi

# Copy failsafe environment
echo "Copying failsafe environment..."
if [ -d "$FAILSAFE_DIR" ]; then
    # Copy diagnostics scripts
    if [ -d "$FAILSAFE_DIR/diagnostics" ]; then
        cp -rp "$FAILSAFE_DIR/diagnostics"/* "$BUILD_DIR/diagnostics/" 2>/dev/null || true
        # Make all diagnostic scripts executable
        find "$BUILD_DIR/diagnostics" -type f -name "*.sh" -exec chmod +x {} \;
    fi
    
    # Copy init scripts
    if [ -d "$FAILSAFE_DIR/init" ]; then
        cp -rp "$FAILSAFE_DIR/init"/* "$BUILD_DIR/init/" 2>/dev/null || true
        find "$BUILD_DIR/init" -type f -name "*.sh" -exec chmod +x {} \;
    fi
    
    # Copy other scripts
    if [ -d "$FAILSAFE_DIR/scripts" ]; then
        cp -rp "$FAILSAFE_DIR/scripts"/* "$BUILD_DIR/scripts/" 2>/dev/null || true
        find "$BUILD_DIR/scripts" -type f -name "*.sh" -exec chmod +x {} \;
    fi
    
    echo "  Failsafe environment copied"
else
    echo "  WARNING: Failsafe directory not found at $FAILSAFE_DIR"
fi

# Create essential device nodes (if needed)
echo "Creating device nodes..."
[ -c "$BUILD_DIR/dev/console" ] || mknod "$BUILD_DIR/dev/console" c 5 1 2>/dev/null || true
[ -c "$BUILD_DIR/dev/null" ] || mknod "$BUILD_DIR/dev/null" c 1 3 2>/dev/null || true
[ -c "$BUILD_DIR/dev/zero" ] || mknod "$BUILD_DIR/dev/zero" c 1 5 2>/dev/null || true

# Create CPIO Archive
echo "Creating CPIO archive..."
mkdir -p "$(dirname "$OUTPUT_IMG")"
pushd "$BUILD_DIR" > /dev/null

# Use find with proper null termination for cpio
if command -v cpio >/dev/null; then
    find . -print0 | cpio --null -ov --format=newc 2>/dev/null | gzip -9 > "$OUTPUT_IMG"
    CPIO_SIZE=$(stat -c%s "$OUTPUT_IMG" 2>/dev/null || stat -f%z "$OUTPUT_IMG" 2>/dev/null || echo "unknown")
    echo "  Archive created: $(numfmt --to=iec-i --suffix=B $CPIO_SIZE 2>/dev/null || echo "${CPIO_SIZE} bytes")"
else
    echo "ERROR: cpio not found. Please install cpio."
    exit 1
fi

popd > /dev/null

echo ""
echo "=========================================="
echo "SUCCESS! Initramfs created at:"
echo "  $OUTPUT_IMG"
echo "=========================================="
echo ""
echo "To test in QEMU, run:"
echo "  ./ApplePiDiagnostics/test_qemu.sh <kernel_image>"
echo ""