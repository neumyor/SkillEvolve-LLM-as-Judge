# Success Memory Item 1
## Title
Verbatim Clue Matching for Trivia Queries
## Description
Recognize quiz-style or riddle-like prompts and prioritize context snippets containing identical phrasing, as they typically contain the direct answer.
## Content
When the question mirrors a known trivia format, scan retrieved documents for exact phrase matches. Extract the entity immediately preceding or following the matched phrase, as contextual clues in trivia sources are usually self-contained and definitive.

# Success Memory Item 2
## Title
Co-Occurring Entity Filtering
## Description
Use multiple specific identifiers from the prompt to narrow down context snippets, isolating the target attribute linked to those exact items.
## Content
Extract distinct named entities from the question (e.g., paired book titles). Search the context for passages that explicitly mention both identifiers together. The correct answer is almost always the single associated entity (e.g., author) presented within that same snippet.

# Success Memory Item 3
## Title
Constraint-First Output Formatting
## Description
Separate internal reasoning from the final response to guarantee strict compliance with required output wrappers.
## Content
After deriving the answer through context analysis, strip all explanatory text, citations, and conversational filler. Place only the final extracted value between the specified tags (e.g., `<answer>Value</answer>`) to prevent parsing failures and meet evaluation criteria.
