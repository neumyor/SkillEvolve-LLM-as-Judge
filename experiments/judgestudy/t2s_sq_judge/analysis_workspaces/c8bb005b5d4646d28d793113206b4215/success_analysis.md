# Success Memory Item 1
## Title
Exact String Fragment Matching
## Description
Locate the incomplete phrase verbatim in the context to extract the immediate continuation.
## Content
When answering quote-completion questions, search the retrieved documents for the exact starting substring. Identify the next word(s) that directly follow it in the source text, relying on literal string overlap rather than semantic guessing.

# Success Memory Item 2
## Title
Prompt Noise Isolation
## Description
Filter out trailing ambiguities or typos in the prompt to focus strictly on the completion target.
## Content
If a prompt ends with awkward phrasing, stray words, or unclear syntax after a quotation, disregard the noise. Treat the input as a straightforward fill-in-the-blank task and extract only the missing lexical unit.

# Success Memory Item 3
## Title
Cross-Snippet Consensus
## Description
Validate the extracted completion by checking its presence across multiple independent context documents.
## Content
Before finalizing the answer, confirm that the completed phrase appears identically in at least two separate context snippets. This guards against extraction errors caused by truncated passages, formatting artifacts, or mismatched document boundaries.
