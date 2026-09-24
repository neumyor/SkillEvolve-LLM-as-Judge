"""Public evidence preparation for the FUSE adaptation (trust boundary).

Ports the original FUSE rule set (``fuse/evidence.py`` in SkillEvolveCPM) to
this harness's artifacts:

* input is a merged concurrent run directory (``results.jsonl`` +
  ``trajectories/<episode_id>.json`` from ``--record-trajectory``);
* the per-step reward signal (``won``/``done``) is scrubbed from the exported
  public trajectory -- the outcome lives only in the manifest row, exactly as
  FUSE keeps reward out of the trajectory and outcome in the manifest;
* evidence workspaces are plain read-only file trees a tool-loop session can
  ``list_files``/``read_file`` (the local replacement for FUSE's mounted
  evidence dirs).

Public step schema (one JSON object per line)::

    {"kind": "step", "step": 1, "model_response": "...", "action": "...",
     "requested_action": "...", "format_valid": true, "admissible": true,
     "admissible_actions": [...], "env_feedback": "...",
     "correction_attempted": false, "correction_response": ""}

The manifest row adds the episode-level context the sessions are allowed to
see: incident id, outcome, task type, gamefile, exported trajectory path.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from alfworld_eval.unified.runner import episode_id

MANIFEST_FIELDS = (
    "incident_id",
    "outcome",
    "task_type",
    "gamefile",
    "trajectory_path",
    "diagnosis_path",
)


@dataclass
class Incident:
    """One exported public episode (FUSE's manifest incident)."""

    incident_id: str
    outcome: str  # success | failure
    task_type: str
    gamefile: str
    trajectory_path: Path
    initial_observation: str
    steps: int
    diagnosis_path: Path | None = None

    def manifest_row(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "outcome": self.outcome,
            "task_type": self.task_type,
            "gamefile": self.gamefile,
            "trajectory_path": str(self.trajectory_path),
            "diagnosis_path": str(self.diagnosis_path) if self.diagnosis_path else "",
        }


# --------------------------------------------------------------------------
# Stage 1: export public trajectories + manifest from a merged run directory
# --------------------------------------------------------------------------

def public_step(raw_step: dict) -> dict:
    """One trajectory step reduced to its public fields.

    ``won`` and ``done`` are the reward channel: ALFWorld exposes them per
    step and the episode outcome is derived from them, so they are removed
    here and re-attached only at the manifest level (as ``outcome``), keeping
    the authoring/diagnosis sessions from seeing a per-step reward signal the
    original FUSE never showed.
    """
    diagnostic = raw_step.get("diagnostic") or {}
    return {
        "kind": "step",
        "step": raw_step.get("step"),
        "model_response": raw_step.get("model_response", ""),
        "requested_action": raw_step.get("requested_action", ""),
        "action": raw_step.get("action", ""),
        "format_valid": bool(raw_step.get("format_valid", False)),
        "admissible": bool(raw_step.get("admissible", False)),
        "admissible_actions": list(diagnostic.get("admissible_actions") or []),
        "correction_attempted": bool(raw_step.get("correction_attempted", False)),
        "correction_response": raw_step.get("correction_response", ""),
        "env_feedback": raw_step.get("env_feedback", ""),
    }


def export_public_trajectory(
    trajectory_json: str | Path,
    out_jsonl: str | Path,
) -> dict:
    """Write the public JSONL for one recorded episode; return its manifest fields.

    Returns ``{"incident_id", "outcome", "task_type", "gamefile",
    "initial_observation", "steps"}`` without the paths, so the caller owns
    where the manifest points.
    """
    source = Path(trajectory_json)
    payload = json.loads(source.read_text(encoding="utf-8"))
    steps = payload.get("trajectory") or []
    if not steps:
        raise ValueError(f"recorded trajectory has no steps: {source}")
    success = bool(payload.get("success"))
    gamefile = str(payload.get("gamefile", ""))
    task_type = str(payload.get("task_type", ""))
    initial_observation = str(payload.get("initial_observation", ""))

    out = Path(out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for raw_step in steps:
            f.write(json.dumps(public_step(raw_step), ensure_ascii=False) + "\n")
    return {
        "incident_id": episode_id(gamefile, 0),
        "outcome": "success" if success else "failure",
        "task_type": task_type,
        "gamefile": gamefile,
        "initial_observation": initial_observation,
        "steps": len(steps),
    }


def export_run(
    run_dir: str | Path,
    out_dir: str | Path,
) -> list[Incident]:
    """Export every recorded trajectory of a merged run into ``out_dir/source``.

    ``run_dir`` is a merged concurrent run directory (``<out-base>/merged``).
    Episodes without a recorded trajectory file are skipped and reported by
    the caller through the returned list (they cannot serve as FUSE evidence).
    """
    run = Path(run_dir)
    traj_dir = run / "trajectories"
    if not traj_dir.is_dir():
        raise FileNotFoundError(f"no trajectories/ directory under {run}")
    out = Path(out_dir)
    source_dir = out / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    incidents: list[Incident] = []
    exported = 0
    for traj_file in sorted(traj_dir.glob("*.json")):
        fields = export_public_trajectory(
            traj_file, source_dir / f"{traj_file.stem}.jsonl"
        )
        exported += 1
        incidents.append(Incident(
            incident_id=fields["incident_id"],
            outcome=fields["outcome"],
            task_type=fields["task_type"],
            gamefile=fields["gamefile"],
            trajectory_path=source_dir / f"{traj_file.stem}.jsonl",
            initial_observation=fields["initial_observation"],
            steps=fields["steps"],
        ))

    results = run / "results.jsonl"
    expected = 0
    if results.is_file():
        with results.open(encoding="utf-8") as f:
            expected = sum(1 for line in f if line.strip())
    if exported != expected:
        # Not fatal for evidence assembly, but it must be visible: a shard that
        # died mid-episode leaves a results row without a trajectory file.
        print(
            f"warning: {run} has {expected} result rows but {exported} recorded "
            "trajectories; episodes without trajectories cannot be FUSE evidence"
        )

    incidents.sort(key=lambda i: i.incident_id)
    _write_manifest(out / "manifest.jsonl", incidents)
    return incidents


def load_manifest(path: str | Path) -> list[Incident]:
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    incidents: list[Incident] = []
    for row in rows:
        missing = [k for k in ("incident_id", "outcome", "task_type", "gamefile",
                               "trajectory_path") if not row.get(k)]
        if missing:
            raise ValueError(f"manifest row missing fields {missing}: {row}")
        incidents.append(Incident(
            incident_id=str(row["incident_id"]),
            outcome=str(row["outcome"]),
            task_type=str(row["task_type"]),
            gamefile=str(row["gamefile"]),
            trajectory_path=Path(row["trajectory_path"]),
            initial_observation=str(row.get("initial_observation", "")),
            steps=int(row.get("steps", 0)),
            diagnosis_path=Path(row["diagnosis_path"]) if row.get("diagnosis_path") else None,
        ))
    return incidents


def _write_manifest(path: Path, incidents: list[Incident]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for incident in incidents:
            row = incident.manifest_row()
            row["initial_observation"] = incident.initial_observation
            row["steps"] = incident.steps
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def attach_diagnoses(manifest_path: str | Path, diagnoses: dict[str, Path]) -> int:
    """Fill ``diagnosis_path`` for incidents whose diagnosis now exists.

    Rewrites the manifest in place (the only field the diagnosis stage is
    allowed to touch) and returns how many rows were updated.
    """
    path = Path(manifest_path)
    incidents = load_manifest(path)
    updated = 0
    for incident in incidents:
        diag = diagnoses.get(incident.incident_id)
        if diag and incident.diagnosis_path != diag:
            incident.diagnosis_path = diag
            updated += 1
    if updated:
        _write_manifest(path, incidents)
    return updated


# --------------------------------------------------------------------------
# Session evidence workspaces
# --------------------------------------------------------------------------

def _copy_file(src: str | Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def write_readme(evidence_dir: Path, text: str) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "README.md").write_text(text, encoding="utf-8")


def write_protocol(evidence_dir: Path, protocol: dict) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "protocol.json").write_text(
        json.dumps(protocol, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_meta_skill(evidence_dir: Path, meta_skill_text: str) -> None:
    target = evidence_dir / "meta_skill"
    target.mkdir(parents=True, exist_ok=True)
    (target / "SKILL.md").write_text(meta_skill_text, encoding="utf-8")


def write_diagnosis_evidence(
    incident: Incident,
    evidence_dir: str | Path,
    *,
    meta_skill_text: str,
    parent_skill_path: str | Path,
    baseline_skill_sha: str = "",
    baseline_model: str = "",
) -> Path:
    """Read-only evidence workspace for one failed episode's diagnosis session.

    Mirrors FUSE's diagnostic workspace: README, instruction (= the episode's
    initial observation), public trajectory, current skill, meta-skill.
    """
    out = Path(evidence_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "instruction.md").write_text(incident.initial_observation, encoding="utf-8")
    _copy_file(incident.trajectory_path, out / "current" / "trajectory.jsonl")
    _copy_file(parent_skill_path, out / "current" / "skill.md")
    write_meta_skill(out, meta_skill_text)
    write_readme(out, (
        "# FUSE Diagnostic Evidence (read-only)\n\n"
        f"Incident `{incident.incident_id}` — a **failed** ALFWorld episode "
        f"(task type `{incident.task_type}`) run with the current skill injected.\n\n"
        "Read in this order: `instruction.md`, `current/trajectory.jsonl`, "
        "`current/skill.md`, `meta_skill/SKILL.md`.\n\n"
        "The trajectory contains the agent's reasoning, chosen actions, the "
        "admissible action list and environment feedback for each step. The "
        "episode's outcome (failure) is known from the manifest; no per-step "
        "reward signal is present by design.\n"
    ))
    write_protocol(out, {
        "session_kind": "diagnosis",
        "incident_id": incident.incident_id,
        "outcome": incident.outcome,
        "task_type": incident.task_type,
        "gamefile": incident.gamefile,
        "steps": incident.steps,
        "baseline_model": baseline_model,
        "baseline_skill_sha256": baseline_skill_sha,
        "result_file": "result/diagnosis.md",
    })
    return out


def write_tagging_evidence(
    incident: Incident,
    evidence_dir: str | Path,
    *,
    meta_skill_text: str,
) -> Path:
    out = Path(evidence_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "instruction.md").write_text(incident.initial_observation, encoding="utf-8")
    _copy_file(incident.trajectory_path, out / "current" / "trajectory.jsonl")
    if incident.diagnosis_path and Path(incident.diagnosis_path).is_file():
        _copy_file(incident.diagnosis_path, out / "diagnosis.md")
    write_meta_skill(out, meta_skill_text)
    write_readme(out, (
        "# FUSE Tagging Evidence (read-only)\n\n"
        f"Incident `{incident.incident_id}` (task type `{incident.task_type}`, "
        f"outcome `{incident.outcome}`).\n\n"
        "Read `instruction.md`, then `current/trajectory.jsonl` (and "
        "`diagnosis.md` when present). Tag the atomic capabilities the *task* "
        "requires, not the events of this one run.\n"
    ))
    write_protocol(out, {
        "session_kind": "tagging",
        "incident_id": incident.incident_id,
        "outcome": incident.outcome,
        "task_type": incident.task_type,
        "steps": incident.steps,
        "result_file": "result/tags.json",
    })
    return out


def write_clustering_evidence(
    incidents: list[Incident],
    tags: list[dict],
    evidence_dir: str | Path,
    *,
    meta_skill_text: str,
) -> Path:
    out = Path(evidence_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "tags.jsonl").open("w", encoding="utf-8") as f:
        for tag in tags:
            f.write(json.dumps(tag, ensure_ascii=False) + "\n")
    write_meta_skill(out, meta_skill_text)
    write_readme(out, (
        "# FUSE Clustering Evidence (read-only)\n\n"
        f"{len(tags)} tagged incidents. Read `tags.jsonl` first; the per-incident "
        "trajectories are available under `incidents/` only when a capability "
        "boundary is unclear from the tags alone.\n"
    ))
    incidents_dir = out / "incidents"
    for incident in incidents:
        if not any(t.get("incident_id") == incident.incident_id for t in tags):
            continue
        episode_dir = incidents_dir / incident.incident_id
        episode_dir.mkdir(parents=True, exist_ok=True)
        _copy_file(incident.trajectory_path, episode_dir / "trajectory.jsonl")
        (episode_dir / "instruction.md").write_text(
            incident.initial_observation, encoding="utf-8"
        )
    write_protocol(out, {
        "session_kind": "clustering",
        "n_incidents": len(tags),
        "result_file": "result/clusters.json",
    })
    return out


def write_authoring_evidence(
    task_type: str,
    members: list[Incident],
    tags: list[dict],
    clusters: dict,
    evidence_dir: str | Path,
    *,
    meta_skill_text: str,
    parent_skill_path: str | Path,
    baseline_model: str = "",
    baseline_skill_sha: str = "",
    validation_summary: dict | None = None,
) -> Path:
    """Read-only evidence workspace for one task-type family's authoring session.

    The authoring session sees: the parent skill (baseline to preserve), this
    family's member index (outcome + tags), the capability clusters, and every
    member's instruction / public trajectory / diagnosis (for failures). This
    mirrors FUSE's per-cluster evidence assembly with family := task type.

    ``validation_summary`` (later rounds) adds the previous round's
    per-episode validation verdicts: which members passed the majority gate,
    which failed, and which of those were previous-round regressions. It is
    the harness-side outcome record (no reward detail), standing in for the
    original's previous-round validation trajectories.
    """
    out = Path(evidence_dir)
    out.mkdir(parents=True, exist_ok=True)
    _copy_file(parent_skill_path, out / "parent" / "skill.md")
    write_meta_skill(out, meta_skill_text)

    member_rows = []
    tags_by_id = {t.get("incident_id"): t for t in tags}
    for incident in sorted(members, key=lambda i: i.incident_id):
        member_rows.append({
            "incident_id": incident.incident_id,
            "outcome": incident.outcome,
            "task_type": incident.task_type,
            "steps": incident.steps,
            "capability_tags": (tags_by_id.get(incident.incident_id) or {}).get(
                "capability_tags", []
            ),
            "capability_summary": (tags_by_id.get(incident.incident_id) or {}).get(
                "capability_summary", ""
            ),
        })
    with (out / "members.jsonl").open("w", encoding="utf-8") as f:
        for row in member_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out / "clusters.json").write_text(
        json.dumps(clusters, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if validation_summary is not None:
        (out / "validation_summary.json").write_text(
            json.dumps(validation_summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    incidents_dir = out / "incidents"
    for incident in members:
        episode_dir = incidents_dir / incident.incident_id
        episode_dir.mkdir(parents=True, exist_ok=True)
        (episode_dir / "instruction.md").write_text(
            incident.initial_observation, encoding="utf-8"
        )
        _copy_file(incident.trajectory_path, episode_dir / "trajectory.jsonl")
        if incident.diagnosis_path and Path(incident.diagnosis_path).is_file():
            _copy_file(incident.diagnosis_path, episode_dir / "diagnosis.md")

    write_readme(out, (
        "# FUSE Authoring Evidence (read-only)\n\n"
        f"Author one complete skill document for the ALFWorld task type "
        f"`{task_type}`.\n\n"
        "Read in this order: `members.jsonl`, `clusters.json`, "
        "`parent/skill.md`, `meta_skill/SKILL.md`, then every "
        "`incidents/<id>/` (instruction, trajectory, and diagnosis for "
        "failures). Trajectories are large; read them per file, never all at "
        "once.\n"
        + (
            "\n`validation_summary.json` records the previous round's "
            "per-episode validation verdicts for this family (pass/fail under "
            "the majority gate, and whether a failure was also a "
            "previous-round regression). Treat every pass as behavior to "
            "preserve, and every failure (persistent or regression) as repair "
            "evidence; the underlying trajectories are the per-incident "
            "files already listed.\n"
            if validation_summary is not None
            else ""
        )
    ))
    write_protocol(out, {
        "session_kind": "authoring",
        "task_type": task_type,
        "n_members": len(members),
        "n_failures": sum(1 for m in members if m.outcome == "failure"),
        "baseline_model": baseline_model,
        "baseline_skill_sha256": baseline_skill_sha,
        "result_file": "result/skill.md",
    })
    return out
