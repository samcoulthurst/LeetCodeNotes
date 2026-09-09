#!/usr/bin/env python3
"""Build a blank practice notebook from CleanNotes.

    build_session.py <topic>   e.g. "stack", "binary" - one whole notebook
    build_session.py --due     only what is due today, across every notebook
    build_session.py --all     every problem in CleanNotes
"""

import argparse
import json
import re
import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import practicelib as lib


def slugify(text):
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def md_cell(source):
    return {"cell_type": "markdown", "id": uuid.uuid4().hex[:8],
            "metadata": {}, "source": source.splitlines(keepends=True)}


def code_cell(source):
    return {"cell_type": "code", "id": uuid.uuid4().hex[:8], "metadata": {},
            "execution_count": None, "outputs": [],
            "source": source.splitlines(keepends=True)}


def unique_path(directory, slug, today):
    base = f"{today.isoformat()}_{slug}"
    path = directory / f"{base}.ipynb"
    n = 2
    while path.exists():
        path = directory / f"{base}_{n}.ipynb"
        n += 1
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("topic", nargs="?", help="substring of a CleanNotes notebook name")
    ap.add_argument("--due", action="store_true", help="only problems due today (plus leeches)")
    ap.add_argument("--all", action="store_true", help="every problem in CleanNotes")
    args = ap.parse_args()

    if sum(bool(x) for x in (args.topic, args.due, args.all)) != 1:
        ap.error("give exactly one of: a topic, --due, or --all")

    today = date.today()
    progress = lib.load_progress()

    # Collect the candidate problems and the setup cells their notebooks need.
    if args.topic:
        path = lib.find_notebook(args.topic)
        problems, setup, source_nb = lib.parse_notebook(path)
        slug = slugify(path.stem)
        heading = path.stem
    else:
        problems, setup, source_nb = [], [], None
        for p in sorted(lib.CLEAN_NOTES.glob("*.ipynb")):
            probs, setups, nb = lib.parse_notebook(p)
            problems.extend(probs)
            setup.extend((str(p), src) for src in setups)
            source_nb = source_nb or nb
        slug = "due" if args.due else "all"
        heading = "Due today" if args.due else "All topics"

    if args.due:
        problems = lib.due_problems(problems, progress, today)

    # Only carry setup cells for notebooks that actually contributed a problem.
    if not args.topic:
        needed = {p["path"] for p in problems}
        setup = [src for src_path, src in setup if src_path in needed]

    if not problems:
        if args.due:
            print("Nothing due today. Pick a topic instead - available notebooks:")
            for p in sorted(lib.CLEAN_NOTES.glob("*.ipynb")):
                print(f"  {p.stem}")
        else:
            print(f"No problems found for {args.topic!r}.")
        return 1

    # Weakest first, so the shaky ones get attempted while fresh. Ties keep notebook order.
    order = {id(p): i for i, p in enumerate(problems)}
    problems.sort(key=lambda p: lib.weakness_key(p, progress, order[id(p)], today))

    listing = "\n".join(
        f"{i}. {p['title']} (LC {p['num']})" + (
            f"  - missed {progress[p['id']]['misses']}x"
            if p["id"] in progress and progress[p["id"]]["misses"] else "")
        for i, p in enumerate(problems, 1)
    )

    cells = [md_cell(
        f"# Practice: {heading}\n\n"
        f"{today.isoformat()} - {len(problems)} problem"
        f"{'s' if len(problems) != 1 else ''}, weakest first.\n\n"
        f"{listing}\n\n"
        "Write each solution from memory, then run `/practice mark`.\n"
    )]

    for cell in setup:
        cells.append(md_cell("### Given\n"))
        cells.append(code_cell(cell))

    for p in problems:
        entry = progress.get(p["id"], {})
        note = ""
        if lib.is_leech(entry):
            note = f"\n_missed {entry['misses']}x - leech_\n"
        elif entry.get("misses"):
            note = f"\n_missed {entry['misses']}x_\n"
        cells.append(md_cell(
            f"## {p['title']} (LC {p['num']})\n"
            f"<!-- practice-id: {p['id']} -->\n{note}"
        ))
        cells.append(code_cell(p["stub"] or "..."))

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": source_nb.get("metadata", {}).get("kernelspec", {}),
            "language_info": source_nb.get("metadata", {}).get("language_info", {}),
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    lib.PRACTICE.mkdir(exist_ok=True)
    out = unique_path(lib.PRACTICE, slug, today)
    out.write_text(json.dumps(nb, indent=1) + "\n")

    plural = "s" if len(problems) != 1 else ""
    print(f"Created {out.relative_to(lib.REPO)} - {len(problems)} problem{plural}:")
    for p in problems:
        print(f"  {p['id']:>6}  {p['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
