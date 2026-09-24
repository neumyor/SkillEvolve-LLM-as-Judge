# Success Memory Item 1
## Title
Direct Descriptor Alignment
## Description
Map specific query modifiers to explicit contextual statements to isolate the target entity.
## Content
Decompose the question into key attributes (e.g., physical shape, cultural origin, function). Scan retrieved passages for sentences that simultaneously contain these attributes. When a single source explicitly links all modifiers to a specific term, extract that term directly as the answer.

# Success Memory Item 2
## Title
Semantic Equivalence Bridging
## Description
Recognize and map synonymous or descriptive variations between the prompt and the knowledge base.
## Content
Queries frequently use simplified or alternative phrasing compared to reference texts. Identify that descriptive terms in the prompt (e.g., "sickle-shaped") may correspond to related terms in the context (e.g., "crescent" or "bent"). Confirm semantic overlap to validate the candidate entity before extraction.

# Success Memory Item 3
## Title
Constraint-First Filtering
## Description
Prioritize exact matches to all query conditions while discarding partial or tangential matches.
## Content
Evaluate each retrieved document against every constraint in the prompt simultaneously. Eliminate candidates that satisfy only some conditions. Finalize the response with the single entity that fully satisfies the combined constraints, outputting only the precise term without supplementary elaboration.
