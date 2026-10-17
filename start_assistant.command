#!/bin/bash
set -euo pipefail

# Always run from this script's project directory.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Prefer the project's virtual environment when available.
if [[ -x "$PROJECT_DIR/.venv/bin/python3" ]]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python3"
elif [[ -x "$PROJECT_DIR/venv/bin/python3" ]]; then
    PYTHON="$PROJECT_DIR/venv/bin/python3"
else
    PYTHON="$(command -v python3)"
fi

# Keep the window open so errors remain visible.
finish() {
    status=$?
    trap - EXIT

    echo ""

    if [[ "$status" -ne 0 ]]; then
        echo "Startup failed. Review the error above."
    else
        echo "Session finished."
    fi

    read -r -p "Press Enter to close..." || true
    exit "$status"
}

trap finish EXIT

echo "Refreshing tuition due-date data..."
"$PYTHON" crawler/fetch_tuition.py --only tuition_due_dates

echo "Checking tuition data format..."
"$PYTHON" - <<'PY'
from pathlib import Path

path = Path("scraped_data/Tuition&Payment/tuition_due_dates.txt")

if not path.exists():
    raise SystemExit("ERROR: Tuition due-date file is missing.")

text = path.read_text(encoding="utf-8")

if "[TABLE RECORD]" not in text or "[/TABLE RECORD]" not in text:
    raise SystemExit(
        "ERROR: Tuition data is not in the expected structured format. "
        "Check the crawler output before rebuilding."
    )

print("Structured tuition records found.")
PY

echo "Checking student data..."
"$PYTHON" - <<'PY'
from student_data.student_store import load_students

students = load_students()

if not students:
    raise SystemExit("ERROR: No student profiles were found.")

print(f"Loaded {len(students)} student profiles.")
PY

echo "Rebuilding vector database..."
HF_HUB_OFFLINE=1 "$PYTHON" src/build_vector.py


echo ""
echo "Starting the Temple RAG assistant..."
HF_HUB_OFFLINE=1 "$PYTHON" main.py