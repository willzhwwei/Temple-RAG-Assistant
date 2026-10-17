import re
import requests

from bs4 import BeautifulSoup
from pathlib import Path


# --------------------------------------------------
# 1. Temple University Parking-related websites
# --------------------------------------------------
PAGES = {
    "parking_overview":
        "https://campusoperations.temple.edu/parking-services",

    "parking_locations":
        "https://campusoperations.temple.edu/parking-services/garages-lots",

    "parking_rates_overview":
        "https://campusoperations.temple.edu/parking-services/parking-rates",

    "student_parking_rates":
        "https://campusoperations.temple.edu/parking-services/parking-rates/student-parking-rates",

    "faculty_staff_parking_rates":
        "https://campusoperations.temple.edu/parking-services/parking-rates/faculty-staff-parking-rates",

    "visitor_parking_rates":
        "https://campusoperations.temple.edu/parking-services/parking-rates/visitor-parking-rates",

    "parking_faq":
        "https://campusoperations.temple.edu/parking-services/frequently-asked-questions",

    "sign_up_for_parking":
        "https://campusoperations.temple.edu/parking-services/sign-parking",

    "parking_account":
        "https://campusoperations.temple.edu/parking-services/sign-parking/manage-tu-parking-account-privileges",

    "accessible_parking":
        "https://campusoperations.temple.edu/parking-services/accessible-parking",

    "parking_citations":
        "https://campusoperations.temple.edu/parking-services/citations-enforcement",

    "metered_parking":
        "https://campusoperations.temple.edu/parking-services/garages-lots/main-campus-metered-parking",

    "event_parking":
        "https://campusoperations.temple.edu/parking-services/event-parking",

    "parking_office_locations":
        "https://campusoperations.temple.edu/parking-services/parking-services-office-locations"
}


# --------------------------------------------------
# 2. Settings
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "scraped_data/Parking"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# --------------------------------------------------
# 3. Small helpers
# --------------------------------------------------
def clean_text(text):
    if not text:
        return ""

    text = text.replace("[click-for-email]", "")
    text = " ".join(text.split())
    return text.strip()


def clean_bullet(line):
    item = line.lstrip("-").strip()

    if item.lower().startswith("the "):
        item = item[4:]

    return item


def add_blank(lines):
    if lines and lines[-1] != "":
        lines.append("")


def save_structured_file(filename, lines):
    output_file = OUTPUT_DIR / filename

    # Remove repeated blank lines
    cleaned = []
    for line in lines:
        if line == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(line)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned).strip() + "\n")

    print(f"Saved structured file: {output_file}")


# --------------------------------------------------
# 4. Extract clean, RAG-friendly webpage text
# --------------------------------------------------
def extract_main_text(soup):
    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "form",
        "aside",
        "noscript"
    ]):
        tag.decompose()

    main_content = soup.find("main")

    if not main_content:
        main_content = soup.body

    if not main_content:
        return ""

    lines = []

    elements = main_content.find_all([
        "h1",
        "h2",
        "h3",
        "h4",
        "p",
        "li",
        "table"
    ])

    for element in elements:
        # Heading
        if element.name in ["h1", "h2", "h3", "h4"]:
            text = clean_text(element.get_text(" ", strip=True))

            if text:
                lines.append("")
                lines.append(text)
                lines.append("")

        # Paragraph
        elif element.name == "p":
            if element.find_parent("li") or element.find_parent("table"):
                continue

            text = clean_text(element.get_text(" ", strip=True))

            if text:
                lines.append(text)

        # Bullet list
        elif element.name == "li":
            if element.find_parent("li"):
                continue

            text = clean_text(element.get_text(" ", strip=True))

            if text:
                lines.append(f"- {text}")

        # Table
        elif element.name == "table":
            rows = element.find_all("tr")

            for row in rows:
                cells = row.find_all(["th", "td"])
                values = []

                for cell in cells:
                    value = clean_text(cell.get_text(" ", strip=True))

                    if value:
                        values.append(value)

                if values:
                    lines.append(" | ".join(values))

            lines.append("")

    cleaned_lines = []
    previous_line = None

    for line in lines:
        line = line.strip()

        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue

        if line == previous_line:
            continue

        cleaned_lines.append(line)
        previous_line = line

    return "\n".join(cleaned_lines).strip()


