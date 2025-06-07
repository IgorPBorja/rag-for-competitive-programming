import numpy as np
import faiss

from sqlalchemy import select

from db.dataset import Page
from core.embedding import Embedder
from db.db import DB
from logging_utils import get_logger

logger = get_logger(__name__)

class VectorDB:
    def __init__(self, db: DB, embedding_model: str, embedding_batch_size: int):
        """
        Builds vector database from the provided SQL database.

        :param db: SQL database for indexing into vector DB
        :param embedding_model: ollama model name
        :param embedding_batch_size: size of the batches that are embedded+indexed at once
        """
        with db.session() as session:
            sample_page = session.scalar(select(Page).limit(1))
        if not sample_page:
            raise ValueError(f"Empty dataset for vector DB!")
        # try embedding a single page content
        sample = Embedder.embed_page_batch([sample_page], embedding_model)

        self._index = faiss.IndexIDMap(faiss.IndexFlatL2(384))
        self._db = db
        self.embedding_model = embedding_model
        self.embedding_dim = sample.dim
        self._build_index(db, embedding_model, embedding_batch_size)

    def _build_index(self, db: DB, embedding_model: str, embedding_batch_size: int, verbose: bool = False):
        """
        Embeds and indexes all of the provided database, using the specified model

        :param db: SQL database for indexing into vector DB
        :param embedding_model: ollama model name
        :param embedding_batch_size: size of the batches that are embedded+indexed at once
        """
        for batch in Embedder.embed_db(db, embedding_model, embedding_batch_size):
            self._index.add_with_ids(batch.embedding, np.array([page.id for page in batch.pages]))
            if verbose:
                logger.info(f"Indexed batch of {len(batch.pages)} webpages with model '{embedding_model}'")

    async def search(self, query: str, top_k: int) -> list[tuple[float, Page]]:
        """
        Searches for top-k webpages semantically related to query in the index.
        
        Returns list of pairs (score, webpage), where score = 1 / (1 + embedding distance)
        """
        query_vector = Embedder.embed_query(query, self.embedding_model).reshape((1, query_vector.shape[-1])).astype(np.float32)
        distances, ids = self._index.search(query_vector, k=top_k)   # two numpy arrays of shape (1, embedding_dim), of types float32 and int64
        scores = (1.0 / (1.0 + distances.flatten()))
        async with self._db.async_session() as session:
            pages = (await session.scalars(
                select(Page).where(Page.id.in_(ids))
            )).all()
        return [(float(s), p) for s, p in zip(scores, pages)]
