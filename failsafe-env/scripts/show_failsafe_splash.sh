#!/bin/sh
# Attempt to display a PPM splash on framebuffer (fbi) or fallback to tty0 text.
PPM="assets/apple_pi_logo.ppm"
MSG="Apple Pi Diagnostics - Failsafe Mode"

# if fbi exists, use it (common on Pi OS)
if command -v fbi >/dev/null 2>&1 && [ -f "$PPM" ]; then
  # fbi requires framebuffer access; this is intended for Pi.
  sudo fbi -T 1 -d /dev/fb0 -noverbose -a "$PPM" || true
else
  # fallback: write minimal text to tty0
  echo "$MSG" > /dev/tty0 2>/dev/null || true
  echo "Failsafe: $MSG"
fi