# --------------------------------------------------
# 5. Save cleaned raw webpage text
# --------------------------------------------------
def save_webpage_text(filename, url, text):
    output_file = OUTPUT_DIR / f"{filename}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            f"Title: Temple University Parking - "
            f"{filename.replace('_', ' ').title()}\n\n"
        )
        f.write("Source:\n")
        f.write(url + "\n\n")
        f.write(text)

    print(f"Saved webpage: {output_file}")


# --------------------------------------------------
# 6. Student Parking Rates -> structured
# --------------------------------------------------
def create_structured_student_parking(text, url):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    structured = [
        "Title: Temple University Student Parking Rates",
        "",
        "Source:",
        url,
        ""
    ]

    campuses = {
        "Main Campus",
        "Health Sciences Center",
        "Ambler Campus",
        "Temple University Center City (TUCC)"
    }

    parking_types = {
        "Overnight Parking",
        "5-Day Commuter Parking",
        "7-Day Commuter Parking",
        "Flex Parking",
        "Carlisle West Garage Parking",
        "Battersby Lot Parking",
        "Rotation Students",
        "Semester Parking"
    }

    for line in lines:
        if line == "Student Parking Rates":
            continue

        if line in campuses:
            add_blank(structured)
            structured.append(f"Campus: {line}")
            add_blank(structured)
            continue

        if line in parking_types:
            add_blank(structured)
            structured.append(f"Parking Type: {line}")
            continue

        if line.startswith("Parking for $"):
            price = (
                line
                .replace("Parking for ", "")
                .replace(" is available in:", "")
            )
            structured.append(f"Price: {price}")
            structured.append("Available Locations:")
            continue

        # Flex details. Price was already captured above.
        if (
            "$13 per entry" in line
            and "Valid 7:00 AM to 10:45 PM" in line
        ):
            structured.append(
                "Valid Hours: Monday-Friday, 7:00 AM-10:45 PM"
            )
            structured.append(
                "Overnight Parking: Not permitted"
            )
            structured.append(
                "Payment Method: Temple ID or Mobile OWLcard"
            )
            structured.append(
                "Parking Account: Funds must be added before use"
            )
            structured.append(
                "Insufficient Funds: Regular hourly or daily rate may apply"
            )
            continue

        if "renew their parking semi-annually" in line.lower():
            structured.append("Renewal: July and January")
            continue

        if line.startswith("$426 per semester"):
            structured.append("Price: $426 per semester")
            continue

        if line.startswith("$266 per semester"):
            structured.append("Price: $266 per semester")
            continue

        if "$110 per month" in line:
            structured.append("Price: $110 per month")
            structured.append(
                "Purchase Location: Carlisle West Garage office"
            )
            continue

        if "prorated after the start" in line.lower():
            structured.append(
                "Prorated Parking: HSC and Main Campus semester parking "
                "may be prorated after the semester begins"
            )
            structured.append(
                "Refund Policy: Refunds are based on the date the parking "
                "handtag is returned"
            )
            continue

        if (
            "$100 per academic year" in line
            and "$70 per semester" in line
        ):
            structured.append("Price: $100 per academic year")
            structured.append("Alternative Price: $70 per semester")
            structured.append("Location: Lot #3")
            continue

        if "215-204-5301" in line:
            structured.append("Parking Services Phone: 215-204-5301")
            continue

        if "discount rate is only available to students" in line.lower():
            structured.append(
                "Eligibility: Discount parking rates are available to TUCC students"
            )
            continue

        if (
            "Monday - Thursday" in line
            and "Friday" in line
            and "Saturday" in line
        ):
            add_blank(structured)
            structured.append("Parking Validation Hours:")
            structured.append("Monday-Thursday: 3:00 PM-10:15 PM")
            structured.append("Friday: 3:00 PM-9:00 PM")
            structured.append("Saturday: 9:00 AM-5:00 PM")
            continue

        if line.startswith("Parkway Parking at 1500 Market Street"):
            add_blank(structured)
            structured.append(
                "Parking Facility: Parkway Parking - 1500 Market Street"
            )
            structured.append("Location: Centre Square Building")
            structured.append("Entrance: 16th Street near Ranstead Street")
            continue

        if line.startswith("Parkway Parking at 1700 Market Street"):
            add_blank(structured)
            structured.append(
                "Parking Facility: Parkway Parking - 1700 Market Street"
            )
            continue

        if "LAZ Parking at 1501" in line:
            add_blank(structured)
            structured.append(
                "Parking Facility: LAZ Parking - Love Park Garage"
            )
            structured.append(
                "Address: 1501 John F. Kennedy Boulevard"
            )
            continue

        if "215-399-2799" in line:
            structured.append("Phone: 215-399-2799")
            continue

        if "215-231-3155" in line:
            structured.append("Phone: 215-231-3155")
            continue

        if "$6 after 3:00 PM" in line:
            structured.append("Weekday Evening Rate: $6 after 3:00 PM")
            structured.append("Exit Requirement: Must exit by midnight")
            continue

        if "$5 after 3:00 PM" in line:
            structured.append("Weekday Evening Rate: $5 after 3:00 PM")
            structured.append("Exit Requirement: Must exit by midnight")
            continue

        if "$6 after 4:00 PM" in line:
            structured.append("Weekday Evening Rate: $6 after 4:00 PM")
            structured.append("Exit Requirement: Must exit by midnight")
            continue

        if "$6 for up to 12 hours" in line:
            structured.append("Weekend Rate: $6 for up to 12 hours")
            structured.append("Exit Requirement: Must exit by midnight")
            continue

        if "$5 for up to 12 hours" in line:
            structured.append("Weekend Rate: $5 for up to 12 hours")
            structured.append("Exit Requirement: Must exit by midnight")
            continue

        # Keep generic bullets last, so phone/rate bullets are parsed first.
        if line.startswith("-"):
            structured.append(f"- {clean_bullet(line)}")
            continue

    save_structured_file(
        "student_parking_rates_structured.txt",
        structured
    )


