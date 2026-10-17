"""Evaluate evidence-based answer verification with an existing local Ollama model.

Run from the project root:
    python3 tests/test_llm_judge.py

Only requires the requests package and an Ollama server with llama3.2:3b.
"""

import json
import re
from collections import Counter

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"
LABELS = {"SUPPORTED", "CONTRADICTED", "INSUFFICIENT"}

TEST_CASES = [
    {
        "question": "When does Fall 2026 begin?",
        "evidence": "Fall 2026 semester begins August 25.",
        "answer": "Fall 2026 begins August 25.",
        "expected": "SUPPORTED",
    },
    {
        "question": "When does Fall 2026 begin?",
        "evidence": "Fall 2026 semester begins August 25. Another deadline is October 15.",
        "answer": "Fall 2026 begins October 15.",
        "expected": "CONTRADICTED",
    },
    {
        "question": "How much is overnight parking?",
        "evidence": "Main Campus overnight parking costs $426 per semester.",
        "answer": "Overnight parking costs $426 per semester at Main Campus.",
        "expected": "SUPPORTED",
    },
    {
        "question": "What is the tuition for Fall 2030?",
        "evidence": "Tuition rates for Fall 2026 are available.",
        "answer": "Fall 2030 tuition is $15,000.",
        "expected": "INSUFFICIENT",
    },
    {
        "question": "Who is eligible for this grant?",
        "evidence": "Only graduate students are eligible for the grant.",
        "answer": "All students are eligible for the grant.",
        "expected": "CONTRADICTED",
    },
    {
        "question": "Is an application required?",
        "evidence": "An application must be submitted before registration.",
        "answer": "You must submit an application before registration.",
        "expected": "SUPPORTED",
    },
    {
        "question": "What is the parking rate?",
        "evidence": "Campus: Main Campus\nParking: Overnight\nRate: $426 per semester",
        "answer": "Main Campus overnight parking costs $426 per semester.",
        "expected": "SUPPORTED",
    },
    {
        "question": "What is the fee?",
        "evidence": "The application fee is $85. The tuition amount is not provided.",
        "answer": "Tuition is $85.",
        "expected": "CONTRADICTED",
    },
]

SYSTEM_PROMPT = """You are an evidence verifier for a university question-answering system.
Your task is to evaluate whether the GIVEN ANSWER is supported by the GIVEN EVIDENCE,
not to answer the question yourself and not to rely on outside knowledge.

Classify the answer into EXACTLY one label:
SUPPORTED: Evidence directly establishes all essential claims of the answer.
CONTRADICTED: Evidence explicitly conflicts with at least one essential claim.
INSUFFICIENT: Evidence does not establish an essential claim, without explicitly contradicting it.

Rules:
- Compare relationships: dates to events, amounts to fee types, qualifications to people.
- Do not treat a word or number appearing somewhere in evidence as proof of its meaning.
- Evidence may be spread across multiple lines, but do not connect unrelated facts.
- If conflicting and unsupported claims coexist, prefer CONTRADICTED.
- If the answer declines to answer, label INSUFFICIENT for this experiment.
- Return ONLY a JSON object with keys "label" and "reason".
- "reason" is one short sentence citing the relevant evidence or describing what is missing.
"""


def parse_result(response_json):
    raw = response_json.get("message", {}).get("content", "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Judge returned non-JSON content: {raw[:300]!r}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Judge JSON is not an object: {raw[:300]!r}")
    label = str(data.get("label", "")).upper().strip()
    if label not in LABELS:
        raise ValueError(f"Judge returned invalid label {label!r}; response={raw[:300]!r}")
    return {"label": label, "reason": str(data.get("reason", "")).strip()}


def judge_case(case):
    payload = {
        "model": MODEL,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 200},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "QUESTION:\n" + case["question"] + "\n\n"
                    "EVIDENCE:\n" + case["evidence"] + "\n\n"
                    "GIVEN ANSWER:\n" + case["answer"]
                ),
            },
        ],
    }
    result = requests.post(OLLAMA_URL, json=payload, timeout=180)
    result.raise_for_status()
    return parse_result(result.json())


def main():
    correct = 0
    attempted = 0
    confusion = Counter()
    print(f"Model: {MODEL} | Evidence support evaluation\n")

    for index, case in enumerate(TEST_CASES, start=1):
        print(f"Test {index}: {case['question']}")
        print(f"Expected:  {case['expected']}")
        try:
            result = judge_case(case)
        except (requests.RequestException, ValueError) as exc:
            print(f"ERROR: {exc}\n{'-' * 52}")
            continue

        predicted = result["label"]
        attempted += 1
        correct += int(predicted == case["expected"])
        confusion[(case["expected"], predicted)] += 1
        print(f"Predicted: {predicted}")
        print(f"Reason:    {result['reason']}")
        print(f"Result:    {'PASS' if predicted == case['expected'] else 'FAIL'}")
        print("-" * 52)

    print(f"Accuracy: {correct}/{attempted}" +
          (f" ({correct / attempted:.1%})" if attempted else " (no valid predictions)"))
    if attempted:
        print("Confusion counts (expected -> predicted):")
        for (expected, predicted), count in sorted(confusion.items()):
            print(f"  {expected} -> {predicted}: {count}")
    if attempted < len(TEST_CASES):
        print(f"Warning: {len(TEST_CASES) - attempted} case(s) could not be evaluated.")

if __name__ == "__main__":
    main()