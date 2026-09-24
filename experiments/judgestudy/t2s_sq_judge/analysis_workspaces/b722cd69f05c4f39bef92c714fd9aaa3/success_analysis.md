# Success Memory Item 1
## Title
Exact-Phrase Matching for Trivia & Clue Prompts
## Description
Leverage verbatim overlap between the prompt and retrieved documents to quickly locate direct question-answer pairs.
## Content
Scan retrieved snippets for exact keyword or phrase alignment rather than relying solely on semantic similarity. When a prompt mirrors a known clue structure, prioritize documents labeled as datasets, quizzes, or archives, as they frequently store the exact answer adjacent to the clue.

# Success Memory Item 2
## Title
Source-Type Prioritization for Structured Data
## Description
Filter retrieved context by document type and metadata to isolate structured Q&A sources over narrative or informational texts.
## Content
Disregard contextual noise like news articles, forecasts, or product descriptions when the query targets a specific factual or entertainment reference. Focus extraction efforts on files with titles indicating repositories, databases, or curated lists, where clues and answers are typically paired in a predictable format.

# Success Memory Item 3
## Title
Strict Output Formatting Enforcement
## Description
Validate the final response against explicit formatting instructions before submission to prevent structural failures.
## Content
After extracting the target information, immediately map it to the requested tag structure. Remove any internal reasoning, conversational fillers, or alternative phrasing to ensure the output strictly complies with parsing requirements and avoids token waste or rejection.
