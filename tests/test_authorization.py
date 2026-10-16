"""
Deterministic regression tests for unsupported authorization claims (no LLM calls).

Failure being guarded: asked whether a named person can independently approve a
budget change exactly at a "> threshold" limit, the model answered yes, treating
"the threshold approval does not apply" plus "escalate to this person" as
approval authority. The deterministic tests check that the model receives the
policy text and the rules; the opt-in live tests at the end (RUN_LIVE_LLM=1,
4 paid calls) check the model's actual answers.
"""

import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import llm_service
from app.rag_service import RAGService

DATA_DIR = Path(__file__).resolve().parents[1] / "backend" / "data"
CHAT_TOP_K = 6

QUESTIONS = [
    "Can Sara approve a budget change of exactly $50,000 on her own?",
    "Is the project lead allowed to sign off on a $50,000 budget increase without anyone else?",
    "هل تستطيع سارة الموافقة على تغيير في الميزانية بقيمة 50,000 دولار بمفردها؟",
]

# Strictly above the threshold: the documents require another party's approval.
ABOVE_QUESTION = "Can Sara approve a budget change of $60,000 on her own?"

# Policy wording the answer depends on (threshold rule and escalation route).
POLICY_PHRASES = ("above $50,000", "escalate to the Project Lead")


@pytest.fixture(scope="module")
def rag():
    return RAGService(data_dir=str(DATA_DIR))


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


def system_messages(call):
    return [m["content"] for m in call["messages"] if m["role"] == "system"]


@pytest.mark.parametrize("question", QUESTIONS + [ABOVE_QUESTION])
def test_policy_text_reaches_the_model(rag, captured, question):
    rag.ask(question, top_k=CHAT_TOP_K)
    evidence = " ".join(system_messages(captured[0])[-1].split())
    for phrase in POLICY_PHRASES:
        assert phrase in evidence, f"{phrase!r} missing from context for {question!r}"


def test_prompt_separates_authority_from_thresholds_and_escalation(rag, captured):
    rag.ask(QUESTIONS[0], top_k=CHAT_TOP_K)
    prompt = " ".join(system_messages(captured[0])[0].split())

    # Strict comparisons are preserved.
    assert '"above", "over", and "more than" mean strictly >.' in prompt
    assert '"at least" means >=.' in prompt
    # "Approval not required" is not "authorized".
    assert "Never infer that a person has approval authority merely because a particular approval requirement does not apply." in prompt
    # Escalation / routing roles are not approval authority (the new clause).
    assert "Being a lead, contact, or escalation point for an item, or bringing it to another body for review, is not approval authority" in prompt
    assert "authorization cannot be determined from the provided documents" in prompt
    # Three-way answer, strict threshold, and consistent opening.
    assert "Yes, only if the documents explicitly grant that permission." in prompt
    assert "No, only if the documents explicitly prohibit it" in prompt
    assert '"The documents do not establish whether..."' in prompt
    assert "The absence of a particular approval requirement is neither permission nor prohibition." in prompt
    assert "does not apply to a value exactly equal to that threshold" in prompt
    assert "Your opening sentence must agree with your conclusion." in prompt

    # Question-level reminder sits after the evidence, right before the question.
    evidence = " ".join(system_messages(captured[0])[-1].split())
    assert "choose exactly one outcome: Yes only if the documents explicitly establish that independent authority;" in evidence
    assert "No only if the documents explicitly require another party's approval for this specific action or amount" in evidence
    assert '"above" / "أكثر من" means strictly greater than' in evidence
    assert evidence.endswith("a value exactly equal to the threshold is not above it.")


def test_rules_are_generic(rag, captured):
    rag.ask(QUESTIONS[0], top_k=CHAT_TOP_K)
    prompt = system_messages(captured[0])[0]
    for specific in ("Sara", "50,000", "Finance Committee", "Project Lead"):
        assert specific not in prompt


# ---------- live LLM checks (opt-in, paid) ----------

live = pytest.mark.skipif(os.getenv("RUN_LIVE_LLM") != "1", reason="Live LLM tests are opt-in: set RUN_LIVE_LLM=1")

GOVERNANCE_DOC = "Almamlaka_Team_Governance.pdf"
# Arabic "لا" opens a negative answer ("لا تستطيع", "لا، ...") unless it starts an
# undetermined statement ("لا تحدد المستندات", "لا توضح", "لا يمكن تحديد").
OPENS_YES_NO = re.compile(r"^\W*(yes\b|no\b|نعم|لا(?!\s*(تحدد|توضح|يمكن تحديد)))", re.IGNORECASE)
UNDETERMINED = re.compile(r"do(es)? not establish|cannot be determined|لا تحدد|لا توضح|لا يمكن تحديد", re.IGNORECASE)


def live_answer(rag, question):
    answer = rag.ask(question=question, top_k=CHAT_TOP_K)["answer"]
    print(f"\n--- Q: {question}\n{answer}\n")
    return answer


@live
@pytest.mark.parametrize("question", QUESTIONS)
def test_live_threshold_value_is_undetermined(rag, question):
    answer = live_answer(rag, question)
    assert not OPENS_YES_NO.search(answer), "opens with Yes/No although authority is not established"
    assert UNDETERMINED.search(answer), "does not say authorization cannot be determined"
    assert GOVERNANCE_DOC in answer


@live
def test_live_value_above_threshold_needs_other_approval(rag):
    answer = live_answer(rag, ABOVE_QUESTION)
    assert re.match(r"^\W*no\b", answer, re.IGNORECASE), "should answer No: another party's approval is required"
    assert "finance committee" in answer.lower()
    assert GOVERNANCE_DOC in answer
