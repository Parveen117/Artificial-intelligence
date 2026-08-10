#!/usr/bin/env python3
"""Build a self-contained Docker Space bundle for the Formal Proof Gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "formal_proof_challenge"
TEMPLATE = PACKAGE / "deployment" / "huggingface-space"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def build(output: Path, source_revision: str = "") -> dict:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    shutil.copy2(TEMPLATE / "README.md", output / "README.md")
    shutil.copy2(TEMPLATE / "Dockerfile", output / "Dockerfile")
    shutil.copytree(
        PACKAGE,
        output / "formal_proof_challenge",
        ignore=shutil.ignore_patterns("outputs", "__pycache__", "deployment", "*.pyc"),
    )

    files = [
        {
            "path": str(path.relative_to(output)).replace(os.sep, "/"),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in iter_files(output)
    ]
    manifest = {
        "schema": "formal-proof-gate-hf-space-bundle-v1",
        "source_revision": source_revision,
        "file_count": len(files),
        "files": files,
    }
    unsigned = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(unsigned).hexdigest()
    (output / "SPACE_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Formal Proof Gate Hugging Face Space bundle")
    parser.add_argument("--output", type=Path, default=Path("dist/formal-proof-gate-space"))
    parser.add_argument("--source-revision", default=os.getenv("GITHUB_SHA", ""))
    args = parser.parse_args()
    manifest = build(args.output, args.source_revision)
    print(json.dumps({
        "ok": True,
        "output": str(args.output),
        "file_count": manifest["file_count"],
        "manifest_sha256": manifest["manifest_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
