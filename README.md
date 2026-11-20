<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/e01d52fb-471a-48fe-9c54-1ace0a243588" />


# ApplePiDiagnostics
Apple Pi Diagnostics is a complete multi-stage hardware testing and recovery system for Raspberry Pi. It repairs bootloaders, runs failsafe diagnostics when Linux cannot boot, and provides a full GUI for CPU, RAM, storage, network, and GPIO tests with simple export options, including QR codes.

🍏 Apple Pi Diagnostics
A Complete All-In-One Hardware Diagnostic & Recovery Environment for Raspberry Pi

Apple Pi Diagnostics (APD) is a fully integrated, multi-stage diagnostic and recovery system designed to help users, makers, and technicians identify and fix Raspberry Pi hardware issues — even when the device cannot boot a normal operating system.

APD provides a reliable, user-friendly, and professional testing environment with a modern graphical interface, multiple export options, and support for every Raspberry Pi model.

⭐ Key Features
Bootloader-Level Recovery

APD can detect and repair:

Corrupt / missing EEPROM

Damaged bootloaders

Incorrect boot configuration

Unreadable partitions

This stage runs before Linux even loads.

Failsafe Framebuffer Mode

If the Pi cannot boot Linux, APD automatically launches into a minimal diagnostic mode that provides:

Basic hardware probing

SD card integrity checks

Power/voltage validation

Clear error explanations

Guidance to reach a full recovery

No desktop environment required.

Full Linux Diagnostic Environment

When the system can boot normally, APD loads a clean, modern GUI that supports:

### Full System Diagnostic Suite (10 Modules)
- **CPU** — multi-core load stress & temperature monitoring
- **RAM** — deterministic pattern write/read integrity & throughput testing
- **Storage** — MicroSD / USB / NVMe speed benchmarks, SD Card CID metadata, kernel MMC error scan, and SMART health
- **Power & Thermal** — `vcgencmd get_throttled` flag decoding (active & historical under-voltage / throttling), rail voltages, SoC temperature, and ARM clock
- **Network** — Ethernet/Wi-Fi interface status, ping, DNS latency, and built-in kiosk Wi-Fi setup (`nmcli`)
- **USB** — device enumeration (`lsusb`) & optional mounted drive speed test
- **HDMI** — display detection (`xrandr`, DRM sysfs, read-only `vcgencmd`) plus fullscreen color-bar / dead-pixel / audio pattern test
- **GPIO** — library detection (`RPi.GPIO` / `gpiozero`), optional loopback test, and read-only 40-pin header viewer
- **Bootloader & Board** — board model/serial/revision, EEPROM version/update status, and `/boot/firmware` health check
- **Peripherals** — read-only probes for I2C, SPI, Bluetooth, Audio, and CSI/V4L cameras

### Kiosk Appliance Features
- Live CPU, memory, temperature, and throttle telemetry on the Overview tab
- Built-in **Reboot** / **Shut Down** controls, **Wi-Fi Setup**, and **USB flash drive auto-mounting** (`udisks2`)
- Automatic release version stamping (`VERSION`) across the splash screen, header, reports, and download filenames (`apple-pi-diagnostics-<tag>.img.xz`)

### Flashing to a Raspberry Pi 4 / 5
1. Download the latest `apple-pi-diagnostics-<version>.img.xz` from [GitHub Releases](https://github.com/swindsor8/ApplePiDiagnostics/releases)
2. Open **Raspberry Pi Imager** → **Choose OS** → **Use custom** → select the `.img.xz` file
3. Select **No** when prompted to apply OS customisation settings
4. Flash to an SD card, insert into your Pi 4 or Pi 5, and power on — it boots straight into the GUI.

Report Export Options

RAM Test
--------

The project includes a programmable RAM diagnostic at `full-linux-gui/app/diagnostics/ram/ram_test.py`.

- CLI usage:

```bash
python3 full-linux-gui/app/diagnostics/ram/ram_test.py --total-mb 128 --chunk-mb 16 --passes 1
```

- GUI:
	- Open the app `full-linux-gui/app/main.py`, click `Run Individual Tests` and enable `RAM Test`.
	- Choose `Total MB`, `Chunk MB`, and `Passes` before pressing `Run Selected`.
	- Live progress appears in the dialog log; results report `status`, `tested_mb`, and throughput (MB/s).

Notes
-----
- The RAM test attempts to avoid allocating more than ~75% of available memory to reduce system instability. Adjust `Total MB` accordingly for thorough testing.
- The test writes a deterministic pattern to each buffer and verifies it on readback. Any mismatch is reported as `FAIL` in the result.

After a diagnostic session, users can save results using any of these built-in methods:

Save to USB Drive

Save to SD Card (Boot Partition)

View Report On Screen

Generate a QR Code

Scan with a phone

View report instantly

No internet required

🧩 Designed for All Users

Apple Pi Diagnostics is built for:

Raspberry Pi beginners

Repair technicians

Makers and educators

Businesses shipping Pi-based products

Anyone who needs reliable Pi hardware verification

No technical experience required — the software automates everything from bootloader repair to report generation.

🛠 How It Works (Three-Stage Architecture)
Stage 1 — Bootloader Recovery

Repairs critical boot components automatically.

Stage 2 — Failsafe Mode

Lightweight framebuffer UI that works even when Linux can't boot.

Stage 3 — Full Diagnostics GUI

A polished desktop environment powered by Python.

📦 Included Utilities

Bootloader repair tools

SD card health checker

EEPROM validator

Live system monitor

Log analyzer

Network tools

Hardware abstraction utilities

QR code generation module

One-click export functions

📁 Project Structure Overview

```
ApplePiDiagnostics/
├── bootloader-tools/     # Stage 1: EEPROM recovery & SD boot validation scripts
├── failsafe-env/         # Stage 2: BusyBox diagnostics & assets bundled in initramfs
├── init                  # Stage 2: Failsafe initramfs entry script & recovery menu
├── full-linux-gui/       # Stage 3: PyQt5 diagnostic GUI, modules, exports & tests
├── deploy/               # Pi OS Bookworm kiosk image setup (X11, openbox, polkit)
├── assets/               # Application logos & icons
├── scripts/              # Build/maintenance helpers (PiShrink pin updater, icons)
├── build-image.sh        # Builds flashable apple-pi-diagnostics-<ver>.img.xz
├── build_failsafe.sh     # Builds ARM64 failsafe initramfs
├── install.sh            # Local installation script on Debian/Ubuntu/Pi OS
├── VERSION               # Stamped application version
└── os_list.json          # Raspberry Pi Imager manifest
```

💡 Why Apple Pi Diagnostics?

Because troubleshooting Raspberry Pi hardware should be simple, reliable, and accessible to everyone, not a guessing game involving LEDs, config files, and multiple SD cards.

APD provides a single download that covers:

Boot issues

OS issues

Hardware issues

User-level diagnostics

Technician-level reporting

All in one clean, cohesive environment.
