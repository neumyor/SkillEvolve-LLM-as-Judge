# Repository notes

Use the parent workspace `AGENTS.md` for experiment safety and measurement
rules. In particular, do not launch an expensive run before independent smoke,
invariant, control, metric and statistics checks have passed. Persist each unit
as it completes and audit it before including its numbers in an analysis.

Source packages are independent projects:

- `packages/skillopt`
- `packages/gepa`
- `packages/skillgen`
- `packages/rethinkskill` and `packages/rethinkskill_study`
- `packages/searchqa-eval`
- `packages/alfworld-eval`

Split manifests and selected benchmark data are part of this assembled
reproduction repository. Caches, virtualenvs and endpoint credentials are
machine-local and ignored by Git. Do not copy credentials into source modules
or shell scripts; use `benchmark/llm_config.local.json` or environment
overrides. The committed `benchmark/llm_config.example.json` contains only
placeholders. Configure the external ALFWorld benchmark root locally rather
than relying on the author's workspace layout.
