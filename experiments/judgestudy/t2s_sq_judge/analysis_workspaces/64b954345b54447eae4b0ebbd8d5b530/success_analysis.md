# Success Memory Item 1
## Title
Multi-Constraint Keyword Mapping
## Description
Decompose trivia prompts into discrete filters (e.g., year, performer, theme) and systematically scan retrieved context for entities satisfying all conditions simultaneously.
## Content
Isolate explicit identifiers from the question. Iterate through the context list, flagging any document that contains matching values for each filter. Prioritize candidates where every constraint aligns before proceeding to answer generation.

# Success Memory Item 2
## Title
Literal Anchoring for Idiomatic Queries
## Description
Resolve puns or double-meaning phrases by identifying their concrete, factual counterpart within the provided context.
## Content
When a question employs colloquial language or wordplay, map the phrase to its literal subject matter present in the documents. Use the contextual evidence to ground the interpretation, ensuring the selected entity matches both the figurative hint and the explicit factual parameters.

# Success Memory Item 3
## Title
Cross-Snippet Convergence Confirmation
## Description
Treat consistent references to the same entity across multiple independent context sources as sufficient grounds for direct extraction.
## Content
If disparate snippets (trivia, reviews, cast listings, news) repeatedly associate the query’s key identifiers with a single title or name, consider this pattern definitive. Bypass further searching and output the convergent entity directly, as retrieval redundancy indicates high confidence.
