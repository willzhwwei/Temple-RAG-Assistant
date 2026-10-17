import re


def _join_metadata_values(values):
    """Store multiple applicable values as one normalized string."""
    values = list(dict.fromkeys(values))
    return "|".join(values)


def extract_metadata(content, document):
    """
    Extract metadata that can help personalize retrieval.

    Conservative rule:
    only add metadata when the chunk explicitly supports it.
    """

    metadata = {}

    category = document["category"]
    document_name = document["document_name"].lower()
    text = content.lower()

    # ---------------------------------------------------------
    # Parking
    # ---------------------------------------------------------
    if category == "Parking":

        # A single chunk may apply to more than one campus.
        campuses = {
            "main campus": "Main Campus",
            "health sciences center": "Health Sciences Center",
            "hsc campus": "Health Sciences Center",
            "ambler campus": "Ambler Campus",
            "temple university center city": "Temple University Center City",
            "tucc": "Temple University Center City",
        }

        campus_values = []

        for keyword, value in campuses.items():
            if keyword in text:
                campus_values.append(value)

        if campus_values:
            metadata["campus"] = _join_metadata_values(
                campus_values
            )

        # Audience is inferred conservatively from the source document.
        if "visitor_parking" in document_name:
            metadata["audience"] = "visitor"

        elif "faculty_staff" in document_name:
            metadata["audience"] = "faculty_staff"

        elif "student_parking" in document_name:
            metadata["audience"] = "student"

        # A chunk may contain multiple parking plans.
        parking_plans = {
            "5-day commuter parking": "5-Day Commuter",
            "7-day commuter parking": "7-Day Commuter",
            "overnight parking": "Overnight",
            "flex parking": "Flex",
            "weekend parking pass": "Weekend Pass",
            "rotation students": "Rotation",
            "discount student parking": "Discount Student Parking",
        }

        parking_plan_values = []

        for keyword, value in parking_plans.items():
            if keyword in text:
                parking_plan_values.append(value)

        if parking_plan_values:
            metadata["parking_plan"] = _join_metadata_values(
                parking_plan_values
            )

        # Billing period should come only from explicit price wording.
        # This metadata is later used by profile-aware filtering/reranking.
        parking_billing_periods = []

        billing_patterns = {
            r"\bper semester\b": "Semester",
            r"\bper academic year\b": "Academic Year",
            r"\bper month\b": "Month",
            r"\bmonthly\b": "Month",
            r"\bper entry\b": "Entry",
            r"\bper hour\b": "Hour",
            r"\b/hour\b": "Hour",
            r"\bper day\b": "Day",
            r"\bdaily rate\b": "Day",
        }

        for pattern, value in billing_patterns.items():
            if re.search(pattern, text):
                parking_billing_periods.append(value)

        if parking_billing_periods:
            metadata["parking_billing_period"] = _join_metadata_values(
                parking_billing_periods
            )

    # ---------------------------------------------------------
    # Academic Calendar
    # ---------------------------------------------------------
    elif category == "Academic Calendar":

        year_match = re.search(
            r"(20\d{2})[_-](20\d{2})",
            document_name,
        )

        if year_match:
            metadata["academic_year"] = (
                f"{year_match.group(1)}-{year_match.group(2)}"
            )

        semester_match = re.search(
            r"(Fall|Spring|Summer I|Summer II)\s+20\d{2}",
            content,
            flags=re.I,
        )

        if semester_match:
            metadata["semester"] = semester_match.group(0)

        levels = []

        if re.search(r"\bundergraduate\b", text):
            levels.append("Undergraduate")

        if re.search(r"\bgraduate\b", text):
            levels.append("Graduate")

        if levels:
            metadata["student_level"] = _join_metadata_values(
                levels
            )

    # ---------------------------------------------------------
    # Health Insurance
    # ---------------------------------------------------------
    elif category == "Health Insurance":

        visa_statuses = []

        if re.search(r"\bf-?1\b", text):
            visa_statuses.append("F-1")

        if re.search(r"\bj-?1\b", text):
            visa_statuses.append("J-1")

        if visa_statuses:
            metadata["visa_status"] = _join_metadata_values(
                visa_statuses
            )

        levels = []

        if re.search(r"\bundergraduate\b", text):
            levels.append("Undergraduate")

        if re.search(r"\bgraduate\b", text):
            levels.append("Graduate")

        if re.search(r"\blaw student(s)?\b", text):
            levels.append("Law")

        if levels:
            metadata["student_level"] = _join_metadata_values(
                levels
            )

        programs = []

        # Program labels must be supported by program-specific wording.
        # Avoid broad keywords such as "medical" or "dental" by themselves,
        # because phrases like "medical care" or "dental benefits" do not
        # mean the chunk is intended for Medical/Dental students.
        program_patterns = {
            "Medical": [
                r"\bmedical student(?:s)?\b",
                r"\bmedical school\b",
                r"\bschool of medicine\b",
                r"\bmedical program(?:s)?\b",
            ],
            "Podiatric": [
                r"\bpodiatric student(?:s)?\b",
                r"\bpodiatric medicine\b",
                r"\bschool of podiatric medicine\b",
                r"\bpodiatric program(?:s)?\b",
            ],
            "Dental": [
                r"\bdental student(?:s)?\b",
                r"\bdental school\b",
                r"\bschool of dentistry\b",
                r"\bdental program(?:s)?\b",
            ],
            "Public Health": [
                r"\bcollege of public health\b",
                r"\bpublic health student(?:s)?\b",
                r"\bpublic health program(?:s)?\b",
            ],
            "Pharmacy": [
                r"\bpharmacy student(?:s)?\b",
                r"\bschool of pharmacy\b",
                r"\bcollege of pharmacy\b",
                r"\bpharmacy program(?:s)?\b",
            ],
        }

        # Temple sometimes lists several professional programs together in
        # one heading, e.g. "Medical, Podiatric, Dental, ... Students".
        # Treat that explicit audience heading as program-specific context.
        professional_program_heading = re.search(
            r"\bmedical\b.*\bpodiatric\b.*\bdental\b.*"
            r"\b(?:public health|pharmacy)\b.*\bstudent(?:s)?\b",
            text,
            flags=re.S,
        )

        if professional_program_heading:
            heading_terms = {
                "medical": "Medical",
                "podiatric": "Podiatric",
                "dental": "Dental",
                "college of public health": "Public Health",
                "pharmacy": "Pharmacy",
            }

            for keyword, value in heading_terms.items():
                if keyword in text:
                    programs.append(value)
        else:
            for value, patterns in program_patterns.items():
                if any(re.search(pattern, text) for pattern in patterns):
                    programs.append(value)

        if programs:
            metadata["program_type"] = _join_metadata_values(
                programs
            )

        # A rate table may contain more than one plan.
        # Store both the legacy short plan_type and the exact insurance_plan
        # used by Student Profile so retrieval does not need to infer it later.
        plan_types = []
        insurance_plans = []

        if (
            "personal choice high option plan" in text
            or "ppo high plan" in text
        ):
            plan_types.append("High Option")
            insurance_plans.append(
                "Personal Choice High Option Plan"
            )

        if (
            "personal choice deductible plan" in text
            or "ppo deductible plan" in text
        ):
            plan_types.append("Deductible")
            insurance_plans.append(
                "Personal Choice Deductible Plan"
            )

        if plan_types:
            metadata["plan_type"] = _join_metadata_values(
                plan_types
            )

        if insurance_plans:
            metadata["insurance_plan"] = _join_metadata_values(
                insurance_plans
            )

        # Coverage metadata comes only from explicit table/header wording.
        # Do not infer personal coverage from generic mentions elsewhere.
        insurance_coverages = []

        coverage_patterns = {
            "student coverage": "Student Coverage",
            "student & child or student & spouse coverage":
                "Student & Child or Student & Spouse Coverage",
            "student and child or student and spouse coverage":
                "Student & Child or Student & Spouse Coverage",
            "student & children/student, spouse & child coverage":
                "Student & Children/Student, Spouse & Child Coverage",
            "student and children/student, spouse and child coverage":
                "Student & Children/Student, Spouse & Child Coverage",
            "family/student, spouse & children coverage":
                "Family/Student, Spouse & Children Coverage",
            "family/student, spouse and children coverage":
                "Family/Student, Spouse & Children Coverage",
        }

        for keyword, value in coverage_patterns.items():
            if keyword in text:
                insurance_coverages.append(value)

        if insurance_coverages:
            metadata["insurance_coverage"] = _join_metadata_values(
                insurance_coverages
            )

    # ---------------------------------------------------------
    # International Students
    # ---------------------------------------------------------
    elif category == "International Students":

        visa_statuses = []

        if re.search(r"\bf-?1\b", text):
            visa_statuses.append("F-1")

        if re.search(r"\bj-?1\b", text):
            visa_statuses.append("J-1")

        if visa_statuses:
            metadata["visa_status"] = _join_metadata_values(
                visa_statuses
            )

        levels = []

        if re.search(r"\bundergraduate\b", text):
            levels.append("Undergraduate")

        if re.search(r"\bgraduate\b", text):
            levels.append("Graduate")

        if levels:
            metadata["student_level"] = _join_metadata_values(
                levels
            )

        stages = []

        # Only assign OPT/STEM OPT when the chunk is actually scoped to
        # students in that stage. A generic mention of OPT in a list of
        # employment options should not turn the whole chunk into OPT-specific
        # metadata.
        stem_opt_scope_patterns = [
            r"\bstem opt student(?:s)?\b",
            r"\bstudent(?:s)?\s+(?:currently\s+)?on\s+stem opt\b",
            r"\bwhile\s+on\s+stem opt\b",
            r"\bparticipating\s+in\s+stem opt\b",
            r"\bon\s+stem opt\b",
        ]

        opt_scope_patterns = [
            r"\bopt student(?:s)?\b",
            r"\bstudent(?:s)?\s+(?:currently\s+)?on\s+(?:post-completion\s+)?opt\b",
            r"\bwhile\s+on\s+(?:post-completion\s+)?opt\b",
            r"\bparticipating\s+in\s+(?:post-completion\s+)?opt\b",
            r"\bon\s+post-completion\s+opt\b",
            r"\btravel\s+while\s+on\s+opt\b",
        ]

        if any(
            re.search(pattern, text)
            for pattern in stem_opt_scope_patterns
        ):
            stages.append("STEM OPT")

        elif any(
            re.search(pattern, text)
            for pattern in opt_scope_patterns
        ):
            stages.append("OPT")

        if (
            "new student" in text
            or "new students" in text
        ):
            stages.append("New")

        if (
            "transfer student" in text
            or "transfer students" in text
            or "transferring" in text
        ):
            stages.append("Transfer")

        if (
            "current student" in text
            or "current students" in text
        ):
            stages.append("Current")

        if stages:
            metadata["student_stage"] = _join_metadata_values(
                stages
            )

    # ---------------------------------------------------------
    # Tuition & Payment
    # ---------------------------------------------------------
    elif category in (
        "Tuition&Payment",
        "Tuition & Payment",
    ):

        semester_match = re.search(
            r"(Fall|Spring|Summer 1|Summer 2)\s+20\d{2}",
            content,
            flags=re.I,
        )

        if semester_match:
            metadata["semester"] = semester_match.group(0)

        levels = []

        if re.search(r"\bundergraduate\b", text):
            levels.append("Undergraduate")

        if re.search(r"\bgraduate\b", text):
            levels.append("Graduate")

        if levels:
            metadata["student_level"] = _join_metadata_values(
                levels
            )

        residency = []

        if "pennsylvania resident" in text:
            residency.append("Pennsylvania")

        if (
            "out-of-state" in text
            or "non-pennsylvania" in text
        ):
            residency.append("Out-of-State")

        if residency:
            metadata["residency"] = _join_metadata_values(
                residency
            )

    return metadata


