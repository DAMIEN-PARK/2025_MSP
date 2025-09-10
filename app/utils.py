from typing import List
from langchain_core.documents import Document


def format_docs(docs: List[Document]) -> str:
    """Join document contents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)
