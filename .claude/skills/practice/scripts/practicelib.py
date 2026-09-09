"""Shared helpers for the /practice skill: CleanNotes parsing and progress bookkeeping."""

import json
import re
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CLEAN_NOTES = REPO / "CleanNotes"
PRACTICE = REPO / "Practice"
PROGRESS = PRACTICE / "progress.json"

# "## Valid Parentheses (LC 20)" -> ("Valid Parentheses", "20").
# The reference cell's heading ("## Reference", "## Reference: ...") has no (LC n), so it
# is excluded for free.
HEADING_RE = re.compile(r"^##\s+(.*?)\s*\(LC\s*(\d+)\)\s*$")

LEECH_MISSES = 3        # misses at which a problem starts resurfacing constantly
LEECH_INTERVAL = 3      # days - the cap applied while a problem is a leech
LEECH_CLEAR_STREAK = 3  # consecutive correct answers needed to clear the flag


def cell_source(cell):
    src = cell.get("source", [])
    return "".join(src) if isinstance(src, list) else src


def build_stub(source):
    """Turn a reference solution into the skeleton LeetCode would hand you.

    Bare function -> its `def` line with an `...` body. Class-based problem -> every
    top-level class header plus its method signatures. Helpers nested inside a function
    are never exposed - remembering those is part of the recall.
    """
    out = []
    in_class = False
    class_had_method = False

    for line in source.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if indent == 0 and (stripped.startswith("class ") or stripped.startswith("def ")):
            if in_class and not class_had_method:
                out.append("    ...")
                out.append("")
            in_class = stripped.startswith("class ")
            class_had_method = False
            out.append(line.rstrip())
            if not in_class:
                out.extend(["    ...", ""])
        elif in_class and indent == 4 and stripped.startswith("def "):
            class_had_method = True
            out.extend([line.rstrip(), "        ...", ""])

    if in_class and not class_had_method:
        out.append("    ...")

    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


def parse_notebook(path):
    """Extract the problems and shared setup cells from one CleanNotes notebook.

    A problem is a markdown cell headed `## Title (LC n)` immediately followed by a code
    cell. Any other code cell (e.g. the ListNode / link / unlink helpers in the Linked List
    notebook) is scaffolding the practice notebook needs verbatim, not an answer.
    """
    nb = json.loads(path.read_text())
    cells = nb.get("cells", [])
    topic = path.stem
    problems = []
    solution_indices = set()

    for i, cell in enumerate(cells):
        if cell.get("cell_type") != "markdown":
            continue
        first_line = cell_source(cell).strip().splitlines()[:1]
        if not first_line:
            continue
        m = HEADING_RE.match(first_line[0].strip())
        if not m:
            continue

        title, num = m.group(1), m.group(2)
        stub = ""
        if i + 1 < len(cells) and cells[i + 1].get("cell_type") == "code":
            solution_indices.add(i + 1)
            stub = build_stub(cell_source(cells[i + 1]))

        problems.append({
            "id": f"LC{num}",
            "num": int(num),
            "title": title,
            "topic": topic,
            "stub": stub,
            "path": str(path),
        })

    setup = [
        cell_source(c)
        for i, c in enumerate(cells)
        if c.get("cell_type") == "code" and i not in solution_indices and cell_source(c).strip()
    ]

    return problems, setup, nb


def all_problems():
    """Every problem across CleanNotes, in filename order then notebook order."""
    out = []
    for path in sorted(CLEAN_NOTES.glob("*.ipynb")):
        problems, _, _ = parse_notebook(path)
        out.extend(problems)
    return out


def find_notebook(topic_query):
    """Resolve a topic substring to exactly one CleanNotes notebook."""
    paths = sorted(CLEAN_NOTES.glob("*.ipynb"))
    q = topic_query.lower().strip()
    matches = [p for p in paths if q in p.stem.lower()]
    if not matches:
        available = ", ".join(p.stem for p in paths)
        raise SystemExit(f"No CleanNotes notebook matches {topic_query!r}.\nAvailable: {available}")
    if len(matches) > 1:
        names = ", ".join(p.stem for p in matches)
        raise SystemExit(f"{topic_query!r} matches more than one notebook: {names}")
    return matches[0]


def load_progress():
    if not PROGRESS.exists():
        return {}
    return json.loads(PROGRESS.read_text())


def save_progress(progress):
    PRACTICE.mkdir(exist_ok=True)
    PROGRESS.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n")


def new_entry(problem):
    return {
        "title": problem["title"],
        "topic": problem["topic"],
        "last": None,
        "due": None,
        "interval": 1,
        "ease": 2.0,
        "attempts": 0,
        "misses": 0,
        "streak": 0,
        "history": [],
    }


def is_leech(entry):
    return entry.get("misses", 0) >= LEECH_MISSES


def days_overdue(entry, today=None):
    today = today or date.today()
    due = entry.get("due")
    if not due:
        return 0
    return (today - date.fromisoformat(due)).days


def weakness_key(problem, progress, index, today=None):
    """Sort key putting the weakest problems first. Ties keep notebook order."""
    entry = progress.get(problem["id"])
    if not entry:
        return (0.0, 0, 0, index)
    attempts = max(1, entry.get("attempts", 0))
    score = entry.get("misses", 0) / attempts
    return (-score, -entry.get("misses", 0), -days_overdue(entry, today), index)


def due_problems(problems, progress, today=None):
    """Problems due today, plus every leech whether or not it is technically due."""
    today = today or date.today()
    out = []
    for p in problems:
        entry = progress.get(p["id"])
        if not entry or not entry.get("due"):
            continue
        if is_leech(entry) or date.fromisoformat(entry["due"]) <= today:
            out.append(p)
    return out


def add_days(day, n):
    return (day + timedelta(days=n)).isoformat()
