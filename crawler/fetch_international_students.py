import requests

from bs4 import BeautifulSoup
from pathlib import Path


# --------------------------------------------------
# 1. Temple University International Student websites
# --------------------------------------------------
# Each page includes metadata that will also be written into the
# structured text file. This helps RAG distinguish similar rules
# (for example F-1 vs J-1, CPT vs OPT, current vs future students).
PAGES = {
    # --------------------------------------------------
    # ISSS / General
    # --------------------------------------------------
    "isss_overview": {
        "url": "https://global.temple.edu/isss",
        "category": "ISSS General",
        "visa_status": "F-1 and J-1",
        "topic": "International Student and Scholar Services overview",
    },
    "student_resources": {
        "url": "https://global.temple.edu/isss/student-resources",
        "category": "ISSS General",
        "visa_status": "F-1 and J-1",
        "topic": "International student resources",
    },
    "office_hours_appointments": {
        "url": "https://global.temple.edu/isss/about-isss/office-hours-and-appointments",
        "category": "ISSS Contact",
        "visa_status": "F-1 and J-1",
        "topic": "ISSS office hours, walk-ins, and appointments",
    },
    "current_students": {
        "url": "https://global.temple.edu/isss/students/current-students",
        "category": "Current Students",
        "visa_status": "F-1 and J-1",
        "topic": "Current international student resources",
    },
    "general_student_information": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/general-student-information",
        "category": "Current Students",
        "visa_status": "F-1 and J-1",
        "topic": "General student information",
    },

    # --------------------------------------------------
    # Future / New International Students
    # --------------------------------------------------
    "future_students": {
        "url": "https://global.temple.edu/isss/student-resources/future-students",
        "category": "Future Students",
        "visa_status": "F-1 and J-1",
        "topic": "Future international student requirements",
    },
    "certificate_eligibility_application": {
        "url": "https://global.temple.edu/isss/student-resources/future-students/certificate-eligibility-application-process",
        "category": "I-20 and DS-2019",
        "visa_status": "F-1 and J-1",
        "topic": "Certificate of Eligibility application process",
    },
    "i20_ds2019_faq": {
        "url": "https://global.temple.edu/isss/student-resources/future-students/i-20ds-2019-faq",
        "category": "I-20 and DS-2019",
        "visa_status": "F-1 and J-1",
        "topic": "I-20 and DS-2019 frequently asked questions",
    },
    "financial_documentation": {
        "url": "https://global.temple.edu/isss/student-resources/future-students/certificate-eligibility-i-20-ds-2019-application-process/financial-documentation",
        "category": "I-20 and DS-2019",
        "visa_status": "F-1 and J-1",
        "topic": "Financial documentation for I-20 or DS-2019",
    },
    "report_arrival": {
        "url": "https://global.temple.edu/isss/student-resources/future-students/report-your-arrival",
        "category": "New Student Arrival",
        "visa_status": "F-1 and J-1",
        "topic": "Reporting arrival in Philadelphia",
    },

    # --------------------------------------------------
    # F-1 Status / Maintaining Legal Status
    # --------------------------------------------------
    "maintaining_f1_status": {
        "url": "https://global.temple.edu/isss/students/current-students/f-1-student/maintaining-f-1-status",
        "category": "F-1 Status",
        "visa_status": "F-1",
        "topic": "Maintaining legal F-1 student status",
    },
    "part_time_enrollment": {
        "url": "https://global.temple.edu/isss/students/current-students/f-1-student/maintaining-legal-status/part-time-enrollment",
        "category": "F-1 Status",
        "visa_status": "F-1",
        "topic": "Part-time enrollment and Reduced Course Load",
    },
    "medical_reduced_course_load": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/maintaining-legal-status/part-time-enrollment/reduced-course-load-rcl-based-medical-condition",
        "category": "F-1 Status",
        "visa_status": "F-1 and J-1",
        "topic": "Medical Reduced Course Load",
    },
    "i20_program_extension": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/maintaining-legal-status/what-do-when-your-i-20-expiring",
        "category": "F-1 Status",
        "visa_status": "F-1",
        "topic": "I-20 expiration and program extension",
    },
    "change_academic_level": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/maintaining-legal-status/change-academic-level",
        "category": "F-1 Status",
        "visa_status": "F-1",
        "topic": "Change of academic level and I-20 update",
    },
    "f1_reinstatement": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/maintaining-legal-status/f-1-student-reinstatement-process",
        "category": "F-1 Status",
        "visa_status": "F-1",
        "topic": "F-1 reinstatement process",
    },
    "sevis_transfer_from_temple": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/transferring-temple-another-school",
        "category": "SEVIS Transfer",
        "visa_status": "F-1 and J-1",
        "topic": "Transferring SEVIS record from Temple to another school",
    },

    # --------------------------------------------------
    # F-1 Employment
    # --------------------------------------------------
    "f1_student_employment": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/f-1-student-employment",
        "category": "Employment",
        "visa_status": "F-1",
        "topic": "F-1 student employment rules",
    },
    "cpt": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/f-1-employment-options/curricular-practical-training-cpt",
        "category": "Employment",
        "visa_status": "F-1",
        "topic": "Curricular Practical Training (CPT)",
    },
    "opt": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/f-1-employment-options/optional-practical-training-opt",
        "category": "Employment",
        "visa_status": "F-1",
        "topic": "Optional Practical Training (OPT) overview",
    },
    "pre_completion_opt": {
        "url": "https://global.temple.edu/isss/students/current-students/f-1-student/f-1-employment-options/campus-employment/optional-practical-training-opt/pre-completion-opt",
        "category": "Employment",
        "visa_status": "F-1",
        "topic": "Pre-completion Optional Practical Training",
    },
    "post_completion_opt": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/f-1-employment-options/optional-practical-training-opt/post-completion-opt",
        "category": "Employment",
        "visa_status": "F-1",
        "topic": "Post-completion Optional Practical Training",
    },
    "stem_opt_extension": {
        "url": "https://global.temple.edu/isss/students/current-students/f-1-student/f-1-employment-options/employment-comparisons/optional-practical-training-opt/stem-opt-extension",
        "category": "Employment",
        "visa_status": "F-1",
        "topic": "24-month STEM OPT extension",
    },
    "opt_faq": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/f-1-student/f-1-employment-options/optional-practical-training-opt/optional-practical-training-frequently-asked-questions",
        "category": "Employment",
        "visa_status": "F-1",
        "topic": "Optional Practical Training frequently asked questions",
    },

    # --------------------------------------------------
    # Travel / Re-entry
    # --------------------------------------------------
    "travel_reentry_us": {
        "url": "https://global.temple.edu/isss/student-resources/current-students/travel-reentry-us",
        "category": "Travel and Re-entry",
        "visa_status": "F-1 and J-1",
        "topic": "International student travel and re-entry to the United States",
    },

    # --------------------------------------------------
    # Beyond Immigration
    # --------------------------------------------------
    "social_security_number": {
        "url": "https://global.temple.edu/isss/students/current-students/beyond-immigration-student-information/applying-social-security-number-f-1-and-j-1-students-only",
        "category": "General Student Information",
        "visa_status": "F-1 and J-1",
        "topic": "Applying for a Social Security Number",
    },
    "dependents": {
        "url": "https://global.temple.edu/isss/students/current-students/beyond-immigration-student-information/dependents",
        "category": "Dependents",
        "visa_status": "F-1 and J-1",
        "topic": "F-2 and J-2 dependents",
    },

    # --------------------------------------------------
    # J-1 Student
    # --------------------------------------------------
    "maintaining_j1_student_status": {
        "url": "https://global.temple.edu/isss/students/current-students/j-1-student/maintaining-j-1-student-status",
        "category": "J-1 Status",
        "visa_status": "J-1",
        "topic": "Maintaining J-1 student status",
    },
}


