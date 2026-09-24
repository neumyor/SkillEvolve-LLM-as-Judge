# Success Memory Item 1
## Title
Cross-Source Corroboration
## Description
Confirm the target answer is consistently referenced across multiple retrieved documents before selection.
## Content
Scan all provided context snippets for recurring entities or phrases tied to the query. Prioritize candidates that appear in independent passages to filter out noise, tangential mentions, or contradictory information.

# Success Memory Item 2
## Title
Constraint Mapping
## Description
Align the extracted answer with every explicit condition stated in the prompt.
## Content
Break down the question into its core requirements (e.g., entity type, temporal markers, relational descriptors). Test the candidate answer against each requirement to ensure direct relevance rather than superficial keyword matching.

# Success Memory Item 3
## Title
Format Enforcement
## Description
Wrap the final answer strictly within the specified structural tags without supplementary text.
## Content
After isolating the correct answer, immediately apply the mandated wrapper (e.g., `<answer>...</answer>`). Exclude reasoning, qualifiers, or conversational filler to guarantee seamless parsing and compliance with evaluation pipelines.
