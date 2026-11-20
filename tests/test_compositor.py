"""
tests/test_compositor.py — Unit Tests for Group Timetable Compositor.
Validates multi-member schedule fusion, golden window extraction, conflict detection, and iCalendar generation.
"""

from datetime import datetime
import unittest

from zero_form_scheduling.compositor import TimetableCompositor, availability_to_color
from zero_form_scheduling.data import get_default_club_members
from zero_form_scheduling.model import ClassSession, MemberSchedule, resolve_room_location


class TestTimetableCompositorEngine(unittest.TestCase):
    def setUp(self):
        self.members = get_default_club_members()
        self.compositor = TimetableCompositor(self.members)

    def test_members_loaded(self):
        self.assertEqual(len(self.members), 6)
        names = [m.name for m in self.members]
        self.assertIn("Nguyễn Minh An", names)
        self.assertIn("Trần Lan Chi", names)
        self.assertIn("Lê Thảo Vy", names)

    def test_shift_matrix_calculation(self):
        matrix = self.compositor.compute_shift_matrix()
        self.assertIn("T2", matrix)
        self.assertIn("ca1", matrix["T2"])

        ca1_t2 = matrix["T2"]["ca1"]
        self.assertEqual(ca1_t2.shift_id, "ca1")
        self.assertEqual(ca1_t2.start_period, 1)
        self.assertEqual(ca1_t2.end_period, 3)
        self.assertEqual(ca1_t2.total_active_members, 6)
        self.assertGreater(ca1_t2.busy_count, 0)
        self.assertLess(len(ca1_t2.free_members), 6)

    def test_find_golden_windows(self):
        windows_100 = self.compositor.find_golden_windows(min_ratio=1.0)
        self.assertGreater(len(windows_100), 0)

        day_codes = [w.day_code for w in windows_100]
        self.assertIn("CN", day_codes)

        for w in windows_100:
            self.assertEqual(w.ratio, 1.0)
            self.assertEqual(w.free_count, 6)
            self.assertEqual(len(w.busy_members), 0)

    def test_toggle_member(self):
        self.assertEqual(len(self.compositor.active_members), 6)
        res = self.compositor.toggle_member("m1")
        self.assertFalse(res)
        self.assertEqual(len(self.compositor.active_members), 5)

        matrix = self.compositor.compute_shift_matrix()
        self.assertEqual(matrix["T2"]["ca1"].total_active_members, 5)

    def test_ics_generation(self):
        ics = self.compositor.generate_ics_content(min_ratio=0.8)
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("END:VCALENDAR", ics)
        self.assertIn("BEGIN:VEVENT", ics)
        self.assertIn("SUMMARY:[CLB FREE]", ics)
        self.assertIn("TZID=Asia/Ho_Chi_Minh", ics)

    def test_chat_message_generation(self):
        msg = self.compositor.generate_chat_message()
        self.assertIn("LỊCH TRỐNG CHUNG CLB", msg)
        self.assertIn("KHUNG GIỜ VÀNG", msg)
        self.assertIn("Nguyễn Minh An", msg)

    def test_availability_to_color_palette(self):
        c100 = availability_to_color(1.0)
        self.assertEqual(c100["badge"], "100%")
        self.assertEqual(c100["bg"], "#dcfce7")

        c80 = availability_to_color(0.83)
        self.assertEqual(c80["badge"], "Đa số")

        c50 = availability_to_color(0.5)
        self.assertEqual(c50["badge"], "Một nửa")

        c0 = availability_to_color(0.2)
        self.assertEqual(c0["badge"], "Kẹt lịch")

    def test_class_session_dual_degree_properties(self):
        s_undergrad = ClassSession(
            start_period=1, end_period=3, course_name="Giải tích 1", room="A608", degree_level="undergrad"
        )
        self.assertFalse(s_undergrad.is_master)
        self.assertEqual(s_undergrad.badge_text, "🎓 ĐH")
        self.assertEqual(s_undergrad.time_range_str, "06:50 - 09:20")

        s_master = ClassSession(
            start_period=13, end_period=15, course_name="Học máy nâng cao", room="C302", degree_level="master"
        )
        self.assertTrue(s_master.is_master)
        self.assertEqual(s_master.badge_text, "🏛️ ThS")
        self.assertEqual(s_master.time_range_str, "18:05 - 20:35")

    def test_unified_schedule_filtering_and_search(self):
        m1 = next(m for m in self.members if m.id == "m1")
        self.assertTrue(m1.is_dual_degree)

        all_sched = self.compositor.compute_unified_individual_schedule(m1, filter_level="all")
        self.assertEqual(len(all_sched["T2"]), 3)

        ug_sched = self.compositor.compute_unified_individual_schedule(m1, filter_level="undergrad")
        self.assertEqual(len(ug_sched["T2"]), 2)
        self.assertTrue(all(not s.is_master for s in ug_sched["T2"]))

        m_sched = self.compositor.compute_unified_individual_schedule(m1, filter_level="master")
        self.assertEqual(len(m_sched["T2"]), 1)
        self.assertTrue(m_sched["T2"][0].is_master)
        self.assertEqual(m_sched["T2"][0].course_name, "Học máy nâng cao & Khai phá dữ liệu")

        search_res = self.compositor.compute_unified_individual_schedule(m1, search_query="LLMs")
        self.assertEqual(len(search_res["T4"]), 1)
        self.assertIn("LLMs", search_res["T4"][0].course_name)

    def test_conflict_detection_engine(self):
        simulated_member = MemberSchedule(
            id="test_dual",
            name="Sinh viên Thử nghiệm",
            is_dual_degree=True,
            schedule={
                "T2": [
                    ClassSession(start_period=1, end_period=3, course_name="Toán ĐH", room="A101", degree_level="undergrad"),
                    ClassSession(start_period=2, end_period=4, course_name="AI ThS Trùng Giờ", room="C202", degree_level="master"),
                ],
                "T3": [
                    ClassSession(start_period=10, end_period=12, course_name="Thực hành ĐH", room="A607", degree_level="undergrad"),
                    ClassSession(start_period=13, end_period=15, course_name="Chuyên đề ThS", room="C305", degree_level="master"),
                ],
            },
        )
        conflicts = self.compositor.detect_schedule_conflicts(simulated_member)
        self.assertEqual(len(conflicts), 2)
        types = [c.conflict_type for c in conflicts]
        self.assertIn("overlap", types)
        self.assertIn("tight_turnaround", types)

    def test_live_status_calculation(self):
        m1 = next(m for m in self.members if m.id == "m1")

        dt_monday_in_class = datetime(2026, 9, 7, 7, 15, 0)
        status = self.compositor.compute_live_status(m1, current_dt=dt_monday_in_class)
        self.assertTrue(status.is_in_class)
        self.assertIsNotNone(status.current_session)
        self.assertIn("Giải tích", status.current_session.course_name)
        self.assertEqual(status.remaining_minutes, 125)

        dt_monday_break = datetime(2026, 9, 7, 12, 15, 0)
        status_break = self.compositor.compute_live_status(m1, current_dt=dt_monday_break)
        self.assertFalse(status_break.is_in_class)
        self.assertIsNotNone(status_break.next_session)
        self.assertEqual(status_break.next_session.course_name, "Học máy nâng cao & Khai phá dữ liệu")

    def test_unified_ics_and_clipboard_export(self):
        m1 = next(m for m in self.members if m.id == "m1")

        ics = self.compositor.generate_unified_ics(m1, filter_level="all")
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("END:VCALENDAR", ics)
        self.assertIn("[🎓 ĐH]", ics)
        self.assertIn("[🏛️ ThS]", ics)
        self.assertIn("Học máy nâng cao", ics)

        clip_txt = self.compositor.generate_unified_clipboard_text(m1, filter_level="all")
        self.assertIn("THỜI KHÓA BIỂU HỢP NHẤT", clip_txt)
        self.assertIn("Song bằng Đại học & Thạc sĩ", clip_txt)

    def test_room_location_resolution(self):
        self.assertIn("Tòa A", resolve_room_location("A608"))
        self.assertIn("Tầng 6", resolve_room_location("A608"))
        self.assertIn("Viện Sau Đại Học", resolve_room_location("C302"))
        self.assertIn("Tòa F", resolve_room_location("F702"))
        self.assertIn("Nhà Thi Đấu Thể Thao", resolve_room_location("TRET-NTD-2"))
        self.assertIn("Học Trực Tuyến", resolve_room_location("HOCTRUCTUYEN-3"))

    def test_workload_metrics_calculation(self):
        m1 = next(m for m in self.members if m.id == "m1")
        stats = self.compositor.compute_workload_stats(m1)
        self.assertGreater(stats["total_periods"], 20)
        self.assertGreater(stats["undergrad_periods"], 10)
        self.assertGreater(stats["master_periods"], 5)
        self.assertIn(stats["intensity"], ["chill", "balanced", "heavy", "overload"])
        self.assertGreaterEqual(stats["evening_classes"], 3)

    def test_today_agenda_timeline(self):
        m1 = next(m for m in self.members if m.id == "m1")
        dt_monday = datetime(2026, 9, 7, 8, 0, 0)
        agenda = self.compositor.get_today_agenda(m1, current_dt=dt_monday)
        self.assertEqual(len(agenda), 3)
        statuses = [item["status"] for item in agenda]
        self.assertIn("live", statuses)
        self.assertIn("upcoming", statuses)


if __name__ == "__main__":
    unittest.main()
