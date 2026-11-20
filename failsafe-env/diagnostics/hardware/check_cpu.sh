#!/bin/sh
echo "[HARDWARE] Checking CPU and memory..."
if [ -f /proc/cpuinfo ]; then
    CORES=$(grep -c "^processor" /proc/cpuinfo 2>/dev/null || echo "0")
    echo "  CPU cores: $CORES"
    if [ "$CORES" -le 0 ]; then
        echo "  FAIL: No CPU cores detected"
        exit 1
    fi
else
    echo "  FAIL: /proc/cpuinfo missing"
    exit 1
fi

if [ -f /proc/meminfo ]; then
    MEM_TOTAL=$(grep "^MemTotal:" /proc/meminfo 2>/dev/null || echo "unknown")
    echo "  $MEM_TOTAL"
fi
echo "CPU/RAM check: OK"
exit 0
