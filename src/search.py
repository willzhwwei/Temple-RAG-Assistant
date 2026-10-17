"""Reusable ChromaDB retrieval helpers."""

import json
import re
from pathlib import Path

import chromadb
from sentence_transformers import (
    SentenceTransformer
)

try:
    from .build_vector import (
        COLLECTION_NAME,
        EMBEDDING_MODEL,
        VECTOR_DB_PATH,
    )

except ImportError:
    from build_vector import (
        COLLECTION_NAME,
        EMBEDDING_MODEL,
        VECTOR_DB_PATH,
    )


# ---------------------------------------------------------
# 1. Connect to embedding model and ChromaDB
# ---------------------------------------------------------

def connect_search(
    db_path=VECTOR_DB_PATH
):
    """
    Load the embedding model and connect
    to an existing collection.
    """

    print(
        f"Vector database path: "
        f"{Path(db_path).resolve()}"
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    client = chromadb.PersistentClient(
        path=db_path
    )

    collection = client.get_collection(
        COLLECTION_NAME
    )

    return model, collection


# ---------------------------------------------------------
# 2. Normalize useful lexical terms
# ---------------------------------------------------------

def _terms(text):
    """
    Return useful lowercase terms
    for lexical relevance.
    """

    aliases = {
        "cost": "price",
        "costs": "price",
        "prices": "price",
        "rate": "price",
        "rates": "price",
        "monthly": "month",
    }

    raw_terms = re.findall(
        r"[a-z0-9]+",
        text.lower()
    )

    terms = {
        aliases.get(term, term)
        for term in raw_terms
    }

    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "for",
        "how",
        "in",
        "is",
        "of",
        "on",
        "the",
        "to",
        "what",
        "when",
    }

    return (
        terms
        - stop_words
    )


def _split_metadata_values(value):
    """
    Convert metadata such as:
    "Main Campus|Ambler Campus"

    into a normalized set.
    """

    if not value:
        return set()

    return {
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    }


def _normalize_phrase(value):
    """
    Normalize a profile or metadata phrase
    for conservative matching.

    Keep the normalization small and explicit so
    profile matching does not become overly broad.
    """

    if not value:
        return ""

    normalized = str(value).lower().replace(
        "&",
        " and "
    )

    normalized = " ".join(
        re.findall(
            r"[a-z0-9]+",
            normalized
        )
    )

    return normalized


# Only these fields may influence a question about the corresponding topic.
_PROFILE_WEIGHTS = {
    "campus": 0.25,
    "student_level": 0.10,
    "visa_status": 0.10,
    "insurance_plan": 0.35,
    "insurance_coverage": 0.20,
    "parking_plan": 0.35,
    "parking_billing_period": 0.15,
}

_GENERAL_VALUES = {
    "all", "any", "general", "unknown", "all students", "students",
    "all campuses", "all plans", "student parking", "unspecified", "n a",
}


def _field_values(field, values):
    """Normalize comparison keys only; never change returned chunk text."""
    normalized = {_normalize_phrase(value) for value in values if value}
    aliases = {
        "insurance_coverage": {
            "student only": "student coverage",
            "student only coverage": "student coverage",
            "student": "student coverage",
            "student and spouse coverage": "student and spouse",
            "student and child coverage": "student and child",
        },
        "parking_plan": {
            "5 day commuter parking": "5 day commuter",
            "7 day commuter parking": "7 day commuter",
            "overnight parking": "overnight",
            "flex parking": "flex",
            "rotation students": "rotation",
        },
        "parking_billing_period": {
            "monthly": "month",
            "per month": "month",
            "semesterly": "semester",
            "per semester": "semester",
            "per academic year": "academic year",
        },
        "visa_status": {
            "f1": "f 1",
            "j1": "j 1",
        },
    }
    if field == "insurance_coverage":
        combined = "student and child or student and spouse coverage"
        if combined in normalized:
            normalized.remove(combined)
            normalized.update({"student and child", "student and spouse"})
    field_aliases = aliases.get(field, {})
    return {field_aliases.get(value, value) for value in normalized if value}


