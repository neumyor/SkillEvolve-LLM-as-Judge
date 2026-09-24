# Success Memory Item 1
## Title
Verbatim Context Matching
## Description
Locate the exact question phrasing within the retrieved documents to pinpoint the answer location.
## Content
Search the context for strings that match the prompt word-for-word. Once found, treat the immediately adjacent text as the direct source for the answer, bypassing unnecessary inference when an explicit textual match exists.

# Success Memory Item 2
## Title
Parse Delimited Q&A Pairs
## Description
Recognize and extract answers from structured snippets where questions and responses are separated by symbols or whitespace.
## Content
Many retrieved paragraphs use delimiters like pipes (`|`), colons, or line breaks to separate clues from solutions. Identify these structural markers to isolate the correct response component without processing extraneous surrounding text.

# Success Memory Item 3
## Title
Immediate Tag Application
## Description
Apply the required output formatting directly to the extracted answer to ensure strict compliance.
## Content
Upon extracting the target phrase, immediately wrap it in the specified tags (e.g., `<answer>...</answer>`). Avoid adding conversational filler or post-extraction validation steps to maintain precision and meet automated evaluation standards.
