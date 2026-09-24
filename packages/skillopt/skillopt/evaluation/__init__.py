"""ReflACT Evaluation -- candidate skill validation and model selection.

Analogous to validation-based early stopping and model selection in neural
network training: evaluates candidate skills on held-out selection sets and
decides whether to accept or reject proposed updates.
"""
from skillopt.evaluation.gate import (  # noqa: F401
    GateAction,
    GateMetric,
    GateResult,
    evaluate_gate,
    select_gate_score,
)
from skillopt.evaluation.adapters import (  # noqa: F401
    GEPAJudgeAcceptanceCriterion,
    SkillGenJudgeAdapter,
)
from skillopt.evaluation.judge_gate import (  # noqa: F401
    JudgeGate,
    available_judge_prompt_variants,
    judge_gate_for_config,
    parse_judge_payload,
    register_judge_prompt_variant,
)
from skillopt.evaluation.full_validation import (  # noqa: F401
    append_validation_audit,
    make_validation_audit,
    validation_decision,
)
