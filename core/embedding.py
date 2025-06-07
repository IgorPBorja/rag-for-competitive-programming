import ollama
import numpy as np

from dataclasses import dataclass
from typing import Generator
from sqlalchemy import select

from db.dataset import Page
from db.db import DB
from logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class BatchEmbedding:
    embedding: np.ndarray[np.float32]
    """Embedding matrix for that batch of webpages"""
    pages: list[Page]
    """List of web pages, in the same order as the embedding matrix"""
    dim: int
    """Dimension of embedding vector"""


class Embedder:
    @staticmethod
    def embed_page_batch(page_batch: list[Page], embedding_model: str) -> BatchEmbedding:
        """
        Embeds a batch of web pages using a ollama model and return the batch response
        (together with info on the dimension of the embedding)
        """
        # TODO add chunking strategies, etc
        content_batch = [page.content for page in page_batch]
        response = ollama.embed(model=embedding_model, input=content_batch)
        embedding_matrix = np.array(response.embeddings, dtype=np.float32)
        embedding_dim = embedding_matrix.shape[-1]
        return BatchEmbedding(embedding=embedding_matrix, pages=page_batch, dim=embedding_dim)

    @staticmethod
    def embed_query(query: str, embedding_model: str) -> np.ndarray[np.float32]:
        """
        Embeds a single query using a specific ollama model
        """
        response = ollama.embed(model=embedding_model, input=query)
        vector = response.embeddings[0]
        return np.array(vector, dtype=np.float32)
            
    @staticmethod
    def embed_db(db: DB, embedding_model: str, batch_size: int) -> Generator[BatchEmbedding, None, None]:
        """
        Embeds a whole SQL database of webpages using a specific ollama model and batch size.
        Generates embeddings lazily (through generators).
        """
        last_id: int = 0
        with db.session() as session:
            while (pages := session.scalars(
                select(Page)
                .where(Page.id > last_id)
                .order_by(Page.id.desc())
                .limit(batch_size)
            ).all()):
                last_id = pages[-1].id
                yield Embedder.embed_page_batch(pages, embedding_model)
