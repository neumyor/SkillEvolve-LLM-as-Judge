# Success Memory Item 1
## Title
Direct Lexical Alignment for Trivial Fact Retrieval
## Description
Identify and exploit near-exact phrasing overlaps between the query and retrieved context to instantly resolve trivia or factoid questions.
## Content
When processing trivia-style prompts, scan the context for sentences that mirror the question's structure or vocabulary. If a document presents a recognizable clue pattern (e.g., "[Clue description], [Target Entity]"), extract the entity directly. Prioritize this textual match over complex reasoning, verify it aligns with the prompt's semantic intent, and output the result using the specified formatting constraints.
