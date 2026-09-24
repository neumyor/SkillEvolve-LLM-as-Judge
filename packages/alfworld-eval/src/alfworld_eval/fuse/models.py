"""Host-side protocol models for the FUSE adaptation.

These mirror the JSON/markdown shells the original FUSE host validates
(``fuse/models.py`` in SkillEvolveCPM): the host parses only the minimal
protocol surface and never re-derives the model's conclusions.

Differences from the original, forced by this harness:

* the diagnostic decision protocol is unchanged (first non-empty line must be
  exactly ``Decision: evolve|no_change|inconclusive``);
* tags keep the original schema (atomic capability tags + summary);
* clusters keep the original decision vocabulary
  (``merge|split|retain-separate|ambiguous|unclassified``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DECISIONS = ("evolve", "no_change", "inconclusive")
CLUSTER_DECISIONS = ("merge", "split", "retain-separate", "ambiguous", "unclassified")


@dataclass
class DiagnosticResult:
    """The parsed first line of a diagnosis plus its free-form markdown."""

    decision: str
    markdown: str

    @classmethod
    def from_markdown(cls, text: str) -> "DiagnosticResult":
        lines = [line.strip() for line in str(text or "").splitlines()]
        first = next((line for line in lines if line), "")
        if not first.startswith("Decision:"):
            raise ValueError(
                "diagnosis must start with 'Decision: evolve|no_change|inconclusive'"
            )
        decision = first[len("Decision:"):].strip()
        if decision not in DECISIONS:
            raise ValueError(f"unknown diagnosis decision: {decision!r}")
        return cls(decision=decision, markdown=str(text or ""))

    def to_dict(self) -> dict:
        return {"decision": self.decision, "markdown": self.markdown}


@dataclass
class TagResult:
    """Capability tags for one incident (one episode)."""

    incident_id: str
    outcome: str  # success | failure -- manifest metadata only
    capability_tags: list[str] = field(default_factory=list)
    capability_summary: str = ""

    @classmethod
    def from_json(cls, payload: dict | str | Path) -> "TagResult":
        if isinstance(payload, Path):
            payload = json.loads(payload.read_text(encoding="utf-8"))
        elif isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise ValueError("tags payload must be a JSON object")
        tags = payload.get("capability_tags")
        if not isinstance(tags, list) or not tags:
            raise ValueError("capability_tags must be a non-empty list")
        if not all(isinstance(tag, str) and tag.strip() for tag in tags):
            raise ValueError("every capability tag must be a non-empty string")
        summary = payload.get("capability_summary", "")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("capability_summary must be a non-empty string")
        incident_id = payload.get("incident_id")
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise ValueError("incident_id must be a non-empty string")
        outcome = payload.get("outcome", "")
        if outcome not in ("success", "failure"):
            raise ValueError("outcome must be 'success' or 'failure'")
        return cls(
            incident_id=incident_id,
            outcome=outcome,
            capability_tags=[str(tag).strip() for tag in tags],
            capability_summary=summary.strip(),
        )


@dataclass
class CapabilityCluster:
    cluster_id: str
    label: str
    definition: str
    decision: str
    member_ids: list[str] = field(default_factory=list)


@dataclass
class ClusterResult:
    """Batch capability clustering over all tagged incidents."""

    capability_clusters: list[CapabilityCluster] = field(default_factory=list)

    @classmethod
    def from_json(cls, payload: dict | str | Path) -> "ClusterResult":
        if isinstance(payload, Path):
            payload = json.loads(payload.read_text(encoding="utf-8"))
        elif isinstance(payload, str):
            payload = json.loads(payload)
        clusters_raw = payload.get("capability_clusters") if isinstance(payload, dict) else None
        if not isinstance(clusters_raw, list) or not clusters_raw:
            raise ValueError("capability_clusters must be a non-empty list")
        clusters: list[CapabilityCluster] = []
        for raw in clusters_raw:
            if not isinstance(raw, dict):
                raise ValueError("each cluster must be a JSON object")
            cluster_id = raw.get("cluster_id")
            label = raw.get("label")
            definition = raw.get("definition")
            decision = raw.get("decision")
            members = raw.get("member_ids")
            if not all(isinstance(v, str) and v.strip()
                       for v in (cluster_id, label, definition, decision)):
                raise ValueError(
                    "cluster_id, label, definition and decision must be non-empty strings"
                )
            if decision not in CLUSTER_DECISIONS:
                raise ValueError(f"unknown cluster decision: {decision!r}")
            if not isinstance(members, list) or not all(
                isinstance(m, str) and m.strip() for m in members
            ):
                raise ValueError("member_ids must be a list of non-empty strings")
            clusters.append(CapabilityCluster(
                cluster_id=cluster_id.strip(),
                label=label.strip(),
                definition=definition.strip(),
                decision=decision,
                member_ids=[str(m).strip() for m in members],
            ))
        return cls(capability_clusters=clusters)

    def validate_membership(self, valid_incident_ids: set[str]) -> None:
        """Every valid incident belongs to exactly one cluster (FUSE rule).

        Unknown member ids are tolerated (the session may reference the
        manifest's stable ids only; anything else is dropped by the host when
        assembling authoring evidence), but a *missing* valid incident would
        silently shrink a family's evidence, so it is an error.
        """
        seen: dict[str, str] = {}
        for cluster in self.capability_clusters:
            for member in cluster.member_ids:
                if member in seen and seen[member] != cluster.cluster_id:
                    raise ValueError(
                        f"incident {member!r} appears in both {seen[member]!r} "
                        f"and {cluster.cluster_id!r}; clusters must be disjoint"
                    )
                seen[member] = cluster.cluster_id
        missing = sorted(valid_incident_ids - set(seen))
        if missing:
            raise ValueError(
                f"{len(missing)} tagged incidents are not members of any cluster: "
                f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
            )


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
