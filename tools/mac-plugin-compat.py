#!/usr/bin/env python3
"""Patch Loon for Mac 0.x plugin caches for the false Loon-version warning.

Loon for Mac ships a 0.x marketing version (e.g. 0.5.0) while its build is unified
with iOS (1011). Plugin metadata declares iOS-style `#!loon_version=3.5.x(build)`.
Loon 0.5.0(1011) currently compares the 0.x marketing version and marks every 3.x
plugin as "Loon 的版本过旧，插件功能受限". Build 1011 is newer than the 3.5.2(996)
features this repository targets, so the warning is a false negative.

This tool only rewrites the local plugin cache header to the installed Mac
version. It never edits plugin logic, remote URLs, CA, subscription, or config.
Back up first; rerun after "更新全部外部资源" if Loon restores the remote headers.
"""
from __future__ import annotations

import argparse
import plistlib
import re
import shutil
from datetime import datetime
from pathlib import Path

DEFAULT_APP = Path("/Applications/Loon.app")
DEFAULT_CACHE = Path("/Library/Application Support/com.loon.Loon/remotePlugin")
BACKUP_ROOT = Path.home() / "Loon-backups"


def app_version(app: Path) -> tuple[str, int]:
    plist = app / "Contents/Info.plist"
    if not plist.is_file():
        raise SystemExit(f"Loon app not found: {plist}")
    with plist.open("rb") as fh:
        data = plistlib.load(fh)
    short = str(data.get("CFBundleShortVersionString", "")).strip()
    build = int(str(data.get("CFBundleVersion", "0")).strip() or 0)
    if not short or build <= 0:
        raise SystemExit(f"invalid version in {plist}: {short!r} ({build})")
    return short, build


def metadata(text: str, key: str) -> str:
    # [ \t] rather than \s: an empty line value must not swallow the next line.
    match = re.search(
        r"^#![ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*(.*)$", text, re.M
    )
    return match.group(1).strip() if match else ""


def required_build(value: str) -> int:
    match = re.search(r"\((\d+)\)", value)
    return int(match.group(1)) if match else -1


def supports_macos(system: str) -> bool:
    if not system.strip():
        return True
    return "macos" in {part.strip().lower() for part in system.split(",")}


def patch_text(text: str, target: str, target_build: int) -> tuple[str, str | None]:
    current = metadata(text, "loon_version")
    if not current:
        return text, "no #!loon_version"
    build = required_build(current)
    if build < 0:
        return text, f"unparseable #!loon_version={current!r}"
    if build > target_build:
        return text, f"requires newer build {build} > {target_build}"
    if not supports_macos(metadata(text, "system")):
        return text, "does not support macOS"
    if current == target:
        return text, None
    updated = re.sub(
        r"(?m)^#!\s*loon_version\s*=\s*.*$",
        f"#!loon_version={target}",
        text,
        count=1,
    )
    return updated, None


def backup_file(path: Path, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    dest = root / path.name
    shutil.copy2(path, dest)
    dest.chmod(0o600)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=DEFAULT_APP)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    parser.add_argument("--backup-root", type=Path, default=BACKUP_ROOT)
    args = parser.parse_args()

    short, build = app_version(args.app)
    target = f"{short}({build})"
    print(f"Loon Mac: {target}")
    if not args.cache.is_dir():
        raise SystemExit(f"plugin cache not found: {args.cache}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = args.backup_root / stamp / "plugin-caches"
    changed = skipped = 0
    for path in sorted(args.cache.glob("*.lpx")):
        text = path.read_text(encoding="utf-8", errors="replace")
        updated, reason = patch_text(text, target, build)
        if reason:
            print(f"SKIP {path.name}: {reason}")
            skipped += 1
            continue
        if updated == text:
            print(f"OK   {path.name}: already {target}")
            continue
        print(f"PATCH {path.name}: {metadata(text, 'name') or '?'}")
        changed += 1
        if args.apply:
            backup_file(path, backup_dir)
            path.write_text(updated, encoding="utf-8")
            path.chmod(0o600)
    if args.apply and changed:
        print(f"backup: {backup_dir}")
        print("restart Loon to reload plugin metadata")
    elif not args.apply:
        print("dry-run: no files changed; add --apply to write")
    print(f"changed={changed} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
