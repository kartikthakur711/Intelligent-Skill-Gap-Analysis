import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi import HTTPException

import api


class Encoder:
    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        return np.array([[1.0, 0.0] for _ in texts])


class Vectorizer:
    def transform(self, texts):
        return np.array([[1.0, 0.0]])


class Model:
    def predict(self, features):
        assert features.shape == (1, 5)
        return np.array([72.5])


class ApiContractTests(unittest.TestCase):
    def test_health_contract(self):
        response = api.health()
        self.assertEqual(response["status"], "ok")
        self.assertEqual(set(response), {"status", "model_available", "catalog_available"})

    def test_http_routes_and_multipart_upload_are_published(self):
        schema = api.app.openapi()
        self.assertEqual({"/api/health", "/api/dashboard", "/api/analyze", "/api/progress"} & set(schema["paths"]), {"/api/health", "/api/dashboard", "/api/analyze", "/api/progress"})
        analyze_op = schema["paths"]["/api/analyze"]["post"]
        self.assertEqual(analyze_op["requestBody"]["content"].keys(), {"multipart/form-data"})

    def test_dashboard_contract_uses_catalog_categories_and_saved_summary(self):
        frame = pd.DataFrame([
            {"job_title": "Data Scientist", "category": "Data", "job_description": "Data role", "job_skill_set": "['Python', 'SQL']", "skills_list": ["Python", "SQL"]},
            {"job_title": "Office Manager", "category": "Operations", "job_description": "Office role", "job_skill_set": "['Excel']", "skills_list": ["Excel"]},
        ])
        summary = {"saved_plan_count": 1, "completed_step_count": 1, "tracked_plan_count": 1, "tracked_step_count": 2, "completed_tracked_step_count": 1, "completion_ratio": .5, "untracked_plan_count": 0}
        with patch.object(api, "catalog", return_value=frame), patch.object(api, "read_headcount_demand", return_value=(None, None)), patch.object(api, "read_headcount_titles", return_value=(None, None)), patch.object(api, "summarize_progress", return_value=summary):
            body = api.dashboard()
        self.assertIn("Data", body["categories"])
        self.assertIn("Operations", body["categories"])
        self.assertEqual(body["progress"]["completion_ratio"], .5)
        self.assertEqual(body["roles"][0]["Job title"], "Data Scientist")

    def test_analysis_contract_preserves_model_feature_order_and_gap_semantics(self):
        frame = pd.DataFrame([
            {"job_title": "Data Scientist", "category": "Data", "job_description": "Python SQL analytics", "job_skill_set": "['Python', 'SQL']", "skills_list": ["Python", "SQL"]},
        ])
        artifacts = {"model": Model(), "vectorizer": Vectorizer()}
        text = b"Python developer with data analysis and project experience across multiple teams and production reports."
        with patch.object(api, "catalog", return_value=frame), patch.object(api, "get_encoder", return_value=Encoder()), patch.object(api, "get_model", return_value=artifacts), patch.object(api, "read_headcount_demand", return_value=(None, None)), patch.object(api, "resources", return_value=[]), patch.object(api, "load_progress", return_value=[]) as load_saved:
            body = api.analyze_text(text.decode(), "Data Scientist", "custom nickname")
        self.assertEqual(body["compatibility"], 72.5)
        self.assertEqual(body["matched_skills"], ["Python"])
        self.assertEqual(body["missing_skills"], ["SQL"])
        self.assertEqual(body["signals"]["skill_coverage"], .5)
        self.assertEqual(body["title_match"]["method"], "exact")
        self.assertIn("not a hiring probability", body["caveat"])
        self.assertEqual(load_saved.call_args.args[1], "custom nickname")

    def test_unknown_role_returns_contract_error(self):
        frame = pd.DataFrame([{"job_title": "Data Scientist", "category": "Data", "job_description": "Data role", "job_skill_set": "['Python']", "skills_list": ["Python"]}])
        with patch.object(api, "catalog", return_value=frame), patch.object(api, "get_encoder", return_value=Encoder()):
            with self.assertRaises(HTTPException) as raised:
                api.analyze_text("x" * 80, "Astronaut")
        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn("No sufficiently relevant", raised.exception.detail)

    def test_progress_contract_persists_only_selected_roadmap_steps(self):
        summary = {"saved_plan_count": 1, "completed_step_count": 1}
        with patch.object(api, "save_progress") as save, patch.object(api, "load_progress", return_value=["Python"]), patch.object(api, "summarize_progress", return_value=summary):
            body = api.update_progress(api.ProgressUpdate(profile="learner", job_title="Data Scientist", roadmap=["Python", "SQL"], completed_skills=["Python"]))
        self.assertEqual(body["completed_skills"], ["Python"])
        self.assertEqual(body["progress"], summary)
        self.assertEqual(save.call_args.args[1:5], ("learner", "Data Scientist", ["Python", "SQL"], ["Python"]))


if __name__ == "__main__":
    unittest.main()

