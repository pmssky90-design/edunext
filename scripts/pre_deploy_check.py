from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    generator = subprocess.run([sys.executable, "generator.py"], cwd=ROOT)
    if generator.returncode:
        return generator.returncode
    audit = subprocess.run([sys.executable, "scripts/audit_site.py"], cwd=ROOT)
    return audit.returncode


if __name__ == "__main__":
    raise SystemExit(main())
