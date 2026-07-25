#!/usr/bin/env python3
"""
PWSL Time Drop Finder — core logic (no GUI)

Vendored from LakeRidgeComputers/pwsl-div-time-drops (improvement-labels build).
Parses a Meet Maestro Time Improvement / Personal Best labels PDF and builds a
printable 3-column label sheet for swims that dropped at least min_drop seconds.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ----------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------

TIME = r"(?:\d{1,2}:\d{2}\.\d{2}|\d{1,3}\.\d{2})"
EVENT_RE = re.compile(r"^#(\d+)\s+(.+)$")
IGNORE_EVENT_THRESHOLD = 100  # skip events numbered 100 and above
DASH_SPLIT_RE = re.compile(r"\s+[\u2013\u2014-]\s+")  # en dash, em dash, or hyphen
EVENT_HEADER_TOKEN_RE = re.compile(r"^#\d+$")


def time_to_seconds(t: str) -> float:
    """Convert a 'SS.ss' or 'M:SS.ss' time string to seconds (float)."""
    if ":" in t:
        minutes, seconds = t.split(":")
        return int(minutes) * 60 + float(seconds)
    return float(t)


def seconds_to_time(sec: float) -> str:
    """Convert seconds (float) back to 'SS.ss' or 'M:SS.ss' notation."""
    minutes = int(sec // 60)
    remainder = sec - minutes * 60
    if minutes:
        return f"{minutes}:{remainder:05.2f}"
    return f"{remainder:.2f}"


def event_number(event_str: str) -> int:
    m = re.match(r"^#(\d+)", event_str)
    return int(m.group(1)) if m else -1


def is_relay_event(event_str: str) -> bool:
    return "relay" in event_str.lower()


# ----------------------------------------------------------------------
# Format validation
# ----------------------------------------------------------------------

def looks_like_improvement_pdf(pdf: pdfplumber.PDF) -> bool:
    """Sanity-check that the selected file is a Time Improvement /
    Personal Best labels PDF (contains at least one 'Personal Best:' line)."""
    if not pdf.pages:
        return False
    first_text = pdf.pages[0].extract_text() or ""
    return "Personal Best:" in first_text


# ----------------------------------------------------------------------
# Column detection
# ----------------------------------------------------------------------

def detect_pdf_columns(pdf: pdfplumber.PDF):
    """Find column start x-positions by clustering '#<number>' token x0 values."""
    starts = set()
    for page in pdf.pages:
        for w in page.extract_words():
            if EVENT_HEADER_TOKEN_RE.match(w["text"]):
                starts.add(round(w["x0"]))

    if not starts:
        return []

    starts = sorted(starts)
    clusters = []
    for x in starts:
        if clusters and x - clusters[-1][-1] < 20:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    return [min(c) for c in clusters]


def column_bounds(col_starts, page_width):
    """Convert column start x-positions into crop boundaries."""
    if len(col_starts) <= 1:
        return [0, page_width]
    return [0] + [s - 2 for s in col_starts[1:]] + [page_width]


# ----------------------------------------------------------------------
# Parser: Improvement / Personal Best card PDFs
# ----------------------------------------------------------------------

NAME_AGE_RE = re.compile(r"^(?P<name>.+)\s+\((?P<age>\d{1,2})\)$")
PB_RE = re.compile(
    r"^Personal Best:\s*(?P<time>" + TIME + r")"
    r"(?:\s*\(-(?P<delta>" + TIME + r")\))?$"
)


def parse_improvement_pdf(path: Path, min_drop: float):
    results = []

    with pdfplumber.open(path) as pdf:
        col_starts = detect_pdf_columns(pdf)

        for page in pdf.pages:
            bounds = column_bounds(col_starts, page.width)
            num_cols = max(len(bounds) - 1, 1)

            for col in range(num_cols):
                crop = page.within_bbox((bounds[col], 0, bounds[col + 1], page.height))
                text = crop.extract_text() or ""
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

                for i in range(0, len(lines) - 4, 5):
                    event_line, name_line, pb_line, team_date_line, meet_line = lines[i:i + 5]

                    event_match = EVENT_RE.match(event_line)
                    if not event_match:
                        continue
                    if int(event_match.group(1)) >= IGNORE_EVENT_THRESHOLD:
                        continue
                    current_event = f"#{event_match.group(1)} {event_match.group(2)}"
                    if is_relay_event(current_event):
                        continue

                    name_match = NAME_AGE_RE.match(name_line)
                    pb_match = PB_RE.match(pb_line)
                    if not name_match or not pb_match:
                        continue

                    delta_raw = pb_match.group("delta")
                    if delta_raw is None:
                        continue

                    drop = time_to_seconds(delta_raw)
                    if drop < min_drop:
                        continue

                    team_parts = DASH_SPLIT_RE.split(team_date_line, maxsplit=1)
                    team = team_parts[0].strip() if team_parts else team_date_line.strip()
                    date = team_parts[1].strip() if len(team_parts) == 2 else ""

                    results.append({
                        "event": current_event,
                        "name": name_match.group("name"),
                        "age": name_match.group("age"),
                        "team": team,
                        "result_time": pb_match.group("time"),
                        "drop_seconds": round(drop, 2),
                        "meet_name": meet_line.strip(),
                        "meet_date": date,
                    })

    return results


def parse_pdf(path: Path, min_drop: float):
    with pdfplumber.open(path) as pdf:
        if not looks_like_improvement_pdf(pdf):
            raise ValueError(
                "This doesn't look like a Time Improvement / Personal Best labels PDF "
                "(no 'Personal Best:' lines found). In Meet Maestro, export the "
                "'Personal Best' or 'Improvement' labels report for this meet, not "
                "the general Results PDF."
            )
    return parse_improvement_pdf(path, min_drop)


def process_file(pdf_path: Path, min_drop: float):
    return parse_pdf(pdf_path, min_drop)


# ----------------------------------------------------------------------
# Label sheet PDF generation
# ----------------------------------------------------------------------

PAGE_W, PAGE_H = letter  # 612 x 792
COL_X = [22.5, 224.1, 425.7]
TOP_OFFSET = 46.9
LINE_HEIGHT = 10.35
ROW_HEIGHT = 72.0
ROWS_PER_PAGE = 10
FONT_NAME = "Helvetica"
FONT_SIZE = 9
CARDS_PER_PAGE = len(COL_X) * ROWS_PER_PAGE


def draw_card(c, x, top, record):
    """Draw one 5-line label card with its top-left line at distance `top`
    from the top of the page."""
    lines = [
        record["event"],
        f"{record['name']} ({record['age']})",
        f"Personal Best: {record['result_time']} (-{record['drop_seconds']:.2f})",
        f"{record['team']} \u2013 {record['meet_date']}" if record["meet_date"]
        else record["team"],
        record["meet_name"],
    ]
    for i, text in enumerate(lines):
        line_top = top + i * LINE_HEIGHT
        baseline_y = PAGE_H - line_top - FONT_SIZE * 0.8
        c.drawString(x, baseline_y, text)


def generate_labels_pdf(results, out_path: Path):
    c = canvas.Canvas(str(out_path), pagesize=letter)
    c.setFont(FONT_NAME, FONT_SIZE)

    for idx, record in enumerate(results):
        pos_in_page = idx % CARDS_PER_PAGE
        if idx > 0 and pos_in_page == 0:
            c.showPage()
            c.setFont(FONT_NAME, FONT_SIZE)

        row = pos_in_page // len(COL_X)
        col = pos_in_page % len(COL_X)
        x = COL_X[col]
        top = TOP_OFFSET + row * ROW_HEIGHT
        draw_card(c, x, top, record)

    c.save()
