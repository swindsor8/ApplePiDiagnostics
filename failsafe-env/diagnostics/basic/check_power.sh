#!/bin/sh
echo "[BASIC] Checking power and thermal status..."
THROTTLE_FILE="/sys/devices/platform/soc/soc:firmware/get_throttled"
if [ -f "$THROTTLE_FILE" ]; then
    VAL=$(cat "$THROTTLE_FILE" 2>/dev/null || echo "unknown")
    echo "  get_throttled: $VAL"
    if [ "$VAL" != "0" ] && [ "$VAL" != "0x0" ] && [ "$VAL" != "unknown" ]; then
        echo "  WARNING: Under-voltage or thermal throttling flag set ($VAL)"
        exit 1
    fi
else
    echo "  Firmware throttle sysfs unavailable (expected outside Raspberry Pi)"
fi

TZ="/sys/class/thermal/thermal_zone0/temp"
if [ -f "$TZ" ]; then
    RAW_T=$(cat "$TZ" 2>/dev/null || echo "0")
    echo "  SoC temp (millideg C): $RAW_T"
fi
echo "Power check: OK"
exit 0
