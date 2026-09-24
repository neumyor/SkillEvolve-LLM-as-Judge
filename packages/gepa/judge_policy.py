"""GEPA-only translation of Judge predictions into candidate-pool coordinates.

The upstream state calls these coordinates val subscores. In Judge mode they
are explicitly ordinal predictions relative to the seed, never test accuracy.
No task contents from validation are inspected and no evaluator is called.
"""
from gepa.core.state import ValsetEvaluation
from gepa.strategies.eval_policy import FullEvaluationPolicy


class JudgePredictionPolicy(FullEvaluationPolicy):
    score_source = "judge_prediction"

    def __init__(self, axes):
        if not axes or len(axes) > 16:
            raise ValueError("Judge prediction requires 1..16 observed task-type axes")
        self.axes = list(axes)

    def seed_prediction(self):
        return ValsetEvaluation(
            outputs_by_val_id={axis: {"score_source": self.score_source} for axis in self.axes},
            scores_by_val_id={axis: 0.0 for axis in self.axes},
        )

    def predict_proposals(self, proposals, state):
        evaluated = []
        for proposal in proposals:
            record = proposal.metadata["judge_gate"]
            delta = record["predicted_changes"]
            parent = state.prog_candidate_val_subscores[proposal.parent_program_ids[0]]
            scores = {axis: parent[axis] + delta[axis] for axis in self.axes}
            evaluated.append((ValsetEvaluation(
                outputs_by_val_id={axis: {"score_source": self.score_source,
                                          "predicted_change": delta[axis]} for axis in self.axes},
                scores_by_val_id=scores,
            ), 0))
        return evaluated


def observed_task_axes(trainset):
    axes = set()
    for item in trainset:
        metadata = item.get("metadata") or {}
        axes.add(str(item.get("task_type") or metadata.get("task_type") or "all_tasks"))
    return sorted(axes)
