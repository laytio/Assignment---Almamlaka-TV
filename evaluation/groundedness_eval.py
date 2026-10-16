import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "evaluation/results.csv"
OUTPUT_FILE = ROOT / "evaluation/groundedness_results.csv"


def normalize(text):
    text = text.lower()
    text = text.replace(",", "")
    text = text.replace("،", "")
    text = re.sub(r"\s+", " ", text)
    return text


def has_any(text, patterns):
    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def evaluate_budget(answer):
    text = normalize(answer)

    checks = {
        "smart_tv_reason": has_any(text, [
            r"smart\s*tv",
            r"smart television",
            r"التلفزيون الذكي",
            r"التلفزيونات الذكية",
            r"شاشات التلفزيون الذكية",
        ]),

        "revised_budget": has_any(text, [
            r"2600000",
            r"2\.6\s*million",
            r"2\.6\s*مليون",
        ]),
    }

    return checks


def evaluate_conflict(answer):
    text = normalize(answer)

    checks = {
        "original_launch_date": has_any(text, [
            r"march\s+15",
            r"15\s+march",
            r"15\s+مارس",
        ]),

        "revised_launch_date": has_any(text, [
            r"april\s+1\b",
            r"1\s+april",
            r"1\s+أبريل",
            r"1\s+ابريل",
        ]),

        "smart_tv_reason": has_any(text, [
            r"smart\s*tv",
            r"smart television",
            r"التلفزيون الذكي",
            r"التلفزيونات الذكية",
            r"شاشات التلفزيون الذكية",
        ]),
    }

    return checks


def evaluate_out_of_scope(answer):
    text = normalize(answer)

    checks = {
        "refusal": has_any(text, [
            r"couldn't find",
            r"cannot find",
            r"not available",
            r"not mentioned",
            r"not provided",
            r"don't have",
            r"لا أجد",
            r"غير موجود",
            r"غير مذكور",
            r"لا تتوفر",
            r"لا توجد معلومات",
        ])
    }

    return checks


def evaluate_row(row):
    test_id = row["test_id"]
    answer = row["answer"]

    if test_id.startswith("budget"):
        checks = evaluate_budget(answer)

    elif test_id.startswith("conflict"):
        checks = evaluate_conflict(answer)

    elif test_id == "out_of_scope":
        checks = evaluate_out_of_scope(answer)

    else:
        checks = {"unknown_test": False}

    passed = sum(checks.values())
    total = len(checks)

    return {
        "test_id": test_id,
        "top_k": row["top_k"],
        "checks_passed": passed,
        "checks_total": total,
        "evidence_alignment_score": round(
            passed / total, 3
        ),
        "failed_checks": "; ".join(
            name
            for name, result in checks.items()
            if not result
        ),
    }


def main():
    with open(INPUT_FILE, encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("No benchmark results found.")

    results = [
        evaluate_row(row)
        for row in rows
    ]

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

    print("\n========== EVIDENCE ALIGNMENT ==========")

    for top_k in [3, 6]:
        subset = [
            row for row in results
            if int(row["top_k"]) == top_k
        ]

        passed = sum(
            row["checks_passed"]
            for row in subset
        )

        total = sum(
            row["checks_total"]
            for row in subset
        )

        print(f"\nTop-{top_k}")
        print(f"Evidence checks: {passed}/{total}")
        print(f"Pass rate: {passed / total:.1%}")

        for row in subset:
            if row["failed_checks"]:
                print(
                    f"  Review {row['test_id']}: "
                    f"{row['failed_checks']}"
                )

    print("\nSaved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()