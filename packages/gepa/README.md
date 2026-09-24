# GEPA integration

Use `make_judge_acceptance_criterion()` as GEPA's `acceptance_criterion`. The
canonical Judge runner uses train-minibatch evidence and a Judge-only
evaluation policy, then scores validation and test once after optimization.
Attach `GEPAFullValidationAudit` as the criterion's `full_validation` callback
only when the explicit per-decision audit is needed to classify false accepts
and false rejects. That audit is disabled by default and never changes the
JudgeGate decision.
