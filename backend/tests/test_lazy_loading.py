import unittest
import sys
from unittest.mock import patch, MagicMock


class TestLazyLoading(unittest.TestCase):
    def test_reranker_module_lazy_by_default(self):
        """core.reranker should have _model as None until get_reranker_model is invoked."""
        import core.reranker as reranker
        # When chunks is empty, rerank() should return [] without loading the model
        result = reranker.rerank("query", [])
        self.assertEqual(result, [])

    def test_reranker_loads_when_needed(self):
        """Calling get_reranker_model should load and cache the model."""
        import core.reranker as reranker
        with patch("core.reranker.CrossEncoder") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            reranker._model = None  # Reset

            model = reranker.get_reranker_model()
            self.assertEqual(model, mock_instance)
            mock_cls.assert_called_once()

            # Second call should use cache, not call CrossEncoder again
            model2 = reranker.get_reranker_model()
            self.assertEqual(model2, mock_instance)
            self.assertEqual(mock_cls.call_count, 1)

            # Cleanup
            reranker._model = None

    def test_retrieval_module_lazy_by_default(self):
        """core.retrieval should have _embed_model as None until requested."""
        import core.retrieval as retrieval
        # Retrieval instance should have _embed_model as None initially
        retrieval_instance = retrieval.Retrieval()
        self.assertIsNone(retrieval_instance._embed_model)

    def test_retrieval_loads_when_needed(self):
        """Calling get_embed_model should load and cache the EmbeddingModel."""
        import core.retrieval as retrieval
        with patch("core.retrieval.EmbeddingModel") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            retrieval._embed_model = None  # Reset

            model = retrieval.get_embed_model()
            self.assertEqual(model, mock_instance)
            mock_cls.assert_called_once()

            # Second call uses cache
            model2 = retrieval.get_embed_model()
            self.assertEqual(model2, mock_instance)
            self.assertEqual(mock_cls.call_count, 1)

            # Cleanup
            retrieval._embed_model = None

    def test_retrieval_getattr_backward_compat(self):
        """Accessing retrieval.embed should trigger get_embed_model lazily."""
        import core.retrieval as retrieval
        with patch("core.retrieval.EmbeddingModel") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            retrieval._embed_model = None

            model = retrieval.embed
            self.assertEqual(model, mock_instance)

            # Cleanup
            retrieval._embed_model = None


if __name__ == "__main__":
    unittest.main()
