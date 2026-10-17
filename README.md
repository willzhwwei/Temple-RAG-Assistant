## Temple RAG Assistant

Build or replace the knowledge base from the crawler output:

```bash
python3 build_rag.py
```

This command selects valid files from `scraped_data/`, prefers
`*_structured.txt` over its matching raw file, excludes citation/metadata
artifacts, chunks documents, embeds them, and recreates the
`temple_campus_data` ChromaDB collection in `vector_db/`.

Start the assistant without rebuilding the database:

```bash
python3 main.py
```

Inspect the five retrieval checks after a rebuild:

```bash
python3 test_retrieval.py
```
