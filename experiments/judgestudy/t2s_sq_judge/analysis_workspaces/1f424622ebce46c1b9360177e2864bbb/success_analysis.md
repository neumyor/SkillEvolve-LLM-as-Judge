# Success Memory Item 1
## Title
Entity-Driven Snippet Scanning
## Description
Map core prompt identifiers directly to retrieved text to isolate the target answer.
## Content
Extract key variables (e.g., year, performer, subject category) from the query and scan document titles and excerpts for exact matches. Prioritize snippets where all variables converge on a single entity, bypassing irrelevant or tangential results.

# Success Memory Item 2
## Title
Multi-Doc Consensus Validation
## Description
Confirm factual claims by checking for consistent statements across independent retrieval results.
## Content
When multiple documents independently report the same name or fact, treat the overlap as sufficient confirmation. Rely on explicit convergence rather than complex synthesis, and avoid introducing external assumptions when the context already aligns.

# Success Memory Item 3
## Title
Constraint-Strict Output Wrapping
## Description
Enforce structural requirements immediately after answer identification to ensure compliance.
## Content
Once the target information is isolated, skip explanatory text and directly enclose the result in the specified tags. Maintain absolute minimalism in the final output to satisfy automated parsing rules and scoring criteria.
