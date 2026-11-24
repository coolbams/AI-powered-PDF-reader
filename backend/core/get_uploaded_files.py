from .supabase_service import list_document_filenames


def get_file_list() -> list[str]:
    """Retrieves the list of all registered PDF filenames directly from Supabase PostgreSQL."""
    return list_document_filenames()
