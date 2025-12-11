#!/usr/bin/env python3
import sys, importlib, json

def main():
    sys.path.insert(0, 'full-linux-gui/app')
    mod = importlib.import_module('diagnostics.cpu.cpu_test')
    res = mod.run_cpu_quick_test(duration=2, workers=1)
    print('status:', res.get('status'))
    samples = res.get('samples') or []
    print('samples_count:', len(samples))
    if samples:
        s = samples[0]
        print('first_sample_keys:', list(s.keys()))
        print('first_sample_max_temp:', s.get('max_temp'))

if __name__ == '__main__':
    main()
