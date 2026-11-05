#!/usr/bin/env python3
"""Require two idle A30 GPUs before starting a cluster2 model server."""
import csv
import io
import subprocess
import sys


def query(fields):
    result = subprocess.run(
        ["nvidia-smi", *fields, "--format=csv,noheader,nounits"],
        check=True, text=True, capture_output=True, timeout=15,
    )
    return list(csv.reader(io.StringIO(result.stdout), skipinitialspace=True))


try:
    devices = query(["--query-gpu=index,name,memory.used"])
    processes = query(["--query-compute-apps=pid"])
    if len(devices) != 2 or any(len(row) != 3 or "A30" not in row[1] or int(row[2]) >= 1000 for row in devices):
        raise ValueError("both A30 GPUs must each use less than 1000 MiB")
    if any(row and row[0].strip() for row in processes):
        raise ValueError("GPU compute processes are present")
except (OSError, ValueError, subprocess.SubprocessError) as exc:
    print(f"GPU_CHECK_FAILED: {exc}", file=sys.stderr)
    sys.exit(1)
print("GPU_CHECK_OK: two A30 GPUs below 1000 MiB and no compute processes")
