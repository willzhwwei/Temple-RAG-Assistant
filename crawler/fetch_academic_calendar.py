import requests

from bs4 import BeautifulSoup
from pathlib import Path


# --------------------------------------------------
# 1. Temple University Academic Calendar websites
# --------------------------------------------------
# The current and upcoming calendars are included because dates and
# deadlines change by academic year.
PAGES = {
    "academic_calendar_overview": {
        "url": "https://registrar.temple.edu/academic-calendar",
        "category": "Academic Calendar",
        "academic_year": "Current and future academic years",
        "topic": "Academic calendar overview and important dates",
    },
    "academic_calendar_2025_2026": {
        "url": "https://registrar.temple.edu/2025-2026-academic-calendar",
        "category": "Academic Calendar",
        "academic_year": "2025-2026",
        "topic": "2025-2026 academic calendar dates and deadlines",
    },
    "academic_calendar_2026_2027": {
        "url": "https://registrar.temple.edu/academic-calendar/2026-2027-academic-calendar",
        "category": "Academic Calendar",
        "academic_year": "2026-2027",
        "topic": "2026-2027 academic calendar dates and deadlines",
    },
    "academic_calendar_guidelines": {
        "url": "https://registrar.temple.edu/academic-calendar-guidelines",
        "category": "Academic Calendar",
        "academic_year": "General guidance",
        "topic": "Academic calendar guidelines and term rules",
    },
}


# --------------------------------------------------
# 2. Settings
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "scraped_data/Academic Calendar"
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
    """Normalize whitespace and remove Temple placeholder text."""
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("[click-for-email]", "")
    return " ".join(text.split()).strip()


def is_noise_line(text):
    """Return True for common Temple navigation and template text."""
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

    return normalized in exact_noise or normalized.startswith("Copyright ")


def add_blank(lines):
    """Add one blank line without creating repeated blank lines."""
    if lines and lines[-1] != "":
        lines.append("")


def save_text_file(output_file, lines, label):
    """Save text while removing repeated blank lines."""
    cleaned = []

    for line in lines:
        line = line.rstrip()
        if line == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(line)

    with open(output_file, "w", encoding="utf-8") as file:
        file.write("\n".join(cleaned).strip() + "\n")

    print(f"Saved {label}: {output_file}")


# --------------------------------------------------
# 4. Remove webpage noise and extract useful content
# --------------------------------------------------
def remove_noise(soup):
    """Remove navigation and other page sections that are not useful for RAG."""
    for tag in soup([
        "script", "style", "nav", "footer", "header", "form", "aside",
        "noscript", "svg",
    ]):
        tag.decompose()

    for selector in [
        ".breadcrumb", ".breadcrumbs", ".search-form", ".site-footer",
        ".footer", ".pager", ".pagination", ".region-sidebar-first",
        ".region-sidebar-second", "[aria-label='breadcrumb']",
    ]:
        for element in soup.select(selector):
            element.decompose()


def get_main_content(soup):
    """Prefer the page's main content, with safe fallbacks."""
    return soup.find("main") or soup.find("article") or soup.body


