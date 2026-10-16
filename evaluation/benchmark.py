import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.rag_service import RAGService


TEST_CASES = [
    {
        "id": "budget_ar",
        "question": "ما سبب زيادة ميزانية المشروع؟",
        "expected_sources": [
            ("Almamlaka_Budget_Timeline.pdf", 1)
        ],
    },
    {
        "id": "budget_en",
        "question": "Why was the project budget increased?",
        "expected_sources": [
            ("Almamlaka_Budget_Timeline.pdf", 1)
        ],
    },
    {
        "id": "conflict_ar",
        "question": "هل يوجد تعارض في تواريخ إطلاق المشروع بين المستندات؟",
        "expected_sources": [
            ("Almamlaka_Budget_Timeline.pdf", 2),
            ("Almamlaka_Team_Governance.pdf", 1),
        ],
    },
    {
        "id": "conflict_en",
        "question": "Are there conflicting project launch dates across the documents?",
        "expected_sources": [
            ("Almamlaka_Budget_Timeline.pdf", 2),
            ("Almamlaka_Team_Governance.pdf", 1),
        ],
    },
    {
        "id": "out_of_scope",
        "question": "Who is the current CEO of Apple?",
        "expected_sources": [],
    },
]


def main():
    rag = RAGService(data_dir=str(ROOT / "backend/data"))

    output_path = ROOT / "evaluation/results.csv"
    rows = []

    for case in TEST_CASES:
        for top_k in [3, 6]:
            print(f"\nTesting {case['id']} | Top-{top_k}")

            start = time.perf_counter()

            result = rag.ask(
                question=case["question"],
                top_k=top_k,
            )

            latency = round(time.perf_counter() - start, 2)

            retrieved = {
                (source["source"], source["page"])
                for source in result["sources"]
            }

            expected = set(case["expected_sources"])

            if expected:
                recall = len(expected & retrieved) / len(expected)
            else:
                recall = None

            rows.append({
                "test_id": case["id"],
                "top_k": top_k,
                "question": case["question"],
                "retrieval_recall": recall,
                "latency_seconds": latency,
                "answer": result["answer"],
                "retrieved_sources": "; ".join(
                    f"{source['source']} p.{source['page']}"
                    for source in result["sources"]
                ),
            })

            print("Latency:", latency, "seconds")
            print("Retrieval Recall:", recall)
            print("Answer:", result["answer"][:200])

    with open(output_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("\nBenchmark completed!")
    print("Results saved to:", output_path)


if __name__ == "__main__":
    main()