def _applicability_values(field, metadata, document):
    """Read explicit metadata or labeled records, not incidental mentions.

    Old indexes lack insurance fields and parking billing periods. Read those
    from structured headings/rate tables without rebuilding or altering chunks.
    Missing evidence is an empty set, never a mismatch.
    """
    values = _split_metadata_values(metadata.get(field))
    if values:
        return _field_values(field, values)

    labels = {
        "insurance_plan": ("Insurance Plan", "Plan Options"),
        "insurance_coverage": ("Insurance Coverage", "Coverage"),
        "parking_plan": ("Parking Type", "Parking Plan"),
        "parking_billing_period": ("Billing Period",),
        "campus": ("Campus",),
        "visa_status": ("Visa Status",),
        "student_level": ("Student Level",),
    }
    lines = document.splitlines()
    for index, line in enumerate(lines):
        label, separator, value = line.partition(":")
        if separator and label.strip().casefold() in {
            name.casefold() for name in labels[field]
        }:
            values.update(_split_metadata_values(value))
        if field == "insurance_plan" and re.fullmatch(
            r"Section:\s*Personal Choice (?:High Option|Deductible) Plan",
            line.strip(), re.I,
        ):
            values.add(value.strip())
        # Read plan rows and coverage headers only in an explicit rate table.
        cells = [cell.strip() for cell in line.split("|")]
        if cells[0].casefold() == "plan options" and len(cells) > 1:
            if field == "insurance_coverage":
                values.update(cells[1:])
            elif field == "insurance_plan":
                for row in lines[index + 1:]:
                    row_cells = [cell.strip() for cell in row.split("|")]
                    if len(row_cells) != len(cells):
                        break
                    values.add(row_cells[0])
        if field == "parking_billing_period" and re.match(
            r"(?:Alternative )?Price:", line.strip(), re.I,
        ):
            values.update(re.findall(
                r"\bper (academic year|semester|month|entry|hour|day)\b",
                line, re.I,
            ))
    return _field_values(field, values)


def _relevant_profile(question, student_profile, evidence):
    """Limit profile use to relevant topics; explicit scenarios take priority."""
    terms = _terms(question)
    # Saved preferences apply to personal questions. Broad questions must keep
    # options for all students, including different levels and visa categories.
    if not terms & {"my", "me", "mine", "i"}:
        return {}
    fields = set()
    if terms & {"insurance", "premium", "coverage"} or "health plan" in question.lower():
        fields.update({"insurance_plan", "insurance_coverage", "student_level"})
    if terms & {"parking", "garage", "permit", "commuter"}:
        fields.update({"campus", "parking_plan", "parking_billing_period"})
    if terms & {"visa", "immigration", "employment", "work", "international", "f1", "j1"} or re.search(
        r"\b[fj]-1\b", question, re.I,
    ):
        fields.add("visa_status")
    if terms & {"tuition", "academic", "undergraduate", "graduate", "registration"}:
        fields.add("student_level")
    if "tuition" in terms or "school fees" in question.lower():
        fields.update({"campus", "student_level"})

    # A comparison/list of options should not be narrowed to a saved profile.
    if terms & {"compare", "comparison", "versus", "vs", "options", "all", "other", "faculty", "staff"}:
        return {}
    normalized_question = " " + _normalize_phrase(question) + " "
    normalized_question = re.sub(r"\bmonthly\b", "month", normalized_question)
    normalized_question = re.sub(r"\bf1\b", "f 1", normalized_question)
    normalized_question = re.sub(r"\bj1\b", "j 1", normalized_question)
    effective = {}
    for field in sorted(fields):
        value = (student_profile or {}).get(field)
        selected = _field_values(field, [value])
        if not selected or selected & _GENERAL_VALUES:
            continue
        # Values explicitly requested in the question override saved values.
        mentioned = set()
        for chunk in evidence:
            for candidate in chunk[field]:
                names = {candidate}
                if field == "campus":
                    names.add(re.sub(r" campus$", "", candidate))
                elif field == "insurance_plan":
                    names.add(re.sub(r"^personal choice | plan$", "", candidate))
                if any(f" {name} " in normalized_question for name in names if name):
                    mentioned.add(candidate)
        if mentioned and not mentioned <= selected:
            continue
        effective[field] = value
    return effective


