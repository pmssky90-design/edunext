from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    generator = subprocess.run([sys.executable, "generator.py"], cwd=ROOT)
    if generator.returncode:
        return generator.returncode
    for audit_path in (
        "scripts/audit_site.py",
        "scripts/audit_sentence_quality.py",
        "scripts/audit_text_anomalies.py",
    ):
        audit = subprocess.run([sys.executable, audit_path], cwd=ROOT)
        if audit.returncode:
            return audit.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
