# Development Guide

This document provides information for developers working on Apple Pi Diagnostics.

## Project Structure

```
ApplePiDiagnostics/
├── bootloader-tools/          # Bootloader repair and validation tools
├── failsafe-env/            # Files for the failsafe initramfs
├── full-linux-gui/          # Complete PyQt5-based diagnostic GUI
│   ├── app/                 # Main application code
│   │   ├── diagnostics/     # Individual diagnostic modules
│   │   ├── exports/         # Report export functionality
│   │   └── gui/            # GUI components
│   ├── requirements.txt     # Python dependencies
│   └── reports/            # Generated reports
├── build_failsafe.sh        # Script to build failsafe initramfs
├── test_*.sh               # Testing scripts
└── install.sh              # Installation script for end users
```

## Development Environment Setup

1. Clone the repository
2. Run `./install.sh` to set up the development environment
3. The GUI can be run with:
   ```bash
   cd full-linux-gui
   source venv/bin/activate
   python app/main.py
   ```

## Testing

### Unit Tests
Individual diagnostic modules can be tested directly:

```bash
cd full-linux-gui/app
python3 -c "
from diagnostics.cpu.cpu_test import run_cpu_quick_test
result = run_cpu_quick_test()
print(result)
"
```

### Failsafe Mode Testing
Test the failsafe initramfs in QEMU:
```bash
./test_qemu.sh <path_to_kernel_image>
```

Test failure modes:
```bash
./test_failure_modes.sh <path_to_kernel_image>
```

### Real Hardware Testing
1. Build the initramfs: `./build_failsafe.sh`
2. Copy to Pi: `scp build/initramfs.cpio.gz pi@<ip>:/boot/`
3. Configure boot (see FAILSAFE_README.md)
4. Reboot and observe behavior

## Adding New Diagnostic Modules

1. Create a new directory in `full-linux-gui/app/diagnostics/`
2. Implement the diagnostic function following the pattern of existing modules
3. Return a standardized result dictionary with at least:
   - `status`: 'OK', 'WARNING', or 'FAIL'
   - Other module-specific data
4. Add import and call in `full-linux-gui/app/main.py`

## Report Generation

The report builder (`diagnostics/report_builder.py`) accepts diagnostic results and generates:
- JSON reports
- HTML reports  
- PDF reports

Export functionality is handled by modules in `exports/`:
- `export_usb.py`: Save to USB drives
- `export_sd_boot.py`: Save to SD card boot partition
- `export_qr.py`: Generate QR codes

## Failsafe Mode Development

The failsafe initramfs is built from:
- `init`: Main init script that runs diagnostics
- `failsafe-env/`: Additional scripts and utilities

To modify failsafe behavior:
1. Edit the `init` script or files in `failsafe-env/`
2. Rebuild with `./build_failsafe.sh`
3. Test with QEMU before deploying to real hardware

## Code Style

- Follow PEP 8 for Python code
- Use descriptive variable names
- Add docstrings to functions and classes
- Include error handling for external dependencies

## Dependencies

### System Dependencies
- Python 3.8+
- PyQt5 development packages
- busybox-static (for failsafe mode)
- Standard Linux utilities (cpio, gzip, etc.)

### Python Dependencies
See `full-linux-gui/requirements.txt`:
- PyQt5>=5.15
- qrcode
- Pillow
- reportlab
- psutil

## Debugging

### GUI Debugging
If the GUI fails to start, check:
1. Python dependencies are installed
2. Display environment variables (DISPLAY, QT_QPA_PLATFORM)
3. PyQt5 installation

### Failsafe Mode Debugging
1. Test in QEMU first
2. Check init script syntax
3. Verify busybox is statically linked
4. Check LED paths for different Pi models

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the terms specified in the LICENSE file.
