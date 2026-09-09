#!/usr/bin/env python3
"""Record marking results and reschedule.

    record.py [notebook] LC20=correct LC739=wrong LC1=minor LC49=skip

Grades: correct | minor | wrong | skip (skip = left unanswered, not counted as a miss).
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import practicelib as lib

GRADES = ("correct", "minor", "wrong", "skip")


def reschedule(entry, grade, today):
    ease = entry.get("ease", 2.0)
    interval = entry.get("interval", 1)

    if grade == "correct":
        ease = min(2.8, ease + 0.1)
        interval = max(1, round(interval * ease))
        entry["streak"] = entry.get("streak", 0) + 1
    elif grade == "minor":
        ease = max(1.3, ease - 0.05)
        interval = max(1, round(interval * 1.2))
        entry["streak"] = 0
    elif grade == "wrong":
        ease = max(1.3, ease - 0.3)
        interval = 1
        entry["misses"] = entry.get("misses", 0) + 1
        entry["streak"] = 0
    else:  # skip - unattempted is not the same as got it wrong
        interval = 1
        entry["streak"] = 0

    # Leeches keep resurfacing until they have been answered cleanly three times running.
    if lib.is_leech(entry):
        if entry["streak"] >= lib.LEECH_CLEAR_STREAK:
            entry["misses"] = 0
        else:
            interval = min(interval, lib.LEECH_INTERVAL)

    entry["ease"] = round(ease, 2)
    entry["interval"] = interval
    entry["attempts"] = entry.get("attempts", 0) + 1
    entry["last"] = today.isoformat()
    entry["due"] = lib.add_days(today, interval)
    entry["history"] = (entry.get("history", []) + [{"date": today.isoformat(), "grade": grade}])[-20:]
    return entry


def main(argv):
    grades, notebook = {}, None
    for arg in argv:
        if "=" in arg:
            pid, _, grade = arg.partition("=")
            pid, grade = pid.strip().upper(), grade.strip().lower()
            if grade not in GRADES:
                raise SystemExit(f"Unknown grade {grade!r} for {pid}. Use one of: {', '.join(GRADES)}")
            grades[pid] = grade
        else:
            notebook = arg

    if not grades:
        raise SystemExit(__doc__)

    today = date.today()
    progress = lib.load_progress()
    catalogue = {p["id"]: p for p in lib.all_problems()}

    for pid, grade in grades.items():
        if pid not in catalogue:
            print(f"warning: {pid} is not in CleanNotes - recording anyway")
        entry = progress.get(pid) or lib.new_entry(catalogue.get(pid, {"title": pid, "topic": "?"}))
        was_leech = lib.is_leech(entry)
        progress[pid] = reschedule(entry, grade, today)

        flag = ""
        if lib.is_leech(entry) and not was_leech:
            flag = "  <- now a leech, will keep coming back"
        elif was_leech and not lib.is_leech(entry):
            flag = "  <- leech cleared"
        print(f"{pid:>6}  {grade:<7} next {entry['due']} (+{entry['interval']}d)"
              f"  misses {entry['misses']}{flag}")

    if notebook:
        print(f"\nsession: {notebook}")
    lib.save_progress(progress)
    print(f"saved {lib.PROGRESS.relative_to(lib.REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
