# Success Memory Item 1
## Title
Targeted Attribute Isolation
## Description
Deconstruct the prompt to separate the core entity from the specific attribute being queried, guiding the search toward exact matches rather than broad summaries.
## Content
Identify the subject and the requested detail. Scan retrieved documents for phrases that explicitly link the subject to the detail, then extract only the precise substring corresponding to the requested attribute.

# Success Memory Item 2
## Title
Direct Text Grounding
## Description
Prioritize explicit statements in the context over inferred connections to ensure accuracy and minimize hallucination.
## Content
Locate sentences that directly state the relationship between the entity and the attribute. Use these verbatim anchors to confirm the answer, discarding ambiguous or tangential mentions that do not explicitly satisfy the query.

# Success Memory Item 3
## Title
Constraint-Aligned Formatting
## Description
Apply output specifications immediately after extraction to maintain compliance and readability.
## Content
Once the exact answer is isolated, strip all explanatory text or intermediate steps. Wrap the concise result strictly within the required delimiters, ensuring the final output contains only the requested value.
