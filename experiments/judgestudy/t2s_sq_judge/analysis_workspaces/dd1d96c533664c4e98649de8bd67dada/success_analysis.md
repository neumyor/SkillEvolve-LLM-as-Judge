# Success Memory Item 1
## Title
Direct Span Extraction via Keyword Alignment
## Description
Locate the answer by matching the question's core entities and modifiers against explicit statements in the retrieved context.
## Content
Scan documents for sentences containing the query's key terms (dates, actors, subjects). Extract the exact noun phrase directly linked to those terms, prioritizing verbatim matches over inferred connections.

# Success Memory Item 2
## Title
Terminology Correlation Across Sources
## Description
Resolve naming variations by identifying synonymous or related terms used in different retrieved documents.
## Content
When multiple sources reference the same event or entity using different labels, map them to a single concept using contextual cues or standard equivalences. This confirms the target entity before extraction.

# Success Memory Item 3
## Title
Constraint-Driven Output Formatting
## Description
Deliver the final answer strictly according to structural instructions, omitting all explanatory text.
## Content
Isolate the identified answer span and remove any surrounding context, reasoning, or filler. Enclose only the concise answer within the specified tags to meet evaluation criteria.
