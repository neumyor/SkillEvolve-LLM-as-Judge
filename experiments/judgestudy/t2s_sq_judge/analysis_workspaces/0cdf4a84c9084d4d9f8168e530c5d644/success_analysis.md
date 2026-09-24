# Success Memory Item 1
## Title
Direct Contextual Entity Lookup
## Description
Locate the target answer by scanning retrieved documents for explicit mentions that pair the question's specific markers with the desired attribute.
## Content
When prompts provide precise identifiers (e.g., county names, adjacent landmarks, dates), search the context for exact textual matches linking those identifiers to the target field. Prioritize direct extraction over inference when the context explicitly states the relationship.

# Success Memory Item 2
## Title
Multi-Constraint Alignment
## Description
Validate the extracted answer by ensuring it simultaneously satisfies all distinct clues provided in the prompt.
## Content
Cross-check every condition mentioned in the question against the retrieved snippets. Confirm that a single source or consistent set of sources fulfills all geographic, temporal, or relational constraints before committing to the final value. Discard candidates that only partially match the prompt's requirements.

# Success Memory Item 3
## Strict Tag Isolation
## Description
Encapsulate the final determined value exclusively within the mandated response tags, excluding all supplementary text.
## Content
After resolving the query, immediately wrap the exact answer string in the specified delimiters (e.g., `<answer>...</answer>`). Do not append explanations, confidence scores, or conversational phrases outside the tags to maintain strict compliance and ensure clean parsing.
