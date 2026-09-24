# Success Memory Item 1
## Title
Constraint-Driven Entity Mapping
## Description
Align explicit temporal, role, and action markers from the query with corresponding phrases in the retrieved documents to isolate the target subject.
## Content
Extract key identifiers (dates, positions, events) from the prompt and scan context snippets for exact or synonymous matches. Prioritize entities where all specified constraints converge simultaneously, treating the query as a set of filtering conditions rather than a narrative description.

# Success Memory Item 2
## Title
Multi-Passage Corroboration
## Description
Leverage redundant information across multiple retrieved sources to verify entity identity before committing to an answer.
## Content
When several independent passages consistently report the same sequence of facts regarding a single individual, use this consensus as a reliable signal for correct identification. Cross-referencing overlapping details reduces false positives from ambiguous or partially matching snippets.

# Success Memory Item 3
## Title
Structural Constraint Enforcement
## Description
Strictly adhere to output formatting rules by isolating the final answer within designated tags and omitting extraneous reasoning in the final response.
## Content
After determining the correct entity, strip all intermediate analysis and output only the requested value wrapped in the specified delimiters. Maintaining rigid compliance with structural requirements prevents parsing failures and ensures seamless integration with downstream evaluation systems.
