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

Full System Diagnostic Suite

CPU stress & temperature testing

RAM integrity testing

SD card read/write benchmarking

USB, HDMI, and GPIO verification

Network (Ethernet/Wi-Fi) diagnostics

Power & voltage stability monitoring

Individual Test Selection

Run only what you need:

CPU test only

Network test only

SD card test only

etc.

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

Organized into:

bootloader_stage/

failsafe_stage/

linux_stage/

desktop_app/

pi_imager/

build_tools/

docs/

💡 Why Apple Pi Diagnostics?

Because troubleshooting Raspberry Pi hardware should be simple, reliable, and accessible to everyone, not a guessing game involving LEDs, config files, and multiple SD cards.

APD provides a single download that covers:

Boot issues

OS issues

Hardware issues

User-level diagnostics

Technician-level reporting

All in one clean, cohesive environment.
