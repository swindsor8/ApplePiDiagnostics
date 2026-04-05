# Development Guide

This document provides information for developers working on Apple Pi Diagnostics.

## Project Structure

```
ApplePiDiagnostics/
├── bootloader-tools/          # Bootloader repair and validation tools
├── failsafe-env/              # Files for the failsafe initramfs
├── full-linux-gui/            # Complete PyQt5-based diagnostic GUI
│   ├── app/
│   │   ├── config.py          # Centralised constants (network addresses, ports)
│   │   ├── main.py            # Application entry point
│   │   ├── diagnostics/       # Individual diagnostic modules
│   │   ├── exports/           # Report export functionality
│   │   ├── gui/               # GUI components
│   │   └── tests/             # Pytest test suite
│   ├── requirements.txt       # Runtime Python dependencies
│   ├── requirements-dev.txt   # Dev/test dependencies (pylint, pytest, bandit, mypy)
│   └── reports/               # Generated reports (gitignored)
├── scripts/
│   └── update-pishrink.sh     # Check/apply PiShrink upstream updates
├── build_failsafe.sh          # Build failsafe initramfs
├── build-image.sh             # Build flashable Pi image
├── install.sh                 # End-user setup script
└── test_*.sh                  # QEMU and failure-mode test scripts
```

## Development Environment Setup

```bash
git clone <repo>
cd ApplePiDiagnostics/full-linux-gui
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # installs runtime + dev deps
```

Run the GUI:
```bash
cd app
python3 main.py
# headless / offscreen:
QT_QPA_PLATFORM=offscreen python3 main.py
```

## Configuration

All hardcoded network addresses and ports live in [`full-linux-gui/app/config.py`](full-linux-gui/app/config.py).
Change them there — do not scatter literals through module files.

| Constant | Default | Purpose |
|----------|---------|---------|
| `GATEWAY_PROBE_HOST` | `8.8.8.8` | UDP socket used to detect local interface IP |
| `GATEWAY_PROBE_PORT` | `53` | Port for the probe above |
| `NETWORK_PING_TARGETS` | `["8.8.8.8","1.1.1.1"]` | Hosts pinged by network diagnostic |
| `NETWORK_DNS_CHECK_HOST` | `www.google.com` | Hostname for DNS latency check |
| `QR_HTTP_PORT` | `8888` | Port for the QR report HTTP server |

> **Privacy note:** The defaults above contact Google and Cloudflare infrastructure at runtime. Replace with local addresses if that is not acceptable for your deployment.

## Testing

### Automated tests (pytest)

```bash
cd full-linux-gui
source venv/bin/activate
pytest app/tests/ -v --timeout=60
```

With coverage:
```bash
pytest app/tests/ --cov=app --cov-report=term-missing
```

Tests are designed to run without real Pi hardware — modules that require GPIO, HDMI, or USB return `UNSUPPORTED` gracefully.

### Run a single diagnostic module manually

```bash
cd full-linux-gui/app
python3 -c "
from diagnostics.cpu.cpu_test import run_cpu_quick_test
import json; print(json.dumps(run_cpu_quick_test(), indent=2))
"
```

Available modules: `cpu`, `ram`, `network`, `storage`, `usb`, `hdmi`, `gpio`.

### Failsafe mode (QEMU)

```bash
./build_failsafe.sh
./test_qemu.sh <path_to_kernel_image>
./test_failure_modes.sh <path_to_kernel_image>
```

### Real hardware

1. Build: `./build_failsafe.sh`
2. Copy: `scp build/initramfs.cpio.gz pi@<ip>:/boot/`
3. Configure boot per `FAILSAFE_README.md`

## Adding a New Diagnostic Module

1. Create `full-linux-gui/app/diagnostics/<name>/` with `__init__.py` and `<name>_test.py`
2. Implement `run_<name>_quick_test() -> dict` — must include a `"status"` key with value in `{"OK","WARNING","FAIL","UNSUPPORTED"}`
3. Add import and call in `main.py` (follow the pattern of existing modules)
4. Add a `Test<Name>` class to `app/tests/test_diagnostics.py`
5. Register in `gui/splash.py` `_check_diagnostics()` so it validates at startup

## Code Style

- Python 3.9+ (type hints, `list[str]` syntax)
- PEP 8; max line length 100
- All subprocess calls must use list args (`shell=False`)
- UI updates from threads must use `QtCore.QMetaObject.invokeMethod()`
- Diagnostic functions must not block the Qt event loop — run in `threading.Thread(daemon=True)`
- Exception messages in reports/UI must go through `_safe_err()` (strips file paths)

## Linting & Security Scanning

```bash
# Pylint (warnings as errors for new code)
pylint --disable=C,R,W0611,E0401 full-linux-gui/app/

# Bandit SAST
bandit -r full-linux-gui/app/ --severity-level medium

# ShellCheck
find . -name "*.sh" | xargs shellcheck --severity=warning
shellcheck init
```

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `pytest.yml` | push/PR to main | Run test suite with coverage |
| `pylint.yml` | push/PR to main | Python linting (3.9, 3.10, 3.11) |
| `shellcheck.yml` | push/PR touching .sh/init | Shell script linting |
| `bandit.yml` | push/PR to main + weekly | Python SAST |
| `codeql.yml` | push/PR to main + weekly | Semantic vulnerability analysis |
| `dependency-review.yml` | every PR | Block CVE-bearing deps |
| `update-pishrink.yml` | weekly + manual | Keep PiShrink pin current |
| `build-release.yml` | on version tag push | Build + publish Pi image release |
| `validate-release.yml` | on release published | Verify SHA256 + os_list.json |
| `stale.yml` | daily | Triage old issues and PRs |

## Dependencies

### Runtime
See `full-linux-gui/requirements.txt` — PyQt5, psutil, reportlab, Pillow, qrcode.

### Development
See `full-linux-gui/requirements-dev.txt` — adds pytest, pytest-cov, pylint, bandit, mypy.

### System (Debian/Pi OS)
```bash
sudo apt install python3-pyqt5 python3-pyqt5.qtsvg busybox-static cpio gzip
```

## Contributing

1. Fork → feature branch → changes → tests pass → pull request
2. All PRs are automatically checked by ShellCheck, Pylint, Pytest, Bandit, and Dependency Review
3. Merging requires all checks to pass
