# Success Memory Item 1
## Title
Anchor Answers on Verbatim Matches in Archival or Quiz Databases
## Description
When prompts contain highly specific, stylized, or quiz-like phrasing, treat exact string overlaps in retrieved documents as primary anchors for entity identification.
## Content
Prioritize scanning contexts for verbatim matches, particularly in trivia archives, database dumps, or structured Q&A repositories. Once a matching passage is located, extract the associated subject directly from that text. Use the exact match as the foundational hypothesis rather than relying solely on semantic similarity, as quiz-style queries often preserve original source wording.

# Success Memory Item 2
## Title
Triangulate Entities Through Consistent Attribute Mapping
## Description
Validate a candidate entity by cross-referencing its alignment with multiple independent descriptors provided in the prompt across different retrieved sources.
## Content
Decompose the query into distinct factual claims (e.g., geographic location, industry role, specific innovation). Systematically check whether the candidate entity satisfies each claim across separate documents. Finalize the answer only when multiple independent passages consistently corroborate the same subject, ensuring robustness against ambiguous names or overlapping historical figures.
