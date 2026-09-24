# Success Memory Item 1
## Title
Extract Answers from Embedded Q&A Contexts
## Description
Identify and retrieve the target term when trivia or proverb prompts appear within conversational or quiz-style document snippets that already contain the resolution.
## Content
When a query matches an incomplete quote or trivia prompt found in the retrieved context, scan the surrounding text for the immediate completion. Forum posts, quiz discussions, and trivia archives frequently embed the answer directly after the prompt. Extract the adjacent term as the final response without requiring additional verification steps.

# Success Memory Item 2
## Title
Leverage Exact Phrase Alignment for Completion Tasks
## Description
Use exact string matching of the query against context snippets to locate the corresponding answer segment within the same document block.
## Content
For proverb or quote completion questions, prioritize contexts containing the exact opening phrase. Once located, examine the remainder of the snippet for the completing word or phrase. This approach capitalizes on how knowledge bases and user-generated content naturally pair prompts with their resolutions, enabling direct extraction.

# Success Memory Item 3
## Title
Recognize Structured Trivia Formatting Patterns
## Description
Adapt to common formatting conventions in trivia databases where questions and answers are presented sequentially or as direct replies.
## Content
Many retrieved sources follow predictable layouts for trivia content, such as placing the answer immediately after the question, using capitalization for emphasis, or framing it as a direct response in a thread. Identify these structural cues to isolate the target term efficiently, treating the context as a self-contained lookup table rather than a narrative passage.
