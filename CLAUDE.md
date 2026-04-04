# CLAUDE.md — Apple Pi Diagnostics

## Project Overview

Apple Pi Diagnostics (APD) is a three-stage hardware diagnostic and recovery system for Raspberry Pi, built in Python with PyQt5. It covers everything from pre-boot bootloader repair through a failsafe framebuffer mode to a full GUI diagnostic suite.

### Three-Stage Architecture

| Stage | Entry point | Runs when |
|-------|-------------|-----------|
| 1 — Bootloader Recovery | `bootloader-tools/` | EEPROM/bootloader is corrupt |
| 2 — Failsafe Mode | `init` (shell script) | Linux cannot boot; uses initramfs |
| 3 — Full GUI | `full-linux-gui/app/main.py` | Normal Linux boot |

---

## Repository Layout

```
ApplePiDiagnostics/
├── full-linux-gui/
│   ├── app/
│   │   ├── main.py                  # Entry point; MainWindow + startup logic
│   │   ├── gui/
│   │   │   └── splash.py            # SplashScreen with live pre-boot checks
│   │   ├── diagnostics/
│   │   │   ├── cpu/cpu_test.py
│   │   │   ├── ram/ram_test.py
│   │   │   ├── storage/storage_test.py
│   │   │   ├── network/network_test.py
│   │   │   ├── usb/usb_test.py
│   │   │   ├── hdmi/hdmi_test.py
│   │   │   ├── gpio/gpio_test.py
│   │   │   └── report_builder.py
│   │   ├── exports/
│   │   │   ├── export_usb.py
│   │   │   ├── export_sd_boot.py
│   │   │   └── export_qr.py
│   │   └── assets/                  # Logo images
│   ├── requirements.txt
│   └── reports/                     # Generated report output
├── failsafe-env/                    # Files bundled into the initramfs
├── bootloader-tools/                # EEPROM / bootloader repair utilities
├── init                             # Failsafe init shell script
├── build_failsafe.sh                # Builds the failsafe initramfs
├── install.sh                       # End-user setup script
├── test_qemu.sh                     # QEMU-based failsafe tests
└── test_failure_modes.sh            # Failure mode simulation tests
```

---

## Development Setup

```bash
# Install Python dependencies
cd full-linux-gui
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the GUI
cd app
python3 main.py
```

System packages needed (Debian/Raspberry Pi OS):
```bash
sudo apt install python3-pyqt5 python3-pyqt5.qtsvg busybox-static cpio gzip
```

---

## Running the GUI

```bash
cd full-linux-gui
source venv/bin/activate
python3 app/main.py
```

On a headless machine, set the display before launching:
```bash
export DISPLAY=:0
# or for offscreen testing:
export QT_QPA_PLATFORM=offscreen
```

---

## Startup Sequence

1. `main()` creates QApplication
2. `SplashScreen` runs 4 pre-boot checks live (system info, storage, network, diagnostics ready), then closes
3. `MainWindow` is created; `show_startup_banner(results)` adds a green/amber banner below the header summarising the check results (auto-dismisses after 8 s)
4. User interacts with 4-tab dashboard (Overview, Testing, Results, Settings)

---

## Diagnostic Modules

Each module lives in `full-linux-gui/app/diagnostics/<name>/` and exposes a single `run_<name>_quick_test()` function returning a dict with at minimum:

```python
{
    "status": "OK" | "WARNING" | "FAIL" | "UNSUPPORTED",
    # ...module-specific keys...
}
```

### Testing a module in isolation

```bash
cd full-linux-gui/app
source ../../venv/bin/activate

python3 -c "
from diagnostics.cpu.cpu_test import run_cpu_quick_test
import json; print(json.dumps(run_cpu_quick_test(), indent=2))
"
```

Replace `cpu` / `run_cpu_quick_test` with any module name. Available modules:

| Module | Function |
|--------|----------|
| cpu | `run_cpu_quick_test()` |
| ram | `run_ram_quick_test()` |
| storage | `run_storage_quick_test()` |
| network | `run_network_quick_test()` |
| usb | `run_usb_quick_test()` |
| hdmi | `run_hdmi_quick_test()` |
| gpio | `run_gpio_quick_test()` |

### RAM test CLI

```bash
python3 full-linux-gui/app/diagnostics/ram/ram_test.py \
    --total-mb 128 --chunk-mb 16 --passes 1
```

---

## Adding a New Diagnostic Module

1. Create `full-linux-gui/app/diagnostics/<name>/` with `__init__.py` and `<name>_test.py`
2. Implement `run_<name>_quick_test() -> dict` — must include a `"status"` key
3. Add the import and call in `main.py` (follow the pattern of the existing seven modules)
4. Add the module to the `_check_diagnostics()` check list in `gui/splash.py` so it is validated at startup

---

## Report Generation & Export

Reports are built by `diagnostics/report_builder.py` using ReportLab (PDF) and standard HTML:

```python
from diagnostics.report_builder import build_report
build_report(results_dict, output_dir)
```

Export helpers:

| Module | Function | Destination |
|--------|----------|-------------|
| `export_usb.py` | `save_report_to_usb()` | `/media/<user>/Apple-Pi-Diagnostics/` |
| `export_sd_boot.py` | `save_report_to_sdboot()` | SD card boot partition |
| `export_qr.py` | `generate_qr_image()` | QR code linking to local HTTP server |

---

## Failsafe Mode

The failsafe runs as an initramfs `init` script before the main filesystem mounts.

```bash
# Build the initramfs
./build_failsafe.sh

# Test in QEMU
./test_qemu.sh <path_to_kernel_image>

# Test failure scenarios
./test_failure_modes.sh <path_to_kernel_image>
```

Checks performed by the `init` script:
- Storage — `/dev/mmcblk0` accessible
- Power — under-voltage flag via `/sys/devices/platform/soc/soc:firmware/get_throttled`
- CPU — `/proc/cpuinfo` readable

LED output codes: double-blink = success → boots to GUI; slow blink = warning; rapid blink = critical failure → failsafe console.

---

## Code Style

- Python 3.8+, PEP 8
- All UI updates from threads must use `QtCore.QMetaObject.invokeMethod()` (thread safety)
- Diagnostic functions must not block the Qt event loop — run in `threading.Thread(daemon=True)`
- New widgets should follow the existing Fusion/white-theme palette and feather-icon SVG style

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| PyQt5 >= 5.15 | GUI framework |
| psutil | Network/process info in diagnostics and splash checks |
| reportlab | PDF report generation |
| Pillow | Image handling (QR codes, assets) |
| qrcode | QR code generation for report export |
