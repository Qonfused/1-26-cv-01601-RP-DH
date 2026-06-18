#!/usr/bin/env python3
## @file
# Copyright (c) 2026, Cory Bennett. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
##
"""Build a LaTeX root file from the workspace root.

This keeps project-relative paths such as ``Exhibits/Documents/...`` usable even
when the root ``.tex`` file lives in a subdirectory like ``Civil/Filing``.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
  env = None
  if command and Path(command[0]).name == "uv":
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", "/tmp/ut-case-uv-cache")
  subprocess.run(command, cwd=ROOT, check=True, env=env)


def force_latexmk(command: list[str]) -> list[str]:
  return [command[0], "-g", *command[1:]]


def python_script_command(script: str) -> list[str]:
  uv = shutil.which("uv")
  if uv:
    return [uv, "run", "--script", script]
  return ["python3", script]


def resolve_doc(doc: str) -> tuple[str, Path, Path]:
  path = Path(doc)

  if path.is_absolute():
    try:
      path = path.relative_to(ROOT)
    except ValueError:
      pass

  tex_path = path if path.suffix == ".tex" else path.with_suffix(".tex")
  output_dir = tex_path.parent if tex_path.parent != Path("") else Path(".")

  doc_text = tex_path.with_suffix("").as_posix()

  return doc_text, output_dir, tex_path


def exhibit_build_id(tex_path: Path) -> str:
  digest = hashlib.sha256(tex_path.as_posix().encode("utf-8")).digest()
  token = base64.b32encode(digest).decode("ascii").lower().rstrip("=")
  return f"{token[:6]}-{token[6:12]}"


def source_uses_exhibit_system(tex_path: Path) -> bool:
  markers = (
    "ExhibitGeneratedDir",
    "ExhibitManifestFile",
    "PreviewGeneratedExhibitPage",
    "PrintExhibitTable",
    "ExhibitPacketCaption",
  )
  try:
    content = tex_path.read_text(encoding="utf-8")
  except OSError:
    return False
  return any(marker in content for marker in markers)


def find_manifest(output_dir: Path, manifest_name: str) -> Path | None:
  candidates = [
    ROOT / output_dir / manifest_name,
    ROOT / output_dir / "exhibit-manifest.txt",
    ROOT / manifest_name,
    ROOT / "exhibit-manifest.txt",
  ]
  return next((path for path in candidates if path.exists()), None)


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("doc", help="LaTeX root file path, with or without .tex")
  args = parser.parse_args()

  doc, output_dir, tex_path = resolve_doc(args.doc)
  exhibit_mode = source_uses_exhibit_system(tex_path)

  if exhibit_mode:
    build_id = exhibit_build_id(tex_path)
    exhibit_output_dir = Path("Exhibits/_Generated") / build_id
    manifest_name = f"exhibit-manifest-{build_id}.txt"
    pretex = (
      rf"\def\ExhibitGeneratedDir{{{exhibit_output_dir.as_posix()}}}"
      rf"\def\ExhibitManifestFile{{{manifest_name}}}"
    )
  else:
    build_id = None
    exhibit_output_dir = None
    manifest_name = None
    pretex = ""

  latexmk = [
    "latexmk",
    "-synctex=1",
    "-interaction=nonstopmode",
    "-file-line-error",
    f"-output-directory={output_dir.as_posix()}",
    "-pdf",
    doc,
  ]
  if pretex:
    latexmk.insert(5, f"-usepretex={pretex}")

  run(latexmk)

  if manifest_name and exhibit_output_dir:
    manifest = find_manifest(output_dir, manifest_name)
    if manifest:
      run(
        [
          *python_script_command("_extract-subexhibits.py"),
          "--manifest",
          str(manifest),
          "--output-dir",
          exhibit_output_dir.as_posix(),
          "--tex-source",
          tex_path.as_posix(),
        ]
      )
      # Re-run once only when extraction generates files used by the source.
      run(force_latexmk(latexmk))

  run(["python3", "_clean-latex-artifacts.py"])

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
