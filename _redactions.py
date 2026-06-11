"""Text redaction helpers for generated exhibit PDFs."""

from __future__ import annotations

from pathlib import Path

try:
  import fitz  # PyMuPDF
except ModuleNotFoundError:
  fitz = None


def parse_redactions(redactions_path: Path | None):
  specs = []
  seen = set()
  if not redactions_path or not redactions_path.exists():
    return specs

  with open(redactions_path, "r", encoding="utf-8") as f:
    for line in f:
      raw = line.strip()
      if not raw or raw.startswith("#"):
        continue
      spec = parse_redaction_spec(raw)
      key = (spec["match"], tuple(spec["preserve"]))
      if key not in seen:
        seen.add(key)
        specs.append(spec)

  specs.sort(key=lambda spec: len(spec["match"]), reverse=True)
  return specs


def parse_redaction_spec(raw: str):
  match_chars = []
  preserve = []
  preserve_start = None

  for char in raw:
    if char == "[" and preserve_start is None:
      preserve_start = len(match_chars)
      continue
    if char == "]" and preserve_start is not None:
      preserve.append((preserve_start, len(match_chars)))
      preserve_start = None
      continue
    match_chars.append(char)

  if preserve_start is not None:
    print(f"Warning: unmatched '[' in redaction term '{raw}'; treating it as a literal term.")
    match = raw
    preserve = []
  else:
    match = "".join(match_chars)

  if not match:
    print(f"Warning: ignoring empty redaction term '{raw}'")

  return {
    "raw": raw,
    "match": match,
    "match_lower": match.lower(),
    "preserve": preserve,
  }


def apply_pdf_redactions(pdf_path: Path, specs):
  if not specs:
    return
  if fitz is None:
    print(f"Warning: PyMuPDF is unavailable; skipping redactions for {pdf_path}")
    return

  doc = fitz.open(pdf_path)
  total_hits = 0
  for page in doc:
    page_hits = 0
    post_redaction_rects = []
    post_redaction_insertions = []
    for spec in specs:
      if spec["preserve"]:
        plans = fitz_partial_redaction_plans(page, spec)
        for plan in plans:
          for rect in plan["remove_rects"]:
            page.add_redact_annot(rect, fill=None, cross_out=False)
            page_hits += 1
          post_redaction_rects.extend(plan["redact_rects"])
          post_redaction_insertions.extend(plan["insertions"])
      else:
        rects = fitz_full_redaction_rects(page, spec)
        for rect in rects:
          page.add_redact_annot(rect, fill=(0, 0, 0), cross_out=False)
          page_hits += 1

    if page_hits:
      page.apply_redactions()
      for rect in post_redaction_rects:
        page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0), width=0, overlay=True)
      for insertion in post_redaction_insertions:
        page.insert_text(
          insertion["point"],
          insertion["text"],
          fontsize=insertion["fontsize"],
          fontname=insertion["fontname"],
          color=insertion["color"],
          overlay=True,
        )
      total_hits += page_hits

  if total_hits:
    tmp_path = pdf_path.with_suffix(".redacted.pdf")
    doc.save(tmp_path, garbage=4, deflate=True)
    doc.close()
    tmp_path.replace(pdf_path)
    print(f"Redacted {total_hits} match(es) in {pdf_path}")
  else:
    doc.close()


def fitz_full_redaction_rects(page, spec):
  rects = []
  for rect in page.search_for(spec["match"], quads=False):
    rect.x0 -= 0.5
    rect.y0 -= 0.5
    rect.x1 += 0.5
    rect.y1 += 0.5
    rects.append(rect)
  if not rects:
    rects.extend(fitz_literal_redaction_rects(page, spec))
  return rects


def fitz_literal_redaction_rects(page, spec):
  chars = fitz_page_chars(page)
  if not chars:
    return []

  text_lower = "".join(char["text"] for char in chars).lower()
  term_lower = spec["match_lower"]
  rects = []
  start = 0

  while True:
    index = text_lower.find(term_lower, start)
    if index == -1:
      break
    match_end = index + len(term_lower)
    rects.extend(
      fitz_rects_for_char_interval(
        chars,
        index,
        match_end,
        pad_x=0.5,
        pad_y=0.5,
      )
    )
    start = match_end

  return rects