def chunk_text(text, chunk_size=650, overlap=120):
    """Chunk normal text on paragraph boundaries with overlap."""

    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError(
            "chunk_size must be positive and overlap must be smaller than it"
        )

    raw_blocks = [
        block.strip()
        for block in text.split("\n\n")
        if block.strip()
    ]

    chunks = []
    current_units = []
    current_len = 0

    for block in raw_blocks:
        block_len = len(block)

        if block_len > chunk_size:
            lines = [
                line.strip()
                for line in block.split("\n")
                if line.strip()
            ]

            for line in lines:
                line_len = len(line)
                separator_len = 2 if current_units else 0

                if (
                    current_len
                    + separator_len
                    + line_len
                    <= chunk_size
                ):
                    current_units.append(line)
                    current_len += (
                        separator_len
                        + line_len
                    )

                else:
                    if current_units:
                        chunks.append(
                            "\n\n".join(current_units)
                        )

                    current_units = [line]
                    current_len = line_len

            continue

        separator_len = 2 if current_units else 0

        if (
            current_len
            + separator_len
            + block_len
            <= chunk_size
        ):
            current_units.append(block)
            current_len += (
                separator_len
                + block_len
            )

        else:
            if current_units:
                chunks.append(
                    "\n\n".join(current_units)
                )

            overlap_units = []
            overlap_len = 0

            for previous_block in reversed(
                current_units
            ):
                added_len = (
                    len(previous_block)
                    + (2 if overlap_units else 0)
                )

                if (
                    overlap_len
                    + added_len
                    <= overlap
                ):
                    overlap_units.insert(
                        0,
                        previous_block
                    )
                    overlap_len += added_len

                else:
                    break

            current_units = (
                overlap_units
                + [block]
            )

            current_len = sum(
                len(item)
                for item in current_units
            )

            current_len += (
                2
                * (len(current_units) - 1)
            )

    if current_units:
        chunks.append(
            "\n\n".join(current_units)
        )

    return chunks


