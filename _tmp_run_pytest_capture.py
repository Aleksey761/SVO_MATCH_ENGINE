from __future__ import annotations

import subprocess
import sys
from pathlib import Path

cmd = [r"f:/SVO/AI/SVO_MATCH_ENGINE/.venv/Scripts/python.exe", "-m", "pytest", "-q"]
output_path = Path("_tmp_pytest_capture_run.txt")

try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent,
        timeout=60,
    )
    output_path.write_text((result.stdout or "") + "\n--- STDERR ---\n" + (result.stderr or ""), encoding="utf-8")
    print(f"RC={result.returncode}")
    last_lines = [line for line in (result.stdout or "").splitlines() if line.strip()]
    if not last_lines and result.stderr:
        last_lines = [line for line in result.stderr.splitlines() if line.strip()]
    for line in last_lines[-5:]:
        print(line)
    sys.exit(result.returncode)
except subprocess.TimeoutExpired as exc:
    stdout = exc.stdout or ""
    stderr = exc.stderr or ""
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")
    output_path.write_text((stdout or "") + "\n--- STDERR ---\n" + (stderr or "") + "\n--- STATUS ---\nTIMEOUT", encoding="utf-8")
    print("RC=TIMEOUT")
    sys.exit(124)
