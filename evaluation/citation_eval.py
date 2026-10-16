import csv
import re
from pathlib import Path


# ==========================================
# File Paths
# ==========================================

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "evaluation/results.csv"
OUTPUT_FILE = ROOT / "evaluation/citation_results.csv"


# ==========================================
# Known Documents
# ==========================================

KNOWN_DOCUMENTS = {
    "Almamlaka_Budget_Timeline.pdf": 2,
    "Almamlaka_Project_Overview.pdf": 2,
    "Almamlaka_Team_Governance.pdf": 2,
}


# ==========================================
# Citation Patterns
# ==========================================

# Supports:
#
# Almamlaka_Budget_Timeline.pdf, Page 1
# Almamlaka_Budget_Timeline.pdf (Page 1)
# Almamlaka_Budget_Timeline.pdf (الصفحة 1)
# Almamlaka_Budget_Timeline.pdf | الصفحة: 1
# **Almamlaka_Budget_Timeline.pdf (الصفحة 1)**
# *Almamlaka_Budget_Timeline.pdf* (Page 1)

CITATION_PATTERN = re.compile(
    r"(Almamlaka_[A-Za-z_]+\.pdf)"
    r"[\s*_\]\),،:|\-–]*"
    r"(?:\(\s*)?"
    r"(?:Page|الصفحة|p\.)"
    r"\s*[:：]?\s*(\d+)",
    re.IGNORECASE,
)


RETRIEVED_PATTERN = re.compile(
    r"(Almamlaka_[A-Za-z_]+\.pdf)\s+p\.(\d+)"
)


# ==========================================
# Extract Citations
# ==========================================

def extract_citations(answer):
    """
    Extract document names and page numbers
    cited in the LLM answer.
    """

    return {
        (filename, int(page))
        for filename, page in CITATION_PATTERN.findall(answer)
    }


# ==========================================
# Extract Retrieved Sources
# ==========================================

def extract_retrieved_sources(text):
    """
    Extract document names and page numbers
    returned by the retrieval system.
    """

    return {
        (filename, int(page))
        for filename, page in RETRIEVED_PATTERN.findall(text)
    }


# ==========================================
# Evaluate Individual Answer
# ==========================================

def evaluate_row(row):

    citations = extract_citations(
        row["answer"]
    )

    retrieved = extract_retrieved_sources(
        row["retrieved_sources"]
    )

    invalid = []

    for filename, page in citations:

        # Check if document exists
        if filename not in KNOWN_DOCUMENTS:

            invalid.append(
                f"{filename}: unknown document"
            )

        # Check if page number is valid
        elif not 1 <= page <= KNOWN_DOCUMENTS[filename]:

            invalid.append(
                f"{filename}: invalid page {page}"
            )

        # Check if cited source was retrieved
        elif (filename, page) not in retrieved:

            invalid.append(
                f"{filename} p.{page}: not retrieved"
            )

    is_out_of_scope = (
        row["test_id"] == "out_of_scope"
    )

    # Determine citation status
    if is_out_of_scope and not citations:

        status = "VALID_REFUSAL"

    elif not citations:

        status = "MISSING_CITATIONS"

    elif invalid:

        status = "INVALID"

    else:

        status = "VALID"

    return {
        "test_id": row["test_id"],
        "top_k": row["top_k"],
        "citation_status": status,
        "citations_detected": len(citations),
        "invalid_citations": "; ".join(invalid),
        "citations": "; ".join(
            f"{filename} p.{page}"
            for filename, page in sorted(citations)
        ),
    }


# ==========================================
# Run Evaluation
# ==========================================

def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Benchmark results not found: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        encoding="utf-8-sig"
    ) as file:

        rows = list(
            csv.DictReader(file)
        )

    if not rows:
        raise ValueError(
            "No benchmark results found."
        )

    results = [
        evaluate_row(row)
        for row in rows
    ]

    # Save results
    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys()
        )

        writer.writeheader()
        writer.writerows(results)

    # Print summary
    print(
        "\n========== CITATION EVALUATION =========="
    )

    for top_k in [3, 6]:

        subset = [
            row for row in results
            if int(row["top_k"]) == top_k
        ]

        print(f"\nTop-{top_k}")

        for row in subset:

            print(
                f"{row['test_id']}: "
                f"{row['citation_status']} "
                f"({row['citations_detected']} citations)"
            )

        valid_count = sum(
            row["citation_status"] == "VALID"
            for row in subset
        )

        refusal_count = sum(
            row["citation_status"] == "VALID_REFUSAL"
            for row in subset
        )

        print(
            f"\nValid citations: {valid_count}"
        )

        print(
            f"Valid refusals: {refusal_count}"
        )

    print(
        "\nResults saved to:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()