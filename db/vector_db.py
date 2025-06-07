import numpy as np
import faiss

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.dataset import DATASET, Page
from core.embedding import Embedder
from db.db import DB
from logging_utils import get_logger

logger = get_logger(__name__)

class VectorDB:
    def __init__(self, db: DB, embedding_model: str, embedding_batch_size: int, verbose: bool = False):
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

        self._index = faiss.IndexIDMap(faiss.IndexFlatL2(sample.dim))
        if verbose:
            logger.info(f"Created vector index for model '{embedding_model}'")
        self._db = db
        self.embedding_model = embedding_model
        self.embedding_dim = sample.dim
        self._len = 0
        self._build_index(db, embedding_model, embedding_batch_size, verbose=verbose)

    def _build_index(self, db: DB, embedding_model: str, embedding_batch_size: int, verbose: bool = False):
        """
        Embeds and indexes all of the provided database, using the specified model

        :param db: SQL database for indexing into vector DB
        :param embedding_model: ollama model name
        :param embedding_batch_size: size of the batches that are embedded+indexed at once
        """
        for batch in Embedder.embed_db(db, embedding_model, embedding_batch_size):
            self._index.add_with_ids(batch.embedding, np.array([page.id for page in batch.pages]))
            self._len += len(batch.pages)
            if verbose:
                logger.info(f"Indexed batch of {len(batch.pages)} webpages with model '{embedding_model}'")

    async def search(self, query: str, top_k: int) -> list[tuple[float, Page]]:
        """
        Searches for top-k webpages semantically related to query in the index.
        
        Returns list of pairs (score, webpage), where score = 1 / (1 + embedding distance)
        """
        query_vector = Embedder.embed_query(query, self.embedding_model)
        query_vector = query_vector.reshape((1, query_vector.shape[-1])).astype(np.float32)
        distances, ids = self._index.search(query_vector, k=top_k)   # two numpy arrays of shape (1, embedding_dim), of types float32 and int64
        scores = (1.0 / (1.0 + distances.flatten()))
        async with self._db.async_session() as session:
            pages = (await session.scalars(
                select(Page).where(Page.id.in_(ids))
                .options(selectinload(Page.url))
            )).all()
        return [(float(s), p) for s, p in zip(scores, pages)]

    def __len__(self) -> int:
        return self._len


if __name__ == "__main__":
    import argparse
    import asyncio
    import shlex

    HELP_TEXT = """
        Use '/index --model MODEL_NAME --batch-size BATCH_SIZE' to index a database using that model and batch size
        Use '/select MODEL_NAME' to use the vector database built using this model
        Use '/show' to show all available vector databases (by model)
        Use '/query -k TOP_K "QUERY"' (note the quotes) to query the top-k most semantically similar results (to the query) against the active vector database
        Use '/help' to show this help text again
        Use '/exit' to exit
    """

    parser = argparse.ArgumentParser()
    cmd_selector = parser.add_subparsers(help="Subcommands", dest="command")

    database_map: dict[str, VectorDB] = {}
    active_db: str | None = None

    init_parser = cmd_selector.add_parser("index", help="Index a SQL database into a vector DB")
    init_parser.add_argument("--model", type=str, help="Ollama model for embedding")
    init_parser.add_argument("--batch-size", type=int, help="Batch size for embedding+indexing action")

    select_parser = cmd_selector.add_parser("select", help="Select a vector database (by embedding model used) to query against")
    select_parser.add_argument("model", type=str, help="Ollama model used for embedding")

    display_parser = cmd_selector.add_parser("show", help="Show available vector databases")
    help_parser = cmd_selector.add_parser("help", help="Show help text")
    exit_parser = cmd_selector.add_parser("exit", help="Exit program")

    query_parser = cmd_selector.add_parser("query", help="Query to search for the most similar documents in the vector DB")
    query_parser.add_argument("-k", type=int, default=5, help="Amount of results to retrieve: show only the top k most similar results")
    query_parser.add_argument("query", type=str, help="User query")

    print(HELP_TEXT)
    while True:
        print(">>> ", end="")
        cmd = input()
        # print(f"{cmd=}")
        if not cmd.startswith('/'):
            print(f"ERROR: invalid command format. Try again")
            continue
        args = parser.parse_args(shlex.split(cmd.removeprefix("/")))  # use of shlex to keep quoted parts together
        if args.command == "help":
            print(HELP_TEXT)
        elif args.command == "show":
            print(f"Active vector databases: {len(database_map)}")
            for model, db in database_map.items():
                if model == active_db: 
                    print(f"[ACTIVE] {model}: {len(db)} items indexed")
                else:
                    print(f"{model}: {len(db)} items indexed")
        elif args.command == "select":
            if args.model not in database_map:
                print(f"ERROR: Vector database for model '{args.model}' does not exist yet")
                continue
            active_db = args.model
        elif args.command == "index":
            database_map[args.model] = VectorDB(DATASET, embedding_model=args.model, embedding_batch_size=args.batch_size, verbose=True)
            print(f"Indexed database for model '{args.model}'")
        elif args.command == "query":
            if not active_db:
                print(f"ERROR: no database is selected")
                continue
            loop = asyncio.get_event_loop()
            db = database_map[active_db]
            results = loop.run_until_complete(db.search(args.query, args.k))
            print(f"Found {len(results)} results.")
            for score, page in results:
                print(f"With score = {score}, found {page.url} (ID={page.id}, UUID={page.page_uuid})")
        elif args.command == "exit":
            print("Exiting...")
            break
