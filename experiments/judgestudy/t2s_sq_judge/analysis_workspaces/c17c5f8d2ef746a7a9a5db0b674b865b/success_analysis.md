# Success Memory Item 1
## Title
Multi-Constraint Co-occurrence Scanning
## Description
Isolate the correct answer by identifying the specific context segment where all distinct query modifiers appear together, rather than relying on thematic relevance alone.
## Content
When a question contains multiple independent constraints (e.g., a specific variant, a dietary condition, and an ingredient), scan the retrieved documents for the exact sentence or phrase where these terms intersect. Direct co-occurrence strongly indicates the source of the factual answer and reduces ambiguity caused by loosely related passages.

# Success Memory Item 2
## Title
Compound Term Decomposition
## Description
Parse indirect question phrasing that references a category or base item to correctly extract the target noun from a compound phrase in the text.
## Content
Questions often use structural cues like "[Modifier] type of this" or "the [X] version of [Y]". Map these cues to compound expressions in the context (e.g., "Denver Omelet") and isolate the core noun ("Omelet") as the answer. This ensures the response matches the grammatical and semantic expectation of the prompt without overcomplicating the extraction.

# Success Memory Item 3
## Title
Verbatim Context Alignment
## Description
Prioritize exact or near-exact lexical extraction from the retrieved context over generative paraphrasing for factual and trivia-style queries.
## Content
For knowledge-retrieval tasks, avoid synthesizing novel phrasing. Identify the precise string in the context that satisfies all prompt conditions and extract it directly. Minimal grammatical adjustment preserves accuracy, prevents hallucination, and aligns with standard evaluation metrics that reward exact matches.
