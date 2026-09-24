# Success Memory Item 1
## Title
Exact Phrase Matching for Clue-Based Queries
## Description
Leverage highly specific or distinctive wording in the prompt to locate direct matches in retrieved documents, particularly in quiz, flashcard, or trivia-style datasets.
## Content
When a question contains unique identifiers or niche phrasing, prioritize scanning context for verbatim or near-verbatim matches. Structured knowledge sources frequently embed prompts and solutions in close proximity, enabling rapid identification without requiring multi-step reasoning or external knowledge.

# Success Memory Item 2
## Title
Proximity-Based Answer Extraction
## Description
Identify correct answers by locating where the prompt's core premise and its corresponding solution appear together within the same paragraph or data entry.
## Content
Focus on documents where the query's key details and the target answer are co-located. This pattern is common in reference materials, historical summaries, and database exports, allowing for direct extraction rather than complex synthesis or cross-document aggregation.

# Success Memory Item 3
## Title
Constraint-First Output Formatting
## Description
Enforce strict adherence to requested output structures immediately upon isolating the answer to prevent parsing failures.
## Content
Once the answer is identified, apply the required delimiters or tags exactly as specified. Omit explanatory text, conversational filler, or intermediate steps in the final output to ensure seamless machine parsing and maximize evaluation metric alignment.
