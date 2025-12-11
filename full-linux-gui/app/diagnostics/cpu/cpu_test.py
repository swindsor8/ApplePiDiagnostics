#!/usr/bin/env python3
import psutil
def run_cpu_test():
    info = {"cpu_count": psutil.cpu_count(logical=True)}
    return {"status": "OK", "info": info}