# --------------------------------------------------
# 2. Settings
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "scraped_data/International Students"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Output directory: {OUTPUT_DIR.resolve()}")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 20


# --------------------------------------------------
# 3. Small helpers
# --------------------------------------------------
def clean_text(text):
    """Normalize whitespace and remove Temple email placeholder text."""
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("[click-for-email]", "")
    text = " ".join(text.split())

    return text.strip()


def is_noise_line(text):
    """Return True for common Temple template/navigation noise."""
    normalized = clean_text(text)

    if not normalized:
        return True

    exact_noise = {
        "Search Keywords",
        "Search",
        "Skip to main content",
        "Link to Temple University website",
        "Cherry & White Directory",
        "Maps & Directions",
        "Privacy Policy",
        "Accessibility",
        "Careers at Temple",
        "TUportal",
        "TUmail",
    }

    if normalized in exact_noise:
        return True

    if normalized.startswith("Copyright "):
        return True

    return False


def add_blank(lines):
    if lines and lines[-1] != "":
        lines.append("")


def remove_repeated_blank_lines(lines):
    cleaned = []

    for line in lines:
        line = line.rstrip()

        if line == "" and cleaned and cleaned[-1] == "":
            continue

        cleaned.append(line)

    return cleaned


def save_text_file(output_file, lines, label="file"):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cleaned = remove_repeated_blank_lines(lines)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned).strip() + "\n")

    print(f"Saved {label}: {output_file}")


