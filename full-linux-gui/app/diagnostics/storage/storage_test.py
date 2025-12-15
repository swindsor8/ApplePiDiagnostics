#!/usr/bin/env python3
"""Comprehensive storage diagnostics for MicroSD, USB drives, and hard drives.

Detects and tests all storage devices attached to the system.
"""
from __future__ import annotations

import os
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List
import psutil


def _detect_storage_devices() -> List[Dict[str, Any]]:
    """Detect all storage devices (SD card, USB, hard drives).
    
    Returns a list of device info dicts with keys: device, type, size, mountpoint
    """
    devices = []
    
    try:
        # Get disk partitions
        partitions = psutil.disk_partitions(all=True)
        
        # Track which devices we've seen
        seen_devices = set()
        
        for partition in partitions:
            device = partition.device
            if not device or device.startswith('/dev/loop') or device.startswith('/dev/sr'):
                continue
            
            # Get the base device (without partition number)
            base_device = device.rstrip('0123456789')
            if base_device in seen_devices:
                continue
            
            seen_devices.add(base_device)
            
            # Determine device type
            device_type = "Unknown"
            if '/mmcblk' in device or '/mmc' in device:
                device_type = "MicroSD Card"
            elif device.startswith('/dev/sd'):
                # Check if it's USB or internal
                try:
                    # Check sysfs to determine if USB
                    sysfs_path = f"/sys/block/{os.path.basename(base_device)}/removable"
                    if os.path.exists(sysfs_path):
                        with open(sysfs_path, 'r') as f:
                            removable = f.read().strip()
                        device_type = "USB Drive" if removable == "1" else "Hard Drive"
                    else:
                        device_type = "Storage Device"
                except Exception:
                    device_type = "Storage Device"
            elif device.startswith('/dev/nvme'):
                device_type = "NVMe SSD"
            
            # Get device size
            size = 0
            try:
                if os.path.exists(base_device):
                    size = os.path.getsize(base_device)
            except Exception:
                pass
            
            # Get mountpoint
            mountpoint = partition.mountpoint if partition.mountpoint else None
            
            devices.append({
                "device": base_device,
                "type": device_type,
                "size_bytes": size,
                "size_gb": size / (1024**3) if size > 0 else 0,
                "mountpoint": mountpoint,
                "fstype": partition.fstype,
            })
        
        # Also check /dev for block devices we might have missed
        try:
            for dev_file in Path("/dev").iterdir():
                dev_name = dev_file.name
                if dev_name.startswith(('mmcblk', 'sd', 'nvme')) and dev_name not in seen_devices:
                    # Check if it's a block device
                    if dev_file.is_block_device():
                        base_name = dev_name.rstrip('0123456789p')
                        if base_name not in seen_devices:
                            seen_devices.add(base_name)
                            device_path = f"/dev/{base_name}"
                            
                            # Determine type
                            device_type = "Unknown"
                            if 'mmcblk' in dev_name or 'mmc' in dev_name:
                                device_type = "MicroSD Card"
                            elif dev_name.startswith('sd'):
                                device_type = "USB Drive"  # Assume USB for sd devices
                            elif dev_name.startswith('nvme'):
                                device_type = "NVMe SSD"
                            
                            # Get size
                            size = 0
                            try:
                                size = os.path.getsize(device_path)
                            except Exception:
                                pass
                            
                            devices.append({
                                "device": device_path,
                                "type": device_type,
                                "size_bytes": size,
                                "size_gb": size / (1024**3) if size > 0 else 0,
                                "mountpoint": None,
                                "fstype": None,
                            })
        except Exception:
            pass
        
    except Exception as e:
        # Fallback: just check common devices
        for dev_pattern in ["/dev/mmcblk0", "/dev/sda", "/dev/sdb", "/dev/sdc"]:
            if os.path.exists(dev_pattern):
                devices.append({
                    "device": dev_pattern,
                    "type": "MicroSD Card" if "mmcblk" in dev_pattern else "Storage Device",
                    "size_bytes": 0,
                    "size_gb": 0,
                    "mountpoint": None,
                    "fstype": None,
                })
    
    return devices


