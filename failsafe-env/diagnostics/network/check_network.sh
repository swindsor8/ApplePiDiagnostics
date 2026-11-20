#!/bin/sh
echo "[NETWORK] Checking network interfaces..."
if [ ! -d /sys/class/net ]; then
    echo "  WARNING: /sys/class/net unavailable"
    exit 0
fi

UP_COUNT=0
for iface_path in /sys/class/net/*; do
    iface=$(basename "$iface_path")
    [ "$iface" = "lo" ] && continue
    state=$(cat "$iface_path/operstate" 2>/dev/null || echo "unknown")
    echo "  Interface $iface: $state"
    if [ "$state" = "up" ]; then
        UP_COUNT=$((UP_COUNT + 1))
    fi
done
echo "Active non-loopback interfaces: $UP_COUNT"
exit 0
