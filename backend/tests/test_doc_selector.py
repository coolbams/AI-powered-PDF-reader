import unittest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.responses import Response

from core.doc_selector import set_document
from core.get_uploaded_files import get_file_list


class TestDocSelector(unittest.TestCase):
    def setUp(self):
        self.test_pdf_name = "__ci_test_dummy_doc__"
        self.mock_content = b"%PDF-1.4 dummy content"

    @patch("core.doc_selector.download_bytes")
    def test_valid_file_without_extension(self, mock_download):
        """Requesting filename without .pdf returns Response with PDF bytes."""
        mock_download.return_value = self.mock_content
        response = set_document(self.test_pdf_name)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.body, self.mock_content)
        mock_download.assert_called_once_with(f"pdfs/{self.test_pdf_name}.pdf")

    @patch("core.doc_selector.download_bytes")
    def test_valid_file_with_extension(self, mock_download):
        """Requesting filename with .pdf returns Response with PDF bytes."""
        mock_download.return_value = self.mock_content
        response = set_document(f"{self.test_pdf_name}.pdf")
        self.assertIsInstance(response, Response)
        self.assertEqual(response.body, self.mock_content)
        mock_download.assert_called_once_with(f"pdfs/{self.test_pdf_name}.pdf")

    @patch("core.doc_selector.download_bytes", return_value=None)
    def test_file_not_found(self, mock_download):
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

    @patch("core.get_uploaded_files.list_document_filenames")
    def test_get_file_list_includes_test_doc(self, mock_list):
        """get_file_list returns document names from Supabase."""
        mock_list.return_value = [self.test_pdf_name]
        files = get_file_list()
        self.assertIn(self.test_pdf_name, files)


if __name__ == "__main__":
    unittest.main()
