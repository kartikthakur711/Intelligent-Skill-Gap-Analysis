import unittest
import csv
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest


class AppRuntimeTests(unittest.TestCase):
    def test_dashboard_imports_and_renders_without_exceptions(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run(timeout=60)

        self.assertFalse(
            app.exception,
            [exception.message for exception in app.exception],
        )
        self.assertEqual(app.radio[0].value, "Dashboard")
        self.assertTrue(
            any(
                "Turn your skills into your next opportunity." in item.value
                for item in app.markdown
            )
        )
        self.assertTrue(any("Skills appearing in the job catalog" in item.value for item in app.subheader))
        self.assertTrue(any("Recently observed provider titles" in item.value for item in app.markdown))
        self.assertTrue(any("does not contain a validated title aggregate yet" in item.value for item in app.info))
        self.assertTrue(any("Saved learning progress" in item.value for item in app.subheader))
        self.assertTrue(any("Saved learning plans" in metric.label for metric in app.metric))
        self.assertTrue(any("Distinct catalog titles" == metric.label and metric.value == "12" for metric in app.metric))
        self.assertTrue(any(item.label == "Search job titles" for item in app.text_input))
        self.assertTrue(any(item.label == "Catalog category" for item in app.selectbox))
        self.assertTrue(app.dataframe)
        self.assertTrue(any("Start with your resume" in button.label for button in app.button))

        app.button[0].click().run(timeout=60)
        self.assertFalse(
            app.exception,
            [exception.message for exception in app.exception],
        )
        self.assertEqual(app.radio[0].value, "Analyze resume")
        self.assertEqual(len(app.file_uploader), 1)
        self.assertTrue(any(item.label == "Browse available catalog titles" for item in app.selectbox))
        self.assertTrue(any(item.label == "Target Job Title" for item in app.text_input))
        role_picker = next(item for item in app.selectbox if item.label == "Browse available catalog titles")
        app = role_picker.select("Data Scientist").run()
        self.assertEqual(next(item for item in app.text_input if item.label == "Target Job Title").value, "Data Scientist")
        self.assertTrue(any("Start your analysis" in item.value for item in app.markdown))
        self.assertTrue(any("Add your resume" in item.value for item in app.markdown))
        self.assertTrue(any("Choose your target role" in item.value for item in app.markdown))
        self.assertTrue(any("Analyze my resume" in button.label for button in app.button))

    def test_dashboard_data_present_empty_missing_and_malformed_sources(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        previous = {key: os.environ.get(key) for key in (
            "SKILLSCOPE_JOB_CATALOG", "SKILLSCOPE_DEMAND_CSV",
            "SKILLSCOPE_DEMAND_METADATA", "LEARNING_PROGRESS_FILE",
        )}
        try:
            with tempfile.TemporaryDirectory(dir=app_path.parent) as directory:
                root = Path(directory)
                catalog = root / "catalog.csv"
                with catalog.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=["job_id", "job_title", "job_description", "job_skill_set"])
                    writer.writeheader()
                    writer.writerow({"job_id": "1", "job_title": "Data Engineer", "job_description": "Python roles", "job_skill_set": "['Python', 'SQL']"})
                demand = root / "demand.csv"
                metadata = root / "demand.metadata.json"
                progress = root / "progress.json"
                os.environ["SKILLSCOPE_JOB_CATALOG"] = str(catalog)
                os.environ["SKILLSCOPE_DEMAND_CSV"] = str(demand)
                os.environ["SKILLSCOPE_DEMAND_METADATA"] = str(metadata)
                os.environ["LEARNING_PROGRESS_FILE"] = str(progress)

                def render():
                    st.cache_data.clear()
                    result = AppTest.from_file(str(app_path)).run(timeout=60)
                    self.assertFalse(result.exception, [item.message for item in result.exception])
                    return "\n".join(item.value for item in (*result.info, *result.caption))

                header = "category,skill,distinct_job_count,window_start_utc,generated_at_utc\n"
                generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                demand.write_text(header + f"Data,python,2,2026-10-25T00:00:00Z,{generated}\n", encoding="utf-8")
                metadata.write_text(json.dumps({"generated_at_utc":generated, "window_start_utc":"2026-10-25T00:00:00Z", "api_records":2, "processed_jobs":2, "category_skill_pairs":1}), encoding="utf-8")
                self.assertIn("matched 1 category/skill pairs", render())

                demand.write_text(header, encoding="utf-8")
                metadata.write_text(json.dumps({"generated_at_utc":generated, "window_start_utc":"2026-10-25T00:00:00Z", "api_records":0, "processed_jobs":0, "category_skill_pairs":0}), encoding="utf-8")
                self.assertIn("found no India listings", render())

                demand.write_text("wrong,headers\nvalue,value\n", encoding="utf-8")
                self.assertIn("missing or invalid snapshot files", render())

                demand.unlink()
                metadata.unlink()
                self.assertIn("missing or invalid snapshot files", render())

                progress.write_text("{invalid", encoding="utf-8")
                result = AppTest.from_file(str(app_path)).run(timeout=60)
                self.assertFalse(result.exception, [item.message for item in result.exception])
                self.assertTrue(any("Saved progress could not be read" in item.value for item in result.warning))
        finally:
            st.cache_data.clear()
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
