# Success Memory Item 1
## Title
Direct Extraction from Structured Context
## Description
Prioritize isolating the explicit answer when retrieved text mirrors the prompt's phrasing or follows a known Q&A/clue format.
## Content
Scan search results for verbatim matches of distinctive query phrases. When a snippet presents a direct question-answer pair, category-label format, or structured metadata, immediately extract the corresponding value without performing additional logical inference or cross-document synthesis.

# Success Memory Item 2
## Title
High-Specificity Phrase Alignment
## Description
Use unique, low-frequency wording from the prompt to rapidly filter and validate the correct information source.
## Content
Identify uncommon nouns, proper names, dates, or idiomatic actions in the query. Map these exact tokens to the retrieved context to confirm entity identity. This minimizes hallucination and prevents confusion between similarly named subjects or unrelated topics in multi-document retrieval.

# Success Memory Item 3
## Title
Constraint-First Output Formatting
## Description
Apply strict structural requirements to the final response immediately after answer determination.
## Content
Once the target answer is identified, bypass explanatory text or step-by-step reasoning in the output block. Wrap the result exclusively in the mandated tags and ensure zero conversational filler. This guarantees compliance with automated evaluation metrics that penalize extra characters or missing delimiters.