# ---------------------------------------------------------
# Structured crawler files
# ---------------------------------------------------------

def chunk_table_text(text, chunk_size=650, overlap=120):
    chunks = []

    parts = re.split(
        r"(\[TABLE RECORD\].*?\[/TABLE RECORD\])",
        text,
        flags=re.S,
    )

    for part in parts:
        if part.startswith("[TABLE RECORD]"):
            chunks.append(
                part
                .replace("[TABLE RECORD]", "")
                .replace("[/TABLE RECORD]", "")
                .strip()
            )

        elif part.strip():
            chunks.extend(
                chunk_text(
                    part,
                    chunk_size,
                    overlap,
                )
            )

    return chunks


def chunk_structured_text(text):
    """
    Chunk structured crawler files by record
    while preserving nearby section context.
    """

    records = [
        record.strip()
        for record in text.split("\n\n")
        if record.strip()
    ]

    chunks = []
    current_section = None

    for record in records:
        lines = record.splitlines()
        first_line = lines[0].strip()

        if first_line.startswith(
            ("Section:", "Campus:")
        ):
            current_section = first_line

            chunks.append(record)
            continue

        if current_section:
            content = (
                f"{current_section}\n\n"
                f"{record}"
            )
        else:
            content = record

        chunks.append(content)

    return chunks


