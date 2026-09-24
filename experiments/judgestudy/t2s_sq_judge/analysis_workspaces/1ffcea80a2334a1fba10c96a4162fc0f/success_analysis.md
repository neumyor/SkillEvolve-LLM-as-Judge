# Success Memory Item 1
## Title
Direct Extraction via Verbatim Keyword Alignment
## Description
When a prompt contains highly specific or unique phrasing, prioritize scanning retrieved context for exact string matches to instantly locate the target entity.
## Content
Map distinctive query terms directly to overlapping context snippets. Extract the associated subject immediately without additional inference, as verbatim alignment typically indicates a direct factual lookup.

# Success Memory Item 2
## Title
Strict Tag Enclosure Enforcement
## Description
Upon extracting the answer, immediately wrap it in the required XML-style tags, omitting all conversational filler, reasoning traces, or supplementary text.
## Content
Validate the output structure against the requested format before submission. Ensure only the raw answer string exists within the tags to maximize exact match scoring and maintain parser compatibility.

# Success Memory Item 3
## Title
Convergence-Based Confidence Acceleration
## Description
Treat consistent repetition of the same answer across multiple retrieved documents as high-confidence evidence, eliminating the need for cross-document reconciliation.
## Content
When search results repeatedly cite the same entity using identical terminology, accept it as definitive. Skip comparative analysis or ambiguity checks to reduce processing overhead and accelerate response generation.
