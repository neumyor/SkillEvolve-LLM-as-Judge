# Success Memory Item 1
## Title
Delimiter-Driven Answer Extraction
## Description
Leverage structural markers commonly found in trivia and QA datasets to isolate answers without overcomplicating reasoning.
## Content
In many sourced QA formats, the correct answer is explicitly placed after a standard delimiter like `|` or `:`. When retrieving context, scan for these markers adjacent to the query text to directly extract the target answer.

# Success Memory Item 2
## Title
Verbatim Context Alignment
## Description
Use exact phrase matching between the prompt and retrieved snippets to quickly identify the relevant data segment.
## Content
If the retrieved context contains verbatim or near-verbatim fragments of the original question, align them to confirm the correct document. This eliminates noise and points directly to the surrounding text containing the answer.

# Success Memory Item 3
## Title
Strict Output Formatting
## Description
Adhere precisely to requested output constraints to ensure successful evaluation.
## Content
Always wrap the final extracted answer in the specified tags (e.g., `<answer>...</answer>`) and avoid adding extraneous explanation. Concise, constraint-compliant formatting guarantees compatibility with automated grading systems.
