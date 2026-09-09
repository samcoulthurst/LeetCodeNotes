#!/usr/bin/env python3
"""Show what is due, what keeps going wrong, and what has never been attempted."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import practicelib as lib


def main():
    today = date.today()
    progress = lib.load_progress()
    problems = lib.all_problems()

    if not progress:
        print(f"No practice recorded yet. {len(problems)} problems across "
              f"{len({p['topic'] for p in problems})} notebooks.")
        print("Start with: /practice <topic>")
        return 0

    due = lib.due_problems(problems, progress, today)
    leeches = [p for p in problems if lib.is_leech(progress.get(p["id"], {}))]
    unseen = [p for p in problems if p["id"] not in progress]

    print(f"Due today ({len(due)}):")
    for p in sorted(due, key=lambda p: -lib.days_overdue(progress[p["id"]], today)):
        e = progress[p["id"]]
        over = lib.days_overdue(e, today)
        when = f"{over}d overdue" if over > 0 else "today"
        print(f"  {p['id']:>6}  {p['title'][:44]:<44} {when}")
    if not due:
        print("  nothing")

    print(f"\nWeak spots (missed {lib.LEECH_MISSES}+ times, capped at {lib.LEECH_INTERVAL}d):")
    for p in leeches:
        e = progress[p["id"]]
        print(f"  {p['id']:>6}  {p['title'][:44]:<44} {e['misses']}/{e['attempts']} missed")
    if not leeches:
        print("  none")

    print("\nBy topic:")
    for topic in sorted({p["topic"] for p in problems}):
        entries = [progress[p["id"]] for p in problems
                   if p["topic"] == topic and p["id"] in progress]
        total = sum(1 for p in problems if p["topic"] == topic)
        if not entries:
            print(f"  {topic:<26} not started ({total} problems)")
            continue
        attempts = sum(e["attempts"] for e in entries)
        misses = sum(e["misses"] for e in entries)
        rate = f"{misses / attempts:.0%}" if attempts else "-"
        print(f"  {topic:<26} {len(entries)}/{total} seen, {misses}/{attempts} missed ({rate})")

    if unseen:
        print(f"\nNever attempted ({len(unseen)}):")
        for p in unseen:
            print(f"  {p['id']:>6}  {p['title'][:44]:<44} {p['topic']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
