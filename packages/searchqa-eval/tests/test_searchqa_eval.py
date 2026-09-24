import pytest

from searchqa_eval.data import load_items, truncate_context
from searchqa_eval.evaluator import evaluate, extract_answer, normalize_answer
from searchqa_eval.prompts import build_system_prompt, build_user_prompt
from searchqa_eval.runner import process_one, run_batch, summarize
from searchqa_eval.skills import load_skill_content

# ── evaluator (SQuAD convention) ─────────────────────────────────────────


def test_normalize_answer():
    assert normalize_answer("The Golden  Gate Bridge!") == "golden gate bridge"


def test_extract_answer_tags_and_fallback():
    assert extract_answer("reasoning... <answer>Paris</answer>") == "Paris"
    assert extract_answer("multiple <answer>a</answer> x <answer>b</answer>") == "b"
    assert extract_answer("no tags here\nfinal line") == "final line"


def test_evaluate_em_f1_sub_em():
    r = evaluate("<answer>William Shakespeare</answer>", ["William Shakespeare"])
    assert r["em"] == 1.0 and r["f1"] == 1.0

    r = evaluate("<answer>Shakespeare</answer>", ["William Shakespeare"])
    assert r["em"] == 0.0
    assert 0.0 < r["f1"] < 1.0
    assert r["sub_em"] == 1.0  # gold contains pred after normalization

    r = evaluate("<answer>Einstein</answer>", ["Newton"])
    assert r["em"] == 0.0 and r["f1"] == 0.0 and r["sub_em"] == 0.0


# ── data ─────────────────────────────────────────────────────────────────


def test_truncate_context_at_doc_boundary():
    docs = [f"[DOC]doc{i}" + "x" * 50 for i in range(200)]
    context = "".join(docs)
    trimmed = truncate_context(context, 6000)
    assert len(trimmed) <= 6000
    assert trimmed.endswith("x" * 50)  # cut exactly at a [DOC] boundary
    # Documented SkillOpt quirk: when truncation triggers, the leading
    # "[DOC]" marker is dropped (split's empty first element takes the
    # no-prefix branch). Body text is still a prefix of the context.
    assert context[5:].startswith(trimmed[:100])
    assert "[DOC]" in trimmed  # later doc separators are preserved


def test_truncate_context_first_doc_too_big():
    context = "[DOC]" + "a" * 7000
    trimmed = truncate_context(context, 6000)
    # Hard-cut fallback keeps the first max_chars and appends a notice,
    # so total length can exceed the budget by the notice length.
    assert trimmed == "[DOC]" + "a" * (6000 - 5) + "\n...[truncated]"


def test_load_items_json_array(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        '[{"id":"1","question":"q","context":"c","answers":["a"]}]',
        encoding="utf-8",
    )
    items = load_items(path)
    assert items[0]["id"] == "1"

    bad = tmp_path / "bad.json"
    bad.write_text('[{"id":"2","question":"q"}]', encoding="utf-8")
    with pytest.raises(ValueError, match="missing required fields"):
        load_items(bad)


# ── prompts ──────────────────────────────────────────────────────────────


def test_system_prompt_with_and_without_skill():
    no_skill = build_system_prompt("")
    assert "## Skill" not in no_skill
    assert "## Task Format" in no_skill

    with_skill = build_system_prompt("Be concise.")
    assert "## Skill\nBe concise." in with_skill
    assert with_skill.index("## Skill") < with_skill.index("## Task Format")


def test_user_prompt_sections():
    user = build_user_prompt("Who wrote Hamlet?", "[DOC]snippet1[DOC]snippet2")
    assert user.startswith("## Context\n")
    assert "## Question\nWho wrote Hamlet?" in user


# ── skills ───────────────────────────────────────────────────────────────


def test_load_skill_content():
    assert load_skill_content("vanilla") == ""
    assert "Concise Answer Normalization" in load_skill_content("skillopt")
    # The placeholder was replaced by the skill generated with
    # scripts/run_trace2skill.py (see README's Trace2Skill section).
    assert "SearchQA Question Answering" in load_skill_content("trace2skill")
    with pytest.raises(ValueError):
        load_skill_content("skillrl")  # not part of this benchmark


