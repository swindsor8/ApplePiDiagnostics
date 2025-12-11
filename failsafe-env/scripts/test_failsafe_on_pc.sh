#!/usr/bin/env bash
echo "=== Simulating Apple Pi Failsafe Environment ==="
echo "Creating temporary rootfs staging area..."

TMPROOT="$(mktemp -d)"
cp -r ../failsafe-env/* "$TMPROOT/" 2>/dev/null || true

echo "Running failsafe_boot.sh..."
bash "$TMPROOT/init/failsafe_boot.sh"

echo "=== Simulation complete. Log ==="
cat "$TMPROOT/failsafe.log"

echo "Temporary staging directory: $TMPROOT"
