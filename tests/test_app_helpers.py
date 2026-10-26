import unittest
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

from app_helpers import (
    build_dashboard_skill_demand,
    build_learning_plan,
    build_learning_roadmap,
    build_skill_recommendations,
    summarize_recent_snapshot,
)


def normalize_skill(value):
    return " ".join(str(value).lower().replace("-", " ").split())


class LearningRoadmapTests(unittest.TestCase):
    def test_excludes_known_skills_and_keeps_missing_skill(self):
        dependencies = {
            "power bi": ["data analysis"],
            "data analysis": ["python", "pandas"],
            "pandas": ["python"],
        }
        roadmap = build_learning_roadmap(
            ["power bi"], dependencies, ["Python", "Pandas"], normalize_skill
        )
        self.assertEqual(roadmap, ["data analysis", "power bi"])
        self.assertNotIn("python", roadmap)
        self.assertNotIn("pandas", roadmap)


class DashboardDataTests(unittest.TestCase):
    def test_snapshot_zeros_are_explained_by_successful_but_limited_coverage(self):
        status = summarize_recent_snapshot(
            [{"category": "Data", "skill_normalized": "excel", "distinct_job_count": "3"}],
            {"generated_at_utc": "2026-10-26T10:00:00Z", "api_records": "10", "processed_jobs": "9"},
            now=datetime(2026, 10, 26, 11, tzinfo=timezone.utc),
        )
        self.assertEqual(status["state"], "available")
        self.assertIn("10 API records", status["message"])
        self.assertIn("zero for a skill", status["message"])

    def test_snapshot_distinguishes_valid_empty_results_from_missing_data(self):
        now = datetime(2026, 10, 26, tzinfo=timezone.utc)
        empty = summarize_recent_snapshot(
            [], {"generated_at_utc": "2026-10-25T23:00:00Z", "api_records": "0", "processed_jobs": "0"}, now=now
        )
        unavailable = summarize_recent_snapshot(None, None, now=now)
        self.assertEqual(empty["state"], "no_listings")
        self.assertIn("valid empty result", empty["message"])
        self.assertEqual(unavailable["state"], "unavailable")

    def test_snapshot_staleness_and_invalid_metadata_are_not_reported_as_zero(self):
        stale = summarize_recent_snapshot(
            [], {"generated_at_utc": "2026-10-20T00:00:00Z", "api_records": "0", "processed_jobs": "0"},
            now=datetime(2026, 10, 26, tzinfo=timezone.utc),
        )
        malformed = summarize_recent_snapshot([], {"generated_at_utc": "not-a-date"})
        self.assertEqual(stale["state"], "stale")
        self.assertEqual(malformed["state"], "unavailable")

    def test_catalog_mentions_are_normalized_ranked_and_joined_to_recent_counts(self):
        rows = build_dashboard_skill_demand(
            [["Python", "SQL"], ["python", "Pandas"], ["SQL"]],
            {"python": 4, "sql": 1},
            normalize_skill,
        )
        self.assertEqual(
            rows,
            [
                {"Skill": "Python", "Catalog mentions": 2, "Recent India listings": 4},
                {"Skill": "SQL", "Catalog mentions": 2, "Recent India listings": 1},
                {"Skill": "Pandas", "Catalog mentions": 1, "Recent India listings": 0},
            ],
        )

    def test_dashboard_demand_does_not_invent_rows_for_an_empty_catalog(self):
        self.assertEqual(build_dashboard_skill_demand([], {"python": 9}, normalize_skill), [])

    def test_dashboard_omits_recent_counts_when_snapshot_is_unavailable(self):
        rows = build_dashboard_skill_demand([["Python"]], None, normalize_skill)
        self.assertEqual(rows, [{"Skill": "Python", "Catalog mentions": 1}])

    def test_deduplicates_prerequisites(self):
        dependencies = {"skill a": ["python"], "skill b": ["python"]}
        roadmap = build_learning_roadmap(
            ["skill a", "skill b"], dependencies, [], normalize_skill
        )
        self.assertEqual(roadmap.count("python"), 1)

    def test_circular_prerequisites_do_not_recurse_forever(self):
        dependencies = {"skill a": ["skill b"], "skill b": ["skill a"]}
        roadmap = build_learning_roadmap(["skill a"], dependencies, [], normalize_skill)
        self.assertEqual(roadmap, ["skill b", "skill a"])

    def test_empty_gap_returns_empty_roadmap(self):
        self.assertEqual(
            build_learning_roadmap([], {}, ["python"], normalize_skill), []
        )


class RecommendationTests(unittest.TestCase):
    def test_resource_catalog_has_skill_names_and_absolute_web_links(self):
        path = Path(__file__).resolve().parents[1] / "learning_resources.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            resources = list(csv.DictReader(handle))
        self.assertTrue(resources)
        self.assertTrue(all(row["skill"].strip() for row in resources))
        self.assertTrue(all(urlparse(row["url"]).scheme in {"http", "https"} for row in resources))

    def test_ranks_using_catalog_and_recent_demand_and_attaches_catalog_resources(self):
        rows = [
            {"Skill": "Python", "Job Demand": 100, "Demand Score": 0.5, "Recent India Listings (48h)": 0},
            {"Skill": "SQL", "Job Demand": 50, "Demand Score": 0.25, "Recent India Listings (48h)": 5},
            {"Skill": "Rare", "Job Demand": 0, "Demand Score": 0, "Recent India Listings (48h)": 0},
        ]
        resources = [
            {"skill": "python", "resource": "Python Docs", "type": "Documentation", "url": "https://docs.python.org/3/"},
        ]
        result = build_skill_recommendations(rows, resources, normalize_skill)
        self.assertEqual([item["Skill"] for item in result], ["Python", "SQL", "Rare"])
        self.assertEqual(result[0]["Resources"][0]["resource"], "Python Docs")
        self.assertEqual(result[1]["Resources"], [])
        self.assertIn("50 job-catalog", result[1]["Explanation"])
        self.assertIn("5 recent India", result[1]["Explanation"])

    def test_recent_demand_can_break_equal_catalog_scores(self):
        result = build_skill_recommendations(
            [
                {"Skill": "A", "Job Demand": 10, "Demand Score": 0.1, "Recent India Listings (48h)": 1},
                {"Skill": "B", "Job Demand": 10, "Demand Score": 0.1, "Recent India Listings (48h)": 4},
            ], [], normalize_skill
        )
        self.assertEqual([row["Skill"] for row in result], ["B", "A"])

    def test_learning_plan_preserves_prerequisite_order_and_assigns_phases(self):
        plan = build_learning_plan(["Python", "Pandas", "Data Science"], normalize_skill)
        self.assertEqual([item["Day"] for item in plan], [30, 60, 90])
        self.assertEqual([item["Phase"] for item in plan], ["First 30 days", "Days 31–60", "Days 61–90"])
        self.assertEqual(
            [skill for phase in plan for skill in phase["Skills"]],
            ["Python", "Pandas", "Data Science"],
        )
        self.assertEqual(build_learning_plan([], normalize_skill)[0]["Skills"], [])

    def test_recommendations_ignore_unknown_or_empty_skill_labels(self):
        result = build_skill_recommendations(
            [{"Skill": "", "Job Demand": 0}, {"Skill": "Unknown", "Job Demand": 0}],
            [], normalize_skill
        )
        self.assertEqual([row["Skill"] for row in result], ["Unknown"])
        self.assertIn("No demand", result[0]["Explanation"])


if __name__ == "__main__":
    unittest.main()

