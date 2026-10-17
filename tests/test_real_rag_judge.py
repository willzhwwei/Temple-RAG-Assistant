"""Evaluate an existing Temple RAG answer against its REAL retrieved chunks.

Place this file at tests/test_real_rag_judge.py, next to test_llm_judge.py.
Run from project root: python3 -u tests/test_real_rag_judge.py --limit 3

This is an exploratory test: judge labels are predictions, not ground truth.
No existing RAG or confidence implementation is modified.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Reuse the exact prompt, parsing, and Ollama interface from the 8-case test.
from test_llm_judge import judge_case

# Importing src.rag loads your existing embedding model and ChromaDB once.
from src.rag import ask_rag
from src.confidence import evaluate_confidence


QUESTIONS = [
    ("Parking", "What is the overnight parking rate for Main Campus students per semester?"),
    ("Academic Calendar", "When does the Fall 2026 semester begin at Temple University?"),
    ("Health Insurance", "What health insurance options are available for international graduate students?"),
    ("International Students", "What are the employment rules for F-1 international students?"),
    ("Tuition", "How much is tuition for international graduate students at Temple University?"),
    ("Insufficient Information", "What will Temple University's tuition be in Fall 2030?"),
]


def combine_evidence(documents, sources):
    """Keep chunk boundaries visible; source names are a deduplicated list."""
    if not documents:
        return "No retrieved documents."
    return "\n\n".join(
        "[Retrieved chunk {}]\n{}".format(i, doc)
        for i, doc in enumerate(documents, start=1)
    )


def main():
    parser = argparse.ArgumentParser(description="Real RAG evidence verification test")
    parser.add_argument("--limit", type=int, default=3, help="Number of questions (1-6); default 3")
    parser.add_argument("--student", default="none", help="Student ID, or none for general Q&A")
    parser.add_argument("--chunks", type=int, default=5, help="Retrieved chunks per question")
    parser.add_argument("--show-evidence", action="store_true", help="Print all retrieved text")
    args = parser.parse_args()

    if not 1 <= args.limit <= len(QUESTIONS):
        parser.error("--limit must be between 1 and {}".format(len(QUESTIONS)))
    if args.chunks < 1:
        parser.error("--chunks must be at least 1")

    student_id = None if args.student.lower() == "none" else args.student
    rows = []
    print("\nReal RAG Evidence Judge | student={}".format(student_id or "none"), flush=True)
    print("Predictions are NOT verified correct labels.\n", flush=True)

    for index, (category, question) in enumerate(QUESTIONS[:args.limit], 1):
        print("=" * 65, flush=True)
        print("Test {}: {}".format(index, category), flush=True)
        print("Question: {}".format(question), flush=True)
        try:
            answer, sources, documents = ask_rag(
                question, n_results=args.chunks, student_id=student_id
            )
            evidence = combine_evidence(documents, sources)
            print("\nRAG Answer:\n{}".format(answer), flush=True)
            print("\nRetrieved sources (not verified citations):", flush=True)
            for source in sources:
                print("- {}".format(source), flush=True)
            print("Chunks: {} | Evidence characters: {}".format(len(documents), len(evidence)), flush=True)
            if args.show_evidence:
                print("\nRetrieved evidence:\n{}".format(evidence), flush=True)

            baseline = evaluate_confidence(question, answer, documents)
            print("\nOld baseline confidence: {}".format(baseline["level"]), flush=True)

            print("Running LLM Judge...", flush=True)
            judged = judge_case({"question": question, "evidence": evidence, "answer": answer})
            print("Judge label: {}".format(judged["label"]), flush=True)
            print("Judge reason: {}".format(judged["reason"]), flush=True)
            print("Human verification: NOT YET DONE", flush=True)

            rows.append({
                "category": category,
                "question": question,
                "student_id": student_id,
                "answer": answer,
                "sources": sources,
                "retrieved_documents": documents,
                "old_baseline": baseline,
                "judge": judged,
                "human_label": None,
            })
        except Exception as exc:
            print("ERROR (continuing): {}: {}".format(type(exc).__name__, exc), flush=True)
            rows.append({"category": category, "question": question, "error": str(exc)})

    out_dir = PROJECT_ROOT / "tests" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "real_rag_judge_results.json"
    with output.open("w", encoding="utf-8") as file:
        json.dump({"timestamp": datetime.now().isoformat(), "results": rows}, file,
                  indent=2, ensure_ascii=False)

    print("\nFinished: {} case(s).".format(len(rows)), flush=True)
    print("Saved evidence and predictions to: {}".format(output), flush=True)
    print("Review the actual evidence before assigning human labels or accuracy.", flush=True)


if __name__ == "__main__":
    main()
