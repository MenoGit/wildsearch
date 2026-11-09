
import unittest
from crawler import is_html_candidate


class TestHTMLFiltering(unittest.TestCase):

    def test_skip_pdf(self):
        self.assertFalse(
            is_html_candidate("https://wdfw.wa.gov/report.pdf")
        )

    def test_skip_image(self):
        self.assertFalse(
            is_html_candidate("https://wdfw.wa.gov/photo.jpg")
        )

    def test_accept_html(self):
        self.assertTrue(
            is_html_candidate("https://wdfw.wa.gov/hunting")
        )

    def test_accept_query_parameters(self):
        self.assertTrue(
            is_html_candidate("https://wdfw.wa.gov/hunting?page=2")
        )

    def test_skip_uppercase_pdf(self):
        self.assertFalse(
            is_html_candidate("https://wdfw.wa.gov/REPORT.PDF")
        )


if __name__ == "__main__":
    unittest.main()

