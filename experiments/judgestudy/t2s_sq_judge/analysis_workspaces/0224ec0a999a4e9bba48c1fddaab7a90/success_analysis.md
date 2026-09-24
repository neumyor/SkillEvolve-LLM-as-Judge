# Success Memory Item 1
## Title
Leverage Structural Delimiters for Direct Trivia Extraction
## Description
Identify and exploit standardized separators (e.g., pipes, colons) in retrieved trivia or dataset contexts to isolate answers without generative inference.
## Content
When processing quiz-style or Jeopardy-format questions, scan retrieved documents for explicit delimiter characters that separate the prompt from the target response. Extract the exact string immediately following these markers. This approach prioritizes precision by treating structured datasets as lookup tables rather than requiring semantic reasoning, significantly reducing hallucination risk for factual entity queries.
