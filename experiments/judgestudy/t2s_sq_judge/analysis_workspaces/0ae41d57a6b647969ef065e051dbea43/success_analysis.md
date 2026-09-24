# Success Memory Item 1
## Title
Exact Phrase Matching for Entity Resolution
## Description
When a question contains a distinctive proper noun or geographic feature, scan the retrieved context for exact or near-exact phrase repetitions to immediately identify the target entity.
## Content
Prioritize context snippets that mirror the query's terminology. A single explicit match often yields the complete answer without requiring cross-document synthesis or complex inference.

# Success Memory Item 2
## Title
Prioritize High-Signal Declarative Snippets
## Description
Favor context passages that function as standalone definitions or flashcards, as they typically contain direct answers structured identically to the prompt.
## Content
Identify documents with clear, self-contained statements matching the question's premise. These high-signal excerpts reduce ambiguity and eliminate the need to aggregate fragmented facts.

# Success Memory Item 3
## Title
Strict Format Enforcement
## Description
Immediately wrap the identified answer in the required output tags upon extraction to guarantee compliance with evaluation metrics.
## Content
After locating the target entity, apply the specified formatting convention (e.g., `<answer>...</answer>`) and verify structural correctness before final submission.
