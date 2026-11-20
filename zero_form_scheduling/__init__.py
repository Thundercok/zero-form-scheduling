"""
zero_form_scheduling — Universal Multi-Mode Timetable Compositor.
Supports both Vietnam Period/Shift systems (TDTU 15 periods) and US/International Clock Time-Blocks.
Enables RFC 5545 iCalendar synchronization and Agentic Reasoning tools.
"""

from zero_form_scheduling.model import (
    TDTU_PERIODS,
    DAYS,
    SHIFTS,
    DAY_ALIASES,
    DAY_TO_VN,
    DAY_TO_EN,
    ClassSession,
    MemberSchedule,
    ShiftAvailability,
    GoldenWindow,
    ScheduleConflict,
    LiveClassStatus,
    normalize_day_code,
    time_to_minutes,
    minutes_to_time,
    period_to_time,
    resolve_room_location,
)
from zero_form_scheduling.compositor import (
    TimetableCompositor,
    availability_to_color,
    degree_to_style,
)
from zero_form_scheduling.data import (
    get_default_club_members,
    get_sample_us_member,
    get_all_sample_members,
    load_club_members,
    save_club_members,
    dict_to_member_schedule,
    member_schedule_to_dict,
)
from zero_form_scheduling.ics import export_to_ics, import_from_ics

__all__ = [
    "TDTU_PERIODS",
    "DAYS",
    "SHIFTS",
    "DAY_ALIASES",
    "DAY_TO_VN",
    "DAY_TO_EN",
    "ClassSession",
    "MemberSchedule",
    "ShiftAvailability",
    "GoldenWindow",
    "ScheduleConflict",
    "LiveClassStatus",
    "normalize_day_code",
    "time_to_minutes",
    "minutes_to_time",
    "period_to_time",
    "resolve_room_location",
    "TimetableCompositor",
    "availability_to_color",
    "degree_to_style",
    "get_default_club_members",
    "get_sample_us_member",
    "get_all_sample_members",
    "load_club_members",
    "save_club_members",
    "dict_to_member_schedule",
    "member_schedule_to_dict",
    "export_to_ics",
    "import_from_ics",
]
