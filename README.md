# Temple RAG Assistant

**A Local AI-Powered Campus Information Assistant Using Retrieval-Augmented Generation (RAG)**

## 1. Project Overview

Temple RAG Assistant is an ongoing academic software project designed to help students retrieve information about Temple University through natural language questions.

The system combines document retrieval, semantic search, and a locally hosted Large Language Model (LLM) to generate answers based on university-related documents.

The project also explores answer confidence evaluation to help users understand whether generated answers are supported by the retrieved evidence.

## 2. Key Features

### Retrieval-Augmented Generation (RAG)
- Retrieves relevant information from a local knowledge base.
- Uses semantic embeddings to find related document passages.
- Provides retrieved context to a local LLM for answer generation.

### Student Profile Filtering
- Supports student-specific information retrieval.
- Filters retrieved documents based on applicable student profiles.

### Local LLM Integration
- Uses Ollama with Llama 3.2 3B.
- Supports local inference without requiring a paid LLM API.

### Answer Confidence Evaluation — In Development
- Investigates methods for assessing whether generated answers are supported by retrieved evidence.
- Explores evidence support, contradiction, and insufficient information.
- Aims to provide qualitative confidence levels: HIGH, MEDIUM, and LOW.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Language Model | Llama 3.2 3B |
| Local LLM Runtime | Ollama |
| Embedding Model | all-MiniLM-L6-v2 |
| Vector Database | ChromaDB |
| Retrieval | Semantic Search |
| Answer Evaluation | Evidence-based confidence assessment |

## 4. System Architecture

```text
             User Question
                   |
                   v
          Student Profile
                   |
                   v
           Semantic Search
                   |
                   v
          Profile Filtering
                   |
                   v
           Document Retrieval
                   |
                   v
             Local LLM
           (Llama 3.2 3B)
                   |
                   v
           Generated Answer
                   |
                   v
        Confidence Evaluation
           (In Development)
                   |
                   v
             Final Output
```

The system is designed to separate document retrieval, answer generation, and answer confidence assessment into different components.

## 5. Project Structure

```text
Temple-RAG-Assistant/
├── crawler/              # University document collection
├── src/
│   ├── rag.py            # RAG pipeline
│   ├── search.py         # Document retrieval
│   ├── llm_ollama.py     # Local LLM integration
│   ├── confidence.py     # Answer confidence evaluation
│   ├── build_vector.py   # Vector database construction
│   └── chunk_data.py     # Document chunking
├── tests/                # Evaluation and testing
├── build_rag.py          # Knowledge base rebuilding
├── main.py               # Assistant entry point
└── README.md
```

Locally generated knowledge-base files, vector database files, and student records are excluded from the public repository.

## 6. Running the Project

### Prerequisites

- Python 3
- Ollama
- Llama 3.2 3B
- Required Python dependencies
- Locally prepared university document data

### Build the Knowledge Base

```bash
python3 build_rag.py
```

The script processes local crawler output, selects valid documents, creates text chunks and embeddings, and rebuilds the ChromaDB collection.

### Start the Assistant

```bash
python3 main.py
```

**Note:** The repository does not include the local vector database, source document dataset, or sample student records. Additional local setup is required before the assistant can run.

## 7. Current Limitations

- Retrieval performance varies across question types.
- Some university fee and policy questions may produce inaccurate or incomplete answers.
- The answer confidence evaluator is still under development and requires further validation.
- The system currently uses a relatively small local language model.

## 8. Future Work

- Improve evidence-based answer verification.
- Evaluate Natural Language Inference (NLI) models for detecting supported and contradictory claims.
- Expand test coverage across university information domains.
- Improve local deployment and reproducibility.
- Explore more efficient LLM inference approaches.

## 9. Project Status

**Status: Active Development**

This project is developed as part of my academic learning and practical exploration of Retrieval-Augmented Generation, local language models, and AI answer reliability.

The long-term goal is to strengthen my skills in AI engineering, software development, and open-source collaboration.