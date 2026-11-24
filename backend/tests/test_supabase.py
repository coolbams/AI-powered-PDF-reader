import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import json

from core import supabase_service


class TestSupabaseService(unittest.TestCase):

    def setUp(self):
        # Reset cached client between tests
        supabase_service._supabase_client = None

    def test_require_supabase_raises_when_disabled(self):
        from core.exceptions import ConfigurationError
        with patch.object(supabase_service, "SUPABASE_URL", None):
            with self.assertRaises(ConfigurationError):
                supabase_service.require_supabase()

    def test_is_supabase_enabled_false_when_placeholder(self):
        with patch.object(supabase_service, "SUPABASE_URL", "https://your-project-ref.supabase.co"), \
             patch.object(supabase_service, "SUPABASE_KEY", "your-supabase-key"):
            self.assertFalse(supabase_service.is_supabase_enabled())

    def test_is_supabase_enabled_true_when_valid(self):
        with patch.object(supabase_service, "SUPABASE_URL", "https://abcxyz.supabase.co"), \
             patch.object(supabase_service, "SUPABASE_KEY", "sb_valid_service_role_key"):
            self.assertTrue(supabase_service.is_supabase_enabled())

    @patch("core.supabase_service.is_supabase_enabled", return_value=True)
    def test_upload_and_download_bytes_mocked(self, mock_enabled):
        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_bucket = MagicMock()

        mock_client.storage = mock_storage
        mock_storage.from_.return_value = mock_bucket
        mock_bucket.download.return_value = b"sample pdf content"

        with patch("core.supabase_service.get_supabase_client", return_value=mock_client):
            # Test upload
            uploaded_path = supabase_service.upload_bytes("pdfs/test.pdf", b"sample pdf content", "application/pdf")
            self.assertEqual(uploaded_path, "pdfs/test.pdf")
            mock_bucket.upload.assert_called_once()

            # Test download
            content = supabase_service.download_bytes("pdfs/test.pdf")
            self.assertEqual(content, b"sample pdf content")
            mock_bucket.download.assert_called_once_with("pdfs/test.pdf")

    @patch("core.supabase_service.is_supabase_enabled", return_value=True)
    def test_record_and_get_document(self, mock_enabled):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_res = MagicMock()
        mock_res.data = [{
            "filename": "test.pdf",
            "file_path": "pdfs/test.pdf",
            "page_count": 5
        }]
        mock_table.upsert.return_value.execute.return_value = mock_res
        mock_table.select.return_value.or_.return_value.limit.return_value.execute.return_value = mock_res

        with patch("core.supabase_service.get_supabase_client", return_value=mock_client):
            rec = supabase_service.record_document(
                filename="test.pdf",
                file_path="pdfs/test.pdf",
                page_count=5
            )
            self.assertEqual(rec["filename"], "test.pdf")
            self.assertEqual(rec["page_count"], 5)

            fetched = supabase_service.get_document_record("test.pdf")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["filename"], "test.pdf")

    @patch("core.supabase_service.is_supabase_enabled", return_value=True)
    def test_list_document_filenames(self, mock_enabled):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_res = MagicMock()
        mock_res.data = [
            {"filename": "document_a.pdf"},
            {"filename": "document_b.pdf"},
        ]
        mock_table.select.return_value.order.return_value.execute.return_value = mock_res

        with patch("core.supabase_service.get_supabase_client", return_value=mock_client):
            names = supabase_service.list_document_filenames()
            self.assertEqual(names, ["document_a", "document_b"])


if __name__ == "__main__":
    unittest.main()
