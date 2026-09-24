# Success Memory Item 1
## Title
Targeted Entity Mapping
## Description
Isolate key proper nouns and phrases from the query to scan context for direct entity overlaps.
## Content
Extract core identifiers (e.g., artist names, song titles, roles) from the question and search retrieved documents for explicit co-occurrences. Prioritize passages that directly link these entities to form a strong candidate answer.

# Success Memory Item 2
## Title
Cross-Passage Convergence
## Description
Confirm answer reliability by identifying consistent mentions across multiple independent context snippets.
## Content
When several retrieved documents independently state the same fact or name regarding the query, treat this consensus as sufficient evidence. Rely on this multi-source alignment to finalize the answer without requiring additional external validation.

# Success Memory Item 3
## Title
Constraint-First Formatting
## Description
Apply requested output wrappers immediately after answer derivation to ensure compliance.
## Content
Once the target information is identified, wrap it precisely in the specified tags (e.g., `<answer>...</answer>`). Maintain clear separation between internal reasoning steps and the final formatted output to prevent structural errors.
