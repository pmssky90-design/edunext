from __future__ import annotations

import html
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def article_text(source: str) -> str:
    match = re.search(r'<article\s+class="content-body">(.*?)</article>', source, flags=re.I | re.S)
    if not match:
        return ""
    value = re.sub(r"<script\b.*?</script>", " ", match.group(1), flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def main() -> int:
    tracked = subprocess.run(
        ["git", "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", "HEAD", "output"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.splitlines()
    html_paths = [path for path in tracked if path.endswith("/index.html") or path == "output/index.html"]
    changed: list[str] = []
    missing: list[str] = []
    for relative in html_paths:
        current_path = ROOT / relative
        if not current_path.exists():
            missing.append(relative)
            continue
        previous = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
        current = current_path.read_text(encoding="utf-8")
        if article_text(previous) != article_text(current):
            changed.append(relative)
    print(f"tracked html: {len(html_paths)}")
    print(f"missing html: {len(missing)}")
    print(f"content text changed: {len(changed)}")
    for path in (missing + changed)[:20]:
        print(path)
    return 1 if missing or changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
