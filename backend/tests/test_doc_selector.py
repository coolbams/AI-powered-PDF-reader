import unittest
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse

from core.doc_selector import set_document, UPLOAD_DIR
from core.get_uploaded_files import get_file_list


class TestDocSelector(unittest.TestCase):
    def setUp(self):
        """Create a temporary test PDF file in UPLOAD_DIR."""
        self.test_pdf_name = "__ci_test_dummy_doc__"
        self.test_pdf_path = UPLOAD_DIR / f"{self.test_pdf_name}.pdf"
        self.test_pdf_path.write_bytes(b"%PDF-1.4 dummy content")

    def tearDown(self):
        """Clean up the temporary test PDF."""
        if self.test_pdf_path.exists():
            self.test_pdf_path.unlink()

    def test_valid_file_without_extension(self):
        """Requesting filename without .pdf returns FileResponse."""
        response = set_document(self.test_pdf_name)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(Path(response.path), self.test_pdf_path)

    def test_valid_file_with_extension(self):
        """Requesting filename with .pdf returns FileResponse."""
        response = set_document(f"{self.test_pdf_name}.pdf")
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(Path(response.path), self.test_pdf_path)

    def test_file_not_found(self):
        """Requesting a nonexistent file raises 404."""
        with self.assertRaises(HTTPException) as ctx:
            set_document("nonexistent_file_xyz_123")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_path_traversal_dot_dot_blocked(self):
        """Directory traversal using .. is rejected with 400."""
        with self.assertRaises(HTTPException) as ctx:
            set_document("../../app.py")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_path_traversal_absolute_slash_blocked(self):
        """Directory traversal using root slash is rejected with 400."""
        with self.assertRaises(HTTPException) as ctx:
            set_document("/etc/passwd")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_get_file_list_includes_test_doc(self):
        """get_file_list returns document stems including the test file."""
        files = get_file_list()
        self.assertIn(self.test_pdf_name, files)


if __name__ == "__main__":
    unittest.main()
