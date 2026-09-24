"""Shared, bounded evidence preparation for execution-free candidate decisions."""
from __future__ import annotations

import json
from collections import defaultdict, deque


PRIVATE_KEYS = {
    "ground_truth", "ground-truth", "reference_answer", "oracle", "gold_answers",
    "answers", "hidden_tests", "verifier_result",
}


def public_value(value):
    if isinstance(value, dict):
        return {str(k): public_value(v) for k, v in value.items()
                if str(k).lower() not in PRIVATE_KEYS}
    if isinstance(value, (list, tuple)):
        return [public_value(v) for v in value]
    return value


def bounded_text(value, limit):
    text = value if isinstance(value, str) else json.dumps(public_value(value), default=str, ensure_ascii=False)
    if len(text) <= limit:
        return text
    marker = "\n[omitted]\n"
    room = max(0, limit - len(marker))
    return text[:room // 2] + marker + text[-(room - room // 2):] if room else marker[:limit]


def select_evidence(batches, max_cards):
    """Round-robin across observed task types/outcomes, newest per group first."""
    groups = defaultdict(deque)
    seen = set()
    total = 0
    for batch in reversed(batches):
        for result in reversed(batch.get("results") or []):
            total += 1
            key = json.dumps(public_value(result), sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            group = (str(result.get("task_type", "unspecified")), str(result.get("hard", "unknown")))
            groups[group].append((result, batch.get("rollout_dir")))
    selected = []
    while groups and len(selected) < max_cards:
        for group in list(groups):
            selected.append(groups[group].popleft())
            if not groups[group]:
                del groups[group]
            if len(selected) == max_cards:
                break
    return selected, {"available": total, "unique": len(seen), "shown": len(selected),
                      "omitted": total - len(selected)}


def replacement_message(*, current_skill, candidate_skill, ranked_patch, batches,
                        previous_attempts, max_cards, card_chars, max_skill_chars,
                        max_patch_chars):
    from skillopt.evolution_controller import format_observation_card

    selected, counts = select_evidence(batches, max_cards)
    cards = []
    for result, rollout_dir in selected:
        rendered = result.get("judge_evidence") or format_observation_card(
            public_value(result), rollout_dir, max_chars=card_chars, view="semantic")
        cards.append(bounded_text(rendered, card_chars))
    history = [{k: a.get(k) for k in ("judge_verdict", "judge_reason")}
               for a in (previous_attempts or [])[-3:]]
    message = "\n\n".join([
        "CURRENT\n" + bounded_text(current_skill or "(empty)", max_skill_chars),
        "CANDIDATE\n" + bounded_text(candidate_skill or "(empty)", max_skill_chars),
        "CHANGE RATIONALE (untrusted proposal)\n" + bounded_text(ranked_patch or {}, max_patch_chars),
        "EXISTING TRAINING EVIDENCE ONLY; candidate has NOT been executed.\n"
        + json.dumps(counts) + "\n" + "\n\n".join(cards),
        "PREVIOUS JUDGMENTS (predictions, not observed outcomes)\n" + bounded_text(history, 1200),
    ])
    return message, counts
