import io
import csv
import json
import tempfile
import unittest
from urllib.error import HTTPError
from pathlib import Path
from unittest.mock import patch

import headcount_importer as importer
from data_pipeline.skill_demand import load_headcount_demand, load_headcount_titles, recent_skill_counts


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
            result = importer.run(self.catalog, self.output, api_key="unused-test-token", posted_since="2026-10-22T00:00:00Z")
        self.assertEqual(result["unique_jobs"], 1)
        self.assertEqual(observed[0]["country"], "IN")
        self.assertEqual(observed[0]["fields"], importer.FIELDS)
        self.assertEqual(observed[0]["posted_since"], "2026-10-22T00:00:00Z")
        self.assertNotIn("updated_since", observed[0])
        content = self.output.read_text(encoding="utf-8")
        self.assertNotIn("private source text", content)
        self.assertNotIn("Python and Scikit-Learn", content)
        self.assertIn("python", content)
        self.assertIn(",1", content)
        self.assertIn("window_start_utc", content)
        self.assertIn("generated_at_utc", content)
        title_path = self.output.with_name("headcount_job_titles.csv")
        with title_path.open(encoding="utf-8", newline="") as handle:
            titles = list(csv.DictReader(handle))
        self.assertEqual(titles, [{
            "job_title": "ML Engineer",
            "distinct_job_count": "1",
            "window_start_utc": "2026-10-22T00:00:00Z",
            "generated_at_utc": json.loads(self.output.with_suffix(".metadata.json").read_text(encoding="utf-8"))["generated_at_utc"],
        }])
        self.assertNotIn("private source text", title_path.read_text(encoding="utf-8"))
        self.assertNotIn("Python and Scikit-Learn", title_path.read_text(encoding="utf-8"))
        metadata = json.loads(self.output.with_suffix(".metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["api_records"], 1)
        self.assertEqual(metadata["processed_jobs"], 1)
        self.assertEqual(metadata["distinct_title_count"], 1)
        self.assertNotIn("private source text", json.dumps(metadata))
        loaded_titles, title_metadata = load_headcount_titles(title_path, self.output.with_suffix(".metadata.json"))
        self.assertEqual(loaded_titles[0]["job_title"], "ML Engineer")
        self.assertEqual(title_metadata["distinct_title_count"], "1")

    def test_fails_when_cap_would_truncate_a_page_walk(self):
        page = {"data": [{"job_id": str(n), "title": "Engineer", "description": "Python"} for n in range(2)], "next_cursor": "opaque", "snapshot_watermark": "w"}
        with patch.object(importer, "request_page", return_value=page):
            with self.assertRaisesRegex(RuntimeError, "safety cap"):
                importer.run(self.catalog, self.output, api_key="unused-test-token", posted_since="2026-10-22T00:00:00Z", max_records=1)
        self.assertFalse(self.output.exists())

    def test_cap_counts_records_even_without_usable_descriptions(self):
        page = {"data": [{"job_id": str(n), "title": "", "description": ""} for n in range(2)], "next_cursor": None, "snapshot_watermark": "w"}
        with patch.object(importer, "request_page", return_value=page):
            with self.assertRaisesRegex(RuntimeError, "safety cap"):
                importer.run(self.catalog, self.output, api_key="unused-test-token", posted_since="2026-10-22T00:00:00Z", max_records=1)
        self.assertFalse(self.output.exists())

    def test_keeps_real_titles_with_missing_descriptions_as_title_only_aggregates(self):
        page = {"data": [
            {"job_id": "one", "title": "Data Analyst", "description": ""},
            {"job_id": "two", "title": " Data   Analyst ", "description": {"state": "unknown"}},
        ], "next_cursor": None, "snapshot_watermark": "w"}
        with patch.object(importer, "request_page", return_value=page):
            result = importer.run(self.catalog, self.output, api_key="unused-test-token", posted_since="2026-10-22T00:00:00Z")
        self.assertEqual(result["unique_jobs"], 2)
        self.assertEqual(result["processed_jobs"], 0)
        with self.output.with_name("headcount_job_titles.csv").open(encoding="utf-8", newline="") as handle:
            titles = list(csv.DictReader(handle))
        self.assertEqual(len(titles), 1)
        self.assertEqual(titles[0]["job_title"], "Data Analyst")
        self.assertEqual(titles[0]["distinct_job_count"], "2")
        self.assertFalse(self.output.with_name("headcount_job_titles.csv").with_suffix(".metadata.json").exists())

    def test_title_reader_distinguishes_missing_empty_and_malformed_snapshots(self):
        title_path = self.output.with_name("headcount_job_titles.csv")
        metadata_path = self.output.with_suffix(".metadata.json")
        self.assertEqual(load_headcount_titles(title_path, metadata_path), (None, None))
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps({
            "generated_at_utc": "2026-10-24T00:00:00Z",
            "window_start_utc": "2026-10-22T00:00:00Z",
            "api_records": 0,
            "processed_jobs": 0,
            "distinct_title_count": 0,
        }), encoding="utf-8")
        title_path.write_text(",".join(importer.TITLE_COLUMNS) + "\n", encoding="utf-8")
        rows, metadata = load_headcount_titles(title_path, metadata_path)
        self.assertEqual(rows, [])
        self.assertEqual(metadata["api_records"], "0")
        title_path.write_text(",".join(importer.TITLE_COLUMNS) + "\nEngineer,invalid,2026-10-22T00:00:00Z,2026-10-24T00:00:00Z\n", encoding="utf-8")
        self.assertEqual(load_headcount_titles(title_path, metadata_path), (None, None))

    def test_reader_keeps_metadata_for_header_only_aggregate(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(",".join(importer.OUTPUT_COLUMNS) + "\n", encoding="utf-8")
        metadata = {"generated_at_utc": "2026-10-24T00:00:00Z", "window_start_utc": "2026-10-22T00:00:00Z", "api_records": 2, "processed_jobs": 0, "category_skill_pairs": 0, "snapshot_watermark": "2026-10-21T22:10:37Z"}
        self.output.with_suffix(".metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        rows, loaded = load_headcount_demand(self.output, importer.normalize)
        self.assertEqual(rows, [])
        self.assertEqual(loaded["api_records"], "2")

    def test_transient_504_retries_and_succeeds_respecting_retry_after(self):
        error = HTTPError("https://api.example.invalid", 504, "timeout", {"Retry-After": "7"}, None)
        response = io.BytesIO(b'{"data": [], "next_cursor": null}')
        with patch.object(importer, "urlopen", side_effect=[error, response]) as request, patch.object(importer.time, "sleep") as sleep:
            result = importer.request_page({"country": "IN"}, "unused-test-token")
        self.assertEqual(result["data"], [])
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(7.0)

    def test_timeout_retries_with_bounded_backoff(self):
        response = io.BytesIO(b'{"data": [], "next_cursor": null}')
        with patch.object(importer, "urlopen", side_effect=[TimeoutError(), response]) as request, patch.object(importer.time, "sleep") as sleep, patch.object(importer.random, "uniform", return_value=1.0):
            importer.request_page({"country": "IN"}, "unused-test-token")
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_exhausted_transient_retries_fail_honestly(self):
        error = HTTPError("https://api.example.invalid", 504, "timeout", {}, None)
        with patch.object(importer, "urlopen", side_effect=[error] * importer.MAX_REQUEST_ATTEMPTS) as request, patch.object(importer.time, "sleep"), patch.object(importer.random, "uniform", return_value=1.0):
            with self.assertRaisesRegex(importer.TransientAPIError, "HTTP 504"):
                importer.request_page({"country": "IN"}, "unused-test-token")
        self.assertEqual(request.call_count, importer.MAX_REQUEST_ATTEMPTS)

    def test_non_retryable_client_error_fails_without_retry(self):
        error = HTTPError("https://api.example.invalid", 400, "bad request", {}, None)
        with patch.object(importer, "urlopen", side_effect=error) as request, patch.object(importer.time, "sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "HTTP 400"):
                importer.request_page({"country": "IN"}, "unused-test-token")
        request.assert_called_once()
        sleep.assert_not_called()

    def test_failed_later_page_preserves_last_known_good_snapshot_pair(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        original_csv = "known-good aggregate\n"
        original_metadata = '{"known_good": true}\n'
        self.output.write_text(original_csv, encoding="utf-8")
        metadata_path = self.output.with_suffix(".metadata.json")
        metadata_path.write_text(original_metadata, encoding="utf-8")
        first_page = {"data": [{"job_id": "new", "title": "Engineer", "description": "Python"}], "next_cursor": "next", "snapshot_watermark": "w"}
        with patch.object(importer, "request_page", side_effect=[first_page, RuntimeError("Headcount API returned HTTP 504")]):
            with self.assertRaisesRegex(RuntimeError, "HTTP 504"):
                importer.run(self.catalog, self.output, api_key="unused-test-token", posted_since="2026-10-22T00:00:00Z")
        self.assertEqual(self.output.read_text(encoding="utf-8"), original_csv)
        self.assertEqual(metadata_path.read_text(encoding="utf-8"), original_metadata)

    def test_fallback_preserves_snapshot_data_and_marks_original_timestamp_stale(self):
        source = self.root / "previous"
        source.mkdir()
        source_csv = "category,skill,distinct_job_count,window_start_utc,generated_at_utc\nAI,python,1,2026-10-22T00:00:00Z,2026-10-24T00:00:00Z\n"
        source_titles = "job_title,distinct_job_count,window_start_utc,generated_at_utc\nEngineer,1,2026-10-22T00:00:00Z,2026-10-24T00:00:00Z\n"
        source_meta = {"generated_at_utc":"2026-10-24T00:00:00Z", "window_start_utc":"2026-10-22T00:00:00Z", "api_records":1, "processed_jobs":1, "category_skill_pairs":1, "distinct_title_count":1}
        (source / "headcount_skill_demand.csv").write_text(source_csv, encoding="utf-8")
        (source / "headcount_job_titles.csv").write_text(source_titles, encoding="utf-8")
        (source / "headcount_skill_demand.metadata.json").write_text(json.dumps(source_meta), encoding="utf-8")
        report = importer.copy_last_known_good(source, self.output, failure="Headcount API returned HTTP 504")
        self.assertEqual(self.output.read_text(encoding="utf-8"), source_csv)
        self.assertEqual(self.output.with_name("headcount_job_titles.csv").read_text(encoding="utf-8"), source_titles)
        metadata = json.loads(self.output.with_suffix(".metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["generated_at_utc"], "2026-10-24T00:00:00Z")
        self.assertEqual(metadata["source_snapshot_generated_at_utc"], "2026-10-24T00:00:00Z")
        self.assertTrue(metadata["stale"])
        self.assertTrue(metadata["fallback"])
        self.assertEqual(report["status"], "stale_fallback")
        rows, loaded = load_headcount_demand(self.output, importer.normalize)
        self.assertEqual(len(rows), 1)
        self.assertEqual(loaded["stale"], "True")

    def test_fallback_fails_clearly_without_valid_previous_snapshot(self):
        with self.assertRaisesRegex(RuntimeError, "no valid previous aggregate snapshot"):
            importer.copy_last_known_good(self.root / "missing", self.output, failure="Headcount API returned HTTP 504")
        self.assertFalse(self.output.exists())

    def test_cli_routes_exhausted_transient_outage_to_fallback(self):
        with patch.object(importer.sys, "argv", ["headcount_importer.py", "--fallback-dir", str(self.root)]), patch.object(importer, "run", side_effect=importer.TransientAPIError("Headcount API returned HTTP 504")), patch.object(importer, "copy_last_known_good", return_value={"status": "stale_fallback"}) as fallback:
            self.assertEqual(importer.main(), 0)
        fallback.assert_called_once_with(self.root, Path("build/headcount_skill_demand.csv"), failure="Headcount API returned HTTP 504")

    def test_requires_secret_without_showing_it(self):
        with self.assertRaisesRegex(ValueError, "HEADCOUNT_API_KEY is required"):
            importer.run(self.catalog, self.output, api_key="", posted_since="2026-10-22T00:00:00Z")


    def test_app_reader_loads_only_aggregate_counts_and_uses_max_across_categories(self):
        aggregate = self.root / "aggregate.csv"
        aggregate.write_text(
            "category,skill,distinct_job_count,window_start_utc,generated_at_utc\n"
            "AI,Python,3,2026-10-22T00:00:00Z,2026-10-24T00:00:00Z\n"
            "Data,Python,2,2026-10-22T00:00:00Z,2026-10-24T00:00:00Z\n",
            encoding="utf-8",
        )
        aggregate.with_suffix(".metadata.json").write_text(json.dumps({"generated_at_utc":"2026-10-24T00:00:00Z", "window_start_utc":"2026-10-22T00:00:00Z", "api_records":2, "processed_jobs":2, "category_skill_pairs":2}), encoding="utf-8")
        rows, metadata = load_headcount_demand(aggregate, importer.normalize)
        self.assertEqual(recent_skill_counts(rows), {"python": 3})
        self.assertEqual(metadata["generated_at_utc"], "2026-10-24T00:00:00Z")

    def test_app_reader_falls_back_when_aggregate_is_missing(self):
        rows, metadata = load_headcount_demand(self.root / "missing.csv", importer.normalize)
        self.assertIsNone(rows)
        self.assertIsNone(metadata)

    def test_app_reader_rejects_malformed_rows_instead_of_treating_them_as_empty(self):
        aggregate = self.root / "malformed.csv"
        aggregate.write_text(
            "category,skill,distinct_job_count,window_start_utc,generated_at_utc\n"
            "AI,Python,not-a-count,2026-10-22T00:00:00Z,2026-10-24T00:00:00Z\n",
            encoding="utf-8",
        )
        aggregate.with_suffix(".metadata.json").write_text(json.dumps({"generated_at_utc":"2026-10-24T00:00:00Z", "window_start_utc":"2026-10-22T00:00:00Z", "api_records":1, "processed_jobs":1, "category_skill_pairs":1}), encoding="utf-8")
        rows, metadata = load_headcount_demand(aggregate, importer.normalize)
        self.assertIsNone(rows)
        self.assertIsNone(metadata)


if __name__ == "__main__":
    unittest.main()
