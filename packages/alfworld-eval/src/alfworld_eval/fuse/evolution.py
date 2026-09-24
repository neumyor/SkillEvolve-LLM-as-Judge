"""Cluster evolution orchestrator for the FUSE adaptation.

Ports ``fuse/cluster_evolution.py`` (SkillEvolveCPM) onto this harness with
family := ALFWorld task type:

    baseline run (train split, parent skill, trajectories recorded)
      -> export public evidence + manifest            (stage 1)
      -> per-failure-episode diagnosis sessions       (stage 2)
      -> per-episode capability tagging               (stage 3)
      -> batch capability clustering                   (stage 4)
      -> per-task-type skill authoring + static check  (stage 5)
      -> train-member validation, N attempts each      (stage 6)
      -> acceptance (gain/regression, infra separated) (stage 7)
      -> staging of the routed publish set             (stage 8)

Every stage is idempotent and resumable: its outputs are checked before any
LLM/eval work is spent, matching the original's ``--resume`` semantics.

Acceptance rules (adapted from the original ``_finalize_authored_cluster``):

* an episode *passes* validation when a strict majority of its attempts
  succeed (2 of 3 by default);
* ``regression``: a baseline-success episode that does not pass and has no
  infrastructure-unresolved attempt;
* ``gain``: a baseline-failure episode that passes;
* a family is ``accepted`` when it has no regression and (>=1 gain if the
  family had failures; all members pass if it had none);
* episodes missing from a validation run count as infrastructure-unresolved,
  never as failures or regressions.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from alfworld_eval.unified.runner import episode_id
from alfworld_eval.unified.skills import TASKS

from . import evidence
from .models import ClusterResult, DiagnosticResult, TagResult
from .sessions import SessionRunner, build_client
from .static_check import DEFAULT_MAX_CHARS, check_candidate_skill

META_SKILLS_DIR = Path(__file__).with_name("meta_skills")

STAGE_ORDER = (
    "export", "diagnose", "tag", "cluster", "author", "validate", "accept", "stage",
)


def _read_meta_skill(name: str) -> str:
    return (META_SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass
class FuseEvolutionConfig:
    """Fixed context for one evolution run (mirrors the original's fixed inputs)."""

    baseline_run_dir: Path          # merged/ dir of the train baseline run
    parent_skill: Path              # the skill that baseline run injected
    out_dir: Path                   # evolution output root
    project_root: Path              # alfworld-eval repo root
    base_url: str
    model: str                      # session model (diagnosis/tagging/authoring)
    api_key: str = ""
    eval_model: str = ""            # episode execution model (default: same)
    eval_base_url: str = ""         # episode endpoint (default: same)
    attempts: int = 3               # validation attempts per episode
    shards: int = 8
    max_skill_chars: int = DEFAULT_MAX_CHARS
    max_session_turns: int = 40
    session_max_tokens: int = 8192
    split: str = "train"            # split of the baseline/validation episodes
    # --- later-round support (FUSE round-2 semantics) ---
    #: Per-task-type parent skills (a staged_skills-style directory). When set
    #: it takes precedence over the flat ``parent_skill`` for authoring, which
    #: is how round 2 derives candidates from round 1's published set.
    parent_skills_dir: Path | None = None
    #: Extra incident ids to diagnose even though their baseline outcome is
    #: success (round 2 diagnoses previous-round regressions this way).
    extra_diagnoses: tuple[str, ...] = ()
    #: {incident_id: {"passed": bool, "regression": bool, ...}} from the
    #: previous round's validation; injected into authoring evidence.
    validation_summary: dict | None = None
    #: {incident_id: {"success": bool}} overriding the baseline outcomes for
    #: acceptance (round 2 compares against round 1's published system, not
    #: the original baseline).
    baseline_outcomes_override: dict | None = None

    def __post_init__(self) -> None:
        self.baseline_run_dir = Path(self.baseline_run_dir).resolve()
        self.parent_skill = Path(self.parent_skill).resolve()
        self.out_dir = Path(self.out_dir).resolve()
        self.project_root = Path(self.project_root).resolve()
        if self.parent_skills_dir is not None:
            self.parent_skills_dir = Path(self.parent_skills_dir).resolve()
        if not self.eval_model:
            self.eval_model = self.model
        if not self.eval_base_url:
            self.eval_base_url = self.base_url

    # -- derived paths ------------------------------------------------------

    @property
    def manifest_path(self) -> Path:
        return self.out_dir / "manifest.jsonl"

    @property
    def source_dir(self) -> Path:
        return self.out_dir / "source"

    @property
    def diagnoses_dir(self) -> Path:
        return self.out_dir / "diagnoses"

    @property
    def tagging_dir(self) -> Path:
        return self.out_dir / "tagging"

    @property
    def skills_dir(self) -> Path:
        return self.out_dir / "skills"

    @property
    def validations_dir(self) -> Path:
        return self.out_dir / "validations"

    @property
    def staged_dir(self) -> Path:
        return self.out_dir / "staged_skills"

    @property
    def parent_sha(self) -> str:
        return _sha256(self.parent_skill)


class FuseEvolution:
    def __init__(self, config: FuseEvolutionConfig):
        self.config = config
        self.client = build_client(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
            max_tokens=config.session_max_tokens,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _session_client(self):
        # One client per stage keeps usage audits separable.
        return build_client(
            base_url=self.config.base_url,
            model=self.config.model,
            api_key=self.config.api_key,
            max_tokens=self.config.session_max_tokens,
        )

    def _print(self, message: str) -> None:
        print(f"[fuse] {message}", flush=True)

    def load_incidents(self) -> list[evidence.Incident]:
        if not self.config.manifest_path.is_file():
            raise FileNotFoundError(
                f"manifest not found at {self.config.manifest_path}; run the "
                "'export' stage first"
            )
        return evidence.load_manifest(self.config.manifest_path)

    def parent_for(self, task_type: str) -> Path:
        """The parent skill document one family's authoring session edits.

        Flat single-file parent (round 1) or the per-type published set of a
        previous round (round 2+: ``parent_skills_dir``, staged_skills layout).
        """
        if self.config.parent_skills_dir is not None:
            path = self.config.parent_skills_dir / f"{task_type}.md"
            if not path.is_file():
                raise FileNotFoundError(
                    f"per-type parent missing for {task_type}: {path}"
                )
            return path
        return self.config.parent_skill

    def parent_sha_for(self, task_type: str) -> str:
        return _sha256(self.parent_for(task_type))

    # ------------------------------------------------------------------
    # stage 1: export
    # ------------------------------------------------------------------

    def stage_export(self) -> list[evidence.Incident]:
        incidents = evidence.export_run(
            self.config.baseline_run_dir, self.config.out_dir
        )
        self._print(
            f"export: {len(incidents)} incidents "
            f"({sum(1 for i in incidents if i.outcome == 'failure')} failures)"
        )
        return incidents

    # ------------------------------------------------------------------
    # stage 2: diagnose failures
    # ------------------------------------------------------------------

    def stage_diagnose(self, *, limit: int = 0) -> dict[str, Path]:
        incidents = self.load_incidents()
        extra_ids = set(self.config.extra_diagnoses)
        by_id = {i.incident_id: i for i in incidents}
        unknown = extra_ids - set(by_id)
        if unknown:
            raise ValueError(
                f"extra_diagnoses reference unknown incidents: {sorted(unknown)}"
            )
        # Baseline failures plus (in later rounds) previous-round regressions,
        # whose baseline outcome was success: both are repair evidence, and
        # FUSE round 2 explicitly re-authors every family rather than skipping.
        targets = [i for i in incidents if i.outcome == "failure"]
        targets += [by_id[i] for i in sorted(extra_ids) if by_id[i].outcome != "failure"]
        if limit:
            targets = targets[:limit]
        meta_skill = _read_meta_skill("diagnosis")
        diagnoses: dict[str, Path] = {}
        for incident in targets:
            target = self.config.diagnoses_dir / incident.incident_id / "diagnosis.md"
            if target.is_file():
                try:
                    DiagnosticResult.from_markdown(target.read_text(encoding="utf-8"))
                except ValueError:
                    # A cached file that violates the first-line protocol is
                    # not a diagnosis; re-run the session instead of crashing.
                    self._print(
                        f"diagnose: cached {incident.incident_id} invalid; re-running"
                    )
                else:
                    diagnoses[incident.incident_id] = target
                    self._print(f"diagnose: cached {incident.incident_id}")
                    continue
            session_dir = self.config.diagnoses_dir / incident.incident_id / "session"
            workspace = evidence.write_diagnosis_evidence(
                incident,
                session_dir / "evidence",
                meta_skill_text=meta_skill,
                parent_skill_path=self.config.parent_skill,
                baseline_skill_sha=self.config.parent_sha,
                baseline_model=self.config.eval_model,
            )
            runner = SessionRunner(
                self._session_client(),
                workspace,
                "result/diagnosis.md",
                session_dir=session_dir,
            )
            outcome = runner.run(
                f"Diagnose failed ALFWorld episode `{incident.incident_id}` "
                f"(task type `{incident.task_type}`). Follow "
                f"`meta_skill/SKILL.md` exactly and write `result/diagnosis.md`.",
                max_turns=self.config.max_session_turns,
            )
            if not outcome.completed:
                self._print(
                    f"diagnose: INCOMPLETE {incident.incident_id}: {outcome.error}"
                )
                continue
            try:
                DiagnosticResult.from_markdown(outcome.result_text)
            except ValueError as exc:
                self._print(f"diagnose: INVALID {incident.incident_id}: {exc}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(outcome.result_path, target)
            diagnoses[incident.incident_id] = target
            self._print(f"diagnose: ok {incident.incident_id}")
        evidence.attach_diagnoses(self.config.manifest_path, diagnoses)
        return diagnoses

    # ------------------------------------------------------------------
    # stage 3: tag every incident
    # ------------------------------------------------------------------

    def stage_tag(self, *, limit: int = 0) -> list[dict]:
        incidents = self.load_incidents()
        selected = incidents if not limit else incidents[:limit]
        meta_skill = _read_meta_skill("tagging")
        tags: list[dict] = []
        for incident in selected:
            target = self.config.tagging_dir / "incidents" / incident.incident_id / "tags.json"
            if target.is_file():
                try:
                    result = TagResult.from_json(target)
                except ValueError:
                    result = None
                if result is not None:
                    tags.append(json.loads(target.read_text(encoding="utf-8")))
                    self._print(f"tag: cached {incident.incident_id}")
                    continue
            session_dir = (
                self.config.tagging_dir / "incidents" / incident.incident_id / "session"
            )
            workspace = evidence.write_tagging_evidence(
                incident,
                session_dir / "evidence",
                meta_skill_text=meta_skill,
            )
            runner = SessionRunner(
                self._session_client(),
                workspace,
                "result/tags.json",
                session_dir=session_dir,
            )
            outcome = runner.run(
                f"Tag the atomic capabilities required by ALFWorld episode "
                f"`{incident.incident_id}` (task type `{incident.task_type}`, "
                f"outcome `{incident.outcome}`). Follow `meta_skill/SKILL.md` "
                f"exactly and write `result/tags.json`.",
                max_turns=self.config.max_session_turns,
            )
            if not outcome.completed:
                self._print(f"tag: INCOMPLETE {incident.incident_id}: {outcome.error}")
                continue
            try:
                TagResult.from_json(outcome.result_path)
            except ValueError as exc:
                self._print(f"tag: INVALID {incident.incident_id}: {exc}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(outcome.result_path, target)
            tags.append(json.loads(target.read_text(encoding="utf-8")))
            self._print(f"tag: ok {incident.incident_id}")
        with (self.config.tagging_dir / "tags.jsonl").open("w", encoding="utf-8") as f:
            for row in tags:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return tags

    # ------------------------------------------------------------------
    # stage 4: cluster
    # ------------------------------------------------------------------

    def stage_cluster(self) -> dict:
        target = self.config.tagging_dir / "clusters.json"
        if target.is_file():
            clusters = ClusterResult.from_json(target)
            self._print(f"cluster: cached ({len(clusters.capability_clusters)} clusters)")
            return json.loads(target.read_text(encoding="utf-8"))

        tags_path = self.config.tagging_dir / "tags.jsonl"
        if not tags_path.is_file():
            raise FileNotFoundError("tags.jsonl not found; run the 'tag' stage first")
        tags = [
            json.loads(line)
            for line in tags_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not tags:
            raise ValueError("no valid tags to cluster")

        meta_skill = _read_meta_skill("clustering")
        session_dir = self.config.tagging_dir / "clustering_session"
        incidents = self.load_incidents()
        workspace = evidence.write_clustering_evidence(
            incidents, tags, session_dir / "evidence", meta_skill_text=meta_skill
        )
        runner = SessionRunner(
            self._session_client(),
            workspace,
            "result/clusters.json",
            session_dir=session_dir,
        )
        outcome = runner.run(
            f"Cluster {len(tags)} tagged ALFWorld incidents by primary atomic "
            f"capability. Follow `meta_skill/SKILL.md` exactly and write "
            f"`result/clusters.json`.",
            max_turns=self.config.max_session_turns + 20,
        )
        if not outcome.completed:
            raise RuntimeError(f"clustering session incomplete: {outcome.error}")
        clusters = ClusterResult.from_json(outcome.result_path)
        valid_ids = {str(row.get("incident_id")) for row in tags}
        clusters.validate_membership(valid_ids)
        shutil.copyfile(outcome.result_path, target)
        self._print(f"cluster: ok ({len(clusters.capability_clusters)} clusters)")
        return json.loads(target.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # stage 5: author one skill per task type
    # ------------------------------------------------------------------

    def _authoring_families(self) -> dict[str, list[evidence.Incident]]:
        incidents = self.load_incidents()
        families: dict[str, list[evidence.Incident]] = {task: [] for task in TASKS}
        for incident in incidents:
            families.setdefault(incident.task_type, []).append(incident)
        return {task: members for task, members in families.items() if members}

    def stage_author(self, *, only_types: tuple[str, ...] = ()) -> dict[str, Path]:
        tags_path = self.config.tagging_dir / "tags.jsonl"
        clusters_path = self.config.tagging_dir / "clusters.json"
        if not tags_path.is_file() or not clusters_path.is_file():
            raise FileNotFoundError("run the 'tag' and 'cluster' stages first")
        tags = [
            json.loads(line)
            for line in tags_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        clusters = json.loads(clusters_path.read_text(encoding="utf-8"))
        families = self._authoring_families()
        if only_types:
            families = {t: m for t, m in families.items() if t in only_types}

        meta_skill = _read_meta_skill("authoring")
        published: dict[str, Path] = {}
        for task_type, members in sorted(families.items()):
            skill_path = self.config.skills_dir / task_type / "skill.md"
            if skill_path.is_file():
                errors = check_candidate_skill(
                    skill_path.read_text(encoding="utf-8"),
                    max_chars=self.config.max_skill_chars,
                )
                if not errors:
                    published[task_type] = skill_path
                    self._print(f"author: cached {task_type}")
                    continue
                self._print(
                    f"author: cached {task_type} FAILED static check ({errors[0]}); "
                    "re-authoring"
                )
            published[task_type] = self._author_one(
                task_type, members, tags, clusters, meta_skill
            )
        return published

    def _validation_summary_for(self, task_type: str) -> dict | None:
        """Previous-round validation verdicts for one family, or None.

        Filters the config's validation summary down to this family's members
        so each authoring session sees only its own episodes' round-1 record.
        """
        summary = self.config.validation_summary
        if not summary:
            return None
        members = {m.incident_id for m in self._authoring_families().get(task_type, [])}
        rows = {
            incident_id: row for incident_id, row in summary.items()
            if incident_id in members
        }
        if not rows:
            return None
        return {
            "task_type": task_type,
            "attempts": self.config.attempts,
            "gate": "strict majority of attempts",
            "episodes": rows,
        }

    def _author_one(
        self,
        task_type: str,
        members: list[evidence.Incident],
        tags: list[dict],
        clusters: dict,
        meta_skill: str,
    ) -> Path:
        session_dir = self.config.skills_dir / task_type / "session"
        next_attempt = len(list(session_dir.glob("attempt-*"))) + 1
        feedback = ""
        # FUSE retry semantics: one retry carrying the validation error.
        for _ in range(2):
            attempt_dir = session_dir / f"attempt-{next_attempt}"
            next_attempt += 1
            workspace_dir = attempt_dir / "evidence"
            workspace = evidence.write_authoring_evidence(
                task_type,
                members,
                tags,
                clusters,
                workspace_dir,
                meta_skill_text=meta_skill,
                parent_skill_path=self.parent_for(task_type),
                baseline_model=self.config.eval_model,
                baseline_skill_sha=self.parent_sha_for(task_type),
                validation_summary=self._validation_summary_for(task_type),
            )
            # The char budget is part of the protocol the session must see.
            protocol_path = workspace / "protocol.json"
            protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
            protocol["max_skill_chars"] = self.config.max_skill_chars
            protocol_path.write_text(
                json.dumps(protocol, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            runner = SessionRunner(
                self._session_client(),
                workspace,
                "result/skill.md",
                session_dir=attempt_dir,
            )
            prompt = (
                f"Author the complete skill document for the ALFWorld task type "
                f"`{task_type}` ({len(members)} member episodes, "
                f"{sum(1 for m in members if m.outcome == 'failure')} failures). "
                f"Follow `meta_skill/SKILL.md` exactly. Deliver by writing "
                f"`result/skill.md`."
            )
            if feedback:
                prompt += (
                    f"\n\nYour previous attempt was rejected by static validation: "
                    f"{feedback} Fix these issues while keeping every evidence-"
                    f"supported improvement."
                )
            outcome = runner.run(prompt, max_turns=self.config.max_session_turns + 20)
            if not outcome.completed:
                feedback = outcome.error or "session did not deliver result/skill.md"
                self._print(
                    f"author: {task_type} attempt {next_attempt - 1} incomplete: {feedback}"
                )
                continue
            errors = check_candidate_skill(
                outcome.result_text, max_chars=self.config.max_skill_chars
            )
            if not errors:
                target = self.config.skills_dir / task_type / "skill.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(outcome.result_path, target)
                self._print(
                    f"author: ok {task_type} (attempt {next_attempt - 1})"
                )
                return target
            feedback = "; ".join(errors)
            self._print(
                f"author: {task_type} attempt {next_attempt - 1} static check "
                f"failed: {feedback}"
            )
        # Two failures -> generation_failed for this family (kept as status).
        raise RuntimeError(
            f"authoring for {task_type} failed twice (static/session); "
            "recorded as generation_failed"
        )

    # ------------------------------------------------------------------
    # stage 6/7: validate on train members + acceptance
    # ------------------------------------------------------------------

    def _type_manifest(self, task_type: str, members: list[evidence.Incident]) -> Path:
        """items.json for one family's train members (validation corpus)."""
        out = self.config.validations_dir / task_type / "items.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        items = [{"gamefile": m.gamefile} for m in members]
        out.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
        return out

    def _run_eval(
        self,
        *,
        out_base: Path,
        method: str,
        items: Path,
        skill_path: Path | None,
        skill_dir: Path | None,
        skip_warmup: bool = False,
    ) -> Path:
        """Invoke the repository's concurrent eval driver as a subprocess.

        The API key is passed through the environment (never the command
        line), matching the driver's own convention.
        """
        unified_args = [
            "--split", self.config.split,
            "--items", str(items),
            "--seed", "42",
        ]
        if skill_path is not None:
            unified_args += ["--skill-path", str(skill_path)]
        if skill_dir is not None:
            unified_args += ["--skill-dir", str(skill_dir)]
        command = [
            sys.executable,
            str(self.config.project_root / "scripts" / "run_eval_concurrent.py"),
            "--method", method,
            "--shards", str(self.config.shards),
            "--base-url", self.config.eval_base_url,
            "--model", self.config.eval_model,
            "--api-key-env", "FUSE_EVAL_API_KEY",
            "--out-base", str(out_base),
            "--unified-args", " ".join(unified_args),
        ]
        if skip_warmup:
            command.append("--skip-warmup")
        env = {
            **os.environ,
            "FUSE_EVAL_API_KEY": self.config.api_key,
            "ALFWORLD_DATA": str(
                self.config.project_root / ".data" / "alfworld"
            ),
            "PYTHONUNBUFFERED": "1",
        }
        result = subprocess.run(command, cwd=str(self.config.project_root), env=env)
        if result.returncode != 0:
            raise RuntimeError(
                f"eval driver failed (exit {result.returncode}) for {out_base}"
            )
        return out_base / "merged"

    def _attempt_outcomes(self, merged_dir: Path) -> dict[str, dict]:
        """Per-episode outcome of one validation run.

        Returns {episode_key: {success, api_errors}}. Episodes missing from
        results.jsonl are simply absent -- the aggregator treats them as
        infrastructure-unresolved attempts.
        """
        results = merged_dir / "results.jsonl"
        if not results.is_file():
            return {}
        outcomes: dict[str, dict] = {}
        with results.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                key = episode_id(str(row.get("gamefile", "")), 0)
                usage = row.get("usage") or {}
                outcomes[key] = {
                    "success": bool(row.get("success")),
                    "api_errors": int(usage.get("api_errors", 0) or 0),
                }
        return outcomes

    def stage_validate(self, *, only_types: tuple[str, ...] = ()) -> dict[str, dict]:
        """Run N attempts per family member with the candidate skill injected.

        Attempts are separate driver runs (the harness has no in-run repeat
        axis); each attempt's merged dir is kept for audit. Resume: an attempt
        whose merged results.jsonl exists is not re-spent.
        """
        families = self._authoring_families()
        if only_types:
            families = {t: m for t, m in families.items() if t in only_types}
        reports: dict[str, dict] = {}
        for task_type, members in sorted(families.items()):
            skill_path = self.config.skills_dir / task_type / "skill.md"
            if not skill_path.is_file():
                reports[task_type] = {
                    "status": "generation_failed",
                    "task_type": task_type,
                    "members": len(members),
                }
                self._print(f"validate: {task_type} has no authored skill")
                continue
            items = self._type_manifest(task_type, members)
            type_dir = self.config.validations_dir / task_type
            attempts: list[dict[str, dict]] = []
            for attempt_index in range(1, self.config.attempts + 1):
                attempt_dir = type_dir / f"attempt-{attempt_index}"
                merged = attempt_dir / "merged"
                marker = merged / "results.jsonl"
                if marker.is_file():
                    self._print(
                        f"validate: {task_type} attempt {attempt_index} cached"
                    )
                else:
                    self._run_eval(
                        out_base=attempt_dir,
                        method="skillopt",
                        items=items,
                        skill_path=skill_path,
                        skill_dir=None,
                        skip_warmup=attempt_index > 1,
                    )
                attempts.append(self._attempt_outcomes(merged))
            reports[task_type] = {
                "status": "validated",
                "task_type": task_type,
                "skill_sha256": _sha256(skill_path),
                "attempts": attempts,
            }
            self._print(f"validate: {task_type} {self.config.attempts} attempts done")
        (self.config.validations_dir / "attempts.json").write_text(
            json.dumps(reports, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return reports

    def stage_accept(self, *, only_types: tuple[str, ...] = ()) -> dict:
        """Compute gain/regression and the acceptance decision per family."""
        attempts_path = self.config.validations_dir / "attempts.json"
        if not attempts_path.is_file():
            raise FileNotFoundError("run the 'validate' stage first")
        reports = json.loads(attempts_path.read_text(encoding="utf-8"))
        baseline = self._baseline_outcomes()
        summary: dict = {"families": {}, "accepted": [], "validation_failed": [],
                         "generation_failed": []}
        for task_type, report in sorted(reports.items()):
            if only_types and task_type not in only_types:
                continue
            if report.get("status") != "validated":
                summary["families"][task_type] = report
                summary[report.get("status", "generation_failed")].append(task_type)
                continue
            members = self._authoring_families().get(task_type, [])
            member_eval: list[dict] = []
            for incident in members:
                key = incident.incident_id
                base_success = baseline.get(key, {}).get("success")
                attempt_rows = []
                for attempt in report["attempts"]:
                    row = attempt.get(key)
                    attempt_rows.append(
                        {"success": bool(row["success"]) if row else None,
                         "present": row is not None}
                    )
                successes = sum(1 for r in attempt_rows if r["success"])
                present = sum(1 for r in attempt_rows if r["present"])
                missing = len(attempt_rows) - present
                passed = successes * 2 > len(attempt_rows)  # strict majority
                # FUSE rule: an attempt with no recorded result is an
                # infrastructure slot, not a failure. When such a slot exists
                # and the episode did not pass, the pass/fail verdict cannot
                # be trusted, so the episode is infrastructure-unresolved and
                # never counts as a regression.
                if base_success is None:
                    verdict = "not_in_baseline"
                elif passed:
                    verdict = "pass"
                elif missing > 0:
                    verdict = "infrastructure_unresolved"
                else:
                    verdict = "fail"
                member_eval.append({
                    "incident_id": key,
                    "baseline_success": base_success,
                    "attempt_successes": successes,
                    "attempts_present": present,
                    "passed": passed,
                    "verdict": verdict,
                })
            judgeable = [m for m in member_eval if m["verdict"] in ("pass", "fail")]
            regressions = [
                m["incident_id"] for m in judgeable
                if m["baseline_success"] and m["verdict"] == "fail"
            ]
            gains = [
                m["incident_id"] for m in judgeable
                if not m["baseline_success"] and m["verdict"] == "pass"
            ]
            had_failures = any(
                not m["baseline_success"]
                for m in member_eval
                if m["baseline_success"] is not None
            )
            if regressions:
                accepted = False
                reason = f"regressions: {regressions}"
            elif had_failures and not gains:
                accepted = False
                reason = "family had failures but no gain"
            elif not judgeable and member_eval:
                accepted = False
                reason = "all members infrastructure-unresolved"
            else:
                accepted = True
                reason = (
                    "all members pass" if not had_failures
                    else f"gains: {gains}"
                )
            family_report = {
                "status": "accepted" if accepted else "validation_failed",
                "task_type": task_type,
                "skill_sha256": report.get("skill_sha256", ""),
                "n_members": len(members),
                "regressions": regressions,
                "gains": gains,
                "reason": reason,
                "members": member_eval,
            }
            summary["families"][task_type] = family_report
            summary["accepted" if accepted else "validation_failed"].append(task_type)
            self._print(
                f"accept: {task_type} -> {family_report['status']} ({reason})"
            )
        out = self.config.out_dir / "report.json"
        out.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return summary

    def _baseline_outcomes(self) -> dict[str, dict]:
        """Per-episode comparison baseline for the acceptance gate.

        Round 1 compares against the original baseline run. A later round
        supplies ``baseline_outcomes_override`` instead: the *published
        system of the previous round* (accepted candidates where they passed
        the majority gate, parent fallback elsewhere), which is what a round-2
        candidate must not regress against.
        """
        override = self.config.baseline_outcomes_override
        if override is not None:
            return {
                incident_id: {"success": bool(row.get("success", False))}
                for incident_id, row in override.items()
            }
        results = self.config.baseline_run_dir / "results.jsonl"
        outcomes: dict[str, dict] = {}
        if not results.is_file():
            return outcomes
        with results.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                outcomes[episode_id(str(row.get("gamefile", "")), 0)] = {
                    "success": bool(row.get("success")),
                }
        return outcomes

    # ------------------------------------------------------------------
    # stage 8: staging of the routed publish set
    # ------------------------------------------------------------------

    def stage_stage(self) -> Path:
        """Materialize ``staged_skills/<task_type>.md``.

        Publish rule (conservative, and stricter than the original which kept
        validation_failed skills): only accepted candidates are published;
        every other type falls back to the parent skill so the routed system
        never contains a regressing document.
        """
        report_path = self.config.out_dir / "report.json"
        if not report_path.is_file():
            raise FileNotFoundError("run the 'accept' stage first")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        staged = self.config.staged_dir
        staged.mkdir(parents=True, exist_ok=True)
        published: dict[str, str] = {}
        for task_type in TASKS:
            family = report.get("families", {}).get(task_type)
            if family and family.get("status") == "accepted":
                source = self.config.skills_dir / task_type / "skill.md"
            elif self.config.parent_skills_dir is not None:
                # Round 2+: the floor is the previous round's published
                # document for this type, not the original flat parent.
                source = self.parent_for(task_type)
            else:
                source = self.config.parent_skill
            target = staged / f"{task_type}.md"
            shutil.copyfile(source, target)
            published[task_type] = _sha256(target)
        (staged / "staging.json").write_text(
            json.dumps({
                "per_type": published,
                "parent_sha256": (
                    _sha256(self.config.parent_skills_dir / f"{TASKS[0]}.md")
                    if self.config.parent_skills_dir is not None
                    else self.config.parent_sha
                ),
                "parent_skills_dir": (
                    str(self.config.parent_skills_dir)
                    if self.config.parent_skills_dir is not None else ""
                ),
                "report": {
                    t: r.get("status") for t, r in report.get("families", {}).items()
                },
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        self._print(f"stage: {len(published)} documents -> {staged}")
        return staged

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        c = self.config
        return {
            "manifest": c.manifest_path.is_file(),
            "diagnoses": len(list(c.diagnoses_dir.glob("*/diagnosis.md"))),
            "tags": len(list((c.tagging_dir / "incidents").glob("*/tags.json")))
            if (c.tagging_dir / "incidents").is_dir() else 0,
            "clusters": (c.tagging_dir / "clusters.json").is_file(),
            "skills": sorted(
                p.parent.name for p in c.skills_dir.glob("*/skill.md")
            ),
            "validations": sorted(
                p.name for p in c.validations_dir.iterdir()
                if p.is_dir() and (p / "attempt-1").is_dir()
            ) if c.validations_dir.is_dir() else [],
            "report": (c.out_dir / "report.json").is_file(),
            "staged": sorted(
                p.name for p in c.staged_dir.glob("*.md")
            ) if c.staged_dir.is_dir() else [],
        }
