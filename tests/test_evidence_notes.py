"""
Deterministic tests for documented-change notes (no LLM calls).

Detection is checked on synthetic text (generic behaviour) and on the real
corpus (verbatim provenance). The relevance threshold is checked with the real
embedding model against relevant paraphrases and unrelated questions in both
languages. The threshold is provisional: the measured gap is narrow
(unrelated <= 0.37, relevant >= 0.44 at the time of writing).
"""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import evidence_notes, llm_service
from app.evidence_notes import detect_changes, find_documented_changes, format_changes
from app.rag_service import RAGService

DATA_DIR = Path(__file__).resolve().parents[1] / "backend" / "data"
CHAT_TOP_K = 6


def chunk(text, source="doc.pdf", page=1):
    return {"source": source, "page": page, "text": text}


@pytest.fixture(scope="module")
def rag():
    return RAGService(data_dir=str(DATA_DIR))


# ---------- detection: generic patterns ----------

@pytest.mark.parametrize("sentence", [
    "The deadline was postponed to May 3, 2030.",
    "The fee has been increased from 10 to 12 dollars.",
    "Following the review, the venue was later moved to Hall B.",
    "Headcount targets were revised to 40.",
    "تم تعديل الموعد النهائي إلى 5 مايو.",
    "جرى تأجيل الاجتماع إلى الأسبوع المقبل.",
])
def test_detects_explicit_changes(sentence):
    assert [c["text"] for c in detect_changes([chunk(sentence)])] == [sentence]


@pytest.mark.parametrize("sentence", [
    "Any delay beyond the milestone poses a risk to the launch.",
    "The budget covers development and marketing.",
    "Changes above the limit must be approved by the committee.",
    "The original plan is described in section 2.",
    "Revised guidelines will be published later.",
    "قد تحدث تأخيرات في المشروع.",
])
def test_ignores_sentences_without_a_recorded_change(sentence):
    assert detect_changes([chunk(sentence)]) == []


def test_module_contains_no_business_facts():
    source = Path(evidence_notes.__file__).read_text(encoding="utf-8")
    assert ".pdf" not in source
    assert not re.search(r"\$\s?\d|\b20\d\d\b|\d{1,3},\d{3}", source)


# ---------- detection: real corpus provenance ----------

def test_corpus_changes_are_verbatim_with_provenance(rag):
    changes = detect_changes(rag.chunks)
    assert changes, "expected at least one documented change in the corpus"
    pages = {(c["source"], c["page"]): re.sub(r"\s+", " ", c["text"]) for c in rag.chunks}
    for change in changes:
        assert change["text"] in pages[(change["source"], change["page"])]
    # Every detected sentence is in a different document from at least one other
    # mention of the same subject, which is what makes the note useful.
    assert len({c["source"] for c in changes}) == len(changes)


# ---------- relevance threshold ----------

RELEVANT = {
    "budget": [
        "What is the total project budget?",
        "ما هي الميزانية الإجمالية للمشروع؟",
        "How much money has been allocated to the initiative?",
        "كم تبلغ ميزانية المبادرة؟",
        "Has the budget changed?",
        "هل تغيرت الميزانية؟",
        "What does the project cost?",
        "كم تكلفة المشروع؟",
        "Do the documents disagree about the project budget?",
    ],
    "launch": [
        "What is the official launch date?",
        "ما هو موعد الإطلاق الرسمي للمشروع؟",
        "When will the platform go live?",
        "متى سيتم إطلاق المنصة؟",
        "Has the launch been delayed?",
        "هل تم تأجيل الإطلاق؟",
        "When does the project launch?",
        "متى يبدأ المشروع؟",
        "Is that still the launch date?",
    ],
}

UNRELATED = [
    "Who is on the project team?",
    "من هم أعضاء فريق المشروع؟",
    "What is the data privacy policy?",
    "ما هي سياسة خصوصية البيانات؟",
    "How will success be measured?",
    "ما هي مؤشرات النجاح؟",
    "ما هي سياسة الإشراف على المحتوى؟",
    "Who is the project lead?",
    "من هو قائد المشروع؟",
    "How many languages will the app support?",
    "What platforms are covered?",
    "Who should I contact for technical escalations?",
    "How often does the steering committee meet?",
    "Who won the 2022 FIFA World Cup?",
]

# Identify each corpus change by a generic subject word in its own text,
# so the test does not depend on amounts, dates or file names.
SUBJECT = {"budget": "budget", "launch": "launch"}


@pytest.mark.parametrize("topic,question", [(t, q) for t, qs in RELEVANT.items() for q in qs])
def test_relevant_questions_get_only_the_matching_change(rag, topic, question):
    notes = find_documented_changes(rag.chunks, question, rag.embedding_service.model)
    subjects = {s for s, word in SUBJECT.items() for n in notes if word in n["text"].lower()}
    assert subjects == {topic}, f"{question!r} -> {[(n['text'][:50], round(n['score'], 2)) for n in notes]}"


@pytest.mark.parametrize("question", UNRELATED)
def test_unrelated_questions_get_no_change_notes(rag, question):
    notes = find_documented_changes(rag.chunks, question, rag.embedding_service.model)
    assert notes == [], f"{question!r} -> {[(n['text'][:50], round(n['score'], 2)) for n in notes]}"


# ---------- integration with the pipeline ----------

@pytest.fixture
def captured(monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        message = SimpleNamespace(content="stub answer", reasoning=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason="stop")],
            model="fake",
            usage=None,
        )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm_service, "get_llm_client", lambda: fake)
    return calls


HEADER = "DOCUMENTED CHANGES (sentences found"


def evidence_message(call):
    return [m["content"] for m in call["messages"] if m["role"] == "system"][-1]


def test_ask_adds_verbatim_cited_notes_for_relevant_question(rag, captured):
    result = rag.ask("ما هي الميزانية الإجمالية للمشروع؟", top_k=CHAT_TOP_K)

    evidence = evidence_message(captured[0])
    expected = find_documented_changes(rag.chunks, "ما هي الميزانية الإجمالية للمشروع؟", rag.embedding_service.model)
    assert format_changes(expected) in evidence
    for note in expected:
        assert f'[SOURCE: {note["source"]} | PAGE: {note["page"]}] "{note["text"]}"' in evidence

    # API response shape is unchanged.
    assert set(result) == {"question", "answer", "sources"}
    assert set(result["sources"][0]) == {"source", "page", "score"}


def test_ask_adds_no_notes_for_unrelated_question(rag, captured):
    rag.ask("Who is on the project team?", top_k=CHAT_TOP_K)
    assert HEADER not in evidence_message(captured[0])


def test_notes_follow_the_untrusted_evidence_and_precede_the_question(rag, captured):
    rag.ask("What is the official launch date?", top_k=CHAT_TOP_K)
    messages = captured[0]["messages"]
    evidence = evidence_message(captured[0])
    assert evidence.index("untrusted data") < evidence.index(HEADER)
    assert messages[-1] == {"role": "user", "content": "What is the official launch date?"}
