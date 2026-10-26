import unittest
from pathlib import Path

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
        self.assertTrue(any("Saved learning progress" in item.value for item in app.subheader))
        self.assertTrue(any("Saved learning plans" in metric.label for metric in app.metric))
        self.assertTrue(app.dataframe)
        self.assertTrue(any("Start with your resume" in button.label for button in app.button))

        app.button[0].click().run(timeout=60)
        self.assertFalse(
            app.exception,
            [exception.message for exception in app.exception],
        )
        self.assertEqual(app.radio[0].value, "Analyze resume")
        self.assertEqual(len(app.file_uploader), 1)
        self.assertTrue(any(button.label == "Analyze Resume" for button in app.button))


if __name__ == "__main__":
    unittest.main()
