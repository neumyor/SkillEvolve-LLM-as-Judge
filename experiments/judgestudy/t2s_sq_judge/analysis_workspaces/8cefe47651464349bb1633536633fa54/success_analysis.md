# Success Memory Item 1
## Title
Exact Phrasing Alignment for Factoid Retrieval
## Description
Prioritize locating sentences in the retrieved context that structurally mirror the prompt's wording to enable direct answer extraction.
## Content
When prompts contain highly specific temporal, numerical, or causal markers, search for verbatim or near-verbatim matches in the context. Reference materials, flashcards, and study guides frequently embed the exact question phrasing alongside its answer. Treat the matched sentence as a direct lookup rather than requiring multi-step inference.

# Success Memory Item 2
## Title
Anchor-Based Entity Isolation
## Description
Use unique identifiers from the prompt as retrieval anchors to pinpoint the exact location of the target answer within dense text.
## Content
Decompose the question into distinctive keywords (e.g., specific years, population figures, event names). Scan the context for these anchors to isolate the relevant passage. Once located, extract the missing entity based on its grammatical relationship to the anchor phrases, ignoring surrounding narrative details that do not affect the core fact.

# Success Memory Item 3
## Title
Format-Aware Answer Extraction
## Description
Recognize common source layouts where statements and answers are paired sequentially, allowing for immediate identification of the target response.
## Content
Many reference texts follow predictable patterns such as "[Statement], [Answer]" or "Q: [Prompt] A: [Response]". When the context exhibits this structure, map the prompt's incomplete statement to the corresponding completion. Ensure the extracted term logically completes the prompt's statement before formatting the final output.
