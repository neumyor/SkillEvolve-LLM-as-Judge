# Success Memory Item 1
## Title
Pattern Recognition for Abbreviated Query Formats
## Description
Identify and adapt to non-conversational, trivia-style, or colon-separated prompts by mapping their components directly to factual entity requests.
## Content
When encountering terse inputs like "Year:Person" or fragmented phrases, treat them as direct lookup requests rather than conversational questions. Strip away assumed narrative framing and isolate the core constraints (e.g., temporal marker + subject) to guide retrieval alignment and answer formulation.

# Success Memory Item 2
## Title
Consensus-Driven Entity Selection
## Description
Prioritize answers that appear consistently across multiple independent context snippets, even when presented in varied formats (titles, cast lists, reviews, or metadata).
## Content
Scan all retrieved documents for overlapping references to the prompt's key constraints. If disparate sources (Wikipedia, IMDb, archives, reviews) independently converge on the same entity matching those constraints, treat the convergence as sufficient evidence and select it without seeking additional corroboration.

# Success Memory Item 3
## Title
Constraint-Compliant Output Isolation
## Description
Generate responses that strictly adhere to formatting requirements by isolating the final answer and suppressing all auxiliary text.
## Content
After determining the target entity, immediately wrap it in the specified tags and output only that string. Omit reasoning traces, confirmations, or supplementary explanations to ensure clean machine parsing and maintain strict compliance with structural constraints.
