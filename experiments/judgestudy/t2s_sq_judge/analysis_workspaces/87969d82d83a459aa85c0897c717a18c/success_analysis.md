# Success Memory Item 1
## Title
Prioritize Verbatim Context Matches for Trivia Queries
## Description
When a question closely mirrors a known prompt or dataset entry within the retrieved context, treat it as a direct lookup rather than a synthesis task.
## Content
Scan all documents for exact or near-exact phrasing overlaps. If a match is found (e.g., in quiz archives, reference lists, or structured Q&A files), extract the corresponding answer field immediately. Rely on the matched snippet as the primary signal, bypassing unnecessary cross-document aggregation.

# Success Memory Item 2
## Title
Cross-Check Entity Attributes Against Independent Snippets
## Description
Confirm extracted answers by aligning key descriptors from the question with supporting details across separate context passages.
## Content
After identifying a candidate answer, quickly scan unrelated snippets for matching metadata (e.g., dates, professions, physical traits, or related names). Consistent attribute alignment across multiple sources confirms accuracy and filters out ambiguous or mismatched results before finalizing.

# Success Memory Item 3
## Title
Isolate Final Output Within Specified Delimiters
## Description
Encapsulate the resolved answer strictly within the required formatting tags, excluding all reasoning or conversational text from the final payload.
## Content
Once the answer is determined, place it directly inside the mandated tags. Maintain a clean, tag-only structure to satisfy automated evaluation parsers and prevent token waste or formatting failures.
