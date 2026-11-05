"""Package the complete source tree without dependencies, secrets, or run data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    exclude_dirs = {"node_modules", "__pycache__", ".git", ".venv", "runs", "build", "dist", "out"}
    selected = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in exclude_dirs for part in relative.parts): continue
        if path.name == "BUILD_CONTRACT.md" or path.name.endswith((".pyc", ".sqlite3", ".sqlite3-wal", ".sqlite3-shm")): continue
        if path.name.startswith(".env") and path.name != ".env.example": continue
        if path.is_symlink(): raise SystemExit(f"Refusing source symlink: {relative}")
        selected.append((path, relative))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in selected:
            archive.write(path, f"storyforge/{relative.as_posix()}")
            manifest.append({"path": relative.as_posix(), "bytes": path.stat().st_size,
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        archive.writestr("storyforge/SOURCE_MANIFEST.json", json.dumps({"version": "0.1.0", "files": manifest}, indent=2)+"\n")
    with zipfile.ZipFile(args.output) as archive:
        bad = archive.testzip()
        if bad: raise SystemExit(f"Archive verification failed: {bad}")
    print(json.dumps({"archive": str(args.output.resolve()), "source_files": len(selected), "bytes": args.output.stat().st_size,
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__": main()
