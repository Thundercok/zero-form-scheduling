# zero-form-scheduling

**Zero-Form Group Scheduling** — a zero-dependency Python foundation for multi-mode academic and club timetable composition, conflict detection, and RFC 5545 iCalendar sync.

## Motivation

Group scheduling tools like When2meet or Doodle assume every participant will manually paint availability grids and redo the form whenever plans drift. Real student clubs and project teams already hold their schedules in fragmented artifacts — university period grids, `.ics` calendars, and natural-language chat messages with soft constraints (*"busy Thursday until 7pm unless urgent"*).

This repository separates the scheduling engine out of [`selective-delegation-agent`](https://github.com/Thundercok/selective-delegation-agent) into a focused codebase to explore **zero-form group coordination**:
1. **Deterministic core (implemented today):** Unified multi-mode schedule representation (Asian 15-period shift grids + continuous US/international clock blocks), group availability matrices, golden window extraction, overlap & cross-building turnaround conflict detection, auto-arrangement into open windows, and two-way RFC 5545 `.ics` export/import.
2. **Next research steps (planned, not yet implemented):**
   - Extracting hard/soft constraints from heterogeneous inputs (timetable exports + informal chat).
   - Minimal-clarification questioning: asking only about ambiguities that change the consensus slot.
   - Fairness-aware tie-breaking when no 100%-free slot exists.

## Quickstart

Requires Python 3.10+ (zero third-party runtime dependencies).

```bash
pip install -e ".[dev]"

# Find shared high-availability windows across sample members
zfs golden --min-ratio 0.8

# Generate a copy-pasteable group availability summary for chat
zfs chat

# Check schedule overlaps and tight turnarounds for a member
zfs conflicts --member m1

# Export shared free windows to RFC 5545 iCalendar
zfs export --min-ratio 0.8 --out group_free.ics
```

## Running Tests

```bash
pytest -v
```

## Project Layout

```text
zero_form_scheduling/
├── model.py        # Multi-mode schedule models (period/shift & clock blocks)
├── compositor.py   # Group availability matrices, golden windows, conflicts, auto-arrange
├── ics.py          # Two-way RFC 5545 iCalendar export & import
├── data.py         # Anonymized sample datasets & JSON persistence
└── cli.py          # `zfs` command-line interface
tests/
├── test_compositor.py
└── test_universal.py
```

## License

MIT — see [LICENSE](LICENSE).
