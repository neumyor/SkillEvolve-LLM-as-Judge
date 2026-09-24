# Success Memory Item 1
## Title
Decompose Descriptive Queries into Factual Constraints
## Description
Break down complex or trivia-style prompts into distinct, isolatable attributes to create a clear matching checklist for document scanning.
## Content
Parse the question to extract key identifiers such as nationality, title, specific actions, and associated events. Use these isolated constraints as sequential filters when reviewing retrieved context to rapidly narrow down potential candidates.

# Success Memory Item 2
## Title
Cross-Document Attribute Alignment
## Description
Confirm that a candidate entity satisfies all extracted constraints by synthesizing information across multiple retrieved snippets rather than relying on a single source.
## Content
When initial keyword matches appear, scan additional context blocks to ensure all defining characteristics (e.g., military role, organizational command, and location of death) consistently point to the same individual. This multi-source alignment minimizes ambiguity and prevents premature selection.

# Success Memory Item 3
## Title
Strict Targeted Formatting
## Description
Isolate the final identified entity and place it directly inside the specified structural tags, omitting supplementary explanations or alternative naming conventions.
## Content
Once the correct entity is confirmed through constraint matching, extract only the primary identifier. Enclose it precisely within the required `<answer>...</answer>` tags to satisfy evaluation parsers and maintain output conciseness.