# --------------------------------------------------
# 4. Remove webpage noise
# --------------------------------------------------
def remove_noise(soup):
    # Remove HTML elements that are not useful for RAG.
    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "form",
        "aside",
        "noscript",
        "svg",
    ]):
        tag.decompose()

    # Temple pages may also place navigation / search content inside divs.
    # These selectors remove common webpage chrome without touching the
    # article/main content.
    noise_selectors = [
        ".breadcrumb",
        ".breadcrumbs",
        ".search-form",
        ".site-footer",
        ".footer",
        ".pager",
        ".pagination",
        ".region-sidebar-first",
        ".region-sidebar-second",
        "[aria-label='breadcrumb']",
    ]

    for selector in noise_selectors:
        for element in soup.select(selector):
            element.decompose()


# --------------------------------------------------
# 5. Get main content
# --------------------------------------------------
def get_main_content(soup):
    # Temple currently uses a <main> area for primary page content.
    main_content = soup.find("main")

    if not main_content:
        main_content = soup.find("article")

    if not main_content:
        main_content = soup.body

    return main_content


# --------------------------------------------------
# 6. Convert webpage into clean RAG-friendly lines
# --------------------------------------------------
def extract_content_lines(soup):
    """
    Extract headings, paragraphs, ordered/unordered list items and tables.

    Heading markers are kept internally so the structured output can label
    sections. The raw output removes those markers and stays human-readable.
    """
    remove_noise(soup)
    main_content = get_main_content(soup)

    if not main_content:
        return []

    extracted = []

    elements = main_content.find_all([
        "h1",
        "h2",
        "h3",
        "h4",
        "p",
        "li",
        "table",
    ])

    for element in elements:
        # ------------------------------
        # Heading
        # ------------------------------
        if element.name in ["h1", "h2", "h3", "h4"]:
            text = clean_text(element.get_text(" ", strip=True))

            if text and not is_noise_line(text):
                level = element.name.upper()
                extracted.append(("heading", level, text))

        # ------------------------------
        # Paragraph
        # ------------------------------
        elif element.name == "p":
            # Paragraph text inside a list/table will be captured there.
            if element.find_parent("li") or element.find_parent("table"):
                continue

            text = clean_text(element.get_text(" ", strip=True))

            if text and not is_noise_line(text):
                extracted.append(("paragraph", None, text))

        # ------------------------------
        # List item
        # ------------------------------
        elif element.name == "li":
            # Skip nested list items here; they are included in the outer text
            # only when appropriate. Direct child items are cleaner for RAG.
            if element.find_parent("li"):
                continue

            text = clean_text(element.get_text(" ", strip=True))

            if not text or is_noise_line(text):
                continue

            parent = element.parent

            if parent and parent.name == "ol":
                direct_items = parent.find_all("li", recursive=False)
                try:
                    number = direct_items.index(element) + 1
                except ValueError:
                    number = 1

                extracted.append(("ordered_item", number, text))
            else:
                extracted.append(("bullet", None, text))

        # ------------------------------
        # Table
        # ------------------------------
        elif element.name == "table":
            table_rows = []

            for row in element.find_all("tr"):
                cells = row.find_all(["th", "td"])
                values = [
                    clean_text(cell.get_text(" ", strip=True))
                    for cell in cells
                ]
                values = [value for value in values if value]

                if values:
                    table_rows.append(" | ".join(values))

            if table_rows:
                extracted.append(("table", None, table_rows))

    # Remove consecutive duplicate entries caused by some Temple page layouts.
    deduplicated = []
    previous_key = None

    for item in extracted:
        kind, extra, value = item
        key_value = tuple(value) if isinstance(value, list) else value
        key = (kind, extra, key_value)

        if key == previous_key:
            continue

        deduplicated.append(item)
        previous_key = key

    return deduplicated


