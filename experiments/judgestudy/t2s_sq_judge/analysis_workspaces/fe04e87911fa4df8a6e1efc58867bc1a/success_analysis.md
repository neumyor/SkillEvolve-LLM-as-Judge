# Success Memory Item 1
## Title
Keyword-Driven Context Isolation
## Description
Systematically scan retrieved passages for overlapping query terms to isolate the single most relevant context block while discarding tangential matches.
## Content
When processing multi-document retrieval, prioritize snippets that simultaneously contain the core subject, action, and distinctive phrasing from the prompt. Ignore documents that share only peripheral keywords but lack the specific contextual link required to answer the question.

# Success Memory Item 2
## Title
Anchor-Based Entity Extraction
## Description
Locate the exact claim or quote in the filtered context and extract the immediately associated proper noun or subject as the answer.
## Content
Once the relevant passage is identified, treat the distinctive phrase or definition as an anchor. Extract the named entity directly tied to it that fulfills the role specified in the question, relying solely on explicit textual evidence rather than external inference.

# Success Memory Item 3
## Title
Constraint-Aligned Output Formatting
## Description
Structure the final response to strictly meet formatting requirements while maintaining concise, direct factual statements.
## Content
After extraction, bypass verbose explanations or restatements of the prompt. Place only the verified entity or short phrase inside the designated tags, ensuring strict compliance with length and structural constraints without sacrificing accuracy.
