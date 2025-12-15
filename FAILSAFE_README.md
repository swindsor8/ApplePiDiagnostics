# Apple Pi Diagnostics - Failsafe Stage

The failsafe stage provides hardware diagnostics and recovery when the main Linux system cannot boot. It runs from an initramfs before the main root filesystem is mounted.

## Features

- **Hardware Diagnostics**: Automatic checks for storage, power, and CPU
- **LED Indicators**: Visual feedback via ACT LED with different blink patterns
- **Framebuffer Display**: Text output on display (when available)
- **Failure Detection**: Detects and reports hardware failures
- **Automatic Recovery**: Attempts to boot main system if hardware is healthy

## LED Indicator Patterns

- **Success (Double Blink)**: Quick double blink, then solid on
  - All hardware checks passed
  - System will boot to full GUI

- **Warning (Slow Blink)**: Slow on/off pattern
  - Non-critical issues detected (e.g., under-voltage)
  - System may still boot

- **Failure (Rapid Blink)**: Fast on/off loop
  - Critical hardware failure detected
  - System enters failsafe console

## Building the Initramfs

```bash
cd Apple-Pi-Diagnostics
./ApplePiDiagnostics/build_failsafe.sh
```

This creates `build/initramfs.cpio.gz` containing:
- Busybox (static binary)
- Init script with diagnostics
- Failsafe environment scripts
- Essential device nodes

## Testing in QEMU

### Basic Test
```bash
./ApplePiDiagnostics/test_qemu.sh <path_to_kernel8.img>
```

### Test Different Failure Modes
```bash
./ApplePiDiagnostics/test_failure_modes.sh <path_to_kernel8.img>
```

Options:
1. Normal Boot - Should succeed and attempt to boot
2. No Storage - Should detect failure and blink rapidly
3. Corrupt Root - Should enter failsafe mode

### Graphical Mode
```bash
./ApplePiDiagnostics/test_qemu.sh <kernel> graphic
```

## Testing on Real Raspberry Pi

1. **Build the initramfs** (on your development machine):
   ```bash
   ./ApplePiDiagnostics/build_failsafe.sh
   ```

2. **Copy to Pi's boot partition**:
   ```bash
   scp build/initramfs.cpio.gz pi@<pi-ip>:/boot/
   ```

3. **Configure boot** (on the Pi):
   Edit `/boot/config.txt` and add:
   ```
   initramfs initramfs.cpio.gz followkernel
   ```

   Edit `/boot/cmdline.txt` and ensure it includes:
   ```
   rdinit=/init
   ```

4. **Reboot and observe**:
   - Watch the ACT LED for blink patterns
   - Check console output for diagnostic messages
   - System should boot to full GUI on success

## Failure Mode Testing on Pi

### Test 1: Remove SD Card
- Power on Pi without SD card
- Expected: Rapid LED blink, no boot

### Test 2: Corrupt Root Filesystem
- Create a test SD with corrupted root partition
- Expected: Slow blink, failsafe console

### Test 3: Under-Voltage
- Use insufficient power supply
- Expected: Warning message, slow blink, may still boot

## Diagnostic Checks

The failsafe init performs these checks:

1. **Storage Check**
   - Verifies `/dev/mmcblk0` exists
   - Tests read access to storage device
   - Critical: System cannot boot without storage

2. **Power Check**
   - Reads `/sys/devices/platform/soc/soc:firmware/get_throttled`
   - Detects under-voltage conditions
   - Warning: May cause instability but not fatal

3. **CPU Check**
   - Verifies CPU is detected via `/proc/cpuinfo`
   - Counts available CPU cores
   - Critical: System cannot function without CPU

## Console Output

The failsafe init provides detailed console output:

```
========================================
Apple Pi Diagnostics - Failsafe Mode
========================================

Checking Storage...
[OK] Storage device accessible
Checking Power...
[OK] Power supply adequate
Checking CPU...
[OK] CPU detected (4 cores)

========================================
Diagnostics Summary:
  Passed:  3
  Warnings: 0
  Failed:  0
========================================

[SUCCESS] Root filesystem valid. Switching to full system...
```

## Troubleshooting

### Initramfs too large
- Ensure using static busybox
- Remove unnecessary files from failsafe-env
- Check compression with `gzip -9`

### LED not working
- Verify LED path exists: `/sys/class/leds/ACT` or `/sys/class/leds/led0`
- Check permissions on LED brightness file
- Some Pi models may use different LED names

### Framebuffer not displaying
- Ensure framebuffer device exists: `/dev/fb0`
- Check kernel framebuffer support
- Console output will still work via serial

### Boot loop
- Check init script syntax
- Verify busybox is statically linked
- Test initramfs in QEMU first

## Integration with Main System

On successful hardware check, the failsafe init:
1. Mounts the root filesystem read-only
2. Verifies `/sbin/init` or systemd exists
3. Unmounts temporary filesystems
4. Executes `switch_root` to hand over to main system

If any critical check fails, the system:
1. Enters failsafe console (`/bin/sh`)
2. Provides diagnostic information
3. Allows manual recovery attempts

## Development

To modify the failsafe behavior:
1. Edit `ApplePiDiagnostics/init` - Main init script
2. Edit scripts in `failsafe-env/diagnostics/` - Diagnostic checks
3. Rebuild: `./ApplePiDiagnostics/build_failsafe.sh`
4. Test: `./ApplePiDiagnostics/test_qemu.sh <kernel>`

## Requirements

- `busybox-static` or statically-linked busybox
- `cpio` for archive creation
- `gzip` for compression
- QEMU (for testing): `qemu-system-aarch64`
- Raspberry Pi kernel image (for testing)

