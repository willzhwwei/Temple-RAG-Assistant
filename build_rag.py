"""Build or rebuild the Temple RAG knowledge base from scraped_data."""

from src.build_vector import build_vector_database


if __name__ == "__main__":
    build_vector_database()
