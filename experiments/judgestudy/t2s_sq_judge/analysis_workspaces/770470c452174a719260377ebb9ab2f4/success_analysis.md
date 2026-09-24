# Success Memory Item 1
## Title
Exact Phrase Matching for Factoid Queries
## Description
Prioritize scanning retrieved snippets for verbatim overlaps when processing highly specific biographical or trivia-style questions.
## Content
When a question contains precise dates, locations, or narrative phrasing, search the retrieved context for direct textual matches rather than relying exclusively on semantic similarity. Exact overlaps often point to structured knowledge bases, trivia archives, or encyclopedia entries formatted as direct Q&A pairs. Once a candidate is identified through phrasing alignment, cross-reference key identifiers (names, dates, places) across multiple retrieved documents to ensure internal consistency before extracting the final answer. This method rapidly isolates the correct entity while minimizing ambiguity in factoid retrieval tasks.
