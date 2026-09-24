# Success Memory Item 1
## Title
Exact-Phrase Matching for Declarative Trivia Questions
## Description
Map statement-style questions directly to retrieved context snippets to quickly identify the target entity, then resolve implicit references to the document's primary subject.
## Content
When presented with a trivia-style clue formatted as a declarative sentence, scan the retrieved context for verbatim or near-verbatim phrase overlaps. Upon locating a matching snippet, extract the main subject of that source document. Replace any pronouns or implied actors in the question with this identified subject. Confirm the mapping by ensuring details align across corroborating context snippets before generating the final response.