def filter_student_candidates(question, student_profile, results):
    """Return surviving original indices, rejection records, and match data."""
    evidence = [
        {
            field: _applicability_values(field, metadata or {}, document or "")
            for field in _PROFILE_WEIGHTS
        }
        for document, metadata in zip(
            results["documents"][0], results["metadatas"][0]
        )
    ]
    profile = _relevant_profile(question, student_profile, evidence)
    terms = _terms(question)
    personal = bool(terms & {"my", "me", "mine", "i"})
    student_parking = (
        bool(terms & {"parking", "garage", "permit", "commuter"})
        and ("student" in terms or (personal and bool(student_profile)))
        and not terms & {"faculty", "staff"}
    )
    kept, filtered = [], []
    for index, metadata in enumerate(results["metadatas"][0]):
        metadata = metadata or {}
        reasons = []
        document = results["documents"][0][index]
        if not document or not document.strip():
            reasons.append({
                "field": "document",
                "profile_value": None,
                "chunk_values": [],
                "reason": "Chunk has no usable source text",
            })
        for field, value in profile.items():
            applicable = evidence[index][field]
            selected = _field_values(field, [value])
            if applicable and not applicable & (_GENERAL_VALUES | selected):
                reasons.append({
                    "field": field,
                    "profile_value": value,
                    "chunk_values": sorted(applicable),
                    "reason": "Explicit applicability conflicts with student profile",
                })
        audience = _split_metadata_values(metadata.get("audience"))
        if student_parking and audience == {"faculty_staff"}:
            reasons.append({
                "field": "audience",
                "profile_value": "student",
                "chunk_values": ["faculty_staff"],
                "reason": "Faculty/staff-only chunk for a student parking question",
            })
        if reasons:
            filtered.append({
                "index": index,
                "id": results["ids"][0][index],
                "source": metadata.get("source", ""),
                "reasons": reasons,
            })
        else:
            kept.append(index)
    return kept, filtered, profile, evidence


def _profile_boost(student_profile, applicability):
    """Boost exact relevant matches using the same evidence as filtering."""
    reasons = [
        field for field, value in student_profile.items()
        if _field_values(field, [value]) & applicability[field]
    ]
    return sum(_PROFILE_WEIGHTS[field] for field in reasons), reasons


def load_student_profile(
    student_id,
    students_path="students.json"
):
    """
    Load one student profile from students.json.
    """

    with open(
        students_path,
        "r",
        encoding="utf-8"
    ) as file:
        students = json.load(file)

    student_id = student_id.upper()

    if student_id not in students:
        raise ValueError(
            f"Unknown student ID: "
            f"{student_id}"
        )

    return students[student_id]


# ---------------------------------------------------------
# 3. Search and rerank
# ---------------------------------------------------------

