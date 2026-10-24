import unittest
from pathlib import Path

import joblib
import numpy as np

from explainability import FEATURE_NAMES, explain_prediction
from model_evaluation import evaluate_saved_model


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "resume_job_ml_model.pkl"


class SavedModelValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = joblib.load(MODEL_PATH)

    def test_saved_artifact_has_expected_runtime_contract(self):
        self.assertIsInstance(self.artifacts, dict)
        self.assertTrue({"model", "vectorizer"} <= self.artifacts.keys())
        self.assertEqual(self.artifacts["model"].n_features_in_, len(FEATURE_NAMES))
        transformed = self.artifacts["vectorizer"].transform(
            ["Python, pandas, and SQL"]
        )
        self.assertEqual(transformed.shape[0], 1)

    def test_representative_inputs_produce_finite_scores_and_attributions(self):
        samples = (
            [0, 4, 0.0, 0.0, 0.0],
            [3, 6, 0.5, 0.4, 0.7],
            [8, 8, 1.0, 1.0, 1.0],
        )
        model = self.artifacts["model"]
        for features in samples:
            with self.subTest(features=features):
                raw_score, contributions = explain_prediction(model, features)
                self.assertTrue(np.isfinite(raw_score))
                self.assertTrue(np.isfinite(contributions).all())
                baseline = float(model.predict(np.zeros((1, len(FEATURE_NAMES))))[0])
                self.assertAlmostEqual(
                    raw_score, baseline + float(contributions.sum()), places=6
                )

    def test_model_outputs_are_compatible_with_app_score_clipping(self):
        model = self.artifacts["model"]
        inputs = np.array(
            [
                [0, 0, 0.0, 0.0, 0.0],
                [2, 5, 0.4, 0.3, 0.6],
                [10, 10, 1.0, 1.0, 1.0],
            ]
        )
        raw = np.asarray(model.predict(inputs), dtype=float)
        displayed = np.clip(raw, 0, 100)
        self.assertEqual(raw.shape, (len(inputs),))
        self.assertTrue(np.isfinite(raw).all())
        self.assertTrue(((displayed >= 0) & (displayed <= 100)).all())

    def test_holdout_evaluation_uses_clipped_predictions_without_fitting(self):
        class FixedModel:
            def predict(self, features):
                return np.array([-5.0, 50.0, 110.0])

            def fit(self, *_args, **_kwargs):
                raise AssertionError("evaluation must not retrain")

        metrics = evaluate_saved_model(
            FixedModel(), np.zeros((3, len(FEATURE_NAMES))), [0.0, 40.0, 100.0]
        )
        self.assertEqual(metrics["n"], 3)
        self.assertAlmostEqual(metrics["mae"], 10.0 / 3.0)
        self.assertAlmostEqual(metrics["rmse"], np.sqrt(100.0 / 3.0))
        self.assertGreaterEqual(metrics["r2"], 0.0)

    def test_holdout_evaluation_rejects_invalid_data(self):
        model = self.artifacts["model"]
        with self.assertRaisesRegex(ValueError, "5 columns"):
            evaluate_saved_model(model, [[1, 2]], [50])
        with self.assertRaisesRegex(ValueError, "0–100"):
            evaluate_saved_model(model, np.zeros((2, 5)), [20, 101])
        with self.assertRaisesRegex(ValueError, "distinct values"):
            evaluate_saved_model(model, np.zeros((2, 5)), [20, 20])


if __name__ == "__main__":
    unittest.main()
