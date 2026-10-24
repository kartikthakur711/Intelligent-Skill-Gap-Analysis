import unittest

from app_helpers import clean_html


class AppHelperTests(unittest.TestCase):
    def test_clean_html_strips_tags_decodes_entities_and_collapses_whitespace(self):
        self.assertEqual(clean_html("<b>Python</b>&nbsp;\n\t&amp;  SQL"), "Python & SQL")

    def test_clean_html_handles_none(self):
        self.assertEqual(clean_html(None), "")


if __name__ == "__main__":
    unittest.main()
