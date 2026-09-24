# Success Memory Item 1
## Title
Resolve Multi-Clue Entity Queries via Overlap
## Description
When a question identifies a target through multiple associated works or titles, locate the common entity that satisfies all descriptors simultaneously.
## Content
Parse each clue in the prompt (e.g., a specific book title and a famous character or series). Scan the retrieved context for documents that explicitly link the same named individual to every clue. Select the entity that appears consistently across all referenced attributes to ensure complete alignment with the query.

# Success Memory Item 2
## Title
Leverage Redundant Contextual Confirmation
## Description
Prioritize direct textual matches where multiple independent snippets converge on a single answer, reducing ambiguity.
## Content
Treat repeated mentions of the same name across different document titles, editorial reviews, and metadata as strong validation. When multiple sources independently associate the target entity with the given clues, extract the name directly without requiring external knowledge or complex inference.

# Success Memory Item 3
## Title
Enforce Constraint-Aware Output Generation
## Description
Strip extraneous information and strictly adhere to formatting rules when delivering the final response.
## Content
After isolating the correct entity, remove all explanatory text, alternative names, or contextual details. Place only the precise, unmodified answer inside the specified tags to guarantee compliance with strict evaluation metrics and user instructions.
