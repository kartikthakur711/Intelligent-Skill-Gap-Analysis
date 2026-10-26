import unittest

import pandas as pd

from role_discovery import catalog_roles, normalize_title


class RoleDiscoveryTests(unittest.TestCase):
    def test_normalizes_common_variants_without_merging_distinct_titles(self):
        self.assertEqual(normalize_title(" ML Engineer "), "machine learning engineer")
        self.assertEqual(normalize_title("Backend Developer"), "backend developer")
        self.assertNotEqual(normalize_title("Data Engineer"), normalize_title("Data Scientist"))

    def test_deduplicates_titles_and_keeps_category_and_row_provenance(self):
        frame = pd.DataFrame([
            {"job_title": "ML Engineer", "category": "AI / ML Engineering"},
            {"job_title": "Machine Learning Engineer", "category": "AI / ML Engineering"},
            {"job_title": "Application Developer", "category": "Web Development"},
            {"job_title": "Software Engineer", "category": "Web Development"},
            {"job_title": "Backend Developer", "category": "Web Development"},
        ])
        roles = catalog_roles(frame)
        self.assertEqual(len(roles), 3)
        ml_role = next(role for role in roles if role["Job title"] == "ML Engineer")
        self.assertEqual(ml_role["Catalog rows"], 2)
        self.assertEqual(ml_role["Categories"], "AI / ML Engineering")

    def test_empty_or_skill_only_catalog_does_not_invent_titles(self):
        self.assertEqual(catalog_roles(pd.DataFrame(columns=["job_title", "category"])), [])
        self.assertEqual(catalog_roles(pd.DataFrame([
            {"job_title": "", "category": "Python"},
            {"job_title": float("nan"), "category": "Data"},
        ])), [])


if __name__ == "__main__":
    unittest.main()
