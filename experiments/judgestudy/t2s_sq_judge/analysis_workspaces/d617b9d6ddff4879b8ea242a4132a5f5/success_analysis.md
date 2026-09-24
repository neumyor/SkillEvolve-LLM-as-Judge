# Success Memory Item 1
## Title
Cross-Document Consensus Validation
## Description
Prioritize answers that are independently corroborated by multiple retrieved snippets to establish high-confidence factual grounding.
## Content
When processing retrieval-augmented queries, scan all provided documents for overlapping claims. If multiple sources explicitly state the same entity or fact, treat that convergence as strong evidence and proceed with extraction, reducing reliance on any single potentially noisy source.

# Success Memory Item 2
## Title
Contextual Resolution of Truncated or Conflicting Snippets
## Description
Do not allow isolated contradictory or cut-off text to derail the answer; evaluate anomalies against the broader context and prioritize direct, unambiguous matches.
## Content
If a snippet appears to contradict the majority or seems incomplete, assess whether it references a different subject, lacks full context, or is truncated. Maintain focus on clear, direct statements that satisfy all question constraints, and use logical inference to dismiss outliers that lack supporting evidence across the rest of the corpus.

# Success Memory Item 3
## Title
Constraint-Mapped Entity Extraction
## Description
Decompose the prompt into explicit criteria, match retrieved facts directly to each condition, and enforce strict output formatting without extraneous text.
## Content
Break down the question into specific requirements (e.g., "wrote X" AND "held role Y"). Scan the context to find an entity that satisfies every condition simultaneously. Extract only that exact entity, verify it aligns with all constraints, and place it inside the required tags without additional commentary or filler.