# ── runner ───────────────────────────────────────────────────────────────


ITEMS = [
    {"id": "1", "question": "What color is the sky?",
     "context": "[DOC]The sky is blue.", "answers": ["blue"]},
    {"id": "2", "question": "Capital of France?",
     "context": "[DOC]Paris is the capital.", "answers": ["Paris"]},
]


class EchoAgent:
    """Returns the first question word as the answer (deterministic)."""

    name = "echo"

    def respond(self, system: str, user: str) -> tuple[str, dict]:
        question = user.split("## Question\n")[1]
        usage = {"prompt_tokens": 10, "completion_tokens": 1}
        return f"<answer>{question.split()[0]}</answer>", usage


def test_process_one_scores():
    result = process_one(ITEMS[0], build_system_prompt(""), EchoAgent())
    assert result.agent_ok
    assert result.predicted_answer.lower() == "what"
    assert result.em == 0.0
    assert result.usage["prompt_tokens"] == 10


def test_run_batch_resume(tmp_path):
    agent = EchoAgent()
    results = run_batch(ITEMS, build_system_prompt(""), agent,
                        out_dir=tmp_path, workers=2)
    assert len(results) == 2
    first_pass = (tmp_path / "results.jsonl").read_text().count("\n")

    # Re-run: everything already done, no new lines appended.
    results2 = run_batch(ITEMS, build_system_prompt(""), agent,
                         out_dir=tmp_path, workers=2)
    assert len(results2) == 2
    assert (tmp_path / "results.jsonl").read_text().count("\n") == first_pass


def test_run_batch_retries_failed_resume_row_without_duplicate(tmp_path):
    class FlakyAgent:
        name = "flaky"
        timeout = 1.0

        def __init__(self):
            self.calls = 0

        def respond(self, _system, _user):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("temporary endpoint timeout")
            return "<answer>Paris</answer>", {}

    item = [{"id": "one", "question": "capital?", "answers": ["Paris"]}]
    agent = FlakyAgent()
    results = run_batch(
        item, build_system_prompt(""), agent, out_dir=tmp_path,
        workers=1, failed_retries=1,
    )
    assert len(results) == 1
    assert results[0].agent_ok is True
    rows = (tmp_path / "results.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1


def test_summarize():
    from searchqa_eval.runner import ItemResult

    rows = [
        ItemResult(id="1", question="q", em=1.0, f1=1.0, sub_em=1.0, hard=1,
                   soft=1.0, predicted_answer="x", gold_answers=["x"],
                   response="", agent_ok=True, usage={"prompt_tokens": 5}),
        ItemResult(id="2", question="q", em=0.0, f1=0.0, sub_em=0.0, hard=0,
                   soft=0.0, predicted_answer="y", gold_answers=["x"],
                   response="", agent_ok=False, fail_reason="boom"),
    ]
    s = summarize(rows)
    assert s["n_items"] == 2 and s["agent_ok"] == 1 and s["agent_failed"] == 1
    assert s["em"] == 1.0  # averaged over scored items only
    assert s["usage"]["prompt_tokens"] == 5


def test_think_block_is_not_scored_as_an_answer():
    """An uncommitted model must score 0, not partial credit for its reasoning.

    With a reasoning endpoint the visible `content` can be empty, leaving only
    the think block. Token-level F1 would award that block partial credit for
    words it happened to mention.
    """
    from searchqa_eval.agent import _restore_think_block
    from searchqa_eval.evaluator import extract_answer, f1_score

    restored = _restore_think_block("", "The capital of France is likely Paris or Lyon")
    assert extract_answer(restored) == ""
    assert f1_score(extract_answer(restored), ["Paris"]) == 0.0

    # A real answer is still extracted, and a rehearsal in the CoT is ignored.
    committed = _restore_think_block(
        "Settled.\n</think>\n<answer>Paris</answer>",
        "Could be <answer>Lyon</answer>? No.",
    )
    assert extract_answer(committed) == "Paris"
