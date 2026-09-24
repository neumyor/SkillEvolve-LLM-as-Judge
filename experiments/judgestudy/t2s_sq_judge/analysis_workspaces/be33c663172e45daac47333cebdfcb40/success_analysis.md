# Success Memory Item 1
## Title
Direct Text Matching for Trivia and Reference Queries
## Description
Identify and extract answers by locating exact phrasing or explicit Q&A structures within retrieved documents, particularly when questions mimic quiz or encyclopedia formats.
## Content
Scan context for sentences that directly mirror the question's syntax or contain explicit answer indicators. Prioritize verbatim matches from reference-style sources over inferential reasoning when available.

# Success Memory Item 2
## Title
Cross-Entity Consistency Confirmation
## Description
Confirm that an extracted answer logically applies to all named entities across their respective domains or historical periods before finalizing.
## Content
After identifying a candidate answer, briefly confirm its applicability to each subject mentioned in the prompt. This prevents selection errors when terms have multiple meanings or when context snippets are fragmented.

# Success Memory Item 3
## Title
Constraint-First Output Generation
## Description
Structure the final response strictly according to requested formatting rules, omitting explanatory text to align with automated evaluation standards.
## Content
Reserve detailed reasoning for internal processing steps. Output only the required tagged answer in the specified format, ensuring compliance with length and structural constraints to maximize scoring potential.
