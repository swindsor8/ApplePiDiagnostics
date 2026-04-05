# Security Policy

## Supported Versions

Only the latest stable release of Apple Pi Diagnostics receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Please report vulnerabilities by **opening a GitHub Issue** in this repository.

Include:
- A clear description of the vulnerability
- Steps to reproduce
- Potential impact or attack scenario
- Your environment (OS, Python version, hardware if relevant)
- Suggested fixes, if any

### What to Expect

- **Acknowledgment:** within **72 hours**
- **Updates:** within **7 days** as investigation progresses
- **Resolution:** patch prioritised and released as soon as possible; credit given unless you prefer otherwise
- **If declined:** reasoning explained in the issue

### Scope

This policy covers the Apple Pi Diagnostics codebase and its direct dependencies. Issues in third-party libraries should be reported to their respective maintainers.

---

## Security Hardening — Implemented Mitigations

The following mitigations were applied as part of a security audit:

### Python Application (`full-linux-gui/app/`)

| Area | Mitigation |
|------|-----------|
| Temporary files | Replaced `NamedTemporaryFile` + close + reopen pattern with `mkdtemp()` to eliminate TOCTOU race conditions (CWE-377) |
| HTML reports | All user-controlled data (`label`, `lines`, `title`, hostname, OS name) escaped with `html.escape()` before embedding in HTML (CWE-79) |
| USB path traversal | `mount_point` resolved with `os.path.realpath()` and validated against trusted prefixes `/media/`, `/mnt/`, `/run/media/` (CWE-22) |
| HTTP server exposure | QR report server binds to the specific LAN interface IP instead of `0.0.0.0` (CWE-200) |
| Exception info disclosure | Raw exception strings sanitised with regex to strip file paths before appearing in reports or UI (CWE-209) |
| Network privacy | External connectivity checks (8.8.8.8, 1.1.1.1, www.google.com) documented in `run_network_test()` docstring; all targets configurable via `config.py` |
| Hardcoded constants | All network addresses and ports centralised in `config.py` |

### Shell Scripts

| File | Mitigation |
|------|-----------|
| `build_failsafe.sh` | Quoted `"$CPIO_SIZE"` in `numfmt` argument |
| `test_failure_modes.sh` | Added `set -euo pipefail`; `trap 'rm -f "$TEMP_IMG"' EXIT`; quoted `"$QEMU_PID"` |
| `test_qemu.sh` | Added `set -euo pipefail` |
| `bootloader-tools/validate_sd.sh` | Added regex validation of device path before use in mount |
| `install.sh` | Desktop entry written with `umask 077` + `chmod 600` |
| `build-image.sh` | PiShrink downloaded from pinned commit SHA and SHA256-verified before execution |

### Automated Scanning

The following GitHub Actions workflows provide ongoing security coverage:

| Workflow | What it catches |
|----------|----------------|
| `codeql.yml` | Semantic code vulnerabilities (security-extended queries) |
| `bandit.yml` | Python-specific SAST: hardcoded secrets, insecure subprocess, weak crypto |
| `dependency-review.yml` | Blocks PRs that introduce dependencies with known CVEs |
| `shellcheck.yml` | Shell script safety issues |
| Dependabot | Automated dependency version updates (pip + GitHub Actions) |

---

Thank you for helping keep Apple Pi Diagnostics secure.
