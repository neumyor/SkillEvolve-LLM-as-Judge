# Success Memory Item 1
## Title
Verbatim Context Matching
## Description
Prioritize locating exact or near-exact phrase overlaps between the prompt and retrieved documents to quickly identify the authoritative source for trivia or factual queries.
## Content
Scan snippets for identical question phrasing. When a direct match is found, treat that document as the sole reference point rather than synthesizing across multiple unrelated results.

# Success Memory Item 2
## Title
Structural Delimiter Extraction
## Description
Recognize and leverage dataset-specific formatting patterns, such as pipe symbols or colons, to cleanly separate questions from their corresponding answers.
## Content
Identify the standard separator used in the source material. Extract only the text segment immediately following this marker to isolate the precise answer string without surrounding noise.

# Success Memory Item 3
## Title
Exact String Preservation & Tagging
## Description
Maintain the exact wording from the source when formatting the final output, applying required containers without modification or conversational filler.
## Content
Copy the isolated answer verbatim. Wrap it strictly in the specified tags. Omit explanations, alternatives, or introductory text to align with automated evaluation standards.