def search(
    question,
    model,
    collection,
    n_results=5,
    student_profile=None
):
    """
    Retrieve broadly, filter explicit profile conflicts, then rerank
    surviving candidates using lexical overlap,
    answer-shape signals,
    and student-profile metadata matches.

    Return Chroma-shaped, aligned Top-K lists for rag.py. Cleaning removes
    unusable chunks and explicit applicability conflicts; source text and
    tables are preserved verbatim. Never refill from rejected candidates.
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must not be empty.")
    if isinstance(n_results, bool) or not isinstance(n_results, int) or n_results < 1:
        raise ValueError("n_results must be a positive integer.")

    # Retrieve a wider semantic
    # candidate pool first.
    candidate_count = min(
        collection.count(),
        max(
            30,
            n_results * 10
        )
    )

    if candidate_count == 0:
        return {key: [[]] for key in (
            "ids", "documents", "metadatas", "distances",
            "filtered_candidates", "rerank_scores", "profile_boosts",
            "profile_reasons",
        )}

    # Embed only the question; the profile is applied to retrieved evidence.
    embedding = model.encode(question)

    results = collection.query(
        query_embeddings=[
            embedding.tolist()
        ],

        n_results=candidate_count,

        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    query_terms = _terms(
        question
    )

    # Filter the broad semantic pool before any candidate is reranked.
    candidates, filtered, relevant_profile, applicability = (
        filter_student_candidates(question, student_profile, results)
    )

    # Detect whether user is
    # asking for a price.
    wants_price = (
        "price" in query_terms
        or "much" in query_terms
    )

    ranked = []

    # -----------------------------------------------------
    # Rerank candidates
    # -----------------------------------------------------

    for index in candidates:
        document = results["documents"][0][index]
        metadata = results["metadatas"][0][index] or {}

        source = metadata.get(
            "source",
            ""
        )

        # Include filename and content
        # in lexical matching.
        searchable_text = (
            f"{source} "
            f"{document}"
        )

        document_terms = _terms(
            searchable_text
        )

        overlap = (
            len(
                query_terms
                & document_terms
            )
            / max(
                1,
                len(query_terms)
            )
        )

        # Preference for dollar amounts
        # when question asks about price.
        answer_shape_boost = 0.0

        if (
            wants_price
            and "$" in document
        ):
            answer_shape_boost = 0.25

        profile_boost, profile_reasons = (
            _profile_boost(
                relevant_profile,
                applicability[index],
            )
        )

        # Chroma distance:
        # lower score = better.
        score = (
            results[
                "distances"
            ][0][index]
            - (
                0.50
                * overlap
            )
            - answer_shape_boost
            - profile_boost
        )

        ranked.append(
            (
                score,
                index,
                profile_boost,
                profile_reasons,
            )
        )

    # -----------------------------------------------------
    # Select best reranked results
    # -----------------------------------------------------

    selected_ranked = sorted(
        ranked,
        key=lambda item: item[0]
    )[:n_results]

    selected = [
        index
        for (
            _,
            index,
            _,
            _
        )
        in selected_ranked
    ]

    # Keep IDs aligned with
    # documents / metadata / distances.
    for key in (
        "ids",
        "documents",
        "metadatas",
        "distances",
    ):
        results[key] = [[
            results[key][0][index]
            for index in selected
        ]]

    # rag.py reads metadata with .get(), including for older sparse indexes.
    results["metadatas"] = [[metadata or {} for metadata in results["metadatas"][0]]]

    # Filter records refer to the original broad candidate pool, not Top-K.
    results["filtered_candidates"] = [filtered]

    # Extra debug fields for evaluation.
    results["rerank_scores"] = [[
        score
        for (
            score,
            _,
            _,
            _
        )
        in selected_ranked
    ]]

    results["profile_boosts"] = [[
        profile_boost
        for (
            _,
            _,
            profile_boost,
            _
        )
        in selected_ranked
    ]]

    results["profile_reasons"] = [[
        profile_reasons
        for (
            _,
            _,
            _,
            profile_reasons
        )
        in selected_ranked
    ]]

    return results


# ---------------------------------------------------------
# 4. Standalone retrieval test
# ---------------------------------------------------------

if __name__ == "__main__":

    model, collection = (
        connect_search()
    )

    print(
        f"Collection loaded: "
        f"{collection.count()} chunks"
    )

    student_id = input(
        "\nStudent ID "
        "(S001-S005, blank = no profile): "
    ).strip()

    student_profile = None

    if student_id:
        try:
            student_profile = (
                load_student_profile(
                    student_id,
                    students_path=(
                        Path(__file__).resolve().parent.parent
                        / "student_data" / "students.json"
                    ),
                )
            )

            print(
                f"\nUsing student profile: "
                f"{student_id.upper()}"
            )

            print(
                f"Name: "
                f"{student_profile.get('name')}"
            )

            print(
                f"Campus: "
                f"{student_profile.get('campus')}"
            )

            print(
                f"Student level: "
                f"{student_profile.get('student_level')}"
            )

            print(
                f"Visa status: "
                f"{student_profile.get('visa_status')}"
            )

        except (
            FileNotFoundError,
            json.JSONDecodeError,
            ValueError
        ) as error:
            print(
                f"Could not load student profile: "
                f"{error}"
            )
            student_profile = None

    question = input(
        "\nAsk a question: "
    ).strip()

    if question:

        results = search(
            question,
            model,
            collection,
            n_results=5,
            student_profile=student_profile
        )

        print(
            "\n"
            + "=" * 60
        )

        print("\nFiltered candidates:")
        for rejected in results["filtered_candidates"][0]:
            print(f"- {rejected['id']} ({rejected['source']})")
            for reason in rejected["reasons"]:
                print(
                    f"  {reason['field']}: {reason['reason']}; "
                    f"profile={reason['profile_value']!r}, "
                    f"chunk={reason['chunk_values']}"
                )
        if not results["filtered_candidates"][0]:
            print("  None")

        for index, (
            result_id,
            document,
            metadata,
            distance,
            rerank_score,
            profile_boost,
            profile_reasons,
        ) in enumerate(
            zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                results["rerank_scores"][0],
                results["profile_boosts"][0],
                results["profile_reasons"][0],
            ),
            1
        ):

            print(
                f"\nResult {index}"
            )

            print(
                f"ID: "
                f"{result_id}"
            )

            print(
                f"Semantic distance: "
                f"{distance:.4f}"
            )

            print(
                f"Final rerank score: "
                f"{rerank_score:.4f}"
            )

            print(
                f"Profile boost: "
                f"{profile_boost:.2f}"
            )

            if profile_reasons:
                print(
                    "Profile matches: "
                    + ", ".join(
                        profile_reasons
                    )
                )

            print(
                "\nMetadata:"
            )

            print(
                metadata
            )

            print(
                "\nContent:"
            )

            print(
                document
            )

            print(
                "\nSource:"
            )

            print(
                metadata.get(
                    "source",
                    "N/A"
                )
            )

            print(
                "-" * 60
            )
