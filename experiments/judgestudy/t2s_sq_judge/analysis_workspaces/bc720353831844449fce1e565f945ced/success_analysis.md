# Success Memory Item 1
## Title
Prioritize Verbatim Context Matches
## Description
For trivia and factoid queries, treat exact phrasing overlaps between the prompt and retrieved documents as primary anchors for identifying the target entity.
## Content
Scan all context passages for sentences that mirror the question's wording. When a match is found (especially in quiz-style or reference sources), use it as the starting point to extract the likely answer, bypassing broader semantic searches.

# Success Memory Item 2
## Title
Corroborate via Unique Metric Alignment
## Description
Strengthen the initial hypothesis by locating independent context snippets that explicitly pair the question's specific numerical or structural constraints with the candidate answer.
## Content
After identifying a potential entity from an exact match, search remaining documents for secondary mentions that connect the target's defining attributes (e.g., total distance, duration, or component breakdown) to that same term. Use this internal consistency to finalize the selection.

# Success Memory Item 3
## Title
Isolate Core Entity and Enforce Output Syntax
## Description
Strip contextual framing to return only the precise noun or phrase requested, immediately applying the required formatting delimiters.
## Content
Once the correct term is confirmed, remove surrounding explanations, dates, or qualifiers. Output only the clean answer string wrapped in the specified tags, avoiding any additional derivation steps or conversational filler in the final response.
