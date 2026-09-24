# Success Memory Item 1
## Title
Trivia Clue Pattern Recognition
## Description
Identify when prompts use trivia or Jeopardy-style phrasing, which frequently appear verbatim or near-verbatim in search results.
## Content
Scan retrieved documents for exact or near-exact phrase matches to the prompt. When a match is found, treat the surrounding sentence as a direct answer source rather than attempting complex multi-hop reasoning or external knowledge retrieval.

# Success Memory Item 2
## Title
Constraint-to-Entity Mapping
## Description
Use specific temporal or structural markers in the prompt to isolate the correct entity within the context.
## Content
Cross-reference key details (e.g., founding year, leadership appointment date) against explicit statements in the text. The valid answer will consistently satisfy all stated constraints within a single factual record, allowing for rapid elimination of distractor documents.

# Success Memory Item 3
## Title
Direct Noun Phrase Extraction
## Description
Once the constrained entity is located, extract the precise name without modification, inference, or paraphrasing.
## Content
Isolate the exact proper noun or organizational title corresponding to the matched constraints. Output the term exactly as it appears in the source material, strictly adhering to the required formatting tags to ensure compliance.
