import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import headcount_importer as importer
from data_pipeline.skill_demand import load_headcount_demand, recent_skill_counts


class HeadcountImporterTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parents[1] / "build" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.root = Path(self.temp.name)
        self.catalog = self.root / "catalog.csv"
        with self.catalog.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=importer.APP_COLUMNS)
            writer.writeheader()
            writer.writerow({"job_id": "1", "category": "AI / ML", "job_title": "ML Engineer", "job_description": "private source text", "job_skill_set": "['Python', 'Scikit-Learn']"})
        self.output = self.root / "out" / "demand.csv"

    def tearDown(self):
        self.temp.cleanup()

    def test_uses_india_filters_deduplicates_and_writes_aggregates_only(self):
        observed = []

        def page(params, key):
            observed.append(params)
            return {"data": [
                {"job_id": "same", "title": {"state": "known", "value": "ML Engineer"}, "description": {"state": "known", "value": "Python and Scikit-Learn"}},
                {"job_id": "same", "title": {"state": "known", "value": "ML Engineer"}, "description": {"state": "known", "value": "Python and Scikit-Learn"}},
            ], "next_cursor": None, "snapshot_watermark": "watermark"}

        with patch.object(importer, "request_page", side_effect=page):
            result = importer.run(self.catalog, self.output, api_key="unused-test-token", updated_since="2026-10-22T00:00:00Z")
        self.assertEqual(result["unique_jobs"], 1)
        self.assertEqual(observed[0]["country"], "IN")
        self.assertEqual(observed[0]["fields"], importer.FIELDS)
        content = self.output.read_text(encoding="utf-8")
        self.assertNotIn("private source text", content)
        self.assertNotIn("Python and Scikit-Learn", content)
        self.assertIn("python", content)
        self.assertIn(",1", content)
        self.assertIn("window_start_utc", content)
        self.assertIn("generated_at_utc", content)

    def test_fails_when_cap_would_truncate_a_page_walk(self):
        page = {"data": [{"job_id": str(n), "title": "Engineer", "description": "Python"} for n in range(2)], "next_cursor": "opaque", "snapshot_watermark": "w"}
        with patch.object(importer, "request_page", return_value=page):
            with self.assertRaisesRegex(RuntimeError, "safety cap"):
                importer.run(self.catalog, self.output, api_key="unused-test-token", updated_since="2026-10-22T00:00:00Z", max_records=1)
        self.assertFalse(self.output.exists())

    def test_requires_secret_without_showing_it(self):
        with self.assertRaisesRegex(ValueError, "HEADCOUNT_API_KEY is required"):
            importer.run(self.catalog, self.output, api_key="", updated_since="2026-10-22T00:00:00Z")


    def test_app_reader_loads_only_aggregate_counts_and_uses_max_across_categories(self):
        aggregate = self.root / "aggregate.csv"
        aggregate.write_text(
            "category,skill,distinct_job_count,window_start_utc,generated_at_utc\n"
            "AI,Python,3,2026-10-22T00:00:00Z,2026-10-24T00:00:00Z\n"
            "Data,Python,2,2026-10-22T00:00:00Z,2026-10-24T00:00:00Z\n",
            encoding="utf-8",
        )
        rows, metadata = load_headcount_demand(aggregate, importer.normalize)
        self.assertEqual(recent_skill_counts(rows), {"python": 3})
        self.assertEqual(metadata["generated_at_utc"], "2026-10-24T00:00:00Z")

    def test_app_reader_falls_back_when_aggregate_is_missing(self):
        rows, metadata = load_headcount_demand(self.root / "missing.csv", importer.normalize)
        self.assertIsNone(rows)
        self.assertIsNone(metadata)


if __name__ == "__main__":
    unittest.main()