def fitz_partial_redaction_plans(page, spec):
  chars = fitz_page_chars(page)
  if not chars:
    return []

  text = "".join(char["text"] for char in chars)
  text_lower = text.lower()
  term_lower = spec["match_lower"]
  plans = []
  start = 0

  while True:
    index = text_lower.find(term_lower, start)
    if index == -1:
      break

    match_end = index + len(term_lower)
    plan = {
      "remove_rects": fitz_rects_for_char_interval(
        chars,
        index,
        match_end,
        pad_x=0.05,
        pad_y=0.05,
      ),
      "redact_rects": [],
      "insertions": [],
    }

    for preserve_start, preserve_end in spec["preserve"]:
      absolute_start = index + preserve_start
      absolute_end = index + preserve_end
      plan["insertions"].extend(
        fitz_insertions_for_char_interval(chars, absolute_start, absolute_end)
      )

    for redact_start, redact_end in redaction_ranges_for_match(spec):
      absolute_start = index + redact_start
      absolute_end = index + redact_end
      plan["redact_rects"].extend(
        fitz_rects_for_char_interval(
          chars,
          absolute_start,
          absolute_end,
          pad_x=0.35,
          pad_y=0.75,
        )
      )

    plans.append(plan)
    start = index + len(term_lower)

  return plans


def fitz_page_chars(page):
  raw = page.get_text("rawdict", sort=True)
  chars = []
  line_id = 0
  for block in raw.get("blocks", []):
    if block.get("type") != 0:
      continue
    for line in block.get("lines", []):
      for span in line.get("spans", []):
        font = span.get("font", "Helvetica")
        fontsize = span.get("size", 11)
        color = span.get("color", 0)
        for char in span.get("chars", []):
          text = char.get("c", "")
          bbox = char.get("bbox")
          if not text or not bbox:
            continue
          rect = fitz.Rect(bbox)
          chars.append(
            {
              "text": text,
              "rect": rect,
              "origin": char.get("origin", (rect.x0, rect.y1)),
              "font": font,
              "fontsize": fontsize,
              "color": color,
              "line_id": line_id,
            }
          )
      line_id += 1
  return chars


def fitz_rects_for_char_interval(chars, interval_start, interval_end, pad_x=0.2, pad_y=0.2):
  rects_by_line = {}
  for char in chars[interval_start:interval_end]:
    line_id = char["line_id"]
    rect = rects_by_line.get(line_id)
    if rect is None:
      rects_by_line[line_id] = fitz.Rect(char["rect"])
    else:
      rect.include_rect(char["rect"])

  rects = []
  for rect in rects_by_line.values():
    rect.x0 -= pad_x
    rect.y0 -= pad_y
    rect.x1 += pad_x
    rect.y1 += pad_y
    rects.append(rect)
  return rects


def fitz_insertions_for_char_interval(chars, interval_start, interval_end):
  insertions = []
  current = []
  current_line = None
  for char in chars[interval_start:interval_end]:
    if current and char["line_id"] != current_line:
      insertions.append(fitz_insertion_for_chars(current))
      current = []
    current.append(char)
    current_line = char["line_id"]

  if current:
    insertions.append(fitz_insertion_for_chars(current))

  return insertions


def fitz_insertion_for_chars(chars):
  first = chars[0]
  return {
    "point": first["origin"],
    "text": "".join(char["text"] for char in chars),
    "fontsize": first["fontsize"],
    "fontname": fitz_base14_font(first["font"]),
    "color": fitz_color_tuple(first["color"]),
  }


def fitz_base14_font(font: str):
  normalized = font.lower().replace(" ", "").replace("-", "")
  if "times" in normalized:
    if "bold" in normalized and ("italic" in normalized or "oblique" in normalized):
      return "tibi"
    if "bold" in normalized:
      return "tibo"
    if "italic" in normalized or "oblique" in normalized:
      return "tiit"
    return "tiro"
  if "courier" in normalized:
    if "bold" in normalized and ("italic" in normalized or "oblique" in normalized):
      return "cobo"
    if "bold" in normalized:
      return "cobo"
    if "italic" in normalized or "oblique" in normalized:
      return "coit"
    return "cour"
  if "bold" in normalized and ("italic" in normalized or "oblique" in normalized):
    return "hebi"
  if "bold" in normalized:
    return "hebo"
  if "italic" in normalized or "oblique" in normalized:
    return "heit"
  return "helv"


def fitz_color_tuple(color):
  if isinstance(color, (tuple, list)):
    return tuple(color)
  if not isinstance(color, int):
    return (0, 0, 0)
  return (
    ((color >> 16) & 255) / 255,
    ((color >> 8) & 255) / 255,
    (color & 255) / 255,
  )


def redaction_ranges_for_match(spec):
  match_length = len(spec["match"])
  if not spec["preserve"]:
    return [(0, match_length)]

  ranges = []
  cursor = 0
  for preserve_start, preserve_end in spec["preserve"]:
    preserve_start = max(0, min(match_length, preserve_start))
    preserve_end = max(preserve_start, min(match_length, preserve_end))
    if cursor < preserve_start:
      ranges.append((cursor, preserve_start))
    cursor = max(cursor, preserve_end)
  if cursor < match_length:
    ranges.append((cursor, match_length))
  return ranges