# ---------------------------------------------------------
# Academic Calendar
# ---------------------------------------------------------

def chunk_academic_calendar(text):
    """
    Chunk Academic Calendar records while
    preserving semester context.
    """

    records = [
        record.strip()
        for record in text.split("\n\n")
        if record.strip()
    ]

    chunks = []
    current_semester = None

    for record in records:
        lines = record.splitlines()
        first_line = lines[0].strip()

        semester = first_line.removeprefix(
            "Section: "
        )

        if semester.startswith(
            (
                "Fall ",
                "Spring ",
                "Summer I ",
                "Summer II ",
            )
        ):
            current_semester = semester
            continue

        if first_line == "Table:":
            rows = [
                row.strip()
                for row in lines[1:]
                if row.strip()
            ]

            final_exam_rows = [
                row
                for row in rows
                if "Final Exams" in row
            ]

            if final_exam_rows:
                chunks.append(
                    f"Semester: {current_semester}\n\n"
                    "Final Exam Schedule:\n"
                    + "\n".join(
                        final_exam_rows
                    )
                )

            for row in rows:
                if row in final_exam_rows:
                    continue

                chunks.append(
                    f"Semester: "
                    f"{current_semester}\n\n"
                    f"{row}"
                )

            continue

        if current_semester:
            content = (
                f"Semester: "
                f"{current_semester}\n\n"
                f"{record}"
            )
        else:
            content = record

        chunks.append(content)

    return chunks


# ---------------------------------------------------------
# Convert documents into chunks
# ---------------------------------------------------------

def chunk_documents(
    documents,
    chunk_size=650,
    overlap=120
):
    """Convert source documents into retrieval chunks."""

    all_chunks = []

    for document in documents:
        document_name = document[
            "document_name"
        ]

        document_label = (
            document_name
            .removesuffix(".txt")
            .replace("_", " ")
            .title()
        )

        context_header = (
            f"[Topic: "
            f"{document['category']} | "
            f"Document: "
            f"{document_label}]\n\n"
        )

        if (
            document["category"]
            == "Academic Calendar"
            and document_name.endswith(
                "_structured.txt"
            )
        ):
            raw_chunks = (
                chunk_academic_calendar(
                    document["content"]
                )
            )

        elif document_name.endswith(
            "_structured.txt"
        ):
            raw_chunks = (
                chunk_structured_text(
                    document["content"]
                )
            )

        else:
            raw_chunks = chunk_table_text(
                document["content"],
                chunk_size=chunk_size,
                overlap=overlap,
            )

        for chunk_index, content in enumerate(
            raw_chunks
        ):
            personalized_metadata = extract_metadata(
                content,
                document,
            )

            all_chunks.append({
                "content":
                    context_header
                    + content,

                "source":
                    document["source"],

                "category":
                    document["category"],

                "document_name":
                    document[
                        "document_name"
                    ],

                "chunk_id":
                    chunk_index,

                **personalized_metadata,
            })

    return all_chunks