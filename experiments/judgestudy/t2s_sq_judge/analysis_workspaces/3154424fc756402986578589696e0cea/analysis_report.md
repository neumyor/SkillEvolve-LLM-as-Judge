# Failure Cause Item 1
## Title
Span-boundary error: full name vs. surname-only answer in Jeopardy-format questions
## Description
The agent correctly identified the entity (Jean Genet) but selected the full name "Jean Genet" instead of the surname-only "Genet" that the context explicitly supports.
## Content
Two retrieved passages directly mirror the Jeopardy-style question format and use just "Genet" as the answer: the jeopardy/14_Qs.txt passage ends with `| Genet.` and the StudyStack flashcard states `... OF "THE MAIDS", GENET.` The agent cited these passages in its reasoning but still committed to "Jean Genet" as the final answer span, likely influenced by Wikipedia passages that use the full name. This is a span-boundary problem — the entity is correct, but the agent included the first name when the context-supported answer for this question format is just the surname. The F1 score of 0.667 confirms partial overlap while EM=0 confirms no exact match.

# Failure Memory Item 1
## Title
Prefer answer spans that match the question's source format
## Description
When a question mirrors a known format (Jeopardy clues, quiz cards, etc.), look for passages that share that same format — they typically contain the expected answer span.
## Content
Jeopardy-style questions and flashcard passages often present answers in a specific canonical form (e.g., surname-only). If multiple passages exist, prioritize those whose structure matches the question's origin format, as they are more likely to reflect the expected answer span rather than encyclopedic descriptions that may use full names or additional qualifiers.

# Failure Memory Item 2
## Title
Distinguish entity errors from span-boundary errors
## Description
A near-miss where the answer overlaps the right entity but differs in length or formatting is usually a span-selection problem, not a retrieval or entity-identification failure.
## Content
When diagnosing failures, check whether the agent identified the correct entity but chose the wrong text span. Metrics like F1 > 0 but EM = 0 indicate partial overlap — the agent found the right information but extracted too much or too little. The fix is adjusting the answer span boundaries, not changing the underlying entity identification. This distinction matters because the root cause and corrective action differ significantly between the two types of errors.

ACTION: TASK_COMPLETE
