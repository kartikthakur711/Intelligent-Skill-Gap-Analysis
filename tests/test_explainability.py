import unittest

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from explainability import FEATURE_NAMES, explain_prediction
from skill_prioritization import priority_from_demand


class ExplainabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = GradientBoostingRegressor(
            n_estimators=8, max_depth=2, random_state=7
        ).fit(
            np.array([
                [0, 0, 0, 0, 0], [2, 3, .2, .1, .3],
                [4, 5, .6, .5, .7], [8, 9, .9, .8, .9],
                [1, 6, .1, .7, .2], [6, 2, .8, .3, .8],
            ]),
            np.array([10, 25, 55, 90, 35, 72]),
        )

    def test_additive_and_repeatable(self):
        features = np.array([3, 6, .5, .4, .7])
        pred, values = explain_prediction(self.model, features)
        pred2, values2 = explain_prediction(self.model, features)
        self.assertEqual(len(FEATURE_NAMES), 5)
        self.assertAlmostEqual(float(self.model.predict([features])[0]), pred)
        self.assertAlmostEqual(pred, float(self.model.predict([[0, 0, 0, 0, 0]])[0]) + values.sum(), places=8)
        np.testing.assert_allclose(values, values2)

    def test_missing_or_wrong_shape_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            explain_prediction(self.model, [1, 2, np.nan, 4, 5])
        with self.assertRaisesRegex(ValueError, "Expected"):
            explain_prediction(self.model, [1, 2, 3])

    def test_skill_priority_has_verified_count_rationale(self):
        catalog = pd.DataFrame({"skills_list": [["Python", "SQL"], ["python"], ["SQL"]]})
        result = priority_from_demand(["Python", "SQL", "Rust"], catalog).set_index("Skill")
        self.assertEqual(result.loc["Python", "Catalog Rows"], 2)
        self.assertEqual(result.loc["SQL", "Priority"], "High")
        self.assertIn("2 loaded catalog rows", result.loc["Python", "Reason"])
        self.assertEqual(result.loc["Rust", "Priority"], "Low")

    def test_priority_uses_app_skill_aliases(self):
        catalog = pd.DataFrame({"skills_list": [["tensorflow keras"], ["mysql database"]]})
        result = priority_from_demand(["tensorflow", "mysql"], catalog).set_index("Skill")
        self.assertEqual(result.loc["tensorflow", "Catalog Rows"], 1)
        self.assertEqual(result.loc["mysql", "Catalog Rows"], 1)

    def test_missing_demand_data_is_marked_unknown(self):
        result = priority_from_demand(["Python"], pd.DataFrame())
        self.assertEqual(result.loc[0, "Priority"], "Unknown")
        self.assertEqual(result.loc[0, "Catalog Rows"], 0)
        self.assertIn("unavailable", result.loc[0, "Reason"])


if __name__ == "__main__":
    unittest.main()
