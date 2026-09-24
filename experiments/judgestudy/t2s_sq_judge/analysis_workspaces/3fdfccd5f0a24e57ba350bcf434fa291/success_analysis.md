# Success Memory Item 1
## Title
Temporal-Descriptive Entity Mapping
## Description
Align queries specifying a precise year and outcome directly with context snippets sharing those exact parameters.
## Content
When a question pairs a date with a descriptive result (e.g., territorial completion), prioritize extracting the named entity that simultaneously satisfies the year, event type, and described effect. This direct parameter matching eliminates ambiguity and accelerates answer isolation.

# Success Memory Item 2
## Title
Multi-Snippet Convergence Confirmation
## Description
Treat independent contextual passages stating the same fact as immediate high-confidence signals.
## Content
When multiple retrieved documents independently name the identical answer, use this redundancy to rapidly establish certainty. Skip speculative reasoning or additional searches, and proceed directly to answer formulation once convergence is observed.

# Success Memory Item 3
## Title
Constraint-First Output Generation
## Description
Enforce strict formatting requirements immediately upon answer identification to prevent structural failures.
## Content
Once the target term is verified, bypass all explanatory text or conversational filler. Place only the concise answer inside the specified delimiters to guarantee full compliance with evaluation metrics and user instructions.
