"""
tests/test_universal.py — Unit Tests for Multi-Mode Clock Engine, RFC 5545 Sync, and CLI.
"""

import io
from contextlib import redirect_stdout
import unittest

from zero_form_scheduling.cli import main as cli_main
from zero_form_scheduling.compositor import TimetableCompositor
from zero_form_scheduling.data import (
    get_all_sample_members,
    get_default_club_members,
    get_sample_us_member,
)
from zero_form_scheduling.model import (
    ClassSession,
    MemberSchedule,
    minutes_to_time,
    normalize_day_code,
    resolve_room_location,
    time_to_minutes,
)


class TestUniversalTimetableEngine(unittest.TestCase):
    def setUp(self):
        self.us_member = get_sample_us_member()
        self.tdtu_members = get_default_club_members()
        self.all_members = get_all_sample_members()
        self.compositor = TimetableCompositor(self.all_members)

    def test_us_member_profile_clock_mode(self):
        self.assertEqual(self.us_member.institution, "UC Berkeley")
        self.assertEqual(self.us_member.id, "us_alex")
        self.assertEqual(self.us_member.name, "Alex Miller")

        t2_sessions = self.us_member.get_day_sessions("T2")
        self.assertEqual(len(t2_sessions), 2)
        s1 = t2_sessions[0]
        self.assertIn("CS 188", s1.course_name)
        self.assertEqual(s1.start_time, "10:00")
        self.assertEqual(s1.end_time, "11:30")
        self.assertEqual(s1.building, "Wheeler Hall")
        self.assertEqual(s1.credits, 4.0)
        self.assertEqual(s1.duration_minutes, 90)
        self.assertEqual(s1.badge_text, "🎓 US")

    def test_day_normalization(self):
        self.assertEqual(normalize_day_code("Monday"), "T2")
        self.assertEqual(normalize_day_code("mon"), "T2")
        self.assertEqual(normalize_day_code("MO"), "T2")
        self.assertEqual(normalize_day_code("Tuesday"), "T3")
        self.assertEqual(normalize_day_code("Wednesday"), "T4")
        self.assertEqual(normalize_day_code("Thursday"), "T5")
        self.assertEqual(normalize_day_code("Friday"), "T6")
        self.assertEqual(normalize_day_code("Saturday"), "T7")
        self.assertEqual(normalize_day_code("Sunday"), "CN")
        self.assertEqual(normalize_day_code("Thứ 2"), "T2")
        self.assertEqual(normalize_day_code("Chủ Nhật"), "CN")

    def test_time_conversions(self):
        self.assertEqual(time_to_minutes("00:00"), 0)
        self.assertEqual(time_to_minutes("08:30"), 510)
        self.assertEqual(time_to_minutes("14:15"), 855)
        self.assertEqual(time_to_minutes("2:30 PM"), 870)
        self.assertEqual(minutes_to_time(855), "14:15")
        self.assertEqual(minutes_to_time(510), "08:30")

    def test_continuous_free_slots_clock_search(self):
        free_slots = self.compositor.find_free_slots_clock(
            day_code="T2",
            min_minutes=60,
            day_start_time="08:00",
            day_end_time="18:00",
            member_id="us_alex",
        )
        self.assertGreaterEqual(len(free_slots), 3)
        lunch_window = next((s for s in free_slots if s["start_time"] == "11:30"), None)
        self.assertIsNotNone(lunch_window)
        self.assertEqual(lunch_window["end_time"], "14:00")
        self.assertEqual(lunch_window["duration_minutes"], 150)

    def test_auto_arrange_study_event(self):
        res = self.compositor.auto_arrange_event(
            title="EECS 126 Midterm Review",
            duration_minutes=90,
            target_day="T2",
            preferred_window="afternoon",
            member_id="us_alex",
        )
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])
        self.assertEqual(res["duration_minutes"], 90)
        self.assertEqual(time_to_minutes(res["end_time"]) - time_to_minutes(res["start_time"]), 90)

    def test_campus_building_location_resolution(self):
        self.assertIn("Wheeler Hall", resolve_room_location("Wheeler 150"))
        self.assertIn("Soda Hall", resolve_room_location("Soda 310"))
        loc_explicit = resolve_room_location("310", building="Soda Hall")
        self.assertIn("Soda Hall", loc_explicit)
        self.assertIn("Room 310", loc_explicit)
        self.assertIn("Tòa A", resolve_room_location("A608"))

    def test_conflict_detection_cross_building_and_overlap(self):
        conflicted_member = MemberSchedule(
            id="test_conflict",
            name="Conflicted Student",
            institution="UC Berkeley",
            schedule={
                "T2": [
                    ClassSession(
                        course_name="CS 61A",
                        start_time="10:00",
                        end_time="11:00",
                        building="Dwinelle Hall",
                        room="Dwinelle 155",
                        mode="clock",
                    ),
                    ClassSession(
                        course_name="Math 53 Overlap",
                        start_time="10:30",
                        end_time="12:00",
                        building="Wheeler Hall",
                        room="Wheeler 212",
                        mode="clock",
                    ),
                ],
                "T3": [
                    ClassSession(
                        course_name="Physics 7A",
                        start_time="09:00",
                        end_time="10:00",
                        building="LeConte Hall",
                        room="LeConte 1",
                        mode="clock",
                    ),
                    ClassSession(
                        course_name="Chemistry 1A",
                        start_time="10:10",
                        end_time="11:30",
                        building="Latimer Hall",
                        room="Latimer 120",
                        mode="clock",
                    ),
                ],
            },
        )
        conflicts = self.compositor.detect_schedule_conflicts(conflicted_member)
        self.assertEqual(len(conflicts), 2)
        types = [c.conflict_type for c in conflicts]
        self.assertIn("overlap", types)
        self.assertIn("campus_travel", types)

    def test_rfc5545_ics_export_and_import(self):
        ics_text = self.compositor.export_schedule_to_ics(self.us_member)
        self.assertIn("BEGIN:VCALENDAR", ics_text)
        self.assertIn("END:VCALENDAR", ics_text)
        self.assertIn("BEGIN:VEVENT", ics_text)
        self.assertIn("CS 188", ics_text)
        self.assertIn("Wheeler Hall", ics_text)

        imported = self.compositor.import_schedule_from_ics(
            ics_text=ics_text,
            member_id="imported_alex",
            member_name="Alex Miller (Imported)",
        )
        self.assertEqual(imported.id, "imported_alex")
        total_sessions = sum(len(v) for v in imported.schedule.values())
        self.assertGreater(total_sessions, 0)
        m_sessions = imported.get_day_sessions("T2")
        self.assertGreaterEqual(len(m_sessions), 1)
        self.assertIn("CS 188", m_sessions[0].course_name)

    def test_cli_golden_and_export(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["golden", "--min-ratio", "1.0"])
        self.assertEqual(rc, 0)
        self.assertIn("100%", buf.getvalue())

        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            rc2 = cli_main(["export", "--min-ratio", "0.8"])
        self.assertEqual(rc2, 0)
        self.assertIn("BEGIN:VCALENDAR", buf2.getvalue())

        buf3 = io.StringIO()
        with redirect_stdout(buf3):
            rc3 = cli_main(["conflicts", "--member", "m1"])
        self.assertEqual(rc3, 0)

        buf4 = io.StringIO()
        with redirect_stdout(buf4):
            rc4 = cli_main(["chat"])
        self.assertEqual(rc4, 0)
        self.assertIn("KHUNG GIỜ VÀNG", buf4.getvalue())


if __name__ == "__main__":
    unittest.main()
