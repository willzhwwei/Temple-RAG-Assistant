import re
import requests
import pdfplumber

from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin
from pypdf import PdfReader


# --------------------------------------------------
# 1. Tuition-related websites
# --------------------------------------------------
PAGES = {
    "tuition_billing_overview":
        "https://sfs.temple.edu/tuition-billing",

    "manage_student_account":
        "https://sfs.temple.edu/tuition-billing/manage-my-account",

    "paying_your_bill":
        "https://sfs.temple.edu/tuition-billing/paying-your-bill",

    "tuition_due_dates":
        "https://bursar.temple.edu/student-account/due-date-schedule",

    "tuition_rates":
        "https://bursar.temple.edu/tuition-fees/tuition-rates-tuition-calculator",

    "tuition_fee_assessment":
        "https://bursar.temple.edu/tuition-fees/tuition-fee-assessment",

    "other_student_account_fees":
        "https://bursar.temple.edu/tuition-fees/tuition-fee-assessment/other-student-account-fees",

    "university_services_fee":
        "https://bursar.temple.edu/tuition-fees/tuition-fee-assessment/university-services-fee",

    "residency_information":
        "https://bursar.temple.edu/tuition-fees/residency-information",

    "billing_and_refunds":
        "https://registrar.temple.edu/billing-and-refunds"
}


# --------------------------------------------------
# 2. Settings
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "scraped_data/Tuition&Payment"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# --------------------------------------------------
# 3. Extract main webpage text
# --------------------------------------------------
def table_records(table):
    """Pair simple table columns with their original headers; never shift blanks."""
    rows = [row for row in table.find_all("tr")
            if row.find_parent("table") is table]
    if not rows:
        return []
    cells = [row.find_all(["th", "td"], recursive=False) for row in rows]
    if any(cell.get("rowspan", "1") != "1" or
           cell.get("colspan", "1") != "1"
           for row in cells for cell in row):
        raise ValueError("Merged table cells require an explicit parser; output was not saved.")
    headers = [" ".join(c.get_text(" ", strip=True).split()) for c in cells[0]]
    # Temple tables may use td cells for their header row.
    known_header = any(h.lower() in ("term", "semester") for h in headers)
    if not headers or not (any(c.name == "th" for c in cells[0]) or known_header):
        raise ValueError("Table headers could not be identified; output was not saved.")
    if any(not h for h in headers) or len(set(headers)) != len(headers):
        raise ValueError("Blank or duplicate table headers; output was not saved.")
    records = []
    caption = table.find("caption")
    heading = table.find_previous(["h1", "h2", "h3", "h4"])
    context = caption or heading
    label = " ".join(context.get_text(" ", strip=True).split()) if context else ""
    for row in cells[1:]:
        if not row:
            continue
        if len(row) != len(headers):
            raise ValueError("Table column count changed; output was not saved.")
        values = [" ".join(c.get_text(" ", strip=True).split()) for c in row]
        if values == headers:
            continue
        fields = ([f"Table context: {label}"] if label else [])
        fields.extend(f"{key}: {value or '(not provided)'}"
                      for key, value in zip(headers, values))
        records.append("[TABLE RECORD]\n" + "\n".join(fields) + "\n[/TABLE RECORD]")
    return records


def extract_main_text(soup, preserve_tables=False):
    for tag in soup(["script", "style", "nav", "footer", "header", "form", "aside"]):
        tag.decompose()
    main_content = soup.find("main") or soup.body or soup
    if preserve_tables:
        tables = main_content.find_all("table")
        if not tables:
            raise ValueError("No due-date tables found; existing file was not overwritten.")
        for table in tables:
            records = table_records(table)
            if not records:
                raise ValueError("Empty due-date table; existing file was not overwritten.")
            table.replace_with("\n\n".join(records))
    text = main_content.get_text(separator="\n\n", strip=True)
    return text.replace("[click-for-email]", "").strip()


# --------------------------------------------------
# 4. Save webpage text
# --------------------------------------------------
def save_webpage_text(filename, url, text):

    output_file = OUTPUT_DIR / f"{filename}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Source:\n")
        f.write(url + "\n\n")
        f.write(text)

    print(f"Saved webpage: {output_file}")


# --------------------------------------------------
# 5. Find PDF
# --------------------------------------------------
def find_pdf_url(soup, page_url):

    for link in soup.find_all("a", href=True):

        href = link["href"]

        if ".pdf" in href.lower():
            return urljoin(page_url, href)

    return None


# --------------------------------------------------
# 6. Download PDF
# --------------------------------------------------
def download_pdf(pdf_url):

    response = requests.get(
        pdf_url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    pdf_file = OUTPUT_DIR / "tuition_rates.pdf"

    with open(pdf_file, "wb") as f:
        f.write(response.content)

    print(f"Saved PDF: {pdf_file}")

    return pdf_file


# --------------------------------------------------
# 7. Extract normal PDF text
# --------------------------------------------------
def extract_pdf_text(pdf_file, pdf_url):

    reader = PdfReader(pdf_file)

    pdf_parts = []

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            pdf_parts.append(page_text)

    pdf_text = "\n\n".join(pdf_parts)

    output_file = OUTPUT_DIR / "tuition_rates_pdf.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Source PDF:\n")
        f.write(pdf_url + "\n\n")
        f.write(pdf_text)

    print(f"Saved PDF text: {output_file}")


