import json
import tempfile
import unittest
from pathlib import Path

from learning_progress import (
    ProgressStoreError,
    load_progress,
    save_progress,
    summarize_progress,
)


def normalize_skill(value):
    return " ".join(str(value).lower().replace("-", " ").split())


class LearningProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(
            dir=Path(__file__).resolve().parents[1]
        )
        self.path = Path(self.temp_dir.name) / "progress.json"
        self.roadmap = ["Python", "Data Analysis", "Power BI"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_round_trip_normalizes_profile_and_skill_labels(self):
        save_progress(
            self.path, "  Kartik  ", "Data Analyst", self.roadmap,
            ["python", "Power BI"], normalize_skill,
        )
        self.assertEqual(
            load_progress(self.path, "kartik", "Data Analyst", self.roadmap, normalize_skill),
            ["Python", "Power BI"],
        )

    def test_raw_profile_label_and_unrelated_completed_skill_are_not_saved(self):
        save_progress(
            self.path, "private@example.com", "Data Analyst", self.roadmap,
            ["Python", "Not in this plan"], normalize_skill,
        )
        data = json.loads(self.path.read_text(encoding="utf-8"))
        serialized = json.dumps(data)
        self.assertNotIn("private@example.com", serialized)
        self.assertEqual(
            load_progress(self.path, "private@example.com", "Data Analyst", self.roadmap, normalize_skill),
            ["Python"],
        )

    def test_progress_is_separated_by_profile_and_job_plan(self):
        save_progress(self.path, "one", "Data Analyst", self.roadmap, ["Python"], normalize_skill)
        self.assertEqual(load_progress(self.path, "two", "Data Analyst", self.roadmap, normalize_skill), [])
        self.assertEqual(load_progress(self.path, "one", "Product Analyst", self.roadmap, normalize_skill), [])

    def test_missing_file_is_an_empty_progress_record(self):
        self.assertEqual(
            load_progress(self.path, "default", "Data Analyst", self.roadmap, normalize_skill), []
        )

    def test_corrupt_file_is_rejected_and_left_unchanged(self):
        original = b"{not-json"
        self.path.write_bytes(original)
        with self.assertRaises(ProgressStoreError):
            save_progress(self.path, "default", "Data Analyst", self.roadmap, ["Python"], normalize_skill)
        self.assertEqual(self.path.read_bytes(), original)

    def test_unsupported_schema_is_rejected_and_left_unchanged(self):
        original = b'{"schema_version":2,"profiles":{}}'
        self.path.write_bytes(original)
        with self.assertRaises(ProgressStoreError):
            load_progress(self.path, "default", "Data Analyst", self.roadmap, normalize_skill)
        self.assertEqual(self.path.read_bytes(), original)

    def test_empty_profile_is_rejected(self):
        with self.assertRaises(ProgressStoreError):
            save_progress(self.path, "  ", "Data Analyst", self.roadmap, [], normalize_skill)

    def test_summary_counts_saved_plans_steps_and_latest_update_without_identifiers(self):
        save_progress(self.path, "one", "Data Analyst", self.roadmap, ["Python"], normalize_skill)
        save_progress(self.path, "two", "Data Scientist", self.roadmap, ["Python", "Power BI"], normalize_skill)
        summary = summarize_progress(self.path)
        self.assertEqual(summary["saved_plan_count"], 2)
        self.assertEqual(summary["completed_step_count"], 3)
        self.assertEqual(summary["tracked_plan_count"], 2)
        self.assertEqual(summary["tracked_step_count"], 6)
        self.assertEqual(summary["completed_tracked_step_count"], 3)
        self.assertEqual(summary["completion_ratio"], 0.5)
        self.assertEqual(summary["fully_completed_plan_count"], 0)
        self.assertTrue(summary["last_updated"].endswith("+00:00"))

    def test_summary_of_missing_file_is_empty(self):
        self.assertEqual(
            summarize_progress(self.path),
            {
                "saved_plan_count": 0,
                "completed_step_count": 0,
                "last_updated": None,
                "tracked_plan_count": 0,
                "untracked_plan_count": 0,
                "fully_completed_plan_count": 0,
                "tracked_step_count": 0,
                "completed_tracked_step_count": 0,
                "completion_ratio": 0.0,
            },
        )

    def test_legacy_plan_without_total_steps_remains_readable_and_untracked(self):
        save_progress(self.path, "legacy", "Analyst", self.roadmap, ["Python"], normalize_skill)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        record = next(iter(next(iter(data["profiles"].values()))["plans"].values()))
        record.pop("total_steps")
        self.path.write_text(json.dumps(data), encoding="utf-8")

        summary = summarize_progress(self.path)
        self.assertEqual(summary["saved_plan_count"], 1)
        self.assertEqual(summary["completed_step_count"], 1)
        self.assertEqual(summary["untracked_plan_count"], 1)
        self.assertEqual(summary["tracked_plan_count"], 0)

        save_progress(self.path, "legacy", "Analyst", self.roadmap, ["Python"], normalize_skill)
        self.assertEqual(summarize_progress(self.path)["untracked_plan_count"], 0)


if __name__ == "__main__":
    unittest.main()
