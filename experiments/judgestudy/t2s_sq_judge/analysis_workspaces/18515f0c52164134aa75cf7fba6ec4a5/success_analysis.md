# Success Memory Item 1
## Title
Direct Entity Pair Extraction from Context
## Description
Locate explicit co-occurrences of known and target entities within retrieved snippets to resolve identification or completion queries.
## Content
Scan the context for exact matches of prompt keywords (dates, treaties, known locations). Identify the missing element by reading the immediate syntactic neighbors that link the known and unknown entities. Prioritize statements that directly assert the relationship over indirect or tangential mentions.

# Success Memory Item 2
## Title
Multi-Snippet Convergence Validation
## Description
Cross-check multiple independent documents to confirm that the extracted entity consistently appears in the same relational context.
## Content
When several retrieved passages independently reference the same entity pairing or event resolution, treat this repetition as strong signal. Ignore isolated or ambiguous references that lack consistent contextual support. This reduces noise and anchors the answer in repeated corpus evidence.

# Success Memory Item 3
## Title
Strict Schema Enforcement for Final Output
## Description
Isolate the minimal valid answer string and immediately wrap it in the required formatting tags, excluding all reasoning or supplementary text.
## Content
After identifying the correct entity, strip away descriptive modifiers, full sentences, or alternative names. Output only the precise term requested. Apply the mandated tag structure exactly as specified to ensure compliance and machine-readability.
