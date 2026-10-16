import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "evaluation/results.csv"
OUTPUT_FILE = ROOT / "evaluation/quality_results.csv"


def normalize(text):
    """Normalize common Arabic and English formatting."""
    text = text.lower()
    text = text.replace(",", "")
    text = text.replace("،", "")
    text = text.replace("٬", "")
    text = text.replace("٫", ".")
    text = re.sub(r"\s+", " ", text)
    return text


def contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def check_budget(answer):
    text = normalize(answer)

    has_reason = contains_any(text, [
        "smart tv",
        "smart television",
        "التلفزيون الذكي",
        "التلفزيونات الذكية",
        "شاشات التلفزيون الذكية"
    ])

    has_revised = contains_any(text, [
        "2600000",
        "2.6 million",
        "2.6 مليون"
    ])

    return has_reason and has_revised


def check_conflict(answer):
    text = normalize(answer)

    has_original = contains_any(text, [
        "march 15", "15 march", "15 مارس"
    ])

    has_revised = contains_any(text, [
        "april 1", "1 april", "1 أبريل", "1 ابريل"
    ])

    return has_original and has_revised


def check_out_of_scope(answer):
    text = normalize(answer)

    refusal_patterns = [
        "couldn't find",
        "cannot find",
        "not available",
        "not mentioned",
        "not provided",
        "don't have",
        "لا أجد",
        "غير موجود",
        "غير مذكور",
        "لا تتوفر",
        "لا توجد معلومات"
    ]

    return contains_any(text, refusal_patterns)


def check_language(answer, question):
    arabic_answer = len(re.findall(r"[\u0600-\u06FF]", answer))
    latin_answer = len(re.findall(r"[A-Za-z]", answer))

    arabic_question = bool(
        re.search(r"[\u0600-\u06FF]", question)
    )

    if arabic_question:
        # Arabic should dominate, allowing English technical terms.
        return arabic_answer >= latin_answer

    return latin_answer > arabic_answer


def evaluate_row(row):
    test_id = row["test_id"]
    answer = row["answer"]
    question = row["question"]

    if test_id.startswith("budget"):
        correctness = check_budget(answer)

    elif test_id.startswith("conflict"):
        correctness = check_conflict(answer)

    elif test_id == "out_of_scope":
        correctness = check_out_of_scope(answer)

    else:
        correctness = False

    language = check_language(answer, question)

    # Citation and groundedness require additional verification.
    # Do not automatically mark them as correct.
    return {
        **row,
        "answer_correctness_heuristic": int(correctness),
        "language_consistency_heuristic": int(language),
        "citation_accuracy": "NOT_EVALUATED",
        "groundedness": "NOT_EVALUATED",
    }


def main():
    with open(INPUT_FILE, encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("No benchmark results found.")

    evaluated = [evaluate_row(row) for row in rows]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=evaluated[0].keys()
        )
        writer.writeheader()
        writer.writerows(evaluated)

    print("\n========== QUALITY EVALUATION ==========")

    for top_k in [3, 6]:
        subset = [
            row for row in evaluated
            if int(row["top_k"]) == top_k
        ]

        correct = sum(
            row["answer_correctness_heuristic"]
            for row in subset
        )

        language = sum(
            row["language_consistency_heuristic"]
            for row in subset
        )

        print(f"\nTop-{top_k}")
        print(f"Answer correctness (heuristic): {correct}/{len(subset)}")
        print(f"Language consistency (heuristic): {language}/{len(subset)}")

        for row in subset:
            if (
                not row["answer_correctness_heuristic"]
                or not row["language_consistency_heuristic"]
            ):
                print(
                    f"  Review: {row['test_id']} "
                    f"| correctness={row['answer_correctness_heuristic']} "
                    f"| language={row['language_consistency_heuristic']}"
                )

    print("\nCitation accuracy: NOT_EVALUATED")
    print("Groundedness: NOT_EVALUATED")
    print("\nSaved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()