# --------------------------------------------------
# 8. Extract raw PDF tables
# --------------------------------------------------
def extract_pdf_tables(pdf_file, pdf_url):

    output_lines = []

    with pdfplumber.open(pdf_file) as pdf:

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):

            tables = page.extract_tables()

            for table_number, table in enumerate(
                tables,
                start=1
            ):

                if not table:
                    continue

                output_lines.append(
                    f"\nPage {page_number} - Table {table_number}"
                )

                for row in table:

                    cleaned_row = []

                    for cell in row:

                        if cell:
                            clean_cell = (
                                cell
                                .replace("\n", " ")
                                .strip()
                            )
                        else:
                            clean_cell = ""

                        cleaned_row.append(clean_cell)

                    row_text = " | ".join(cleaned_row)

                    if row_text.strip():
                        output_lines.append(row_text)

    output_file = OUTPUT_DIR / "tuition_rates_table.txt"

    with open(output_file, "w", encoding="utf-8") as f:

        f.write("Source PDF:\n")
        f.write(pdf_url + "\n\n")

        f.write("\n".join(output_lines))

    print(f"Saved raw PDF table: {output_file}")

    return output_lines


# --------------------------------------------------
# 9. Convert tuition table into RAG-friendly text
# --------------------------------------------------
def create_structured_tuition_data(
    table_lines,
    pdf_url
):

    structured = []

    structured.append(
        "Temple University Tuition Rates"
    )

    structured.append(
        "Academic Year: 2026-2027"
    )

    structured.append(
        f"Source: {pdf_url}"
    )

    structured.append("")

    # 找 $12,312、$ 12,312、$684 等金額
    money_pattern = r"\$\s*[\d,]+"

    for line in table_lines:

        # 只處理真正有 tuition 金額的 row
        amounts = re.findall(
            money_pattern,
            line
        )

        # 清理金額，例如 "$ 12,312" -> "$12,312"
        amounts = [
            amount.replace("$ ", "$")
            for amount in amounts
        ]

        # --------------------------------------------------
        # 標準 Tuition row：
        # 一個 Program + 8 個金額
        # --------------------------------------------------
        if len(amounts) == 8:

            program = line

            for amount in re.findall(
                money_pattern,
                line
            ):
                program = program.replace(
                    amount,
                    ""
                )

            program = (
                program
                .replace("|", " ")
                .strip()
            )

            # 清除多餘空白
            program = " ".join(
                program.split()
            )

            if not program:
                continue

            structured.append(
                f"Program: {program}"
            )

            structured.append(
                f"Full-time per semester - "
                f"PA Resident: {amounts[0]}"
            )

            structured.append(
                f"Full-time per semester - "
                f"Out-of-State: {amounts[1]}"
            )

            structured.append(
                f"Full-time annual - "
                f"PA Resident: {amounts[2]}"
            )

            structured.append(
                f"Full-time annual - "
                f"Out-of-State: {amounts[3]}"
            )

            structured.append(
                f"Full-time overload per credit hour - "
                f"PA Resident: {amounts[4]}"
            )

            structured.append(
                f"Full-time overload per credit hour - "
                f"Out-of-State: {amounts[5]}"
            )

            structured.append(
                f"Part-time per credit hour - "
                f"PA Resident: {amounts[6]}"
            )

            structured.append(
                f"Part-time per credit hour - "
                f"Out-of-State: {amounts[7]}"
            )

            structured.append("")

    output_file = (
        OUTPUT_DIR /
        "tuition_rates_structured.txt"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(structured)
        )

    print(
        f"Saved structured tuition data: "
        f"{output_file}"
    )


# --------------------------------------------------
# 10. Process Tuition Rates PDF
# --------------------------------------------------
def process_tuition_pdf(
    soup,
    page_url
):

    pdf_url = find_pdf_url(
        soup,
        page_url
    )

    if not pdf_url:
        print("Tuition PDF not found.")
        return

    print(
        f"Found PDF: {pdf_url}"
    )

    # Download
    pdf_file = download_pdf(
        pdf_url
    )

    # Raw PDF text
    extract_pdf_text(
        pdf_file,
        pdf_url
    )

    # Raw PDF table
    table_lines = extract_pdf_tables(
        pdf_file,
        pdf_url
    )

    # RAG-friendly structured tuition data
    create_structured_tuition_data(
        table_lines,
        pdf_url
    )


# --------------------------------------------------
# 11. Fetch all Tuition pages
# --------------------------------------------------
def fetch_all_tuition_pages(only=None):

    for filename, url in PAGES.items():
        if only and filename != only:
            continue

        print(
            "\n" + "=" * 60
        )

        print(
            f"Fetching: {url}"
        )

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

            # Tuition Rates requires PDF processing
            if filename == "tuition_rates":

                process_tuition_pdf(
                    soup,
                    url
                )

            # Save normal webpage
            text = extract_main_text(
                soup, preserve_tables=(filename == "tuition_due_dates")
            )

            save_webpage_text(
                filename,
                url,
                text
            )

        except requests.RequestException as e:

            print(
                f"Failed to fetch: {url}"
            )

            print(
                f"Error: {e}"
            )

        except Exception as e:

            print(
                f"Unexpected error: {url}"
            )

            print(
                f"Error: {e}"
            )


# --------------------------------------------------
# 12. Run
# --------------------------------------------------
if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=sorted(PAGES))
    args = parser.parse_args()
    fetch_all_tuition_pages(only=args.only)

    print(
        "\n" + "=" * 60
    )

    print(
        "All tuition data collection finished."
    )
