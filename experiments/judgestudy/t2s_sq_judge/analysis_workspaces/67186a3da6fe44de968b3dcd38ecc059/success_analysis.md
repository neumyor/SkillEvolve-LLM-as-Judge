# Success Memory Item 1
## Title
Trivia-Style Query Pattern Recognition
## Description
Identify questions formatted as trivia clues or flashcard prompts, which typically expect a single definitive entity rather than open-ended analysis.
## Content
When a query reads like a quiz clue or study card, scan retrieved documents for educational archives, flashcard sets, or trivia logs. These sources are explicitly structured to pair the exact clue text with its corresponding answer, allowing direct extraction without additional reasoning.

# Success Memory Item 2
## Title
Verbatim Snippet Matching for Answer Extraction
## Description
Leverage exact phrasing overlaps between the question and context to locate pre-formatted Q&A lines where the answer is appended to the clue.
## Content
Treat distinctive question phrases as search anchors. If a context snippet repeats the query verbatim but continues with a proper noun, location, or term, extract that trailing entity as the answer. This bypasses complex parsing when the context already contains a solved instance of the prompt.

# Success Memory Item 3
## Title
Source Hierarchy for Direct-Pair Documents
## Description
Prioritize extraction from documents explicitly designed for rapid fact retrieval over narrative or analytical texts.
## Content
Assign higher weight to context fragments labeled as study aids, archives, or quick-reference lists. These formats inherently compress information into direct clue-to-answer mappings. Extract the paired term immediately following the matched clue, as these sources are optimized for precise, unambiguous responses.
