# Success Memory Item 1
## Title
Direct Extraction from Structured Retrieval Snippets
## Description
Parse delimiter-separated or clearly formatted context blocks to isolate factual answers without requiring external synthesis.
## Content
Scan retrieved documents for exact keyword alignment with the prompt. When context uses consistent separators (e.g., pipes or colons) between queries and responses, treat the adjacent segment as the definitive answer. Extract only the core entity or term, ignoring surrounding metadata or partial matches.

# Success Memory Item 2
## Title
Constraint-First Output Generation
## Description
Prioritize strict adherence to formatting instructions immediately after information retrieval to ensure compliance.
## Content
Upon identifying the target information, cross-check against explicit output requirements (tag usage, length limits, tone). Construct the final response using only the mandated structure and extracted value. Omit reasoning traces, explanations, or conversational elements that risk violating constraints.

# Success Memory Item 3
## Title
Factoid Resolution via Contextual Mirroring
## Description
Resolve trivia and definition-based questions by treating them as direct lookup operations when context provides complete statements.
## Content
Match the question's phrasing to contextual sentences. If the context contains a self-contained statement mirroring the query, isolate the referenced component (typically a proper noun, title, or date). Validate that the extracted term directly satisfies the prompt's semantic gap before finalizing.