# --------------------------------------------------
# 7. Create clean raw webpage text
# --------------------------------------------------
def build_raw_lines(filename, url, content_items):
    lines = [
        f"Title: Temple University International Student - {filename.replace('_', ' ').title()}",
        "",
        "Source:",
        url,
        "",
    ]

    for kind, extra, value in content_items:
        if kind == "heading":
            add_blank(lines)
            lines.append(value)
            add_blank(lines)

        elif kind == "paragraph":
            lines.append(value)

        elif kind == "bullet":
            lines.append(f"- {value}")

        elif kind == "ordered_item":
            lines.append(f"{extra}. {value}")

        elif kind == "table":
            add_blank(lines)
            lines.extend(value)
            add_blank(lines)

    return lines


# --------------------------------------------------
# 8. Create structured RAG text
# --------------------------------------------------
def build_structured_lines(filename, page_info, content_items):
    """
    Create one structured file per webpage.

    This is still part of the crawler/data-cleaning stage. It does not chunk,
    embed, query ChromaDB, or call an LLM.
    """
    url = page_info["url"]
    category = page_info["category"]
    visa_status = page_info["visa_status"]
    topic = page_info["topic"]

    lines = [
        f"Title: Temple University - {topic}",
        "",
        "Source:",
        url,
        "",
        f"Category: {category}",
        f"Visa Status: {visa_status}",
        f"Topic: {topic}",
        "Audience: Temple University international students",
        "",
    ]

    current_heading = None

    for kind, extra, value in content_items:
        if kind == "heading":
            # The site's H1 often repeats the page title. Keep later headings
            # as explicit Section labels because they are valuable for RAG.
            normalized_title = topic.lower().replace("-", " ")
            normalized_heading = value.lower().replace("-", " ")

            if extra == "H1" and (
                normalized_heading in normalized_title
                or normalized_title in normalized_heading
            ):
                continue

            if value == current_heading:
                continue

            add_blank(lines)
            lines.append(f"Section: {value}")
            current_heading = value

        elif kind == "paragraph":
            lines.append(value)

        elif kind == "bullet":
            lines.append(f"- {value}")

        elif kind == "ordered_item":
            lines.append(f"Step {extra}: {value}")

        elif kind == "table":
            add_blank(lines)
            lines.append("Table:")
            lines.extend(value)
            add_blank(lines)

    return lines


# --------------------------------------------------
# 9. Fetch one International Student webpage
# --------------------------------------------------
def fetch_page(filename, page_info):
    url = page_info["url"]

    print("\n" + "=" * 70)
    print(f"Fetching: {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Use the final redirected URL as the source if Temple redirects
        # an older page path to a newer page path.
        final_url = response.url
        page_info = dict(page_info)
        page_info["url"] = final_url

        soup = BeautifulSoup(response.text, "html.parser")
        content_items = extract_content_lines(soup)

        if not content_items:
            print(f"No useful text found: {final_url}")
            return False

        # Clean raw page for manual inspection.
        raw_lines = build_raw_lines(
            filename,
            final_url,
            content_items,
        )
        save_text_file(
            OUTPUT_DIR / f"{filename}.txt",
            raw_lines,
            "raw webpage",
        )

        # RAG-friendly structured version.
        structured_lines = build_structured_lines(
            filename,
            page_info,
            content_items,
        )
        save_text_file(
            OUTPUT_DIR / f"{filename}_structured.txt",
            structured_lines,
            "structured webpage",
        )

        if final_url.rstrip("/") != url.rstrip("/"):
            print(f"Redirected to: {final_url}")

        return True

    except requests.RequestException as e:
        print(f"Failed to fetch: {url}")
        print(f"Error: {e}")
        return False

    except Exception as e:
        print(f"Unexpected error: {url}")
        print(f"Error: {e}")
        return False


# --------------------------------------------------
# 10. Fetch all International Student pages
# --------------------------------------------------
def fetch_all_international_student_pages():
    successful = 0
    failed = []

    for filename, page_info in PAGES.items():
        if fetch_page(filename, page_info):
            successful += 1
        else:
            failed.append(filename)

    print("\n" + "=" * 70)
    print("International Student data collection summary")
    print(f"Successful: {successful}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("Failed pages:")
        for filename in failed:
            print(f"- {filename}")


# --------------------------------------------------
# 11. Run
# --------------------------------------------------
if __name__ == "__main__":
    fetch_all_international_student_pages()

    print("\n" + "=" * 70)
    print("All Temple University international student data collection finished.")
    print(f"Files saved to: {OUTPUT_DIR}")
    print(f"Absolute output path: {OUTPUT_DIR.resolve()}")
