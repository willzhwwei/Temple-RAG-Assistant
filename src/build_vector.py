from collections import Counter
from hashlib import sha1
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

try:
    from .chunk_data import chunk_documents
    from .load_data import load_documents
except ImportError:
    from chunk_data import chunk_documents
    from load_data import load_documents

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "temple_campus_data"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTOR_DB_PATH = str(PROJECT_ROOT / "vector_db")


def _chunk_id(chunk):
    value = f"{chunk['source']}:{chunk['chunk_id']}:{chunk['content']}"
    return f"chunk_{sha1(value.encode('utf-8')).hexdigest()}"


def build_vector_database(data_dir="scraped_data", db_path=VECTOR_DB_PATH):
    """Replace the collection and populate it from the selected crawler corpus."""

    resolved_db_path = Path(db_path).resolve()

    print(f"Vector database path: {resolved_db_path}")
    print(f"Current working directory: {Path.cwd()}")

    documents = load_documents(data_dir)
    chunks = chunk_documents(documents)

    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")

    if not chunks:
        raise ValueError(
            "No usable crawler documents were found; "
            "database was not changed."
        )

    # Encode before touching ChromaDB.
    # If model loading or encoding fails,
    # the current database remains intact.
    print(f"Loading embedding model: {EMBEDDING_MODEL}")

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    embeddings = model.encode(
        [
            chunk["content"]
            for chunk in chunks
        ],
        show_progress_bar=True,
    )

    print(
        f"Embeddings created: "
        f"{len(embeddings)}"
    )

    if len(embeddings) != len(chunks):
        raise ValueError(
            f"Embedding count "
            f"({len(embeddings)}) "
            f"does not match chunk count "
            f"({len(chunks)})."
        )

    client = chromadb.PersistentClient(
        path=str(resolved_db_path)
    )

    try:
        client.delete_collection(
            COLLECTION_NAME
        )

        print(
            f"Deleted existing collection: "
            f"{COLLECTION_NAME}"
        )

    except Exception as error:

        # Chroma raises an exception when the
        # collection does not exist.
        if (
            "does not exist"
            not in str(error).lower()
            and "not found"
            not in str(error).lower()
        ):
            raise

        print(
            f"No existing collection "
            f"to delete: "
            f"{COLLECTION_NAME}"
        )

    collection = client.create_collection(
        COLLECTION_NAME
    )

    print(
        f"Created collection: "
        f"{COLLECTION_NAME}"
    )

    # ---------------------------------------------------------
    # Insert chunks in batches
    # ---------------------------------------------------------

    for start in range(
        0,
        len(chunks),
        100,
    ):
        batch = chunks[
            start:start + 100
        ]

        batch_embeddings = embeddings[
            start:start + len(batch)
        ]

        if len(batch_embeddings) != len(batch):
            raise ValueError(
                f"Batch at offset "
                f"{start} has "
                f"{len(batch)} chunks but "
                f"{len(batch_embeddings)} "
                f"embeddings."
            )

        print(
            f"Inserting batch "
            f"{start // 100 + 1}: "
            f"{len(batch)} chunks"
        )

        collection.add(

            ids=[
                _chunk_id(chunk)
                for chunk in batch
            ],

            documents=[
                chunk["content"]
                for chunk in batch
            ],

            embeddings=[
                embedding.tolist()
                for embedding
                in batch_embeddings
            ],

            # Store every useful chunk field
            # as Chroma metadata.
            #
            # "content" is excluded because it
            # is already stored under documents.
            #
            # Empty metadata values are also
            # excluded.
            metadatas=[
                {
                    key: value

                    for key, value
                    in chunk.items()

                    if (
                        key != "content"
                        and value
                        not in (
                            None,
                            "",
                        )
                    )
                }

                for chunk in batch
            ],
        )

        print(
            f"Collection count after "
            f"batch "
            f"{start // 100 + 1}: "
            f"{collection.count()}"
        )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    print("\nRebuild complete")

    print(
        f"Source documents loaded: "
        f"{len(documents)}"
    )

    print(
        f"Chunks created: "
        f"{len(chunks)}"
    )

    print(
        f"Records stored in ChromaDB: "
        f"{collection.count()}"
    )

    print(
        "Documents by category:"
    )

    for category, count in sorted(
        Counter(
            doc["category"]
            for doc in documents
        ).items()
    ):
        print(
            f"  {category}: {count}"
        )

    return collection


if __name__ == "__main__":
    build_vector_database()