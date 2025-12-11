#!/usr/bin/env python3
import sys, importlib, json

def main():
	# prefer fork start method to avoid forkserver/spawn issues in tests
	try:
		import multiprocessing as _mp
		_mp.set_start_method('fork', force=True)
	except Exception:
		pass

	sys.path.insert(0, 'full-linux-gui/app')
	mod = importlib.import_module('diagnostics.cpu.cpu_test')
	res = mod.run_cpu_quick_test(duration=3, workers=1)
	print(json.dumps(res, indent=2))


if __name__ == '__main__':
	main()
