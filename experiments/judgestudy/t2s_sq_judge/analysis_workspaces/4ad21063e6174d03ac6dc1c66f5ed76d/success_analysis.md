# Success Memory Item 1
## Title
Exact-Phrase Matching for Trivia & Quiz-Style Queries
## Description
When processing highly specific factual questions or trivia prompts, prioritize scanning retrieved context for exact keyword, date, or phrase overlaps. Retrieval often surfaces structured Q&A, Jeopardy-style clues, or FAQ entries where the answer is explicitly paired with the query text. Extracting directly from these matched segments yields high precision and minimizes hallucination risk.
## Content
1. Isolate unique identifiers in the prompt (specific dates, rare phrases, numerical values, or proper nouns).
2. Scan all retrieved passages for exact string matches containing those identifiers.
3. Locate the explicit answer pair within the same sentence or paragraph block.
4. Cross-check adjacent sentences in the matching passage to confirm contextual alignment before extraction.
