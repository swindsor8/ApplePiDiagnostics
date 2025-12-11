#!/bin/sh
# Apple Pi Diagnostics - Failsafe Boot Script
# Runs when Linux fails or during pre-Linux initialization.

LOG_FILE="/failsafe.log"

echo "=== Apple Pi Diagnostics Failsafe Boot ===" | tee -a $LOG_FILE
echo "[INFO] Starting minimal framebuffer diagnostics..." | tee -a $LOG_FILE

# Basic framebuffer message
# Works on almost all Raspberry Pi models without X11 or Wayland
fb_console() {
    echo "[FB] $1" >> $LOG_FILE
    echo "$1" > /dev/tty0 2>/dev/null || true
}

fb_console "Apple Pi Diagnostics - Failsafe Mode"
fb_console "Initializing minimal system..."

# Run basic diagnostics
for D in /diagnostics/basic/*.sh; do
    if [ -x "$D" ]; then
        fb_console "Running $(basename $D)..."
        "$D" >> $LOG_FILE 2>&1
    fi
done

# Storage tests
for D in /diagnostics/storage/*.sh; do
    if [ -x "$D" ]; then
        fb_console "Running $(basename $D)..."
        "$D" >> $LOG_FILE 2>&1
    fi
done

# Hardware tests
for D in /diagnostics/hardware/*.sh; do
    if [ -x "$D" ]; then
        fb_console "Running $(basename $D)..."
        "$D" >> $LOG_FILE 2>&1
    fi
done

# Network tests
for D in /diagnostics/network/*.sh; do
    if [ -x "$D" ]; then
        fb_console "Running $(basename $D)..."
        "$D" >> $LOG_FILE 2>&1
    fi
done

fb_console "Failsafe diagnostics complete."
fb_console "If possible, loading full Apple Pi Diagnostics OS..."
exit 0