def extract_content_items(soup):
    """Extract headings, paragraphs, list items, and tables in page order."""
    remove_noise(soup)
    main_content = get_main_content(soup)

    if not main_content:
        return []

    extracted = []
    elements = main_content.find_all([
        "h1", "h2", "h3", "h4", "p", "li", "table",
    ])

    for element in elements:
        if element.name in ["h1", "h2", "h3", "h4"]:
            text = clean_text(element.get_text(" ", strip=True))
            if text and not is_noise_line(text):
                extracted.append(("heading", element.name.upper(), text))

        elif element.name == "p":
            if element.find_parent("li") or element.find_parent("table"):
                continue
            text = clean_text(element.get_text(" ", strip=True))
            if text and not is_noise_line(text):
                extracted.append(("paragraph", None, text))

        elif element.name == "li":
            if element.find_parent("li"):
                continue
            text = clean_text(element.get_text(" ", strip=True))
            if not text or is_noise_line(text):
                continue

            if element.parent and element.parent.name == "ol":
                items = element.parent.find_all("li", recursive=False)
                extracted.append(("ordered_item", items.index(element) + 1, text))
            else:
                extracted.append(("bullet", None, text))

        elif element.name == "table":
            rows = []
            for row in element.find_all("tr"):
                values = [
                    clean_text(cell.get_text(" ", strip=True))
                    for cell in row.find_all(["th", "td"])
                ]
                values = [value for value in values if value]
                if values:
                    rows.append(" | ".join(values))
            if rows:
                extracted.append(("table", None, rows))

    # Some page templates repeat adjacent content. Keep one copy.
    deduplicated = []
    previous_item = None
    for item in extracted:
        if item == previous_item:
            continue
        deduplicated.append(item)
        previous_item = item

    return deduplicated


# --------------------------------------------------
# 5. Build raw and RAG-friendly text files
# --------------------------------------------------
def build_raw_lines(filename, url, content_items):
    lines = [
        f"Title: Temple University Academic Calendar - {filename.replace('_', ' ').title()}",
        "", "Source:", url, "",
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


def build_structured_lines(page_info, content_items):
    """Add consistent metadata and section labels for better RAG retrieval."""
    topic = page_info["topic"]
    lines = [
        f"Title: Temple University - {topic}",
        "", "Source:", page_info["url"], "",
        f"Category: {page_info['category']}",
        f"Academic Year: {page_info['academic_year']}",
        f"Topic: {topic}",
        "Audience: Temple University students", "",
    ]

    current_heading = None
    for kind, extra, value in content_items:
        if kind == "heading":
            if extra == "H1" and value.lower() in topic.lower():
                continue
            if value != current_heading:
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
# 6. Fetch one Academic Calendar webpage
# --------------------------------------------------
def fetch_page(filename, page_info):
    requested_url = page_info["url"]
    print("\n" + "=" * 70)
    print(f"Fetching: {requested_url}")

    try:
        response = requests.get(
            requested_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Record the final URL when Temple redirects an older page.
        final_url = response.url
        page_info = dict(page_info)
        page_info["url"] = final_url

        content_items = extract_content_items(
            BeautifulSoup(response.text, "html.parser")
        )
        if not content_items:
            print(f"No useful text found: {final_url}")
            return False

        save_text_file(
            OUTPUT_DIR / f"{filename}.txt",
            build_raw_lines(filename, final_url, content_items),
            "raw webpage",
        )
        save_text_file(
            OUTPUT_DIR / f"{filename}_structured.txt",
            build_structured_lines(page_info, content_items),
            "structured webpage",
        )

        if final_url.rstrip("/") != requested_url.rstrip("/"):
            print(f"Redirected to: {final_url}")
        return True

    except requests.RequestException as error:
        print(f"Failed to fetch: {requested_url}")
        print(f"Error: {error}")
        return False
    except Exception as error:
        print(f"Unexpected error: {requested_url}")
        print(f"Error: {error}")
        return False


# --------------------------------------------------
# 7. Fetch all Academic Calendar pages
# --------------------------------------------------
def fetch_all_academic_calendar_pages():
    successful = 0
    failed = []

    for filename, page_info in PAGES.items():
        if fetch_page(filename, page_info):
            successful += 1
        else:
            failed.append(filename)

    print("\n" + "=" * 70)
    print("Academic Calendar data collection summary")
    print(f"Successful: {successful}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failed pages:")
        for filename in failed:
            print(f"- {filename}")


if __name__ == "__main__":
    fetch_all_academic_calendar_pages()
    print("\n" + "=" * 70)
    print("All Temple University academic calendar data collection finished.")
    print(f"Files saved to: {OUTPUT_DIR}")
    print(f"Absolute output path: {OUTPUT_DIR.resolve()}")