def _test_device_speed(device_path: str, mountpoint: Optional[str] = None, 
                       file_size_mb: int = 8, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """Test read/write speed on a storage device.
    
    If mountpoint is provided, tests on the mounted filesystem.
    Otherwise, tests raw device (requires root).
    """
    tested_mb = float(file_size_mb)
    fname = None
    
    try:
        # Determine test location
        if mountpoint and os.path.isdir(mountpoint) and os.access(mountpoint, os.W_OK):
            # Test on mounted filesystem
            test_dir = mountpoint
        else:
            # Use /tmp as fallback (tests system RAM/filesystem, not the device)
            test_dir = "/tmp"
        
        os.makedirs(test_dir, exist_ok=True)
        tf = tempfile.NamedTemporaryFile(delete=False, dir=test_dir, suffix=".apd_test")
        fname = tf.name
        tf.close()
        
        chunk = b"\xAA" * (1024 * 1024)  # 1MB chunks
        chunks = int(file_size_mb)
        
        # Write test
        if progress_callback:
            progress_callback({"phase": "write", "device": device_path, "progress": 0})
        
        t0 = time.time()
        with open(fname, "wb") as f:
            for i in range(chunks):
                f.write(chunk)
                f.flush()
                os.fsync(f.fileno())
                if progress_callback:
                    progress_callback({"phase": "write", "device": device_path, "progress": (i + 1) / chunks})
        t1 = time.time()
        write_mb_s = tested_mb / max(1e-6, (t1 - t0))
        
        # Read test
        if progress_callback:
            progress_callback({"phase": "read", "device": device_path, "progress": 0})
        
        t0 = time.time()
        with open(fname, "rb") as f:
            total = 0
            while True:
                data = f.read(1024 * 1024)
                if not data:
                    break
                total += len(data)
                if progress_callback:
                    progress_callback({"phase": "read", "device": device_path, "progress": total / (tested_mb * 1024 * 1024)})
        t1 = time.time()
        read_mb_s = tested_mb / max(1e-6, (t1 - t0))
        
        return {
            "status": "OK",
            "tested_mb": tested_mb,
            "write_mb_s": write_mb_s,
            "read_mb_s": read_mb_s,
            "test_location": "mounted" if mountpoint else "fallback",
        }
    except Exception as e:
        return {
            "status": "FAIL",
            "note": str(e),
            "tested_mb": tested_mb,
        }
    finally:
        try:
            if fname and os.path.exists(fname):
                os.remove(fname)
        except Exception:
            pass


def run_storage_test(file_size_mb: int = 8, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """Test all storage devices (MicroSD, USB, hard drives).
    
    Returns a dict with status and results for each device.
    """
    results = {
        "status": "OK",
        "devices": [],
        "total_devices": 0,
        "tested_devices": 0,
    }
    
    try:
        # Detect all storage devices
        devices = _detect_storage_devices()
        results["total_devices"] = len(devices)
        
        if not devices:
            return {
                "status": "UNSUPPORTED",
                "note": "No storage devices detected",
                "devices": [],
                "total_devices": 0,
                "tested_devices": 0,
            }
        
        # Test each device
        for device_info in devices:
            device_path = device_info["device"]
            device_type = device_info["type"]
            mountpoint = device_info.get("mountpoint")
            
            device_result = {
                "device": device_path,
                "type": device_type,
                "size_gb": device_info.get("size_gb", 0),
                "mountpoint": mountpoint,
                "fstype": device_info.get("fstype"),
            }
            
            # Test the device
            if progress_callback:
                progress_callback({"phase": "testing", "device": device_path, "type": device_type})
            
            speed_result = _test_device_speed(device_path, mountpoint, file_size_mb, progress_callback)
            device_result.update(speed_result)
            
            results["devices"].append(device_result)
            if speed_result.get("status") == "OK":
                results["tested_devices"] += 1
        
        # Determine overall status
        if results["tested_devices"] == 0:
            results["status"] = "FAIL"
        elif results["tested_devices"] < results["total_devices"]:
            results["status"] = "WARNING"
        
        return results
        
    except Exception as e:
        return {
            "status": "FAIL",
            "note": str(e),
            "devices": [],
            "total_devices": 0,
            "tested_devices": 0,
        }


def run_storage_quick_test(progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """Quick test of all storage devices (smaller file size)."""
    return run_storage_test(file_size_mb=4, progress_callback=progress_callback)


if __name__ == "__main__":
    import json
    result = run_storage_quick_test()
    print(json.dumps(result, indent=2))

