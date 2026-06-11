#!/usr/bin/env python3
"""Extract reusable cropped signature PDFs from SIGNATURES.pdf."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


PAGE_WIDTH_PT = 612.0
PAGE_HEIGHT_PT = 792.0


@dataclass(frozen=True)
class PixelBox:
  left: int
  top: int
  right: int
  bottom: int


@dataclass(frozen=True)
class CropBox:
  left: float
  bottom: float
  right: float
  top: float
  width: float
  height: float


def read_ppm(path: Path) -> tuple[int, int, bytes]:
  with path.open("rb") as handle:
    def token() -> str:
      out = bytearray()
      while True:
        byte = handle.read(1)
        if not byte:
          raise ValueError("Unexpected end of PPM header")
        if byte == b"#":
          handle.readline()
          continue
        if byte not in b" \t\r\n":
          break
      while byte and byte not in b" \t\r\n":
        out.extend(byte)
        byte = handle.read(1)
      return out.decode("ascii")

    magic = token()
    if magic != "P6":
      raise ValueError(f"Expected P6 PPM, got {magic!r}")
    width = int(token())
    height = int(token())
    max_value = int(token())
    if max_value != 255:
      raise ValueError(f"Unsupported PPM max value: {max_value}")
    data = handle.read()

  expected = width * height * 3
  if len(data) != expected:
    raise ValueError(f"Expected {expected} image bytes, got {len(data)}")
  return width, height, data


def render_source_pdf(source: Path, output_stem: Path, dpi: int) -> Path:
  subprocess.run(
    [
      "pdftoppm",
      "-singlefile",
      "-f",
      "1",
      "-l",
      "1",
      "-r",
      str(dpi),
      str(source),
      str(output_stem),
    ],
    check=True,
  )
  return output_stem.with_suffix(".ppm")


def dark_pixel_map(width: int, height: int, data: bytes, threshold: int) -> tuple[list[int], list[tuple[int, int]]]:
  row_counts = [0] * height
  row_extents: list[tuple[int, int]] = [(width, -1) for _ in range(height)]

  for y in range(height):
    row_offset = y * width * 3
    left = width
    right = -1
    count = 0
    for x in range(width):
      index = row_offset + x * 3
      red, green, blue = data[index], data[index + 1], data[index + 2]
      if red < threshold and green < threshold and blue < threshold:
        count += 1
        if x < left:
          left = x
        if x > right:
          right = x
    row_counts[y] = count
    row_extents[y] = (left, right)

  return row_counts, row_extents


def find_signature_boxes(
  width: int,
  height: int,
  data: bytes,
  threshold: int,
  expected_count: int,
  row_gap_px: int,
  min_row_dark_px: int,
) -> list[PixelBox]:
  row_counts, row_extents = dark_pixel_map(width, height, data, threshold)
  active_rows = [row for row, count in enumerate(row_counts) if count >= min_row_dark_px]
  if not active_rows:
    raise RuntimeError("No signature ink was detected")

  groups: list[tuple[int, int]] = []
  start = previous = active_rows[0]
  for row in active_rows[1:]:
    if row - previous <= row_gap_px:
      previous = row
      continue
    groups.append((start, previous))
    start = previous = row
  groups.append((start, previous))

  if len(groups) != expected_count:
    diagnostic = ", ".join(f"{top}-{bottom}" for top, bottom in groups)
    raise RuntimeError(
      f"Expected {expected_count} signature rows, detected {len(groups)} "
      f"groups: {diagnostic}. Try adjusting --threshold or --row-gap-px."
    )

  boxes: list[PixelBox] = []
  for top, bottom in groups:
    left = width
    right = -1
    for row in range(top, bottom + 1):
      row_left, row_right = row_extents[row]
      if row_right >= 0:
        left = min(left, row_left)
        right = max(right, row_right)
    boxes.append(PixelBox(left=left, top=top, right=right, bottom=bottom))

  return boxes


def pixel_box_to_crop(box: PixelBox, dpi: int, margin_pt: float) -> CropBox:
  scale = 72.0 / dpi
  x0 = max(0.0, box.left * scale - margin_pt)
  x1 = min(PAGE_WIDTH_PT, (box.right + 1) * scale + margin_pt)
  y0 = max(0.0, box.top * scale - margin_pt)
  y1 = min(PAGE_HEIGHT_PT, (box.bottom + 1) * scale + margin_pt)

  return CropBox(
    left=x0,
    bottom=PAGE_HEIGHT_PT - y1,
    right=PAGE_WIDTH_PT - x1,
    top=y0,
    width=x1 - x0,
    height=y1 - y0,
  )


def write_cropped_pdf(source: Path, crop: CropBox, output_pdf: Path) -> None:
  subprocess.run(
    [
      "pdfjam",
      str(source),
      "1",
      "--trim",
      f"{crop.left:.4f}pt {crop.bottom:.4f}pt {crop.right:.4f}pt {crop.top:.4f}pt",
      "--clip",
      "true",
      "--papersize",
      f"{{{crop.width:.4f}pt,{crop.height:.4f}pt}}",
      "--outfile",
      str(output_pdf),
    ],
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT,
  )


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--source", type=Path, default=Path("SIGNATURES.pdf"))
  parser.add_argument("--output-dir", type=Path, default=Path("Signatures"))
  parser.add_argument("--dpi", type=int, default=300)
  parser.add_argument("--threshold", type=int, default=245)
  parser.add_argument("--count", type=int, default=4)
  parser.add_argument("--margin-pt", type=float, default=8.0)
  parser.add_argument("--row-gap-px", type=int, default=None)
  parser.add_argument("--min-row-dark-px", type=int, default=5)
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  source = args.source.resolve()
  output_dir = args.output_dir.resolve()
  output_dir.mkdir(parents=True, exist_ok=True)

  row_gap_px = args.row_gap_px if args.row_gap_px is not None else max(1, round(args.dpi * 0.18))

  with tempfile.TemporaryDirectory(prefix="signature-extract-") as tmp:
    tmpdir = Path(tmp)
    ppm_path = render_source_pdf(source, tmpdir / "signatures", args.dpi)
    width, height, data = read_ppm(ppm_path)
    boxes = find_signature_boxes(
      width=width,
      height=height,
      data=data,
      threshold=args.threshold,
      expected_count=args.count,
      row_gap_px=row_gap_px,
      min_row_dark_px=args.min_row_dark_px,
    )

    for index, box in enumerate(boxes, start=1):
      crop = pixel_box_to_crop(box, args.dpi, args.margin_pt)
      output_pdf = output_dir / f"signature{index}.pdf"
      write_cropped_pdf(source, crop, output_pdf)
      print(
        f"Wrote {output_pdf.relative_to(Path.cwd())} "
        f"({crop.width:.1f}pt x {crop.height:.1f}pt)"
      )


if __name__ == "__main__":
  main()