# --------------------------------------------------
# 7. Visitor Parking Rates -> structured
# --------------------------------------------------
def create_structured_visitor_parking(text, url):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    structured = [
        "Title: Temple University Visitor Parking Rates",
        "",
        "Source:",
        url,
        ""
    ]

    expecting_locations = False

    for line in lines:
        if line == "Visitor Parking Rates":
            continue

        if line in ["Main Campus", "Health Sciences Center"]:
            add_blank(structured)
            structured.append(f"Campus: {line}")
            add_blank(structured)
            expecting_locations = False
            continue

        if "daily rate of $22 per entry" in line.lower():
            structured.append("Parking Type: Daily Visitor Parking")
            structured.append("Price: $22 per entry")
            structured.append("Available Locations:")
            expecting_locations = True
            continue

        if "1/2 hour rate of $3.00" in line:
            add_blank(structured)
            structured.append("Parking Type: Half-Hour Parking")
            structured.append("Price: $3.00 per half hour")
            structured.append("Available Locations:")
            expecting_locations = True
            continue

        if "hourly rate of $6.00" in line:
            add_blank(structured)
            structured.append("Parking Type: Hourly Parking")
            structured.append("Price: $6.00 per hour")
            structured.append("Available Locations:")
            expecting_locations = True
            continue

        if "hourly rate of $7.00" in line:
            add_blank(structured)
            structured.append("Parking Facility: Tuttleman Lot")
            structured.append("Hourly Rate: $7.00 per hour")

            if "$22" in line:
                structured.append("Parking Facility: Cecil B. Moore Lot")
                structured.append("All-Day Rate: $22")

            expecting_locations = False
            continue

        if "certain events" in line.lower() and "$27 per entry" in line:
            structured.append("Event Parking Rate: $27 per entry")
            continue

        if line == "Weekend Passes":
            add_blank(structured)
            structured.append("Parking Type: Weekend Parking Pass")
            expecting_locations = False
            continue

        if "Weekend Parking Pass" in line and "$40" in line:
            structured.append("Price: $40")
            continue

        if "Friday at 3PM" in line and "Monday at 8AM" in line:
            structured.append(
                "Valid Period: Friday at 3:00 PM through Monday at 8:00 AM"
            )
            structured.append("Location: Liacouras Garage")
            structured.append("Re-entry: Allowed during the valid period")
            continue

        if "Wednesday prior to the weekend" in line:
            structured.append(
                "Purchase Method: TU Parking Account"
            )
            structured.append(
                "Purchase Timing: Wednesday before the weekend"
            )
            structured.append(
                "Eligibility: Temple student or employee"
            )
            continue

        if line.startswith("-") and expecting_locations:
            structured.append(f"- {clean_bullet(line)}")
            continue

    save_structured_file(
        "visitor_parking_rates_structured.txt",
        structured
    )


