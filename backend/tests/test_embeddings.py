import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.embeddings import embed, generate_ids


class TestEmbeddings(unittest.TestCase):
    def test_generate_ids(self):
        chunks = [
            {"metadata": {"page_number": 1}},
            {"metadata": {"page_number": 2}},
        ]
        ids = generate_ids(chunks, "docA")
        self.assertEqual(ids, ["docA_page1_chunk0", "docA_page2_chunk1"])

    @patch("core.embeddings.EmbeddingModel")
    @patch("core.embeddings.chromadb.PersistentClient")
    def test_embed_with_in_memory_list(self, mock_client_cls, mock_embed_cls):
        mock_embeder = MagicMock()
        mock_embeder.embed_documents.return_value = [[0.1, 0.2]]
        mock_embed_cls.return_value = mock_embeder

        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        sample_chunks = [
            {"text": "Hello world", "metadata": {"page_number": 1}}
        ]

        embed(sample_chunks, "test_doc")

        mock_embeder.embed_documents.assert_called_once_with(["Hello world"])
        mock_collection.upsert.assert_called_once()
        call_kwargs = mock_collection.upsert.call_args[1]
        self.assertEqual(call_kwargs["ids"], ["test_doc_page1_chunk0"])
        self.assertEqual(call_kwargs["documents"], ["Hello world"])
        self.assertEqual(call_kwargs["metadatas"], [{"page_number": 1}])

    @patch("core.embeddings.EmbeddingModel")
    @patch("core.embeddings.chromadb.PersistentClient")
    def test_embed_with_file_path(self, mock_client_cls, mock_embed_cls):
        mock_embeder = MagicMock()
        mock_embeder.embed_documents.return_value = [[0.3, 0.4]]
        mock_embed_cls.return_value = mock_embeder

        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_cls.return_value = mock_client

        sample_chunks = [
            {"text": "From file", "metadata": {"page_number": 3}}
        ]

        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tmp:
            json.dump(sample_chunks, tmp)
            tmp_path = tmp.name

        try:
            embed(tmp_path, "file_doc")
            mock_embeder.embed_documents.assert_called_once_with(["From file"])
            mock_collection.upsert.assert_called_once()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch("core.embeddings.EmbeddingModel")
    @patch("core.embeddings.chromadb.PersistentClient")
    def test_embed_empty_chunks(self, mock_client_cls, mock_embed_cls):
        mock_embeder = MagicMock()
        mock_embed_cls.return_value = mock_embeder
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Should return early without calling embed_documents or upsert
        embed([], "empty_doc")
        mock_embeder.embed_documents.assert_not_called()


if __name__ == "__main__":
    unittest.main()
