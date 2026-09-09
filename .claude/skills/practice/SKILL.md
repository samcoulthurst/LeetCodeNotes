---
name: practice
description: Drill the CleanNotes LeetCode notebooks from memory and mark the answers. Use when the user wants to practice, revise, drill, or be tested on the notebooks, when they ask to mark or check answers they have written, or when they ask what is due or what they keep getting wrong.
---

# Practice

A two-step loop over `CleanNotes/`: generate a blank notebook, the user writes the solutions
from memory, then mark them against the reference.

All three scripts live in `.claude/skills/practice/scripts/` and are run with `python3` from the
repo root. They own all file and schedule mechanics - never hand-write notebook JSON, and never
edit `Practice/progress.json` directly.

## Modes

| Invocation | Action |
|---|---|
| `/practice <topic>` | `build_session.py <topic>` - one whole notebook (substring match, e.g. `stack`, `binary`, `linked`) |
| `/practice due` | `build_session.py --due` - only what is due today, plus every leech |
| `/practice all` | `build_session.py --all` - every problem in CleanNotes |
| `/practice mark [notebook]` | the marking procedure below |
| `/practice status` | `status.py` - relay the table as-is |

Bare `/practice` with no argument: if the newest `Practice/*.ipynb` has answer cells edited away
from `...`, treat it as `mark`; otherwise ask which topic.

## Starting a session

Run the script, then report the file path and the problem list. Say nothing about the solutions -
no hints, no approach summaries, no complexity reminders. That is the whole response.

## Marking

Review by **reading**. Do not execute the code, do not write test files, do not edit the practice
notebook - feedback goes in the terminal only.

1. Resolve the target: the argument, else the newest `Practice/*.ipynb` by mtime.
2. Read it. Each problem is a markdown cell containing `<!-- practice-id: LC<n> -->` followed by
   one code cell holding the answer.
3. **Re-read the reference for every problem** from the matching `CleanNotes/*.ipynb` cell - the
   heading `## <Title> (LC <n>)` and the code cell after it. Never mark from memory.
4. Judge each answer on:
   - correctness on the general case;
   - edge cases - empty input, single element, duplicates, all-equal values, target absent,
     binary-search bounds and the `<` / `<=` in the loop condition, null head and single-node
     lists, integer overflow of the midpoint is not a concern in Python;
   - time and space complexity against the reference approach;
   - whether it actually uses the technique the topic teaches - a correct O(n^2) answer in the
     Two Pointers notebook has still missed the point.
   Style differences from the reference are not errors. Different-but-equally-good approaches are
   `correct`; say how it differs from the reference and move on.
5. Grade each one:
   - `correct` - right, and appropriate complexity;
   - `minor` - right idea and right complexity, but a small bug, a missed edge case, or a needless
     inefficiency within the same complexity class;
   - `wrong` - incorrect, or the wrong complexity class;
   - `skip` - the body is still `...` or otherwise unattempted. Do not grade an unattempted
     problem `wrong`.
6. Report in the terminal: one block per problem with the verdict, and for anything not `correct`
   **a concrete failing input** and what it produces versus what it should. Then a summary line and
   a short "focus next" list drawn from the problems now flagged as leeches.
7. Run `record.py <notebook> LC20=correct LC739=wrong ...` with every graded problem in one call,
   and relay the next due dates it prints.

## How scheduling works

`Practice/progress.json` holds one entry per problem: `interval`, `ease`, `due`, `attempts`,
`misses`, `streak`, and the last 20 grades. `record.py` applies an SM-2 variant - `correct` grows
the interval by the ease factor, `minor` grows it slightly, `wrong` resets it to one day, `skip`
resets the interval without counting a miss.

Problems missed 3 or more times become **leeches**: their interval is capped at 3 days and they are
included in every `--due` session regardless of due date, until three correct answers in a row
clear the flag. Sessions are always ordered weakest-first (miss rate, then miss count, then how
overdue), so shaky problems get attempted while the user is fresh.

## Notes

- Problems are discovered by parsing `## <Title> (LC <n>)` headings, so new CleanNotes notebooks
  are picked up with no code change.
- Code cells that are not a solution - such as the `ListNode` / `link` / `unlink` helpers in the
  Linked List notebook - are copied into the practice notebook verbatim under a `### Given`
  heading, and are not marked.
- Class-based problems (LC 146) are stubbed with their class and method signatures; bare-function
  problems get the `def` line. Imports are deliberately omitted - recalling them is part of it.
