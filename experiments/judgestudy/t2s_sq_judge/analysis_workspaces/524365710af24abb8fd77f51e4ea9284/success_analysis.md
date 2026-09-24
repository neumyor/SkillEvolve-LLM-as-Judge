# Success Memory Item 1
## Title
Verbatim Query Anchoring
## Description
Use exact phrasing matches from the prompt to locate the answer within retrieved documents.
## Content
Scan all context passages for strings that precisely mirror the user's question. Treat the matched segment as a direct anchor point, then extract the corresponding answer typically positioned immediately adjacent to it.

# Success Memory Item 2
## Title
Delimiter-Driven Information Isolation
## Description
Leverage consistent structural markers in source data to cleanly separate questions from answers.
## Content
Identify recurring formatting conventions such as pipe symbols, colons, or section headers. Use these delimiters to parse out the target value without processing surrounding narrative or metadata, ensuring high extraction accuracy.

# Success Memory Item 3
## Title
Constraint-Strict Output Rendering
## Description
Apply requested formatting tags precisely while suppressing all non-essential text.
## Content
Enclose only the final extracted answer within the specified markup tags. Exclude reasoning traces, conversational phrases, or self-check statements from the final output to guarantee compliance and maximize signal-to-noise ratio.
