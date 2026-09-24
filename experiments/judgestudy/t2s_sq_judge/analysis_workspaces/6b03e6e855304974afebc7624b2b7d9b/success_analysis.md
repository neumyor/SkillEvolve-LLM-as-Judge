# Success Memory Item 1
## Title
Parse Colon-Separated Association Queries
## Description
Identify the structural pattern of trivia or entity-linking questions formatted as `[Descriptor]:[Context/Entity]` to determine the required relationship.
## Content
When encountering prompts structured as a descriptive phrase followed by a colon and a specific entity, treat it as a request to identify the subject that connects both elements. Map the descriptor to the target entity using the retrieved context to isolate the missing piece.

# Success Memory Item 2
## Title
Leverage Explicit Relational Phrases in Context
## Description
Scan retrieved documents for direct action or possession verbs that link the query's descriptor to the given entity.
## Content
Focus on contextual sentences containing keywords that establish the relationship (e.g., "knighted aboard," "captain of," "famous ship"). Use these explicit links to verify the correct subject without inferring beyond the provided text.

# Success Memory Item 3
## Title
Extract Exact Named Entities for Final Output
## Description
Isolate the precise proper noun or full name that satisfies the query, ensuring strict compliance with formatting constraints.
## Content
Once the connecting subject is identified, extract only the exact name/title mentioned in the context. Avoid paraphrasing or adding explanatory text, and wrap the result in the required tags to meet evaluation criteria.
