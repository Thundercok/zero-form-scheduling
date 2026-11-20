"""
zero_form_scheduling.cli — Zero-dependency CLI for multi-mode group scheduling.

Usage:
    zfs golden [--min-ratio 0.8]
    zfs chat
    zfs conflicts [--member m1]
    zfs export [--min-ratio 0.8] [--out group_free.ics]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List, Optional

from zero_form_scheduling.compositor import TimetableCompositor
from zero_form_scheduling.data import get_all_sample_members, get_default_club_members


def _build_compositor(include_us: bool = False) -> TimetableCompositor:
    members = get_all_sample_members() if include_us else get_default_club_members()
    return TimetableCompositor(members)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zfs",
        description="Zero-Form Group Scheduling: multi-mode timetable composition, conflict detection, and RFC 5545 iCalendar sync.",
    )
    parser.add_argument(
        "--include-us",
        action="store_true",
        help="Include the clock-mode international student profile alongside period-mode profiles.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_golden = sub.add_parser("golden", help="List shared high-availability windows across active members.")
    p_golden.add_argument("--min-ratio", type=float, default=0.8, help="Minimum fraction of free members (default: 0.8).")

    sub.add_parser("chat", help="Print a copy-pasteable group availability summary for chat.")

    p_conflicts = sub.add_parser("conflicts", help="Detect schedule overlaps and tight turnarounds for a member.")
    p_conflicts.add_argument("--member", default="m1", help="Member ID to inspect (default: m1).")

    p_export = sub.add_parser("export", help="Export shared free windows as RFC 5545 iCalendar (.ics).")
    p_export.add_argument("--min-ratio", type=float, default=0.8, help="Minimum fraction of free members (default: 0.8).")
    p_export.add_argument("--out", type=Path, default=None, help="Output .ics path (prints to stdout if omitted).")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    compositor = _build_compositor(include_us=args.include_us)

    if args.command == "golden":
        windows = compositor.find_golden_windows(min_ratio=args.min_ratio)
        if not windows:
            print(f"No shared windows found at >= {args.min_ratio:.0%} availability.")
            return 0
        for w in windows:
            pct = int(round(w.ratio * 100))
            print(
                f"{w.day_code} ({w.day_name}) | P{w.start_period}-P{w.end_period} ({w.time_range}) "
                f"| {w.free_count}/{w.total_count} free ({pct}%)"
            )
        return 0

    if args.command == "chat":
        print(compositor.generate_chat_message())
        return 0

    if args.command == "conflicts":
        member = next((m for m in compositor.members if m.id == args.member), None)
        if member is None:
            print(f"Unknown member id: {args.member}", file=sys.stderr)
            return 2
        conflicts = compositor.detect_schedule_conflicts(member)
        if not conflicts:
            print(f"No schedule conflicts detected for {member.name} ({member.id}).")
            return 0
        for c in conflicts:
            print(f"[{c.conflict_type}] {c.day_code}: {c.message}")
        return 0

    if args.command == "export":
        ics = compositor.generate_ics_content(min_ratio=args.min_ratio)
        if args.out is not None:
            args.out.write_text(ics, encoding="utf-8")
            print(f"Wrote {args.out}")
        else:
            print(ics)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
