# Success Memory Item 1
## Title
Verbatim Phrase Anchoring
## Description
Locate the exact or near-exact wording of the prompt's clue within the retrieved context to isolate the relevant passage.
## Content
Trivia-style or quoted prompts often appear verbatim in source documents. Scanning for these distinctive strings immediately narrows the search space to the correct paragraph, eliminating noise from unrelated results and providing a direct anchor for answer extraction.

# Success Memory Item 2
## Title
Attribute-to-Subject Mapping
## Description
Connect descriptive keywords from the clue to the target entity using explicit contextual definitions or metadata.
## Content
When a prompt describes a concept indirectly (e.g., referencing a figure, role, or function), identify the subject explicitly paired with those descriptors in the same context window. Document titles, headers, or adjacent sentences often provide the direct link needed to resolve the reference without external knowledge.

# Success Memory Item 3
## Title
Direct Entity Extraction
## Description
Isolate and return only the precise noun or term requested by the clue, avoiding unnecessary elaboration.
## Content
Once the contextual link is established, extract the single target word or phrase that completes the clue. Maintain strict adherence to the requested output format, prioritizing conciseness and exact match over explanatory text to satisfy automated evaluation criteria.
