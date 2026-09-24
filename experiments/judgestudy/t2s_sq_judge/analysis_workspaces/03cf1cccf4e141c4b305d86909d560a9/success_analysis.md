# Success Memory Item 1
## Title
Entity-Centric Context Tracing
## Description
Isolate the key named entity or reference in the prompt and use retrieved context to trace its direct associations with potential answer candidates.
## Content
When processing reference-based or trivia questions, extract the central proper noun, character, or phrase. Scan the retrieved documents specifically for co-occurrences or explicit links between this entity and candidate titles/sources. Prioritize matches found in document titles, headers, or summary snippets, as these typically indicate the definitive answer without requiring external knowledge or complex inference.

# Success Memory Item 2
## Title
Metadata-Driven Answer Confirmation
## Description
Leverage structural cues in retrieved context to validate the connection between a query reference and its source, bypassing unnecessary interpretive steps.
## Content
For questions containing partial quotes, cultural allusions, or descriptive clues, treat them as direct pointers rather than puzzles to be solved analytically. Verify the pointer by checking if the retrieved context explicitly pairs the reference with a specific work or author in its metadata. If multiple documents consistently link the reference to the same title, accept it as the answer and format it concisely per instructions.
