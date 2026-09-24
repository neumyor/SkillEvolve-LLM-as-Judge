# Success Memory Item 1
## Title
Anchor-Based Entity Resolution
## Description
Map partial or descriptive prompts to concrete entities using explicit contextual markers like dates, locations, and historical events.
## Content
When a question provides specific temporal, spatial, or factual anchors (e.g., "1795 in Chapel Hill"), scan the retrieved context to locate the corresponding subject. Once the primary entity is identified, pivot directly to extracting the specific attribute requested by the prompt.

# Success Memory Item 2
## Title
Multi-Snippet Consistency Check
## Description
Confirm the identified entity and target answer by ensuring alignment across multiple independent context documents.
## Content
Cross-reference overlapping details from different sources to solidify the subject's identity and the accuracy of the extracted fact. Prioritize answers that are consistently supported across the retrieved evidence set to minimize extraction errors.

# Success Memory Item 3
## Title
Strict Delimiter Formatting
## Description
Isolate the final answer string and enclose it exclusively within the required output tags, stripping all intermediate reasoning or conversational text.
## Content
After deriving the correct value, immediately apply the specified output template (e.g., `<answer>...</answer>`). Omit step-by-step logic, self-checks, or supplementary explanations to guarantee strict compliance with automated parsing and evaluation criteria.
