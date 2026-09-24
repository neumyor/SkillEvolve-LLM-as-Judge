# Success Memory Item 1
## Title
Constraint-Aligned Entity Resolution
## Description
Systematically map specific temporal, editorial, or factual constraints from the prompt onto retrieved context to isolate the correct entity, while actively filtering out closely related distractors that fail to meet the full constraint set.
## Content
1. Parse the prompt to isolate hard constraints (e.g., author, publication year, editing/restoration year, specific textual changes).
2. Scan retrieved context for exact alignment with these constraints, prioritizing sources that explicitly link multiple constraints to a single title or subject.
3. Compare candidate entities against the constraint set; discard any that share partial metadata (e.g., same author or era) but mismatch critical details.
4. Confirm the remaining entity satisfies all constraints before generating a concise final answer.
