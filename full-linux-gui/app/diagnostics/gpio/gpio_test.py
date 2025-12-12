"""GPIO diagnostics.

This module performs safe detection of GPIO libraries and reports capability.
It does not toggle pins by default to avoid accidental hardware state changes.
"""
from __future__ import annotations

from typing import Dict, Any


def run_gpio_probe() -> Dict[str, Any]:
    try:
        import RPi.GPIO as GPIO  # type: ignore
        return {"status": "OK", "driver": "RPi.GPIO", "note": "GPIO available (no pins toggled)"}
    except Exception:
        try:
            import gpiozero  # type: ignore
            return {"status": "OK", "driver": "gpiozero", "note": "GPIO available (no pins toggled)"}
        except Exception:
            return {"status": "UNSUPPORTED", "note": "No Raspberry Pi GPIO libraries available"}


def run_gpio_quick_test() -> Dict[str, Any]:
    return run_gpio_probe()


def run_gpio_loopback(pin_out: int, pin_in: int, pulses: int = 3, pulse_ms: int = 100, allow: bool = False) -> Dict[str, Any]:
    """Perform a simple loopback test: toggle `pin_out` and read `pin_in`.

    For safety this will only run if `allow` is True. Returns OK on success,
    or UNSUPPORTED if GPIO libs not available or allow is False.
    """
    if not allow:
        return {"status": "UNSUPPORTED", "note": "Loopback tests require explicit allow=True"}

    try:
        try:
            import RPi.GPIO as GPIO  # type: ignore
            use = "RPi.GPIO"
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin_out, GPIO.OUT)
            GPIO.setup(pin_in, GPIO.IN)
        except Exception:
            # try gpiozero
            try:
                from gpiozero import OutputDevice, InputDevice  # type: ignore
                use = "gpiozero"
                out = OutputDevice(pin_out)
                inp = InputDevice(pin_in)
            except Exception:
                return {"status": "UNSUPPORTED", "note": "No GPIO library available"}

        success = True
        results = []
        for i in range(pulses):
            if 'GPIO' in locals():
                GPIO.output(pin_out, True)
                import time as _t
                _t.sleep(pulse_ms / 1000.0)
                val = GPIO.input(pin_in)
                GPIO.output(pin_out, False)
            else:
                out.on()
                import time as _t
                _t.sleep(pulse_ms / 1000.0)
                val = inp.value
                out.off()
            results.append(bool(val))

        # cleanup for RPi.GPIO
        if 'GPIO' in locals():
            try:
                GPIO.cleanup()
            except Exception:
                pass

        if all(results):
            return {"status": "OK", "results": results, "driver": use}
        else:
            return {"status": "FAIL", "results": results, "driver": use}
    except Exception as e:
        return {"status": "FAIL", "note": str(e)}


if __name__ == "__main__":
    import json
    print(json.dumps(run_gpio_quick_test()))
