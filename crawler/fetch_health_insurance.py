import requests

from bs4 import BeautifulSoup
from pathlib import Path


# --------------------------------------------------
# 1. Temple University Student Health Insurance websites
# --------------------------------------------------
# Keep the filenames consistent with the health-insurance files already
# used by the Temple RAG project. Each page also has simple metadata that
# is written to the structured version for easier retrieval.
PAGES = {
    "student_health_insurance": {
        "url": "https://careers.temple.edu/hr-resources/our-functional-areas/benefits-administration/health-insurance-plans/student-health-0",
        "category": "Student Health Insurance",
        "student_group": "Undergraduate, Graduate, Law, Medical, Podiatric, Dental, Pharmacy, International, and eligible graduate assistants",
        "topic": "Student health insurance classifications and enrollment process",
    },

    "student_health_insurance_plan": {
        "url": "https://careers.temple.edu/hr-resources/our-functional-areas/benefits-administration/health-insurance-plans/student-health",
        "category": "Student Health Insurance",
        "student_group": "Eligible Temple University students",
        "topic": "Student health insurance plan, enrollment periods, and coverage dates",
    },

    "health_insurance_plan_options": {
        "url": "https://careers.temple.edu/our-functional-areas/employee-benefits/student-health-insurance/plan-options",
        "category": "Student Health Insurance",
        "student_group": "Eligible Temple University students",
        "topic": "Student health insurance plan options and benefits",
    },

    "health_insurance_monthly_rates": {
        "url": "https://careers.temple.edu/hr-resources/our-functional-areas/employee-benefits/student-health-insurance/monthly-rates",
        "category": "Student Health Insurance",
        "student_group": "Undergraduate, Graduate, Dental, Law, Pharmacy, Medical, Podiatric, International students, and eligible graduate assistants",
        "topic": "Student health insurance monthly rates",
    },

    # International-student-specific Temple ISSS insurance information.
    "international_student_health_insurance": {
        "url": "https://global.temple.edu/isss/student-resources/beyond-immigration-student-information/student-health-insurance",
        "category": "International Student Health Insurance",
        "student_group": "F-1 and J-1 international students",
        "topic": "International student health insurance requirements and enrollment",
    },

    "j1_health_insurance_requirements": {
        "url": "https://global.temple.edu/isss/students/current-students/j-1-student/maintaining-legal-status/j-1-student-health-insurance-requirements",
        "category": "International Student Health Insurance",
        "student_group": "J-1 students and J-2 dependents",
        "topic": "J-1 student health insurance requirements",
    },

    # Helpful supporting Temple page explaining insurance options and why
    # coverage matters when receiving care in Philadelphia.
    "student_health_services_insurance": {
        "url": "https://studenthealth.temple.edu/appointments/health-insurance",
        "category": "Student Health Services",
        "student_group": "Temple University students",
        "topic": "Health insurance options for Temple students",
    },
}


# --------------------------------------------------
# 2. Settings
# --------------------------------------------------
# Build the output path from this file so the crawler works from any
# terminal directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "scraped_data/Health Insurance"
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
    """Normalize whitespace and remove common Temple placeholder text."""
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("[click-for-email]", "")
    text = " ".join(text.split())

    return text.strip()


def is_noise_line(text):
    """Return True for common Temple navigation/template text."""
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
    # Remove webpage elements that are not useful for RAG.
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

    # Temple pages may put breadcrumbs/search/sidebar content inside divs.
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
    main_content = soup.find("main")

    if not main_content:
        main_content = soup.find("article")

    if not main_content:
        main_content = soup.body

    return main_content


# --------------------------------------------------
# 6. Convert webpage into clean RAG-friendly items
# --------------------------------------------------
def extract_content_items(soup):
    """
    Extract headings, paragraphs, ordered/unordered list items and tables.

    The structure is kept so the same page can be saved as:
    1. clean raw text for manual checking
    2. metadata-rich structured text for RAG
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
                extracted.append(("heading", element.name.upper(), text))

        # ------------------------------
        # Paragraph
        # ------------------------------
        elif element.name == "p":
            # List/table text is handled separately to avoid duplicates.
            if element.find_parent("li") or element.find_parent("table"):
                continue

            text = clean_text(element.get_text(" ", strip=True))

            if text and not is_noise_line(text):
                extracted.append(("paragraph", None, text))

        # ------------------------------
        # List item
        # ------------------------------
        elif element.name == "li":
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

    # Remove consecutive duplicate items caused by webpage layouts.
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
        f"Title: Temple University Health Insurance - {filename.replace('_', ' ').title()}",
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
    url = page_info["url"]
    category = page_info["category"]
    student_group = page_info["student_group"]
    topic = page_info["topic"]

    lines = [
        f"Title: Temple University - {topic}",
        "",
        "Source:",
        url,
        "",
        f"Category: {category}",
        f"Student Group: {student_group}",
        f"Topic: {topic}",
        "Audience: Temple University students",
        "",
    ]

    current_heading = None

    for kind, extra, value in content_items:
        if kind == "heading":
            # The H1 normally repeats the page title, so avoid an unnecessary
            # duplicate Section label when it closely matches the topic.
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
# 9. Fetch one Health Insurance webpage
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

        # If Temple redirects an older page, save the final official URL.
        final_url = response.url
        page_info = dict(page_info)
        page_info["url"] = final_url

        soup = BeautifulSoup(response.text, "html.parser")
        content_items = extract_content_items(soup)

        if not content_items:
            print(f"No useful text found: {final_url}")
            return False

        # Clean raw webpage for manual inspection.
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
# 10. Fetch all Health Insurance pages
# --------------------------------------------------
def fetch_all_health_insurance_pages():
    successful = 0
    failed = []

    for filename, page_info in PAGES.items():
        if fetch_page(filename, page_info):
            successful += 1
        else:
            failed.append(filename)

    print("\n" + "=" * 70)
    print("Health Insurance data collection summary")
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
    fetch_all_health_insurance_pages()

    print("\n" + "=" * 70)
    print("All Temple University health insurance data collection finished.")
    print(f"Files saved to: {OUTPUT_DIR}")
    print(f"Absolute output path: {OUTPUT_DIR.resolve()}")
