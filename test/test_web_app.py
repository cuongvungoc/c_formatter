"""Tests for the Flask formatter web app."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import app  # noqa: E402


class WebAppTests(unittest.TestCase):
    """Validate the Flask routes used by the formatter UI."""

    def setUp(self) -> None:
        """Create a test client for each test."""

        self.client = app.test_client()

    def test_home_page_loads(self) -> None:
        """Render the main formatter page."""

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"C Formatter", response.data)
        self.assertIn(b'name="source"', response.data)
        self.assertIn(b'name="keep_line_breaks"', response.data)

    def test_formats_posted_source(self) -> None:
        """Format pasted C source from a POST request."""

        response = self.client.post("/", data={"source": "int main(){return 0;}"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"int main() {", response.data)
        self.assertIn(b"return 0;", response.data)

    def test_keep_line_breaks_checkbox_enables_preserve_mode(self) -> None:
        """Preserve input blank lines when the checkbox is submitted."""

        response = self.client.post(
            "/",
            data={
                "source": "int a(){return 1;}\n\n\nint b(){return 2;}",
                "keep_line_breaks": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"int a() {", response.data)
        self.assertIn(b"}\n\n\nint b() {", response.data)
        self.assertIn(b"checked", response.data)

    def test_health_route(self) -> None:
        """Return a deployment health response."""

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
