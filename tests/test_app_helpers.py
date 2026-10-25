import unittest

from app_helpers import build_learning_roadmap


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

    def test_deduplicates_prerequisites(self):
        dependencies = {
            "skill a": ["python"],
            "skill b": ["python"],
        }
        roadmap = build_learning_roadmap(
            ["skill a", "skill b"], dependencies, [], normalize_skill
        )
        self.assertEqual(roadmap.count("python"), 1)

    def test_empty_gap_returns_empty_roadmap(self):
        self.assertEqual(
            build_learning_roadmap([], {}, ["python"], normalize_skill), []
        )


if __name__ == "__main__":
    unittest.main()
