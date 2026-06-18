#!/usr/bin/env python3
## @file
# Copyright (c) 2026, Cory Bennett. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
##
"""Remove LaTeX build artifacts while preserving source and PDF output files."""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path


ROOT = Path(__file__).resolve().parent

PATTERNS = (
  "*.aux",
  "*.bbl",
  "*.blg",
  "*.fdb_*",
  "*.fdb_latexmk",
  "*.fls",
  "*.idx",
  "*.ind",
  "*.log",
  "*.lof",
  "*.lot",
  "*.out",
  "*.synctex",
  "*.synctex.*",
  "*.synctex.gz",
  "*.synctex(busy)",
  "*.synctex.gz(busy)",
  "*.toc",
  "*.acn",
  "*.acr",
  "*.alg",
  "*.glg",
  "*.glo",
  "*.gls",
  "*.ist",
  "*.nav",
  "*.snm",
  "*.vrb",
  "exhibit-manifest.txt",
  "exhibit-manifest-*.txt",
)

SKIP_DIRS = {
  ".git",
  ".agents",
  ".codex",
  ".vscode",
  "__pycache__",
}


def is_skipped(path: Path) -> bool:
  rel_parts = path.relative_to(ROOT).parts
  return any(part in SKIP_DIRS for part in rel_parts[:-1])


def is_artifact(path: Path) -> bool:
  try:
    generated_rel = path.relative_to(ROOT / "Exhibits" / "_Generated")
  except ValueError:
    generated_rel = None

  if generated_rel is not None and path.name == "exhibit-manifest.txt":
    return False

  return any(fnmatch.fnmatch(path.name, pattern) for pattern in PATTERNS)


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--dry-run", action="store_true")
  args = parser.parse_args()

  matches = sorted(
    path
    for path in ROOT.rglob("*")
    if path.is_file() and not is_skipped(path) and is_artifact(path)
  )

  for path in matches:
    rel = path.relative_to(ROOT)
    if args.dry_run:
      print(rel)
    else:
      path.unlink()
      print(f"Removed {rel}")

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
