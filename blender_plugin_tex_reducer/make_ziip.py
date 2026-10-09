#!/usr/bin/env python3
import subprocess, zipfile, sys
from pathlib import Path
print("ok")
root = Path(".").resolve()
out = root / f"{root.name}.zip"
print(root)
try:
    res = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, capture_output=True, check=True,
    )
except (subprocess.CalledProcessError, FileNotFoundError):
    sys.exit("Not a git repository (or git not installed). Use the fallback below.")



files = sorted(set(
    f for f in res.stdout.decode("utf-8").split("\0")
    if f and "/" not in f   # only files directly in the current folder
))



with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        p = root / rel
        if p.resolve() == out or not p.is_file():
            continue
        zf.write(p, f"{root.name}/{rel}")   # top-level folder inside the zip



print(f"{len(files)} files -> {out}")