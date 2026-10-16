"""
Deterministic tests for the repetition-loop guard (no LLM calls).

Reported failure: an Arabic answer began with a valid summary, then repeated
"الترجمة" hundreds of times. A loop must trigger one retry with repetition
penalties, and a persisting loop must be replaced by a safe fallback in the
question's language. Normal answers must pass through untouched.
"""

from types import SimpleNamespace

import pytest

from app import llm_service
from app.llm_service import is_degenerate

CONTEXT = "[SOURCE: doc.pdf | PAGE: 1]\nSample evidence.\n[/SOURCE]"

ARABIC_SUMMARY = (
    "تهدف مبادرة التوسع الرقمي إلى تحديث الحضور الرقمي للقناة عبر منصات البث "
    "والهاتف المحمول، مع دعم المحتوى والترجمة بعدة لغات "
    "(Almamlaka_Project_Overview.pdf، الصفحة 2). "
)

ARABIC_LOOP = ARABIC_SUMMARY + " ".join(["الترجمة"] * 300)
ENGLISH_WORD_LOOP = "The project covers three platforms. " + " ".join(["platform"] * 200)
ENGLISH_PHRASE_LOOP = "Summary: " + "the project the project " * 40
LOW_DIVERSITY = " ".join(["budget launch team"] * 60)

NORMAL_ANSWERS = {
    "english_with_citations": (
        "The total project budget has two documented values:\n\n"
        "1. **Original value**: $2,400,000 (Almamlaka_Project_Overview.pdf, Page 1).\n"
        "2. **Revised value**: $2,600,000 (Almamlaka_Budget_Timeline.pdf, Page 1).\n\n"
        "The revised value is the latest documented value "
        "(Almamlaka_Budget_Timeline.pdf, Page 1)."
    ),
    "arabic_with_citations": (
        "الميزانية الأصلية للمشروع كانت 2,400,000 دولار أمريكي "
        "(Almamlaka_Project_Overview.pdf، الصفحة 1). أما الميزانية المعدلة "
        "فبلغت 2,600,000 دولار أمريكي (Almamlaka_Budget_Timeline.pdf، الصفحة 1)، "
        "وذلك لتغطية تكاليف إضافية لدمج التلفزيون الذكي "
        "(Almamlaka_Budget_Timeline.pdf، الصفحة 1)."
    ),
    "markdown_table": (
        "| Quarter | Development | Marketing | Operations | Total |\n"
        "|---|---|---|---|---|\n"
        "| Q1 2027 | $450,000 | $120,000 | $60,000 | $630,000 |\n"
        "| Q2 2027 | $500,000 | $150,000 | $70,000 | $720,000 |\n"
        "| Q3 2027 | $400,000 | $100,000 | $60,000 | $560,000 |\n"
        "| Q4 2027 | $350,000 | $90,000 | $50,000 | $490,000 |"
    ),
    "numbered_list": "\n".join(
        f"{i}. Team member {name} works in the {dept} department (Almamlaka_Team_Governance.pdf, Page 1)."
        for i, (name, dept) in enumerate(
            [("Sara", "Digital Strategy"), ("Omar", "Engineering"), ("Lina", "Design"),
             ("Khalid", "Marketing"), ("Rana", "Legal & Compliance")], 1
        )
    ),
    "english_refusal": llm_service.ENGLISH_REFUSAL,
    "arabic_refusal": llm_service.ARABIC_REFUSAL,
}


# ---------- detector ----------

@pytest.mark.parametrize("text", [ARABIC_LOOP, ENGLISH_WORD_LOOP, ENGLISH_PHRASE_LOOP, LOW_DIVERSITY])
def test_detects_repetition_loops(text):
    assert is_degenerate(text)


@pytest.mark.parametrize("name", NORMAL_ANSWERS)
def test_normal_answers_are_not_flagged(name):
    assert not is_degenerate(NORMAL_ANSWERS[name])


def test_short_repetition_is_allowed():
    # A few repeats (e.g. emphasis or a short list) are below the limit.
    assert not is_degenerate("Yes, yes, yes. The launch was moved to April 1, 2027.")


# ---------- retry and fallback ----------

@pytest.fixture
def fake_llm(monkeypatch):
    """Fake OpenRouter client returning queued answers and recording each request."""
    state = SimpleNamespace(answers=[], calls=[])

    def create(**kwargs):
        state.calls.append(kwargs)
        message = SimpleNamespace(content=state.answers.pop(0), reasoning=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason="stop")],
            model="fake",
            usage=None,
        )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm_service, "get_llm_client", lambda: fake)
    return state


def penalized(call):
    return "frequency_penalty" in call or "repetition_penalty" in call["extra_body"]


def test_clean_answer_uses_one_call_without_penalties(fake_llm):
    clean = NORMAL_ANSWERS["english_with_citations"]
    fake_llm.answers = [clean]

    answer = llm_service.generate_grounded_response("What is the budget?", CONTEXT)

    assert answer == clean
    assert len(fake_llm.calls) == 1
    assert not penalized(fake_llm.calls[0])


def test_loop_then_clean_answer_retries_once_with_penalties(fake_llm):
    clean = NORMAL_ANSWERS["arabic_with_citations"]
    fake_llm.answers = [ARABIC_LOOP, clean]

    answer = llm_service.generate_grounded_response("شو في معلومه لازم اعرفها بالملف", CONTEXT)

    assert answer == clean
    assert len(fake_llm.calls) == 2
    assert not penalized(fake_llm.calls[0])
    assert penalized(fake_llm.calls[1])
    # The retry resends the same conversation.
    assert fake_llm.calls[1]["messages"] == fake_llm.calls[0]["messages"]


@pytest.mark.parametrize("question,loop,fallback", [
    ("شو في معلومه لازم اعرفها بالملف", ARABIC_LOOP, llm_service.ARABIC_FALLBACK),
    ("What should I know about the project?", ENGLISH_WORD_LOOP, llm_service.ENGLISH_FALLBACK),
])
def test_persistent_loop_returns_fallback_in_question_language(fake_llm, question, loop, fallback):
    fake_llm.answers = [loop, loop]

    answer = llm_service.generate_grounded_response(question, CONTEXT)

    assert answer == fallback
    assert len(fake_llm.calls) == 2  # bounded: never more than one retry
    assert not is_degenerate(answer)
