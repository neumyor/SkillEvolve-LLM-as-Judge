# FUSE Capability Clustering (ALFWorld)

Cluster the tagged incidents by their primary atomic capability. Read `tags.jsonl` first — one line per incident, each with `capability_tags`, `capability_summary`, `outcome`, and `task_type`. Only read an incident's trajectory under `incidents/<id>/trajectory.jsonl` when a capability boundary is unclear from the tags alone.

Write the result to `result/clusters.json` with the write tool, in this exact shape:

```json
{
  "schema_version": 1,
  "capability_clusters": [
    {
      "cluster_id": "capability-c001",
      "label": "concise action-oriented label",
      "definition": "shared operation, object, precondition, and completion contract",
      "decision": "merge",
      "member_ids": ["<incident ids>"]
    }
  ]
}
```

## Completion Contract

The host reads only `result/clusters.json`; a final reply is not a delivery. Use the `write_file` tool before ending. Every incident present in `tags.jsonl` must be a member of exactly one cluster, and clusters must be disjoint.

## Clustering rules

- Each incident is represented by its **primary** atomic capability: the one that most directly produces the episode's deliverable (e.g. for a heating task, "heat an object with the correct appliance", not "navigate rooms"). The remaining tags stay in the incident row and must not be re-used as membership.
- Judge boundaries by the primary capability's operation, object, precondition state, and completion criterion — not by task-type label, outcome, summary similarity, or surface wording. Do not use embeddings, thresholds, or score matching; decide.
- `decision` is one of `merge` (episodes share the full capability contract), `split` (the boundary needs division), `retain-separate` (a genuine singleton), `ambiguous`, or `unclassified`.
- Two episodes with the same primary capability belong to the same cluster even when one succeeded and one failed, and even when they are of different ALFWorld task types. Outcome and task type are metadata, not cluster keys.
- Do not force a fixed number of clusters; do not create one cluster per task type by default. Let the primary capabilities decide.