# --------------------------------------------------
# 8. Faculty & Staff Parking Rates -> structured
# --------------------------------------------------
def create_structured_faculty_staff_parking(text, url):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    structured = [
        "Title: Temple University Faculty and Staff Parking Rates",
        "",
        "Source:",
        url,
        ""
    ]

    expecting_locations = False

    for line in lines:
        if line == "Faculty & Staff Parking Rates":
            continue

        if line in ["Main Campus", "Health Sciences Center", "Ambler Campus"]:
            add_blank(structured)
            structured.append(f"Campus: {line}")
            add_blank(structured)
            expecting_locations = False
            continue

        if line in ["Monthly Parking", "Flex Parking", "Monthly/Semester Parking"]:
            add_blank(structured)
            structured.append(f"Parking Type: {line}")
            continue

        match = re.search(
            r"Parking for (\$[\d,.]+ per (?:month|entry)) is available in:",
            line
        )

        if match:
            structured.append(f"Price: {match.group(1)}")
            structured.append("Available Locations:")
            expecting_locations = True
            continue

        match_single = re.search(
            r"Parking for (\$[\d,.]+ per month) is available in the (.+?)(?:\s*\.|$)",
            line
        )

        if match_single:
            structured.append(f"Price: {match_single.group(1)}")
            structured.append(f"Location: {match_single.group(2).strip()}")
            expecting_locations = False
            continue

        if (
            "$13 per entry" in line
            and "Valid 7:00 AM to 10:45 PM" in line
        ):
            structured.append(
                "Valid Hours: Monday-Friday, 7:00 AM-10:45 PM"
            )
            structured.append("Overnight Parking: Not permitted")
            structured.append("Payment Method: Temple ID or Mobile OWLcard")
            structured.append("Parking Account: Funds must be added before use")
            structured.append(
                "Insufficient Funds: Regular hourly or daily rate may apply"
            )
            continue

        if "renew their parking annually in july" in line.lower():
            structured.append("Renewal: Annually in July")
            continue

        if "$135 per academic year" in line:
            structured.append("Price: $135 per academic year")
            structured.append("Available Locations:")
            structured.append("- Lot #1")
            structured.append("- Lot #2")
            expecting_locations = False
            continue

        if line.startswith("-") and expecting_locations:
            structured.append(f"- {clean_bullet(line)}")
            continue

    save_structured_file(
        "faculty_staff_parking_rates_structured.txt",
        structured
    )


# --------------------------------------------------
# 9. Fetch one Parking webpage
# --------------------------------------------------
def fetch_page(filename, url):
    print("\n" + "=" * 60)
    print(f"Fetching: {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )
        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = extract_main_text(soup)

        if not text:
            print(f"No useful text found: {url}")
            return

        # Always save the clean raw page.
        save_webpage_text(filename, url, text)

        # Rate pages also receive dedicated RAG-ready structured files.
        if filename == "student_parking_rates":
            create_structured_student_parking(text, url)

        elif filename == "visitor_parking_rates":
            create_structured_visitor_parking(text, url)

        elif filename == "faculty_staff_parking_rates":
            create_structured_faculty_staff_parking(text, url)

    except requests.RequestException as e:
        print(f"Failed to fetch: {url}")
        print(f"Error: {e}")

    except Exception as e:
        print(f"Unexpected error: {url}")
        print(f"Error: {e}")


# --------------------------------------------------
# 10. Fetch all Parking pages
# --------------------------------------------------
def fetch_all_parking_pages():
    for filename, url in PAGES.items():
        fetch_page(filename, url)


# --------------------------------------------------
# 11. Run
# --------------------------------------------------
if __name__ == "__main__":
    fetch_all_parking_pages()

    print("\n" + "=" * 60)
    print("All Temple University parking data collection finished.")
